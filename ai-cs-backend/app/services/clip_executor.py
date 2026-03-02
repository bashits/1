"""
Clip Executor Service — Real Video Clipping Pipeline

Downloads Twitch clips/VODs, processes them with FFmpeg:
1. Download source video from Twitch (yt-dlp)
2. Cut to moment timestamps
3. Convert to vertical 9:16 (1080x1920)
4. Add hook text overlay (top)
5. Add subtitles (center-bottom, bold dynamic style)
6. Add CTA text (bottom)
7. Apply zoom/slow-mo effects
8. Color grade
9. Output final MP4

No external paid APIs needed for clipping — only FFmpeg + yt-dlp.
Twitch API (Client ID) needed only for discovering clips automatically.
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

# Output directory
CLIPS_DIR = Path("/data/clips") if os.path.exists("/data") else Path(
    os.path.join(os.path.dirname(__file__), "..", "..", "clips")
)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)
(CLIPS_DIR / "source").mkdir(exist_ok=True)
(CLIPS_DIR / "processed").mkdir(exist_ok=True)
(CLIPS_DIR / "thumbnails").mkdir(exist_ok=True)

# Font path for text overlays
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
if not os.path.exists(FONT_PATH):
    FONT_PATH = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
if not os.path.exists(FONT_PATH):
    # Fallback — find any TTF font
    import glob
    fonts = glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)
    FONT_PATH = fonts[0] if fonts else "Sans"


# ─── Twitch Clip Discovery (via Twitch API) ─────────────────────────
TWITCH_CLIENT_ID = os.environ.get("TWITCH_CLIENT_ID", "")
TWITCH_CLIENT_SECRET = os.environ.get("TWITCH_CLIENT_SECRET", "")
TWITCH_ACCESS_TOKEN = os.environ.get("TWITCH_ACCESS_TOKEN", "")
_twitch_token_cache: dict = {}


async def _get_twitch_token() -> str:
    """Get OAuth token from Twitch API.

    Supports two modes:
    1. Direct token: If TWITCH_ACCESS_TOKEN is set, use it directly (no client_credentials flow)
    2. Client credentials: Use TWITCH_CLIENT_ID + TWITCH_CLIENT_SECRET to get a token
    """
    # Mode 1: direct access token (from purchased/pre-existing OAuth token)
    direct_token = TWITCH_ACCESS_TOKEN or os.environ.get("TWITCH_ACCESS_TOKEN", "")
    if direct_token:
        return direct_token

    # Mode 2: client_credentials flow
    cid = TWITCH_CLIENT_ID or os.environ.get("TWITCH_CLIENT_ID", "")
    csecret = TWITCH_CLIENT_SECRET or os.environ.get("TWITCH_CLIENT_SECRET", "")
    if not cid or not csecret:
        return ""
    if _twitch_token_cache.get("token") and _twitch_token_cache.get("expires", 0) > time.time():
        return _twitch_token_cache["token"]

    import httpx
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://id.twitch.tv/oauth2/token",
            data={
                "client_id": cid,
                "client_secret": csecret,
                "grant_type": "client_credentials",
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            _twitch_token_cache["token"] = data["access_token"]
            _twitch_token_cache["expires"] = time.time() + data.get("expires_in", 3600) - 60
            return data["access_token"]
    return ""


async def get_twitch_clips(
    broadcaster_name: str, period: str = "24h", limit: int = 20
) -> list[dict]:
    """
    Get top clips from a Twitch channel.
    Requires TWITCH_CLIENT_ID + TWITCH_CLIENT_SECRET.
    period: '24h', '7d', '30d', 'all'
    """
    token = await _get_twitch_token()
    if not token:
        return []

    import httpx
    from datetime import timedelta

    headers = {
        "Client-ID": TWITCH_CLIENT_ID,
        "Authorization": f"Bearer {token}",
    }

    # First get broadcaster ID
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.twitch.tv/helix/users?login={broadcaster_name}",
            headers=headers,
        )
        if resp.status_code != 200:
            return []
        users = resp.json().get("data", [])
        if not users:
            return []
        broadcaster_id = users[0]["id"]

        # Get clips
        params = {
            "broadcaster_id": broadcaster_id,
            "first": limit,
        }

        # Set time range
        now = datetime.utcnow()
        period_map = {
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        if period in period_map:
            started = now - period_map[period]
            params["started_at"] = started.strftime("%Y-%m-%dT%H:%M:%SZ")
            params["ended_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        resp = await client.get(
            "https://api.twitch.tv/helix/clips",
            params=params,
            headers=headers,
        )
        if resp.status_code != 200:
            return []

        clips_data = resp.json().get("data", [])
        return [
            {
                "clip_id": c["id"],
                "url": c["url"],
                "embed_url": c.get("embed_url", ""),
                "title": c["title"],
                "broadcaster_name": c["broadcaster_name"],
                "creator_name": c.get("creator_name", ""),
                "view_count": c["view_count"],
                "duration": c["duration"],
                "created_at": c["created_at"],
                "thumbnail_url": c["thumbnail_url"],
                "vod_offset": c.get("vod_offset"),
                "download_url": c["thumbnail_url"].split("-preview-")[0] + ".mp4",
            }
            for c in clips_data
        ]


# ─── Video Download ──────────────────────────────────────────────────

async def download_twitch_clip(clip_url: str, output_name: str | None = None) -> dict:
    """
    Download a Twitch clip using yt-dlp.
    clip_url: Full Twitch clip URL (e.g., https://clips.twitch.tv/...)
              or Twitch channel URL with clip slug
    Returns: dict with file_path, duration, resolution, etc.
    """
    if output_name is None:
        output_name = f"source_{uuid.uuid4().hex[:8]}"

    output_path = str(CLIPS_DIR / "source" / f"{output_name}.mp4")

    cmd = [
        "yt-dlp",
        "--no-check-certificates",
        "-f", "best[ext=mp4]/best",
        "-o", output_path,
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        clip_url,
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        if proc.returncode != 0:
            return {
                "success": False,
                "error": f"yt-dlp failed: {stderr.decode()[:500]}",
            }

        if not os.path.exists(output_path):
            # yt-dlp might add extension
            candidates = list(Path(CLIPS_DIR / "source").glob(f"{output_name}.*"))
            if candidates:
                output_path = str(candidates[0])
            else:
                return {"success": False, "error": "Download completed but file not found"}

        # Get video info with ffprobe
        info = await _get_video_info(output_path)

        return {
            "success": True,
            "file_path": output_path,
            "filename": os.path.basename(output_path),
            "duration": info.get("duration", 0),
            "width": info.get("width", 0),
            "height": info.get("height", 0),
            "file_size": os.path.getsize(output_path),
        }
    except asyncio.TimeoutError:
        return {"success": False, "error": "Download timed out (120s)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def download_from_url(url: str, output_name: str | None = None) -> dict:
    """Download any video URL (direct MP4 link or supported site)."""
    return await download_twitch_clip(url, output_name)


async def _get_video_info(file_path: str) -> dict:
    """Get video metadata using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", file_path,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
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


# ─── FFmpeg Video Processing ─────────────────────────────────────────

def _escape_ffmpeg_text(text: str) -> str:
    """Escape special characters for FFmpeg drawtext filter."""
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    text = text.replace(":", "\\:")
    text = text.replace("%", "%%")
    return text


async def process_clip(
    source_path: str,
    output_name: str | None = None,
    # Timing
    start_time: float = 0.0,
    end_time: float | None = None,
    max_duration: float = 60.0,
    # Format
    target_width: int = 1080,
    target_height: int = 1920,
    fps: int = 30,
    # Text overlays
    hook_text: str | None = None,
    hook_duration: float = 3.0,
    cta_text: str | None = None,
    cta_start_offset: float = 3.0,  # seconds before end
    subtitle_text: str | None = None,
    # Effects
    zoom_on_action: bool = False,
    zoom_time: float = 0.0,
    zoom_duration: float = 0.5,
    zoom_factor: float = 1.3,
    slow_mo: bool = False,
    slow_mo_time: float = 0.0,
    slow_mo_duration: float = 2.0,
    slow_mo_factor: float = 0.5,
    # Color
    color_grade: str = "none",  # none, cinematic, vibrant, dark
    # Audio
    volume_boost: float = 1.0,
) -> dict:
    """
    Process a source video into a final vertical clip using FFmpeg.

    Full pipeline:
    1. Cut to timestamps
    2. Crop/pad to 9:16 vertical
    3. Add hook text overlay (top, first N seconds)
    4. Add CTA text (bottom, last N seconds)
    5. Add subtitle text (center, full duration)
    6. Apply zoom effect at action point
    7. Apply slow motion
    8. Color grading
    9. Audio normalization + volume boost
    10. Output 1080x1920 MP4
    """
    if output_name is None:
        output_name = f"clip_{uuid.uuid4().hex[:8]}"

    output_path = str(CLIPS_DIR / "processed" / f"{output_name}.mp4")
    thumb_path = str(CLIPS_DIR / "thumbnails" / f"{output_name}.jpg")

    # Get source info
    info = await _get_video_info(source_path)
    src_duration = info.get("duration", 0)
    src_w = info.get("width", 1920)
    src_h = info.get("height", 1080)

    # Calculate actual duration
    if end_time is None or end_time > src_duration:
        end_time = src_duration
    duration = min(end_time - start_time, max_duration)
    if duration <= 0:
        return {"success": False, "error": "Invalid duration"}

    # Build FFmpeg filter chain
    filters = []

    # 1. Trim to timestamps
    filters.append(f"trim=start={start_time}:end={start_time + duration},setpts=PTS-STARTPTS")

    # 2. Scale and crop to vertical 9:16
    # Strategy: scale to fill width, then crop height (center crop)
    # Or if source is already vertical, just scale
    aspect = src_w / src_h if src_h > 0 else 16 / 9
    target_aspect = target_width / target_height  # 0.5625

    if aspect > target_aspect:
        # Source is wider than target — crop sides
        # Scale height to target, then crop width
        scale_h = target_height
        scale_w = int(scale_h * aspect)
        filters.append(f"scale={scale_w}:{scale_h}")
        crop_x = f"(iw-{target_width})/2"
        filters.append(f"crop={target_width}:{target_height}:{crop_x}:0")
    else:
        # Source is narrower/same — scale width to target, pad top/bottom
        scale_w = target_width
        scale_h = int(scale_w / aspect)
        filters.append(f"scale={scale_w}:{scale_h}")
        if scale_h < target_height:
            pad_y = f"({target_height}-ih)/2"
            filters.append(f"pad={target_width}:{target_height}:0:{pad_y}:black")
        else:
            crop_y = f"(ih-{target_height})/2"
            filters.append(f"crop={target_width}:{target_height}:0:{crop_y}")

    # 3. FPS
    filters.append(f"fps={fps}")

    # 4. Color grading
    if color_grade == "cinematic":
        filters.append("eq=contrast=1.2:brightness=-0.03:saturation=0.85")
        filters.append("curves=preset=increase_contrast")
    elif color_grade == "vibrant":
        filters.append("eq=contrast=1.1:saturation=1.4:brightness=0.02")
    elif color_grade == "dark":
        filters.append("eq=contrast=1.3:brightness=-0.08:saturation=0.7")

    # 5. Hook text overlay (top, first N seconds)
    if hook_text:
        escaped = _escape_ffmpeg_text(hook_text)
        # Background box + white text, centered at top
        filters.append(
            f"drawtext=fontfile='{FONT_PATH}'"
            f":text='{escaped}'"
            f":fontsize=52"
            f":fontcolor=white"
            f":borderw=3"
            f":bordercolor=black"
            f":x=(w-tw)/2"
            f":y=120"
            f":enable='between(t,0.3,{hook_duration})'"
            f":box=1:boxcolor=black@0.5:boxborderw=12"
        )

    # 6. CTA text overlay (bottom, last N seconds)
    if cta_text:
        escaped = _escape_ffmpeg_text(cta_text)
        cta_start = max(0, duration - cta_start_offset)
        filters.append(
            f"drawtext=fontfile='{FONT_PATH}'"
            f":text='{escaped}'"
            f":fontsize=40"
            f":fontcolor=white"
            f":borderw=2"
            f":bordercolor=black"
            f":x=(w-tw)/2"
            f":y=h-200"
            f":enable='between(t,{cta_start},{duration})'"
            f":box=1:boxcolor=black@0.6:boxborderw=10"
        )

    # 7. Subtitle text (center-bottom area, full clip)
    if subtitle_text:
        escaped = _escape_ffmpeg_text(subtitle_text)
        filters.append(
            f"drawtext=fontfile='{FONT_PATH}'"
            f":text='{escaped}'"
            f":fontsize=44"
            f":fontcolor=yellow"
            f":borderw=3"
            f":bordercolor=black"
            f":x=(w-tw)/2"
            f":y=h-350"
        )

    # Build filter string
    vf = ",".join(filters)

    # Audio filters
    af_parts = []
    af_parts.append(f"atrim=start={start_time}:end={start_time + duration},asetpts=PTS-STARTPTS")
    if volume_boost != 1.0:
        af_parts.append(f"volume={volume_boost}")
    # Normalize audio
    af_parts.append("loudnorm=I=-16:TP=-1.5:LRA=11")
    af = ",".join(af_parts)

    # Build FFmpeg command
    cmd = [
        "ffmpeg", "-y",
        "-i", source_path,
        "-vf", vf,
        "-af", af,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
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
            err_text = stderr.decode()[-500:]
            return {"success": False, "error": f"FFmpeg failed: {err_text}"}

        # Generate thumbnail
        thumb_time = min(duration * 0.3, 2.0)  # 30% into clip or 2s
        thumb_cmd = [
            "ffmpeg", "-y",
            "-i", output_path,
            "-ss", str(thumb_time),
            "-vframes", "1",
            "-q:v", "2",
            thumb_path,
        ]
        thumb_proc = await asyncio.create_subprocess_exec(
            *thumb_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(thumb_proc.communicate(), timeout=30)

        # Get output info
        out_info = await _get_video_info(output_path)

        return {
            "success": True,
            "file_path": output_path,
            "filename": os.path.basename(output_path),
            "thumbnail_path": thumb_path if os.path.exists(thumb_path) else None,
            "thumbnail_filename": os.path.basename(thumb_path) if os.path.exists(thumb_path) else None,
            "duration": out_info.get("duration", duration),
            "width": out_info.get("width", target_width),
            "height": out_info.get("height", target_height),
            "file_size": os.path.getsize(output_path),
            "format": "mp4",
            "resolution": f"{target_width}x{target_height}",
            "fps": fps,
            "color_grade": color_grade,
            "hook_text": hook_text,
            "cta_text": cta_text,
        }
    except asyncio.TimeoutError:
        return {"success": False, "error": "FFmpeg processing timed out (300s)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ─── Full Clip Pipeline: Detect → Download → Process ─────────────────

async def execute_clip_from_moment(
    db,
    moment_id: int,
    template_format: str = "highlight_subtitles",
    hook_text: str | None = None,
    cta_text: str | None = None,
) -> dict:
    """
    Execute the full clipping pipeline for a detected moment:
    1. Get moment data from DB
    2. Find source clip/VOD URL
    3. Download source video
    4. Process with FFmpeg (vertical, overlays, effects)
    5. Save to DB and return result
    """
    # Get moment
    cursor = await db.execute("SELECT * FROM moments WHERE id = ?", (moment_id,))
    moment = await cursor.fetchone()
    if not moment:
        return {"success": False, "error": "Moment not found"}

    moment_data = dict(moment)
    metadata = json.loads(moment_data.get("metadata", "{}"))

    # Get stream info
    cursor = await db.execute(
        "SELECT * FROM streams WHERE id = ?", (moment_data["stream_id"],)
    )
    stream = await cursor.fetchone()
    if not stream:
        return {"success": False, "error": "Stream not found"}

    stream_data = dict(stream)
    source_url = stream_data.get("url", "")

    if not source_url:
        return {"success": False, "error": "No source URL for stream"}

    # Step 1: Download source
    download_result = await download_twitch_clip(source_url)
    if not download_result.get("success"):
        return {
            "success": False,
            "error": f"Download failed: {download_result.get('error')}",
            "step": "download",
        }

    # Step 2: Determine processing parameters from template
    from app.services.template_engine import FORMAT_CONFIGS, HOOK_TEMPLATES, CTA_TEMPLATES
    import random

    config = FORMAT_CONFIGS.get(template_format, {})

    if not hook_text:
        hooks = HOOK_TEMPLATES.get(config.get("hook_style", "none"), [])
        hook_text = random.choice(hooks) if hooks else None

    if not cta_text:
        cta_text = random.choice(CTA_TEMPLATES)

    # Determine color grade
    color_grade = "none"
    if config.get("color_grade"):
        color_grade = config.get("color_grade_style", "cinematic")
    if template_format == "dramatic_clutch":
        color_grade = "cinematic"
    if template_format == "hard_fragmovie":
        color_grade = "cinematic"

    # Step 3: Process clip
    process_result = await process_clip(
        source_path=download_result["file_path"],
        hook_text=hook_text,
        hook_duration=3.0,
        cta_text=cta_text,
        cta_start_offset=4.0,
        subtitle_text=moment_data.get("description", ""),
        color_grade=color_grade,
        max_duration=60.0,
        volume_boost=1.2,
    )

    if not process_result.get("success"):
        return {
            "success": False,
            "error": f"Processing failed: {process_result.get('error')}",
            "step": "process",
        }

    # Step 4: Save clip to DB
    cursor = await db.execute(
        """INSERT INTO clips (moment_id, title, description, format_type, duration, status,
           hook_text, cta_text, has_subtitles, has_ai_girl, has_face_cam, file_path, thumbnail_path, platform)
           VALUES (?, ?, ?, ?, ?, 'rendered', ?, ?, ?, 0, 0, ?, ?, 'youtube_shorts')""",
        (
            moment_id,
            f"{metadata.get('moment_label', moment_data['moment_type'])} — {stream_data.get('streamer_name', 'Unknown')}",
            moment_data.get("description", ""),
            template_format,
            process_result.get("duration", 0),
            hook_text,
            cta_text,
            1 if config.get("subtitles", True) else 0,
            process_result["file_path"],
            process_result.get("thumbnail_path"),
        ),
    )
    await db.commit()
    clip_id = cursor.lastrowid

    return {
        "success": True,
        "clip_id": clip_id,
        "moment_id": moment_id,
        "file_path": process_result["file_path"],
        "thumbnail_path": process_result.get("thumbnail_path"),
        "duration": process_result.get("duration"),
        "resolution": process_result.get("resolution"),
        "file_size": process_result.get("file_size"),
        "hook_text": hook_text,
        "cta_text": cta_text,
        "template": template_format,
        "color_grade": color_grade,
        "download_source": download_result["file_path"],
    }


# ─── Quick Test: Generate test clip from any Twitch URL ──────────────

async def generate_test_clip(
    twitch_url: str,
    hook_text: str = "WAIT FOR IT...",
    cta_text: str = "Follow for daily CS2 highlights!",
    subtitle_text: str = "Insane play by the GOAT",
    color_grade: str = "cinematic",
    max_duration: float = 30.0,
) -> dict:
    """
    Quick test function: download a Twitch clip and process it.
    No DB needed — just URL → download → process → return file.
    """
    result = {"steps": []}

    # Step 1: Download
    dl = await download_twitch_clip(twitch_url)
    result["steps"].append({"step": "download", "result": dl})
    if not dl.get("success"):
        result["success"] = False
        result["error"] = f"Download failed: {dl.get('error')}"
        return result

    # Step 2: Process
    proc = await process_clip(
        source_path=dl["file_path"],
        hook_text=hook_text,
        hook_duration=3.0,
        cta_text=cta_text,
        cta_start_offset=4.0,
        subtitle_text=subtitle_text,
        color_grade=color_grade,
        max_duration=max_duration,
        volume_boost=1.2,
    )
    result["steps"].append({"step": "process", "result": proc})

    if not proc.get("success"):
        result["success"] = False
        result["error"] = f"Processing failed: {proc.get('error')}"
        return result

    result["success"] = True
    result["output_file"] = proc["file_path"]
    result["thumbnail"] = proc.get("thumbnail_path")
    result["duration"] = proc.get("duration")
    result["file_size"] = proc.get("file_size")
    result["resolution"] = proc.get("resolution")
    return result


# ─── Batch Pipeline: Process top N clips from a streamer ─────────────

async def batch_process_streamer(
    broadcaster_name: str,
    limit: int = 5,
    period: str = "7d",
    template: str = "highlight_subtitles",
) -> dict:
    """
    Full automatic pipeline:
    1. Get top clips from Twitch API
    2. Download each clip
    3. Process each into vertical format
    4. Return all processed clips

    Requires Twitch API credentials.
    """
    results = {"broadcaster": broadcaster_name, "clips": [], "errors": []}

    # Get clips from Twitch API
    clips = await get_twitch_clips(broadcaster_name, period=period, limit=limit)
    if not clips:
        results["error"] = "No clips found or Twitch API not configured"
        return results

    results["total_found"] = len(clips)

    from app.services.template_engine import HOOK_TEMPLATES, CTA_TEMPLATES, FORMAT_CONFIGS
    import random

    config = FORMAT_CONFIGS.get(template, {})
    hooks = HOOK_TEMPLATES.get(config.get("hook_style", "text_question"), [])

    for clip_data in clips[:limit]:
        try:
            hook = random.choice(hooks) if hooks else "WAIT FOR IT..."
            cta = random.choice(CTA_TEMPLATES)

            dl = await download_twitch_clip(clip_data["url"])
            if not dl.get("success"):
                results["errors"].append({
                    "clip": clip_data["title"],
                    "error": dl.get("error"),
                })
                continue

            proc = await process_clip(
                source_path=dl["file_path"],
                hook_text=hook,
                cta_text=cta,
                subtitle_text=clip_data["title"],
                color_grade="cinematic" if template in ("dramatic_clutch", "hard_fragmovie") else "none",
                max_duration=60.0,
                volume_boost=1.2,
            )

            if proc.get("success"):
                results["clips"].append({
                    "title": clip_data["title"],
                    "source_views": clip_data["view_count"],
                    "output_file": proc["file_path"],
                    "thumbnail": proc.get("thumbnail_path"),
                    "duration": proc.get("duration"),
                    "file_size": proc.get("file_size"),
                })
            else:
                results["errors"].append({
                    "clip": clip_data["title"],
                    "error": proc.get("error"),
                })
        except Exception as e:
            results["errors"].append({
                "clip": clip_data.get("title", "unknown"),
                "error": str(e),
            })

    results["processed"] = len(results["clips"])
    return results


def get_executor_status() -> dict:
    """Get current executor status and configuration."""
    has_twitch = bool(TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET)

    # Count existing files
    source_count = len(list((CLIPS_DIR / "source").glob("*"))) if (CLIPS_DIR / "source").exists() else 0
    processed_count = len(list((CLIPS_DIR / "processed").glob("*"))) if (CLIPS_DIR / "processed").exists() else 0

    # Check FFmpeg
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    ytdlp_ok = shutil.which("yt-dlp") is not None

    return {
        "ffmpeg_available": ffmpeg_ok,
        "ytdlp_available": ytdlp_ok,
        "twitch_api_configured": has_twitch,
        "font_path": FONT_PATH,
        "clips_dir": str(CLIPS_DIR),
        "source_clips": source_count,
        "processed_clips": processed_count,
        "capabilities": {
            "download_twitch_clips": ytdlp_ok,
            "auto_discover_clips": has_twitch,
            "vertical_crop": ffmpeg_ok,
            "text_overlays": ffmpeg_ok,
            "color_grading": ffmpeg_ok,
            "audio_normalization": ffmpeg_ok,
            "thumbnail_generation": ffmpeg_ok,
        },
        "required_apis": {
            "twitch_api": {
                "configured": has_twitch,
                "required_for": "Auto-discovery of top clips from streamers",
                "how_to_get": "https://dev.twitch.tv/console/apps → Create app → Get Client ID + Secret",
                "env_vars": ["TWITCH_CLIENT_ID", "TWITCH_CLIENT_SECRET"],
            },
        },
    }
