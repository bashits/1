"""
Autonomous CS2 Reel Pipeline — Full Chain Orchestrator

The SINGLE entry point that chains everything:
1. Twitch 24h analysis → validate freshness (GATE: block if stale)
2. Select top 3 streams by viewers
3. Discover best clips from those streams (Twitch Clips API)
4. Score moments from clips (multi-signal: views, recency, duration)
5. Analyze current trends (formats, fonts, music, hooks, pacing)
6. Match best template to each moment based on trend data
7. Assemble final reel (music + effects, no voice) — stream-process, no local VOD storage

Validation gates:
- GATE 1: Twitch data must be REAL (not fallback/known patterns)
- GATE 2: At least 1 live CS2 stream must exist
- GATE 3: At least 1 clip must be found from top streamers
- GATE 4: Trend analysis must return real scraped data (not just known patterns)

If ANY gate fails → pipeline refuses to run and returns detailed error.
"""

import asyncio
import json
import logging
import os
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger("autonomous_pipeline")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: DATA FRESHNESS VALIDATOR
# ═══════════════════════════════════════════════════════════════════════

class FreshnessGate:
    """Validates that all data sources are fresh before pipeline runs."""

    MAX_TWITCH_AGE_SECONDS = 3600       # 1 hour — Twitch data must be < 1h old
    MAX_TREND_AGE_SECONDS = 7200        # 2 hours — trend analysis can be slightly older
    MIN_LIVE_STREAMS = 1                # At least 1 live CS2 stream
    MIN_CLIPS = 1                       # At least 1 clip found

    @staticmethod
    def validate_twitch_data(twitch_streams: list[dict]) -> dict:
        """GATE 1+2: Validate Twitch streams are real and fresh."""
        if not twitch_streams:
            return {
                "passed": False,
                "gate": "twitch_data",
                "error": "No Twitch CS2 streams found. Cannot proceed without live data.",
                "remedy": "Check Twitch API credentials or wait for CS2 streams to go live.",
            }

        # Check if data is from real sources (no static fallback allowed)
        sources = set(s.get("source", "unknown") for s in twitch_streams)
        real_sources = {"twitch_api", "twitchtracker", "twitchtracker_scrape", "twitch_tracker", "twitch_tracker_scrape"}
        has_real_data = bool(sources & real_sources)

        if not has_real_data:
            return {
                "passed": False,
                "gate": "twitch_freshness",
                "error": "Twitch data is not from live API/scraping sources (static fallback detected).",
                "sources_found": list(sources),
                "remedy": "Set TWITCH_CLIENT_ID + TWITCH_CLIENT_SECRET or fix TwitchTracker scraping.",
            }

        # Visible freshness timestamp must exist
        fetched_at_values = [s.get("fetched_at") for s in twitch_streams if s.get("fetched_at")]
        if not fetched_at_values:
            return {
                "passed": False,
                "gate": "twitch_timestamp_missing",
                "error": "Twitch streams missing fetched_at timestamp - freshness is not visible.",
                "remedy": "Ensure scrape_twitch_cs2_streams() attaches fetched_at to each stream.",
            }

        newest_fetched_at = None
        newest_dt = None
        for fetched_at in fetched_at_values:
            try:
                dt = datetime.fromisoformat(str(fetched_at))
                if dt.tzinfo is not None:
                    dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
                if newest_dt is None or dt > newest_dt:
                    newest_dt = dt
                    newest_fetched_at = str(fetched_at)
            except (ValueError, TypeError):
                continue

        if newest_dt is None:
            return {
                "passed": False,
                "gate": "twitch_timestamp_invalid",
                "error": "Twitch streams have invalid fetched_at timestamps.",
                "remedy": "Ensure fetched_at is ISO format.",
            }

        age_seconds = (datetime.utcnow() - newest_dt).total_seconds()
        if age_seconds > FreshnessGate.MAX_TWITCH_AGE_SECONDS:
            return {
                "passed": False,
                "gate": "twitch_freshness",
                "error": f"Twitch stream data is {int(age_seconds)}s old (max: {FreshnessGate.MAX_TWITCH_AGE_SECONDS}s).",
                "fetched_at": newest_fetched_at,
                "remedy": "Re-scrape Twitch streams or clear cache.",
            }

        live_streams = [s for s in twitch_streams if s.get("is_live")]
        if len(live_streams) < FreshnessGate.MIN_LIVE_STREAMS:
            return {
                "passed": False,
                "gate": "twitch_min_live_streams",
                "error": f"Only {len(live_streams)} live CS2 streams found, need at least {FreshnessGate.MIN_LIVE_STREAMS}.",
                "remedy": "Wait for CS2 streamers to go live on Twitch.",
            }

        total_viewers = 0
        for s in live_streams:
            try:
                total_viewers += int(s.get("viewers") or 0)
            except (ValueError, TypeError):
                continue

        # If viewer counts are missing/unknown (0), we can't pick top streams reliably.
        if total_viewers <= 0:
            return {
                "passed": False,
                "gate": "twitch_viewers_missing",
                "error": "Viewer counts are missing/unknown - cannot proceed without visible current stats.",
                "sources_found": list(sources),
                "remedy": "Use Twitch API (best) or improve TwitchTracker viewer parsing.",
            }

        # Sort for reporting
        live_sorted = sorted(live_streams, key=lambda s: int(s.get("viewers") or 0), reverse=True)

        return {
            "passed": True,
            "gate": "twitch_data",
            "streams_count": len(live_streams),
            "sources": list(sources),
            "total_viewers": total_viewers,
            "top_streamer": live_sorted[0].get("name", "Unknown"),
            "fetched_at": newest_fetched_at,
        }

    @staticmethod
    def validate_clips(clips: list[dict]) -> dict:
        """GATE 3: Validate that real clips were found."""
        if not clips:
            return {
                "passed": False,
                "gate": "clips_found",
                "error": "No clips found from top CS2 streamers in the last 24h.",
                "remedy": "Try a longer period (7d) or check that streamers have clips enabled.",
            }

        return {
            "passed": True,
            "gate": "clips_found",
            "clips_count": len(clips),
            "top_clip_views": clips[0].get("view_count", 0),
            "top_clip_title": clips[0].get("title", "Unknown")[:60],
        }

    @staticmethod
    def validate_trends(trend_data: dict) -> dict:
        """GATE 4: Validate that trend analysis has current data."""
        if not trend_data:
            return {
                "passed": False,
                "gate": "trend_analysis",
                "error": "Trend analysis returned no data.",
                "remedy": "Run /api/montage/trends/live to populate trend cache.",
            }

        recs = trend_data.get("recommendations", {})
        data_type = recs.get("data_type", "unknown")
        meta = trend_data.get("meta", {})
        total_data_points = meta.get("total_data_points", 0)

        # Must have SOME real datapoints, otherwise this is just defaults.
        if not total_data_points:
            return {
                "passed": False,
                "gate": "trend_empty",
                "error": "Trend analysis has 0 data points - cannot proceed without fresh stats.",
                "remedy": "Ensure Twitch/YouTube scraping returns real items.",
            }

        twitch_source = meta.get("twitch_source", "none")
        if twitch_source in ("known_db", "none", "unknown"):
            return {
                "passed": False,
                "gate": "trend_twitch_source",
                "error": f"Trend analysis is based on non-live Twitch source: {twitch_source}.",
                "remedy": "Configure TWITCH_CLIENT_ID + TWITCH_CLIENT_SECRET or fix Twitch scraping.",
            }

        # Check freshness of scraped_at timestamp
        scraped_at_str = meta.get("scraped_at", "")
        if scraped_at_str:
            try:
                scraped_at = datetime.fromisoformat(scraped_at_str)
                age_seconds = (datetime.utcnow() - scraped_at).total_seconds()
                if age_seconds > FreshnessGate.MAX_TREND_AGE_SECONDS:
                    return {
                        "passed": False,
                        "gate": "trend_freshness",
                        "error": f"Trend data is {int(age_seconds)}s old (max: {FreshnessGate.MAX_TREND_AGE_SECONDS}s).",
                        "scraped_at": scraped_at_str,
                        "remedy": "Run fresh trend analysis via /api/montage/trends/live.",
                    }
            except (ValueError, TypeError):
                pass

        return {
            "passed": True,
            "gate": "trend_analysis",
            "data_type": data_type,
            "total_data_points": total_data_points,
            "top_format": trend_data.get("format_analysis", {}).get("top_format", "unknown"),
        }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: STREAM & CLIP DISCOVERY
# ═══════════════════════════════════════════════════════════════════════

async def _fetch_top_streams(
    twitch_client_id: str = "",
    twitch_client_secret: str = "",
    top_n: int = 3,
) -> dict:
    """
    Step 1: Fetch top N CS2 streams from Twitch (last 24h).
    Uses the trend_analyzer's scrape_twitch_cs2_streams which has
    API → TwitchTracker → known DB fallback chain.
    """
    from app.services.trend_analyzer import scrape_twitch_cs2_streams

    streams = await scrape_twitch_cs2_streams(twitch_client_id, twitch_client_secret)

    # Sort by viewers descending, take top N
    streams.sort(key=lambda s: s.get("viewers", 0), reverse=True)
    top_streams = streams[:top_n]

    return {
        "all_streams": streams,
        "top_streams": top_streams,
        "total_found": len(streams),
    }


async def _fetch_clips_from_streams(
    top_streams: list[dict],
    twitch_client_id: str = "",
    twitch_client_secret: str = "",
    period: str = "24h",
    clips_per_stream: int = 5,
) -> dict:
    """
    Step 2: Get best clips from top streams via Twitch Clips API.
    Streams clips directly (no local VOD storage).
    """
    from app.services.clip_montage import discover_trending_cs2_clips

    # discover_trending_cs2_clips already does OAuth + clips API
    result = await discover_trending_cs2_clips(
        twitch_client_id=twitch_client_id,
        twitch_client_secret=twitch_client_secret,
        limit=clips_per_stream * len(top_streams),
        period=period,
    )

    if not result.get("success"):
        return {
            "success": False,
            "error": result.get("error", "Clip discovery failed"),
            "clips": [],
        }

    return {
        "success": True,
        "clips": result.get("clips", []),
        "total_found": result.get("total_found", 0),
        "streamers_checked": result.get("streamers_checked", []),
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: MOMENT SCORING (from real clips, not simulated)
# ═══════════════════════════════════════════════════════════════════════

def _score_clip_as_moment(clip: dict) -> dict:
    """
    Score a real Twitch clip as a 'moment' using available signals:
    - view_count (popularity signal)
    - duration (clip length — shorter = more punchy)
    - broadcaster_viewers (stream popularity at time of clip)
    - recency (newer = more relevant)
    - title keywords (detect moment type from title)

    This replaces the simulated moment_detector for real clips.
    """
    title = clip.get("title", "").lower()
    views = clip.get("view_count", 0)
    duration = clip.get("duration", 30)
    broadcaster_viewers = clip.get("broadcaster_viewers", 0)

    # Detect moment type from title keywords
    moment_type = "insane_play"  # default
    type_keywords = {
        "ace": ["ace", "эйс", "5k", "5 kill"],
        "clutch": ["clutch", "клатч", "1v", "1vs", "retake"],
        "multi_kill": ["3k", "4k", "triple", "quad", "spray", "transfer"],
        "headshot_sequence": ["headshot", "hs", "one tap", "flick"],
        "knife_kill": ["knife", "нож", "blade"],
        "wallbang": ["wallbang", "wall bang", "through wall"],
        "meme_fail": ["fail", "funny", "lol", "wtf", "фейл", "смешно"],
        "emotional_reaction": ["react", "scream", "rage", "omg", "insane"],
        "toxic_moment": ["toxic", "trash talk", "bm"],
        "insane_spray": ["spray", "control", "burst"],
    }

    for mtype, keywords in type_keywords.items():
        if any(kw in title for kw in keywords):
            moment_type = mtype
            break

    # Score components
    # 1. View score (log scale, max at ~100k views)
    import math
    view_score = min(0.4, math.log10(max(views, 1)) / 12.5)

    # 2. Duration score (15-30s clips score highest for reels)
    if 10 <= duration <= 35:
        duration_score = 0.2
    elif duration <= 60:
        duration_score = 0.1
    else:
        duration_score = 0.05

    # 3. Broadcaster popularity
    broadcaster_score = min(0.15, broadcaster_viewers / 100000)

    # 4. Moment type base score
    from app.services.moment_detector import MOMENT_SCORING
    type_scoring = MOMENT_SCORING.get(moment_type, {"base": 0.55, "viral_mult": 1.0})
    type_score = type_scoring["base"] * 0.25

    # Composite
    composite = view_score + duration_score + broadcaster_score + type_score

    # Viral multiplier for exceptional clips
    if views > 10000:
        composite *= type_scoring.get("viral_mult", 1.0)

    composite = min(1.0, composite)

    return {
        "clip": clip,
        "moment_type": moment_type,
        "score": round(composite, 3),
        "breakdown": {
            "view_score": round(view_score, 3),
            "duration_score": round(duration_score, 3),
            "broadcaster_score": round(broadcaster_score, 3),
            "type_score": round(type_score, 3),
        },
        "detected_type_label": MOMENT_SCORING.get(moment_type, {}).get("label", moment_type),
    }


def _rank_moments(clips: list[dict]) -> list[dict]:
    """Rank all clips as moments and return sorted by score."""
    scored = [_score_clip_as_moment(c) for c in clips]
    scored.sort(key=lambda m: m["score"], reverse=True)
    return scored


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: TREND-BASED TEMPLATE SELECTION
# ═══════════════════════════════════════════════════════════════════════

def _select_template_for_moment(
    moment: dict,
    trend_recommendations: dict,
) -> dict:
    """
    Intelligently select the best montage template for a moment
    based on current trend analysis.

    Uses:
    - moment type → base template affinity
    - trend preferred_style → boost matching templates
    - recommended_pacing → adjust duration
    - recommended_color_grade → pass to montage
    - recommended_music_style → pass to montage
    """
    moment_type = moment.get("moment_type", "insane_play")

    # Base template affinities per moment type
    type_templates = {
        "ace": ["dramatic_ace", "highlight_react", "quick_kill"],
        "clutch": ["highlight_react", "dramatic_ace", "girl_commentary"],
        "multi_kill": ["highlight_react", "quick_kill", "meme_edit"],
        "headshot_sequence": ["quick_kill", "highlight_react"],
        "knife_kill": ["meme_edit", "highlight_react"],
        "wallbang": ["quick_kill", "meme_edit"],
        "meme_fail": ["fail_compilation", "meme_edit"],
        "emotional_reaction": ["highlight_react", "girl_commentary"],
        "toxic_moment": ["meme_edit", "fail_compilation"],
        "insane_play": ["highlight_react", "dramatic_ace", "quick_kill"],
        "insane_spray": ["highlight_react", "quick_kill"],
    }

    candidates = type_templates.get(moment_type, ["highlight_react"])

    # Boost template that matches trending style
    trend_style = trend_recommendations.get("preferred_style", "")
    trend_template_map = {
        "sigma_edit": "highlight_react",
        "highlight_react": "highlight_react",
        "pro_clutch": "dramatic_ace",
        "funny_moments": "fail_compilation",
        "ace_compilation": "dramatic_ace",
        "tutorial_tip": "quick_kill",
    }
    trend_preferred = trend_template_map.get(trend_style, "")
    if trend_preferred and trend_preferred in candidates:
        # Move to front
        candidates.remove(trend_preferred)
        candidates.insert(0, trend_preferred)

    selected_template = candidates[0]

    # Build design config from trends
    pacing = trend_recommendations.get("recommended_pacing", "medium")
    duration_map = {"fast": 12, "medium": 15, "build_up": 20}
    target_duration = duration_map.get(pacing, 15)

    # Adjust duration from trend recommendations
    trend_duration = trend_recommendations.get("recommended_duration_sec")
    if trend_duration and isinstance(trend_duration, (int, float)):
        target_duration = min(int(trend_duration), 30)  # Cap at 30s for reels

    return {
        "template_id": selected_template,
        "moment_type": moment_type,
        "target_duration": target_duration,
        "color_grade": trend_recommendations.get("recommended_color_grade", "cinematic"),
        "music_style": trend_recommendations.get("recommended_music_style", "electronic"),
        "font_style": trend_recommendations.get("recommended_font_style", "glow_outline"),
        "hook_type": trend_recommendations.get("recommended_hook", "text_hook"),
        "pacing": pacing,
        "trend_influence": {
            "preferred_style": trend_style,
            "mapped_template": trend_preferred,
            "candidates_considered": candidates,
        },
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 5: REEL ASSEMBLY (no voice, music + effects only)
# ═══════════════════════════════════════════════════════════════════════

async def _assemble_reel(
    clip_url: str,
    template_config: dict,
    hook_text: str = "",
    cta_text: str = "Follow for daily CS2 highlights!",
) -> dict:
    """
    Assemble final reel from clip URL using selected template.
    No voice/girl overlay — just gameplay + music + effects + text.
    Stream-processes the clip (downloads to temp, processes, deletes source).
    """
    from app.services.clip_montage import create_montage

    result = await create_montage(
        clip_url=clip_url,
        template_id=template_config["template_id"],
        moment_type=template_config["moment_type"],
        hook_text=hook_text,
        cta_text=cta_text,
        subtitle_text="",
        start_time=0.0,
        max_duration=float(template_config.get("target_duration", 15)),
        enable_girl=False,  # No girl overlay in autonomous mode
        color_grade=template_config.get("color_grade", "cinematic"),
    )

    return result


# ═══════════════════════════════════════════════════════════════════════
# SECTION 6: HOOK TEXT GENERATION (from trends + moment type)
# ═══════════════════════════════════════════════════════════════════════

def _generate_hook_from_trends(
    moment_type: str,
    clip_title: str,
    broadcaster_name: str,
    hook_type: str = "text_hook",
) -> str:
    """Generate attention-grabbing hook text based on moment type and trends."""
    hooks_by_type = {
        "ace": [
            "5 KILLS. 0 DEATHS.",
            "THE PERFECT ACE",
            "HE DELETED THE ENTIRE TEAM",
            f"{broadcaster_name.upper()} GOES CRAZY",
        ],
        "clutch": [
            "1 vs 5. NO CHANCE... RIGHT?",
            "IMPOSSIBLE CLUTCH",
            "THEY THOUGHT IT WAS OVER...",
            "WATCH THIS CLUTCH",
        ],
        "multi_kill": [
            "SPRAY TRANSFER GOD",
            "3K IN 2 SECONDS",
            "THEY COULDN'T STOP HIM",
            "MULTI-KILL MADNESS",
        ],
        "meme_fail": [
            "WAIT FOR IT...",
            "THIS WENT SO WRONG",
            "HE REALLY DID THAT",
            "BIGGEST FAIL TODAY",
        ],
        "knife_kill": [
            "THE DISRESPECT",
            "KNIFE ONLY",
            "HE BROUGHT A KNIFE...",
        ],
        "insane_play": [
            "WAIT FOR IT...",
            "THIS IS WHY HE'S #1",
            "INSANE PLAY",
            f"{broadcaster_name.upper()} IS DIFFERENT",
        ],
    }

    # Get hooks for this moment type, fallback to insane_play
    pool = hooks_by_type.get(moment_type, hooks_by_type["insane_play"])

    # Hook type variations
    if hook_type == "question_hook":
        pool = [
            "CAN HE DO IT?",
            "IS THIS THE BEST PLAY EVER?",
            "HOW IS THIS POSSIBLE?",
            f"IS {broadcaster_name.upper()} THE GOAT?",
        ]
    elif hook_type == "pov_hook":
        pool = [
            "POV: YOU'RE WATCHING A GOD",
            "POV: RANKED LOBBY DESTROYER",
            f"POV: {broadcaster_name.upper()} IN YOUR GAME",
        ]

    # Deterministic selection (no randomness). Use a stable hash so the same
    # clip title consistently produces the same hook.
    if not pool:
        return clip_title[:60] if clip_title else "CS2 HIGHLIGHT"
    key = f"{moment_type}|{broadcaster_name}|{clip_title}".encode("utf-8", errors="ignore")
    digest = hashlib.md5(key).hexdigest()
    idx = int(digest[:8], 16) % len(pool)
    return pool[idx]


# ═══════════════════════════════════════════════════════════════════════
# SECTION 7: THE MAIN ORCHESTRATOR
# ═══════════════════════════════════════════════════════════════════════

async def run_autonomous_pipeline(
    twitch_client_id: str = "",
    twitch_client_secret: str = "",
    youtube_api_key: str = "",
    top_streams_count: int = 3,
    clips_per_stream: int = 5,
    period: str = "24h",
    max_reels: int = 1,
    target_duration: float = 15.0,
    cta_text: str = "Follow for daily CS2 highlights!",
    skip_freshness_check: bool = False,
) -> dict:
    """
    MAIN ORCHESTRATOR — runs the complete autonomous pipeline.

    Full chain:
    1. Fetch Twitch CS2 streams (last 24h) → GATE: validate freshness
    2. Select top N streams by viewer count
    3. Discover best clips from those streams → GATE: validate clips exist
    4. Score clips as moments (real data, not simulated)
    5. Analyze current trends → GATE: validate trend freshness
    6. Select best template for top moment based on trends
    7. Generate hook text from trends + moment type
    8. Assemble final reel (music + effects, no voice)

    Returns:
        Complete pipeline result with reel output, or gate failure details.
    """
    pipeline_id = uuid.uuid4().hex[:12]
    started_at = datetime.utcnow()
    steps = []
    gates = []

    logger.info(f"[Pipeline {pipeline_id}] Starting autonomous pipeline")

    # Read API keys from env if not provided
    twitch_client_id = twitch_client_id or os.environ.get("TWITCH_CLIENT_ID", "")
    twitch_client_secret = twitch_client_secret or os.environ.get("TWITCH_CLIENT_SECRET", "")
    youtube_api_key = youtube_api_key or os.environ.get("YOUTUBE_API_KEY", "")

    # ══════════════════════════════════════════════════════════════════
    # STEP 1: Fetch Twitch CS2 streams
    # ══════════════════════════════════════════════════════════════════
    step1 = {"step": 1, "name": "fetch_twitch_streams", "status": "running"}
    steps.append(step1)

    try:
        stream_result = await _fetch_top_streams(
            twitch_client_id, twitch_client_secret, top_streams_count
        )
        step1["status"] = "success"
        step1["streams_found"] = stream_result["total_found"]
        step1["top_streams"] = [
            {"name": s.get("name", "?"), "viewers": s.get("viewers", 0)}
            for s in stream_result["top_streams"]
        ]
    except Exception as e:
        step1["status"] = "failed"
        step1["error"] = str(e)
        return _pipeline_result(pipeline_id, started_at, steps, gates, success=False,
                                error=f"Step 1 failed: {e}")

    # GATE 1+2: Validate Twitch data freshness
    gate_twitch = FreshnessGate.validate_twitch_data(stream_result["all_streams"])
    gates.append(gate_twitch)

    if not gate_twitch["passed"] and not skip_freshness_check:
        logger.warning(f"[Pipeline {pipeline_id}] GATE FAILED: {gate_twitch['gate']}")
        return _pipeline_result(pipeline_id, started_at, steps, gates, success=False,
                                error=f"Freshness gate failed: {gate_twitch['error']}",
                                gate_failure=gate_twitch)

    # ══════════════════════════════════════════════════════════════════
    # STEP 2: Discover clips from top streams
    # ══════════════════════════════════════════════════════════════════
    step2 = {"step": 2, "name": "discover_clips", "status": "running"}
    steps.append(step2)

    try:
        clips_result = await _fetch_clips_from_streams(
            stream_result["top_streams"],
            twitch_client_id, twitch_client_secret,
            period=period,
            clips_per_stream=clips_per_stream,
        )
        step2["status"] = "success" if clips_result.get("success") else "failed"
        step2["clips_found"] = len(clips_result.get("clips", []))
        step2["streamers_checked"] = clips_result.get("streamers_checked", [])
        if not clips_result.get("success"):
            step2["error"] = clips_result.get("error", "Unknown error")
    except Exception as e:
        step2["status"] = "failed"
        step2["error"] = str(e)
        clips_result = {"success": False, "clips": [], "error": str(e)}

    # GATE 3: Validate clips exist
    gate_clips = FreshnessGate.validate_clips(clips_result.get("clips", []))
    gates.append(gate_clips)

    if not gate_clips["passed"] and not skip_freshness_check:
        logger.warning(f"[Pipeline {pipeline_id}] GATE FAILED: {gate_clips['gate']}")
        return _pipeline_result(pipeline_id, started_at, steps, gates, success=False,
                                error=f"Clip gate failed: {gate_clips['error']}",
                                gate_failure=gate_clips)

    # ══════════════════════════════════════════════════════════════════
    # STEP 3: Score clips as moments
    # ══════════════════════════════════════════════════════════════════
    step3 = {"step": 3, "name": "score_moments", "status": "running"}
    steps.append(step3)

    try:
        ranked_moments = _rank_moments(clips_result.get("clips", []))
        step3["status"] = "success"
        step3["moments_scored"] = len(ranked_moments)
        step3["top_moment"] = {
            "type": ranked_moments[0]["moment_type"] if ranked_moments else "none",
            "score": ranked_moments[0]["score"] if ranked_moments else 0,
            "clip_title": ranked_moments[0]["clip"]["title"][:60] if ranked_moments else "none",
        }
    except Exception as e:
        step3["status"] = "failed"
        step3["error"] = str(e)
        return _pipeline_result(pipeline_id, started_at, steps, gates, success=False,
                                error=f"Moment scoring failed: {e}")

    # ══════════════════════════════════════════════════════════════════
    # STEP 4: Analyze current trends
    # ══════════════════════════════════════════════════════════════════
    step4 = {"step": 4, "name": "analyze_trends", "status": "running"}
    steps.append(step4)

    try:
        from app.services.trend_analyzer import analyze_current_trends
        trend_data = await analyze_current_trends(
            twitch_client_id, twitch_secret=twitch_client_secret,
            youtube_api_key=youtube_api_key,
        )
        step4["status"] = "success"
        step4["top_format"] = trend_data.get("format_analysis", {}).get("top_format", "unknown")
        step4["data_sources"] = trend_data.get("meta", {}).get("total_data_points", 0)
    except Exception as e:
        step4["status"] = "failed"
        step4["error"] = str(e)
        trend_data = {}

    # GATE 4: Validate trend data (soft gate — warn but allow known patterns)
    gate_trends = FreshnessGate.validate_trends(trend_data)
    gates.append(gate_trends)

    if not gate_trends["passed"] and not skip_freshness_check:
        logger.warning(f"[Pipeline {pipeline_id}] GATE FAILED: {gate_trends['gate']}")
        return _pipeline_result(pipeline_id, started_at, steps, gates, success=False,
                                error=f"Trend gate failed: {gate_trends['error']}",
                                gate_failure=gate_trends)

    # Extract trend recommendations
    trend_recs = trend_data.get("recommendations", {})

    # ══════════════════════════════════════════════════════════════════
    # STEP 5: Select template for best moment(s) based on trends
    # ══════════════════════════════════════════════════════════════════
    step5 = {"step": 5, "name": "select_templates", "status": "running"}
    steps.append(step5)

    reel_plans = []
    try:
        for moment in ranked_moments[:max_reels]:
            template_config = _select_template_for_moment(moment, trend_recs)

            # Override target_duration if user specified
            if target_duration and target_duration != 15.0:
                template_config["target_duration"] = int(target_duration)

            # Generate hook text
            clip = moment["clip"]
            hook = _generate_hook_from_trends(
                moment["moment_type"],
                clip.get("title", ""),
                clip.get("broadcaster_name", "Unknown"),
                template_config.get("hook_type", "text_hook"),
            )

            reel_plans.append({
                "moment": moment,
                "template": template_config,
                "hook_text": hook,
                "clip_url": clip.get("download_url") or clip.get("url", ""),
            })

        step5["status"] = "success"
        step5["plans"] = [
            {
                "clip": p["moment"]["clip"]["title"][:50],
                "template": p["template"]["template_id"],
                "hook": p["hook_text"],
                "moment_type": p["moment"]["moment_type"],
            }
            for p in reel_plans
        ]
    except Exception as e:
        step5["status"] = "failed"
        step5["error"] = str(e)
        return _pipeline_result(pipeline_id, started_at, steps, gates, success=False,
                                error=f"Template selection failed: {e}")

    if not reel_plans:
        return _pipeline_result(pipeline_id, started_at, steps, gates, success=False,
                                error="No valid reel plans could be created")

    # ══════════════════════════════════════════════════════════════════
    # STEP 6: Assemble final reel(s)
    # ══════════════════════════════════════════════════════════════════
    step6 = {"step": 6, "name": "assemble_reels", "status": "running"}
    steps.append(step6)

    assembled_reels = []
    for plan in reel_plans:
        if not plan["clip_url"]:
            continue

        try:
            reel_result = await _assemble_reel(
                clip_url=plan["clip_url"],
                template_config=plan["template"],
                hook_text=plan["hook_text"],
                cta_text=cta_text,
            )

            if reel_result.get("success"):
                assembled_reels.append({
                    "output_path": reel_result.get("output_path"),
                    "duration": reel_result.get("duration"),
                    "resolution": reel_result.get("resolution"),
                    "file_size": reel_result.get("file_size"),
                    "template": plan["template"]["template_id"],
                    "moment_type": plan["moment"]["moment_type"],
                    "clip_source": {
                        "title": plan["moment"]["clip"]["title"],
                        "broadcaster": plan["moment"]["clip"].get("broadcaster_name", "Unknown"),
                        "views": plan["moment"]["clip"].get("view_count", 0),
                    },
                    "hook_text": plan["hook_text"],
                    "trend_influence": plan["template"].get("trend_influence", {}),
                    "trend_config": {
                        "color_grade": plan["template"].get("color_grade"),
                        "music_style": plan["template"].get("music_style"),
                        "pacing": plan["template"].get("pacing"),
                    },
                    "total_cost": reel_result.get("total_cost", 0),
                })
            else:
                assembled_reels.append({
                    "success": False,
                    "error": reel_result.get("error", "Assembly failed"),
                    "clip_title": plan["moment"]["clip"]["title"][:50],
                })
        except Exception as e:
            assembled_reels.append({
                "success": False,
                "error": str(e),
                "clip_title": plan["moment"]["clip"]["title"][:50],
            })

    step6["status"] = "success" if any(r.get("output_path") for r in assembled_reels) else "failed"
    step6["reels_assembled"] = len([r for r in assembled_reels if r.get("output_path")])
    step6["reels_failed"] = len([r for r in assembled_reels if not r.get("output_path")])

    success = step6["reels_assembled"] > 0

    return _pipeline_result(
        pipeline_id, started_at, steps, gates,
        success=success,
        reels=assembled_reels,
        trend_snapshot={
            "top_format": trend_data.get("format_analysis", {}).get("top_format"),
            "recommended_pacing": trend_recs.get("recommended_pacing"),
            "recommended_color": trend_recs.get("recommended_color_grade"),
            "recommended_music": trend_recs.get("recommended_music_style"),
            "twitch_top_streamer": trend_recs.get("twitch_insight", {}).get("top_streamer"),
            "twitch_avg_viewers": trend_recs.get("twitch_insight", {}).get("avg_viewers"),
        },
    )


# ═══════════════════════════════════════════════════════════════════════
# SECTION 8: PIPELINE STATUS & DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════

def _pipeline_result(
    pipeline_id: str,
    started_at: datetime,
    steps: list,
    gates: list,
    success: bool = False,
    error: str = "",
    gate_failure: dict | None = None,
    reels: list | None = None,
    trend_snapshot: dict | None = None,
) -> dict:
    """Build standardized pipeline result."""
    elapsed = (datetime.utcnow() - started_at).total_seconds()
    return {
        "pipeline_id": pipeline_id,
        "success": success,
        "error": error or None,
        "gate_failure": gate_failure,
        "elapsed_seconds": round(elapsed, 1),
        "started_at": started_at.isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
        "steps": steps,
        "gates": gates,
        "gates_passed": all(g.get("passed", False) for g in gates),
        "reels": reels or [],
        "reels_count": len([r for r in (reels or []) if r.get("output_path")]),
        "trend_snapshot": trend_snapshot,
    }


async def get_pipeline_readiness(
    twitch_client_id: str = "",
    twitch_client_secret: str = "",
) -> dict:
    """
    Pre-flight check: verify all systems are ready before running pipeline.
    Returns readiness status for each component.
    """
    import shutil

    twitch_id = twitch_client_id or os.environ.get("TWITCH_CLIENT_ID", "")
    twitch_secret = twitch_client_secret or os.environ.get("TWITCH_CLIENT_SECRET", "")

    checks = {
        "twitch_api": {
            "configured": bool(twitch_id and twitch_secret),
            "required": True,
            "description": "Twitch API credentials for stream/clip discovery",
        },
        "ffmpeg": {
            "configured": shutil.which("ffmpeg") is not None,
            "required": True,
            "description": "FFmpeg for video processing",
        },
        "yt_dlp": {
            "configured": shutil.which("yt-dlp") is not None,
            "required": True,
            "description": "yt-dlp for clip downloading",
        },
        "trend_cache": {
            "configured": False,
            "required": False,
            "description": "Trend analysis cache (will be populated on first run)",
        },
    }

    # Check trend cache
    try:
        from app.services.trend_analyzer import get_cache_status
        cache_status = get_cache_status()
        checks["trend_cache"]["configured"] = any(
            v.get("cached", False) for v in cache_status.values() if isinstance(v, dict)
        )
        checks["trend_cache"]["details"] = cache_status
    except Exception:
        pass

    all_required_ok = all(
        c["configured"] for c in checks.values() if c["required"]
    )

    return {
        "ready": all_required_ok,
        "checks": checks,
        "missing": [
            k for k, v in checks.items()
            if v["required"] and not v["configured"]
        ],
    }
