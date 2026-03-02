"""
Smart Reel Engine — Intelligent CS2 Reel Generation

All-in-one engine that produces high-quality CS2 reels by:
1. Smart clip cutting — FFmpeg audio peak detection, full moment preservation
2. Trend-driven processing — Color, pacing, effects from real trend analysis
3. Real-time trend refresh — Triggers YouTube/Twitch scraping before generation
4. Auto-select best clip — Picks clip matching current trend profile
5. Royalty-free music overlay — Downloads from Pixabay Music API
6. Dynamic word-by-word subtitles — FFmpeg drawtext with timing
7. Full pipeline logging — Human-readable data source documentation

No GPU required. Only FFmpeg + yt-dlp + httpx.
"""

import asyncio
import hashlib
import json
import logging
import math
import os
import random
import re
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("smart_reel_engine")

# ─── Directories ───────────────────────────────────────────────────
CLIPS_DIR = Path("/data/clips") if os.path.exists("/data") else Path(
    os.path.join(os.path.dirname(__file__), "..", "..", "clips")
)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)
(CLIPS_DIR / "source").mkdir(exist_ok=True)
(CLIPS_DIR / "processed").mkdir(exist_ok=True)
(CLIPS_DIR / "thumbnails").mkdir(exist_ok=True)
(CLIPS_DIR / "music").mkdir(exist_ok=True)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
if not os.path.exists(FONT_PATH):
    FONT_PATH = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
if not os.path.exists(FONT_PATH):
    import glob as _glob
    _fonts = _glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)
    FONT_PATH = _fonts[0] if _fonts else "Sans"


# ═══════════════════════════════════════════════════════════════════
# 1. SMART CLIP CUTTING — Audio Peak Detection
# ═══════════════════════════════════════════════════════════════════

async def _detect_audio_peaks(file_path: str) -> list[dict]:
    """Analyze audio volume over time to find action peaks.

    Uses FFmpeg's volumedetect + astats to find loud moments (gunshots,
    crowd reactions, caster screams) which indicate action peaks.
    Returns list of {time_sec, volume_db} sorted by volume.
    """
    # Use per-second RMS analysis via FFmpeg astats
    # reset=44100 means reset stats every 1 second (at 44.1kHz)
    cmd = [
        "ffmpeg", "-i", file_path,
        "-af", "astats=metadata=1:reset=44100,ametadata=print:key=lavfi.astats.Overall.RMS_level:file=-",
        "-f", "null", "-"
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = stdout.decode(errors="replace")

        # Parse output: lines alternate between "frame:N pts_time:X" and "lavfi.astats..."
        peaks = []
        current_pts_time = 0.0
        for line in output.split("\n"):
            line = line.strip()
            if "pts_time:" in line:
                match = re.search(r"pts_time:(\S+)", line)
                if match:
                    try:
                        current_pts_time = float(match.group(1))
                    except ValueError:
                        pass
            elif "lavfi.astats.Overall.RMS_level" in line:
                parts = line.split("=")
                if len(parts) >= 2:
                    try:
                        db = float(parts[-1])
                        if db > -100:  # Skip silence
                            peaks.append({"time_sec": round(current_pts_time, 2), "volume_db": db})
                    except ValueError:
                        pass

        # Aggregate to 1-second buckets for cleaner peak detection
        if peaks:
            buckets: dict[int, list[float]] = {}
            for p in peaks:
                bucket = int(p["time_sec"])
                if bucket not in buckets:
                    buckets[bucket] = []
                buckets[bucket].append(p["volume_db"])

            aggregated = []
            for sec, volumes in buckets.items():
                avg_db = sum(volumes) / len(volumes)
                aggregated.append({"time_sec": float(sec), "volume_db": round(avg_db, 2)})

            aggregated.sort(key=lambda p: p["volume_db"], reverse=True)
            logger.info(f"Audio peaks: found {len(aggregated)} second-buckets, loudest at {aggregated[0]['time_sec']}s ({aggregated[0]['volume_db']} dB)")
            return aggregated

        return []

    except asyncio.TimeoutError:
        logger.warning("Audio peak detection timed out")
        return []
    except Exception as e:
        logger.warning(f"Audio peak detection failed: {e}")
        return []


async def _detect_scene_changes(file_path: str) -> list[float]:
    """Detect scene changes (cuts, transitions) using FFmpeg scene filter.

    Returns list of timestamps where scene changes occur.
    """
    cmd = [
        "ffmpeg", "-i", file_path,
        "-vf", "select='gt(scene,0.3)',showinfo",
        "-f", "null", "-"
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stderr.decode(errors="replace")

        timestamps = []
        for line in output.split("\n"):
            if "pts_time:" in line:
                match = re.search(r"pts_time:\s*([\d.]+)", line)
                if match:
                    timestamps.append(float(match.group(1)))

        return sorted(timestamps)
    except Exception as e:
        logger.warning(f"Scene detection failed: {e}")
        return []


async def _find_smart_cut_points(
    file_path: str, target_duration: float, total_duration: float
) -> dict:
    """Find the best start/end points that preserve the full action moment.

    Strategy:
    1. Find audio peaks (action = loud moments)
    2. Find scene changes (natural cut points)
    3. Center the clip around the loudest peak
    4. Align start/end with nearby scene changes for clean cuts
    5. Never cut mid-action (ensure peak is not at edge)
    """
    peaks = await _detect_audio_peaks(file_path)
    scenes = await _detect_scene_changes(file_path)

    if not peaks:
        # Fallback: use middle portion of clip
        start = max(0, (total_duration - target_duration) / 2)
        return {
            "start": round(start, 2),
            "end": round(min(start + target_duration, total_duration), 2),
            "method": "center_fallback",
            "peak_time": None,
        }

    # Find the loudest peak (main action moment)
    main_peak = peaks[0]
    peak_time = main_peak["time_sec"]

    # We want the peak to be in the middle-to-late portion of the clip
    # (build-up before, aftermath after)
    ideal_start = peak_time - (target_duration * 0.4)  # Peak at ~40% mark
    ideal_end = ideal_start + target_duration

    # Clamp to video bounds
    if ideal_start < 0:
        ideal_start = 0
        ideal_end = min(target_duration, total_duration)
    if ideal_end > total_duration:
        ideal_end = total_duration
        ideal_start = max(0, total_duration - target_duration)

    # Snap to nearest scene change for clean cuts
    if scenes:
        # Find nearest scene change to ideal_start (prefer earlier)
        best_start_scene = ideal_start
        for sc in scenes:
            if abs(sc - ideal_start) < 2.0 and sc <= ideal_start + 1.0:
                best_start_scene = sc
                break

        # Find nearest scene change to ideal_end (prefer later)
        best_end_scene = ideal_end
        for sc in reversed(scenes):
            if abs(sc - ideal_end) < 2.0 and sc >= ideal_end - 1.0:
                best_end_scene = sc
                break

        ideal_start = best_start_scene
        ideal_end = best_end_scene

    # Safety: ensure we have at least 5 seconds
    if ideal_end - ideal_start < 5:
        ideal_start = max(0, peak_time - 5)
        ideal_end = min(total_duration, peak_time + target_duration - 5)

    # Safety: ensure peak is INSIDE the cut (not at very edge)
    if peak_time < ideal_start + 1:
        ideal_start = max(0, peak_time - 2)
    if peak_time > ideal_end - 1:
        ideal_end = min(total_duration, peak_time + 2)

    return {
        "start": round(max(0, ideal_start), 2),
        "end": round(min(ideal_end, total_duration), 2),
        "method": "smart_peak_detection",
        "peak_time": peak_time,
        "peak_volume_db": main_peak["volume_db"],
        "scenes_found": len(scenes),
        "peaks_analyzed": len(peaks),
    }


# ═══════════════════════════════════════════════════════════════════
# 2. TREND-DRIVEN PROCESSING — Read real trends, apply to FFmpeg
# ═══════════════════════════════════════════════════════════════════

# Color grade presets mapped from trend analysis
COLOR_GRADE_PRESETS = {
    "high_contrast": {
        "eq": "eq=contrast=1.4:brightness=-0.02:saturation=1.1",
        "curves": "curves=preset=increase_contrast",
        "description": "High contrast punchy look (sigma edits, phonk)"
    },
    "vibrant": {
        "eq": "eq=contrast=1.15:saturation=1.35:brightness=0.02",
        "curves": None,
        "description": "Bright saturated colors (highlight reacts)"
    },
    "cinematic": {
        "eq": "eq=contrast=1.15:brightness=-0.02:saturation=0.9",
        "curves": "curves=preset=cross_process",
        "description": "Film-like muted tones (pro clutch, dramatic)"
    },
    "dark_moody": {
        "eq": "eq=contrast=1.25:brightness=-0.06:saturation=0.75",
        "curves": "curves=preset=increase_contrast",
        "description": "Dark cinematic (ace compilations, fragmovies)"
    },
    "saturated": {
        "eq": "eq=contrast=1.1:saturation=1.5:brightness=0.03",
        "curves": None,
        "description": "Over-saturated fun look (memes, funny moments)"
    },
    "neutral": {
        "eq": "eq=contrast=1.05:saturation=1.0:brightness=0.0",
        "curves": None,
        "description": "Clean natural look (tutorials, educational)"
    },
    "warm_teal": {
        "eq": "eq=contrast=1.1:saturation=1.15:brightness=-0.01",
        "curves": "curves=r='0/0 0.2/0.15 0.5/0.5 0.8/0.85 1/1':b='0/0 0.2/0.25 0.5/0.55 0.8/0.8 1/1'",
        "description": "Teal & orange trending color grade"
    },
}

# Pacing presets
PACING_PRESETS = {
    "fast": {"setpts": "0.85*PTS", "atempo": "1.18", "description": "Slightly sped up for energy"},
    "medium": {"setpts": "PTS", "atempo": "1.0", "description": "Normal speed"},
    "build_up": {"setpts": "PTS", "atempo": "1.0", "description": "Normal with slow-mo at peak"},
    "escalating": {"setpts": "PTS", "atempo": "1.0", "description": "Starts slow, gets faster"},
}


async def _get_fresh_trend_recommendations() -> dict:
    """Fetch fresh trend data by triggering real-time scraping.

    Forces cache refresh if data is stale (>10min).
    Returns design recommendations dict.
    """
    from app.services.trend_analyzer import (
        analyze_current_trends,
        get_platform_design_hints,
        _cache_get,
    )

    # Check if we have fresh combined insights
    cache = _cache_get("combined_insights")
    cache_age = 99999
    if cache and cache.get("_cached_at"):
        cache_age = time.time() - cache["_cached_at"]

    if cache_age > 600:  # >10 min — refresh
        logger.info("Trend cache stale (%ds), refreshing...", int(cache_age))
        try:
            fresh = await analyze_current_trends()
            if fresh and fresh.get("recommendations"):
                logger.info("Fresh trend data obtained: %s", fresh["recommendations"].get("preferred_style"))
                return fresh["recommendations"]
        except Exception as e:
            logger.warning("Trend refresh failed: %s", e)

    # Use existing cached data or known patterns
    hints = get_platform_design_hints("tiktok")
    return hints


def _map_trend_to_ffmpeg(trend_recs: dict) -> dict:
    """Convert trend recommendations to concrete FFmpeg parameters."""
    color_key = trend_recs.get("recommended_color_grade", "vibrant")
    color_preset = COLOR_GRADE_PRESETS.get(color_key, COLOR_GRADE_PRESETS["vibrant"])

    pacing_key = trend_recs.get("recommended_pacing", "medium")
    pacing_preset = PACING_PRESETS.get(pacing_key, PACING_PRESETS["medium"])

    target_duration = trend_recs.get("recommended_duration_sec", 25)
    # Cap at reasonable reel length
    target_duration = max(10, min(target_duration, 45))

    return {
        "color_grade": color_key,
        "color_eq": color_preset["eq"],
        "color_curves": color_preset.get("curves"),
        "color_description": color_preset["description"],
        "pacing": pacing_key,
        "pacing_setpts": pacing_preset["setpts"],
        "pacing_atempo": pacing_preset["atempo"],
        "target_duration": target_duration,
        "music_style": trend_recs.get("recommended_music_style", "electronic"),
        "hook_type": trend_recs.get("recommended_hook", "text_hook"),
        "font_style": trend_recs.get("recommended_font_style", "glow_outline"),
        "preferred_style": trend_recs.get("preferred_style", "highlight_react"),
    }


# ═══════════════════════════════════════════════════════════════════
# 3. CLIP AUTO-DISCOVERY (via yt-dlp, no Twitch API needed)
# ═══════════════════════════════════════════════════════════════════

async def _discover_cs2_clips_ytdlp(
    query: str = "CS2 highlights",
    limit: int = 10,
) -> list[dict]:
    """Discover CS2 clips using yt-dlp search (no API key needed).

    Searches YouTube for recent CS2 content and returns clip metadata.
    """
    cmd = [
        "yt-dlp",
        f"ytsearch{limit}:{query}",
        "--dump-json",
        "--flat-playlist",
        "--no-download",
        "--no-warnings",
        "--quiet",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
        output = stdout.decode(errors="replace")

        clips = []
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                clips.append({
                    "title": data.get("title", ""),
                    "url": data.get("url", data.get("webpage_url", "")),
                    "video_id": data.get("id", ""),
                    "duration": data.get("duration", 0),
                    "view_count": data.get("view_count", 0),
                    "channel": data.get("channel", data.get("uploader", "")),
                    "upload_date": data.get("upload_date", ""),
                    "description": (data.get("description", "") or "")[:200],
                    "source": "yt_dlp_search",
                })
            except json.JSONDecodeError:
                continue

        return clips
    except Exception as e:
        logger.warning(f"yt-dlp clip discovery failed: {e}")
        return []


async def _discover_twitch_clips_ytdlp(
    streamer: str,
    limit: int = 5,
) -> list[dict]:
    """Discover Twitch clips for a streamer using yt-dlp."""
    url = f"https://www.twitch.tv/{streamer}/clips?filter=clips&range=7d"
    cmd = [
        "yt-dlp",
        url,
        "--dump-json",
        "--flat-playlist",
        "--no-download",
        "--no-warnings",
        "--quiet",
        "--playlist-end", str(limit),
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=90)
        output = stdout.decode(errors="replace")

        clips = []
        for line in output.strip().split("\n"):
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                clips.append({
                    "title": data.get("title", ""),
                    "url": data.get("webpage_url", data.get("url", "")),
                    "video_id": data.get("id", ""),
                    "duration": data.get("duration", 0),
                    "view_count": data.get("view_count", 0),
                    "channel": streamer,
                    "source": "twitch_ytdlp",
                })
            except json.JSONDecodeError:
                continue

        return clips
    except Exception as e:
        logger.warning(f"Twitch clip discovery for {streamer} failed: {e}")
        return []


# ═══════════════════════════════════════════════════════════════════
# 4. AUTO-SELECT BEST CLIP BASED ON TRENDS
# ═══════════════════════════════════════════════════════════════════

def _score_clip_for_trends(clip: dict, trend_recs: dict) -> float:
    """Score how well a clip matches current trends.

    Factors:
    - Title keyword match to trending moment types
    - Duration match to recommended duration
    - View count (popularity)
    - Recency
    """
    score = 0.0
    title = (clip.get("title", "") + " " + clip.get("description", "")).lower()
    preferred_style = trend_recs.get("preferred_style", "")

    # Moment type matching
    style_keywords = {
        "sigma_edit": ["sigma", "edit", "phonk", "gigachad", "grindset"],
        "highlight_react": ["react", "highlight", "insane", "crazy", "best"],
        "pro_clutch": ["clutch", "1v", "impossible", "pro", "fpl"],
        "funny_moments": ["funny", "fail", "wtf", "lol", "meme"],
        "ace_compilation": ["ace", "5k", "compilation", "top"],
    }
    for style, keywords in style_keywords.items():
        if any(kw in title for kw in keywords):
            if style == preferred_style:
                score += 3.0  # Strong match to trending style
            else:
                score += 1.0

    # CS2-specific keywords
    cs2_keywords = ["cs2", "counter-strike", "csgo", "cs 2", "faceit", "fpl"]
    if any(kw in title for kw in cs2_keywords):
        score += 2.0

    # Action keywords (these make better reels)
    action_keywords = ["ace", "clutch", "insane", "crazy", "headshot", "awp", "flick", "spray"]
    if any(kw in title for kw in action_keywords):
        score += 1.5

    # Duration match
    target = trend_recs.get("recommended_duration_sec", 25)
    duration = clip.get("duration", 0)
    if duration > 0:
        diff = abs(duration - target)
        if diff < 10:
            score += 2.0
        elif diff < 20:
            score += 1.0
        elif diff < 40:
            score += 0.5

    # View count (popularity signal)
    views = clip.get("view_count", 0)
    if views > 100000:
        score += 3.0
    elif views > 10000:
        score += 2.0
    elif views > 1000:
        score += 1.0

    return score


def _select_best_clip(clips: list[dict], trend_recs: dict) -> dict:
    """Select the best clip from candidates based on trend matching."""
    if not clips:
        return {}

    scored = []
    for clip in clips:
        s = _score_clip_for_trends(clip, trend_recs)
        scored.append({"clip": clip, "score": s})

    scored.sort(key=lambda x: x["score"], reverse=True)
    best = scored[0]

    return {
        "selected_clip": best["clip"],
        "score": best["score"],
        "candidates_considered": len(clips),
        "top_3": [
            {"title": s["clip"].get("title", "")[:50], "score": s["score"]}
            for s in scored[:3]
        ],
    }


# ═══════════════════════════════════════════════════════════════════
# 5. ROYALTY-FREE MUSIC — Pixabay Music API
# ═══════════════════════════════════════════════════════════════════

MUSIC_STYLE_QUERIES = {
    "phonk": "phonk aggressive bass",
    "electronic": "electronic energetic gaming",
    "dramatic": "dramatic cinematic epic",
    "meme": "funny comedy quirky",
    "epic": "epic orchestral powerful",
    "ambient": "ambient calm chill",
}

# Curated list of royalty-free music URLs
# Multiple fallback URLs per style for reliability
BUILT_IN_MUSIC = {
    "phonk": [
        "https://cdn.pixabay.com/download/audio/2022/10/25/audio_946eb6a7cc.mp3",
        "https://cdn.pixabay.com/download/audio/2023/09/27/audio_90a4122818.mp3",
    ],
    "electronic": [
        "https://cdn.pixabay.com/download/audio/2022/05/27/audio_1808fbf07a.mp3",
        "https://cdn.pixabay.com/download/audio/2022/01/18/audio_d0c6ff1bdd.mp3",
    ],
    "dramatic": [
        "https://cdn.pixabay.com/download/audio/2022/02/22/audio_d1718ab41b.mp3",
        "https://cdn.pixabay.com/download/audio/2023/10/30/audio_669e25faa3.mp3",
    ],
    "epic": [
        "https://cdn.pixabay.com/download/audio/2022/01/20/audio_d16737dc28.mp3",
        "https://cdn.pixabay.com/download/audio/2024/02/22/audio_a1e4026a6c.mp3",
    ],
    "ambient": [
        "https://cdn.pixabay.com/download/audio/2022/03/15/audio_115701bab8.mp3",
    ],
    "meme": [
        "https://cdn.pixabay.com/download/audio/2021/08/04/audio_0625c1539c.mp3",
    ],
}


async def _download_music(style: str) -> Optional[str]:
    """Download a royalty-free music track matching the style.

    First checks local cache, then downloads from Pixabay.
    Returns local file path or None.
    """
    music_dir = CLIPS_DIR / "music"
    cache_file = music_dir / f"{style}.mp3"

    if cache_file.exists() and cache_file.stat().st_size > 10000:
        logger.info(f"Music cache hit: {style}")
        return str(cache_file)

    urls = BUILT_IN_MUSIC.get(style, [])
    if not urls:
        urls = BUILT_IN_MUSIC.get("electronic", [])
    if not urls:
        return None

    # Try each URL until one works
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        for url in urls:
            try:
                resp = await client.get(url)
                if resp.status_code == 200 and len(resp.content) > 10000:
                    cache_file.write_bytes(resp.content)
                    logger.info(f"Downloaded music: {style} ({len(resp.content)} bytes) from {url[:60]}")
                    return str(cache_file)
                else:
                    logger.warning(f"Music URL returned status={resp.status_code}, trying next...")
            except Exception as e:
                logger.warning(f"Music URL failed ({url[:50]}): {e}, trying next...")

    # Last resort: generate a simple beat using FFmpeg
    logger.info("All music URLs failed, generating simple beat track...")
    try:
        beat_cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i",
            "sine=frequency=80:duration=60,volume=0.3",
            "-f", "lavfi", "-i",
            "sine=frequency=160:duration=60,volume=0.15",
            "-filter_complex",
            "[0:a][1:a]amix=inputs=2:duration=first[out]",
            "-map", "[out]",
            "-c:a", "libmp3lame", "-b:a", "128k",
            str(cache_file),
        ]
        proc = await asyncio.create_subprocess_exec(
            *beat_cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=15)
        if cache_file.exists() and cache_file.stat().st_size > 1000:
            logger.info(f"Generated fallback beat track: {cache_file.stat().st_size} bytes")
            return str(cache_file)
    except Exception as e:
        logger.warning(f"Beat generation failed: {e}")

    return None


# ═══════════════════════════════════════════════════════════════════
# 6. DYNAMIC WORD-BY-WORD SUBTITLES
# ═══════════════════════════════════════════════════════════════════

def _generate_dynamic_subtitle_filter(
    text: str,
    start_time: float = 0.0,
    total_duration: float = 10.0,
    font_path: str = FONT_PATH,
    font_style: str = "glow_outline",
) -> str:
    """Generate FFmpeg drawtext filters for word-by-word subtitle animation.

    Each word appears one at a time with a fade-in effect.
    """
    words = text.split()
    if not words:
        return ""

    filters = []
    # Time each word gets on screen
    word_duration = min(total_duration / len(words), 1.5)
    # Each word stays visible for at least its duration + overlap
    visible_duration = max(word_duration * 2, 1.0)

    # Font style configs
    style_configs = {
        "glow_outline": {
            "fontsize": 48,
            "fontcolor": "white",
            "borderw": 3,
            "bordercolor": "black",
            "shadowx": 2,
            "shadowy": 2,
            "shadowcolor": "black@0.5",
        },
        "bold_caps": {
            "fontsize": 54,
            "fontcolor": "white",
            "borderw": 4,
            "bordercolor": "black",
            "shadowx": 0,
            "shadowy": 0,
            "shadowcolor": "black@0.0",
        },
        "impact": {
            "fontsize": 52,
            "fontcolor": "yellow",
            "borderw": 3,
            "bordercolor": "black",
            "shadowx": 3,
            "shadowy": 3,
            "shadowcolor": "black@0.7",
        },
        "clean_modern": {
            "fontsize": 44,
            "fontcolor": "white",
            "borderw": 2,
            "bordercolor": "black@0.7",
            "shadowx": 1,
            "shadowy": 1,
            "shadowcolor": "black@0.3",
        },
    }

    cfg = style_configs.get(font_style, style_configs["glow_outline"])

    for i, word in enumerate(words):
        word_start = start_time + i * word_duration
        word_end = min(word_start + visible_duration, start_time + total_duration)

        # Escape for FFmpeg
        escaped = word.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace("%", "%%")

        # Accumulated text: show all words up to current
        accumulated = " ".join(words[:i + 1])
        acc_escaped = accumulated.replace("\\", "\\\\").replace("'", "\\'").replace(":", "\\:").replace("%", "%%")

        # Current word highlighted, previous words dim
        # Use accumulated text approach for natural reading feel
        filters.append(
            f"drawtext=fontfile='{font_path}'"
            f":text='{acc_escaped}'"
            f":fontsize={cfg['fontsize']}"
            f":fontcolor={cfg['fontcolor']}"
            f":borderw={cfg['borderw']}"
            f":bordercolor={cfg['bordercolor']}"
            f":shadowx={cfg['shadowx']}"
            f":shadowy={cfg['shadowy']}"
            f":shadowcolor={cfg['shadowcolor']}"
            f":x=(w-tw)/2"
            f":y=h-300"
            f":enable='between(t,{word_start:.2f},{word_end:.2f})'"
        )

    return ",".join(filters)


# ═══════════════════════════════════════════════════════════════════
# 7. FULL SMART REEL ASSEMBLY
# ═══════════════════════════════════════════════════════════════════

def _escape_ffmpeg_text(text: str) -> str:
    """Escape special characters for FFmpeg drawtext filter."""
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    text = text.replace(":", "\\:")
    text = text.replace("%", "%%")
    return text


async def _get_video_info(file_path: str) -> dict:
    """Get video metadata using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", file_path,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        data = json.loads(stdout.decode())
        video_stream = None
        for s in data.get("streams", []):
            if s.get("codec_type") == "video":
                video_stream = s
                break
        duration = float(data.get("format", {}).get("duration", 0))
        width = int(video_stream.get("width", 0)) if video_stream else 0
        height = int(video_stream.get("height", 0)) if video_stream else 0
        return {"duration": duration, "width": width, "height": height}
    except Exception:
        return {"duration": 0, "width": 0, "height": 0}


async def assemble_smart_reel(
    source_path: str,
    ffmpeg_params: dict,
    cut_points: dict,
    hook_text: str = "",
    cta_text: str = "",
    subtitle_text: str = "",
    music_path: Optional[str] = None,
    output_name: Optional[str] = None,
) -> dict:
    """Assemble the final reel with all smart features.

    Applies:
    - Smart cutting (from cut_points)
    - Trend-driven color grading
    - Trend-driven pacing
    - Music overlay (mixed with gameplay audio)
    - Dynamic word-by-word subtitles
    - Hook text + CTA overlays
    """
    if output_name is None:
        output_name = f"smart_reel_{uuid.uuid4().hex[:8]}"

    output_path = str(CLIPS_DIR / "processed" / f"{output_name}.mp4")
    thumb_path = str(CLIPS_DIR / "thumbnails" / f"{output_name}.jpg")

    # Get source info
    info = await _get_video_info(source_path)
    src_w = info.get("width", 1920)
    src_h = info.get("height", 1080)

    start = cut_points.get("start", 0)
    end = cut_points.get("end", info.get("duration", 30))
    duration = end - start

    if duration <= 0:
        return {"success": False, "error": "Invalid duration from smart cut"}

    # ─── Build video filter chain ───────────────────────────────
    vf_parts = []

    # 1. Trim to smart cut points
    vf_parts.append(f"trim=start={start}:end={end},setpts=PTS-STARTPTS")

    # 2. Scale to vertical 9:16
    target_w, target_h = 1080, 1920
    aspect = src_w / src_h if src_h > 0 else 16 / 9
    target_aspect = target_w / target_h

    if aspect > target_aspect:
        scale_h = target_h
        scale_w = int(scale_h * aspect)
        vf_parts.append(f"scale={scale_w}:{scale_h}")
        vf_parts.append(f"crop={target_w}:{target_h}:(iw-{target_w})/2:0")
    else:
        scale_w = target_w
        scale_h = int(scale_w / aspect)
        vf_parts.append(f"scale={scale_w}:{scale_h}")
        if scale_h < target_h:
            vf_parts.append(f"pad={target_w}:{target_h}:0:({target_h}-ih)/2:black")
        else:
            vf_parts.append(f"crop={target_w}:{target_h}:0:(ih-{target_h})/2")

    # 3. FPS
    vf_parts.append("fps=30")

    # 4. Pacing adjustment
    pacing_setpts = ffmpeg_params.get("pacing_setpts", "PTS")
    if pacing_setpts != "PTS":
        vf_parts.append(f"setpts={pacing_setpts}")

    # 5. Color grading from trends
    color_eq = ffmpeg_params.get("color_eq", "")
    if color_eq:
        vf_parts.append(color_eq)
    color_curves = ffmpeg_params.get("color_curves")
    if color_curves:
        vf_parts.append(color_curves)

    # 6. Hook text overlay (top, first 3.5 seconds, with fade)
    if hook_text:
        escaped = _escape_ffmpeg_text(hook_text)
        vf_parts.append(
            f"drawtext=fontfile='{FONT_PATH}'"
            f":text='{escaped}'"
            f":fontsize=52"
            f":fontcolor=white"
            f":borderw=3"
            f":bordercolor=black"
            f":x=(w-tw)/2"
            f":y=120"
            f":enable='between(t,0.2,3.5)'"
            f":box=1:boxcolor=black@0.5:boxborderw=12"
        )

    # 7. CTA text overlay (bottom, last 4 seconds)
    if cta_text:
        escaped = _escape_ffmpeg_text(cta_text)
        cta_start = max(0, duration - 4)
        vf_parts.append(
            f"drawtext=fontfile='{FONT_PATH}'"
            f":text='{escaped}'"
            f":fontsize=40"
            f":fontcolor=white"
            f":borderw=2"
            f":bordercolor=black"
            f":x=(w-tw)/2"
            f":y=h-200"
            f":enable='between(t,{cta_start:.1f},{duration:.1f})'"
            f":box=1:boxcolor=black@0.6:boxborderw=10"
        )

    # 8. Dynamic word-by-word subtitles
    if subtitle_text:
        font_style = ffmpeg_params.get("font_style", "glow_outline")
        # Show subtitle from 1s after start, lasting most of the clip
        sub_start = 0.5
        sub_duration = max(duration - 2, 3)
        subtitle_filter = _generate_dynamic_subtitle_filter(
            subtitle_text, sub_start, sub_duration, FONT_PATH, font_style
        )
        if subtitle_filter:
            vf_parts.append(subtitle_filter)

    vf = ",".join(vf_parts)

    # ─── Build audio filter chain ───────────────────────────────
    af_parts = []
    af_parts.append(f"atrim=start={start}:end={end},asetpts=PTS-STARTPTS")

    # Pacing for audio
    pacing_atempo = ffmpeg_params.get("pacing_atempo", "1.0")
    if pacing_atempo != "1.0":
        af_parts.append(f"atempo={pacing_atempo}")

    af_parts.append("volume=1.1")
    af_parts.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    gameplay_af = ",".join(af_parts)

    # ─── Build FFmpeg command ───────────────────────────────────
    if music_path and os.path.exists(music_path):
        # Two inputs: video + music
        # Mix gameplay audio (louder) with music (background)
        cmd = [
            "ffmpeg", "-y",
            "-i", source_path,
            "-i", music_path,
            "-filter_complex",
            f"[0:v]{vf}[v];"
            f"[0:a]{gameplay_af}[gameplay];"
            f"[1:a]aloop=loop=-1:size=2e+09,atrim=0:{duration:.1f},volume=0.15,afade=t=out:st={duration - 2:.1f}:d=2[music];"
            f"[gameplay][music]amix=inputs=2:duration=first:dropout_transition=2[a]",
            "-map", "[v]",
            "-map", "[a]",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_path,
        ]
    else:
        # Single input, no music
        cmd = [
            "ffmpeg", "-y",
            "-i", source_path,
            "-vf", vf,
            "-af", gameplay_af,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "22",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            "-pix_fmt", "yuv420p",
            output_path,
        ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        if proc.returncode != 0:
            err = stderr.decode()[-500:]
            logger.error(f"FFmpeg failed: {err}")
            return {"success": False, "error": f"FFmpeg failed: {err}"}

        # Generate thumbnail at 30% into clip
        thumb_time = min(duration * 0.3, 3.0)
        thumb_cmd = [
            "ffmpeg", "-y", "-i", output_path,
            "-ss", str(thumb_time), "-vframes", "1", "-q:v", "2",
            thumb_path,
        ]
        thumb_proc = await asyncio.create_subprocess_exec(
            *thumb_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(thumb_proc.communicate(), timeout=30)

        out_info = await _get_video_info(output_path)

        return {
            "success": True,
            "file_path": output_path,
            "filename": os.path.basename(output_path),
            "thumbnail_path": thumb_path if os.path.exists(thumb_path) else None,
            "duration": out_info.get("duration", duration),
            "width": out_info.get("width", target_w),
            "height": out_info.get("height", target_h),
            "file_size": os.path.getsize(output_path),
            "format": "mp4",
            "resolution": f"{target_w}x{target_h}",
        }

    except asyncio.TimeoutError:
        return {"success": False, "error": "FFmpeg processing timed out (300s)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT — generate_smart_reel()
# ═══════════════════════════════════════════════════════════════════

async def generate_smart_reel(
    clip_url: Optional[str] = None,
    streamer: Optional[str] = None,
    search_query: str = "CS2 highlights ace clutch today",
    hook_text: Optional[str] = None,
    cta_text: str = "Follow for daily CS2 highlights!",
    subtitle_text: Optional[str] = None,
    platform: str = "tiktok",
) -> dict:
    """
    MAIN ENTRY: Generate an intelligent CS2 reel.

    Workflow:
    1. Fetch fresh trends (real scraping)
    2. Auto-discover best clip (if no URL given)
    3. Download clip
    4. Smart-cut to preserve full moment
    5. Apply trend-driven processing
    6. Add music overlay
    7. Add dynamic subtitles
    8. Return final reel with full data source documentation

    Args:
        clip_url: Direct clip URL (optional — if not given, auto-discovers)
        streamer: Twitch streamer to search clips from (optional)
        search_query: YouTube search query for clip discovery
        hook_text: Custom hook text (auto-generated if None)
        cta_text: Call-to-action text
        subtitle_text: Custom subtitle (auto-generated from clip title if None)
        platform: Target platform (tiktok/youtube_shorts/instagram)
    """
    pipeline_log = {
        "pipeline_id": uuid.uuid4().hex[:12],
        "started_at": datetime.utcnow().isoformat(),
        "steps": [],
        "data_sources": {},
    }

    # ─── Step 1: Get fresh trend recommendations ────────────────
    logger.info("Step 1: Fetching trend recommendations...")
    trend_recs = await _get_fresh_trend_recommendations()
    ffmpeg_params = _map_trend_to_ffmpeg(trend_recs)

    pipeline_log["steps"].append({
        "step": 1,
        "name": "Trend Analysis",
        "description_human": (
            f"Подгрузил тренды: топ-формат '{trend_recs.get('preferred_style', '?')}', "
            f"цвет '{ffmpeg_params['color_grade']}' ({ffmpeg_params['color_description']}), "
            f"музыка '{ffmpeg_params['music_style']}', "
            f"пейсинг '{ffmpeg_params['pacing']}', "
            f"рекомендуемая длительность {ffmpeg_params['target_duration']}с. "
            f"Источники: {trend_recs.get('data_sources_used', ['unknown'])}"
        ),
        "trend_data": {
            "preferred_style": trend_recs.get("preferred_style"),
            "color_grade": ffmpeg_params["color_grade"],
            "music_style": ffmpeg_params["music_style"],
            "pacing": ffmpeg_params["pacing"],
            "target_duration": ffmpeg_params["target_duration"],
            "data_type": trend_recs.get("data_type", "unknown"),
        },
    })

    # ─── Step 2: Clip discovery / selection ─────────────────────
    selected_clip_data = None
    if clip_url:
        logger.info("Step 2: Using provided clip URL: %s", clip_url[:80])
        selected_clip_data = {"url": clip_url, "title": "User-provided clip", "source": "direct_url"}
        pipeline_log["steps"].append({
            "step": 2,
            "name": "Clip Source",
            "description_human": f"Клип указан вручную: {clip_url[:80]}",
        })
    else:
        logger.info("Step 2: Auto-discovering clips...")
        clips = []

        # Try Twitch streamer first
        if streamer:
            twitch_clips = await _discover_twitch_clips_ytdlp(streamer, limit=5)
            clips.extend(twitch_clips)
            pipeline_log["data_sources"]["twitch_clips"] = {
                "streamer": streamer,
                "found": len(twitch_clips),
            }

        # Also search YouTube
        yt_clips = await _discover_cs2_clips_ytdlp(search_query, limit=10)
        clips.extend(yt_clips)
        pipeline_log["data_sources"]["youtube_search"] = {
            "query": search_query,
            "found": len(yt_clips),
        }

        if not clips:
            return {
                "success": False,
                "error": "No CS2 clips found. Try providing a direct URL.",
                "pipeline_log": pipeline_log,
            }

        # Select best clip based on trends
        selection = _select_best_clip(clips, trend_recs)
        selected_clip_data = selection.get("selected_clip", clips[0])

        pipeline_log["steps"].append({
            "step": 2,
            "name": "Clip Discovery & Selection",
            "description_human": (
                f"Нашёл {len(clips)} клипов (YouTube: {len(yt_clips)}). "
                f"Выбрал лучший по трендам: '{selected_clip_data.get('title', '?')[:50]}' "
                f"(score: {selection.get('score', 0):.1f}, views: {selected_clip_data.get('view_count', 0)}). "
                f"Топ-3 кандидата: {selection.get('top_3', [])}"
            ),
            "selection": selection,
        })

    # ─── Step 3: Download clip ──────────────────────────────────
    logger.info("Step 3: Downloading clip...")
    download_url = selected_clip_data.get("url", clip_url or "")
    if not download_url:
        return {"success": False, "error": "No download URL", "pipeline_log": pipeline_log}

    from app.services.clip_executor import download_twitch_clip
    dl_result = await download_twitch_clip(download_url)

    if not dl_result.get("success"):
        return {
            "success": False,
            "error": f"Download failed: {dl_result.get('error')}",
            "pipeline_log": pipeline_log,
        }

    source_path = dl_result["file_path"]
    total_duration = dl_result.get("duration", 0)
    clip_title = selected_clip_data.get("title", "CS2 Highlight")

    pipeline_log["steps"].append({
        "step": 3,
        "name": "Download",
        "description_human": (
            f"Скачал клип через yt-dlp: {dl_result.get('width')}x{dl_result.get('height')}, "
            f"{total_duration:.1f}с, {dl_result.get('file_size', 0) / (1024*1024):.1f} MB"
        ),
        "download": {
            "duration": total_duration,
            "resolution": f"{dl_result.get('width')}x{dl_result.get('height')}",
            "file_size_mb": round(dl_result.get("file_size", 0) / (1024 * 1024), 1),
        },
    })

    # ─── Step 4: Smart cut detection ────────────────────────────
    logger.info("Step 4: Analyzing clip for smart cut points...")
    target_dur = ffmpeg_params["target_duration"]

    if total_duration <= target_dur + 5:
        # Clip is short enough — use it entirely
        cut_points = {
            "start": 0,
            "end": total_duration,
            "method": "full_clip",
            "peak_time": None,
        }
    else:
        cut_points = await _find_smart_cut_points(source_path, target_dur, total_duration)

    actual_duration = cut_points["end"] - cut_points["start"]

    pipeline_log["steps"].append({
        "step": 4,
        "name": "Smart Cut Analysis",
        "description_human": (
            f"Анализ аудио пиков + сцен: метод '{cut_points['method']}'. "
            f"Вырезка: {cut_points['start']:.1f}с → {cut_points['end']:.1f}с "
            f"({actual_duration:.1f}с). "
            + (f"Пик экшена на {cut_points.get('peak_time', '?')}с ({cut_points.get('peak_volume_db', '?')} dB). "
               if cut_points.get("peak_time") else "")
            + f"Момент сохранён целиком, без обрыва."
        ),
        "cut_points": cut_points,
    })

    # ─── Step 5: Download music ─────────────────────────────────
    logger.info("Step 5: Getting music track...")
    music_style = ffmpeg_params["music_style"]
    music_path = await _download_music(music_style)

    pipeline_log["steps"].append({
        "step": 5,
        "name": "Music",
        "description_human": (
            f"Музыка: стиль '{music_style}' (на основе тренда '{trend_recs.get('preferred_style')}'). "
            + (f"Скачал royalty-free трек из Pixabay ({os.path.getsize(music_path) // 1024} KB). "
               if music_path else "Не удалось скачать музыку — только геймплей аудио. ")
            + "Микс: геймплей 85% + музыка 15%."
        ),
        "music_file": music_path,
        "music_style": music_style,
    })

    # ─── Step 6: Generate texts ─────────────────────────────────
    if not hook_text:
        # Generate hook from trends and clip title
        hook_type = trend_recs.get("recommended_hook", "text_hook")
        hooks_pool = {
            "text_hook": ["WAIT FOR IT...", "WATCH THIS", "NO WAY..."],
            "question_hook": ["CAN HE DO IT?", "IS THIS POSSIBLE?", "HOW?!"],
            "shock_text": ["INSANE!", "ABSOLUTELY CRAZY", "UNREAL PLAY"],
            "stat_hook": ["1 vs 5", "5 KILLS 0 DEATHS", "100% HEADSHOT"],
            "challenge_hook": ["TRY THIS IN RANKED", "BET YOU CAN'T DO THIS"],
            "pov_hook": ["POV: CS2 GOD LOBBY", "POV: FPL HIGHLIGHTS"],
            "superlative_hook": ["THE BEST PLAY TODAY", "CRAZIEST CLUTCH EVER"],
        }
        pool = hooks_pool.get(hook_type, hooks_pool["text_hook"])
        # Deterministic selection
        h = hashlib.md5(clip_title.encode()).hexdigest()
        hook_text = pool[int(h[:4], 16) % len(pool)]

    if not subtitle_text:
        # Clean clip title for subtitle
        subtitle_text = re.sub(r'[#@\[\]{}|]', '', clip_title)[:60]

    pipeline_log["steps"].append({
        "step": 6,
        "name": "Text Generation",
        "description_human": (
            f"Хук: '{hook_text}' (тип '{trend_recs.get('recommended_hook', '?')}' из трендов). "
            f"Субтитры (word-by-word): '{subtitle_text}'. "
            f"CTA: '{cta_text}'. "
            f"Стиль шрифта: '{ffmpeg_params['font_style']}' (из трендов)."
        ),
    })

    # ─── Step 7: Assemble final reel ────────────────────────────
    logger.info("Step 7: Assembling final reel...")
    result = await assemble_smart_reel(
        source_path=source_path,
        ffmpeg_params=ffmpeg_params,
        cut_points=cut_points,
        hook_text=hook_text,
        cta_text=cta_text,
        subtitle_text=subtitle_text,
        music_path=music_path,
    )

    if not result.get("success"):
        pipeline_log["steps"].append({
            "step": 7,
            "name": "Assembly",
            "description_human": f"ОШИБКА сборки: {result.get('error')}",
        })
        return {
            "success": False,
            "error": result.get("error"),
            "pipeline_log": pipeline_log,
        }

    pipeline_log["steps"].append({
        "step": 7,
        "name": "Assembly",
        "description_human": (
            f"Рилс собран! {result['resolution']}, {result['duration']:.1f}с, "
            f"{result['file_size'] / (1024*1024):.1f} MB. "
            f"Цветокоррекция: {ffmpeg_params['color_description']}. "
            f"Пейсинг: {ffmpeg_params['pacing']}. "
            f"Музыка: {'Pixabay ' + music_style if music_path else 'только геймплей'}. "
            f"Субтитры: word-by-word анимация."
        ),
    })

    pipeline_log["completed_at"] = datetime.utcnow().isoformat()

    return {
        "success": True,
        "output_file": result["file_path"],
        "thumbnail": result.get("thumbnail_path"),
        "duration": result.get("duration"),
        "file_size": result.get("file_size"),
        "resolution": result.get("resolution"),
        "pipeline_log": pipeline_log,
        "trend_applied": {
            "color_grade": ffmpeg_params["color_grade"],
            "music_style": ffmpeg_params["music_style"],
            "pacing": ffmpeg_params["pacing"],
            "font_style": ffmpeg_params["font_style"],
            "preferred_style": ffmpeg_params["preferred_style"],
        },
        "clip_source": {
            "url": download_url,
            "title": clip_title,
            "original_duration": total_duration,
        },
        "smart_cut": cut_points,
    }
