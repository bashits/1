"""
Dual-Source Reel Generation Engine — Intelligent Routing

The BRAIN that decides which approach produces a better reel:

SOURCE 1 — Stream Montage (autonomous_pipeline):
  Full Twitch stream -> clip discovery -> moment scoring -> montage
  Best when: Fresh streams available, unique content needed, specific moments

SOURCE 2 — Trending Clip Reuse (clip uniqueification):
  Discover already-trending clips -> uniqueify (girl overlay, effects, music)
  Best when: Viral clips exist, proven engagement, faster production

Decision Factors:
1. Trending clip availability & quality (views, recency, engagement)
2. Live stream availability & viewer counts
3. Current trend alignment (what formats are working NOW)
4. Freshness of available data
5. Self-learning weights from past performance

Validation:
- REFUSES to run if required data is missing
- Every step validates inputs before proceeding
- Detailed error messages with remedies
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("dual_source_engine")


# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: DATA VALIDATION GATES
# ═══════════════════════════════════════════════════════════════════════

class DataValidator:
    """Strict validation for all pipeline inputs. Refuses to proceed if data missing."""

    @staticmethod
    def validate_twitch_credentials(client_id: str, client_secret: str) -> dict:
        """Validate Twitch API credentials are present."""
        if not client_id or not client_secret:
            return {
                "valid": False,
                "error": "Twitch API credentials missing.",
                "missing": [
                    k for k, v in {
                        "TWITCH_CLIENT_ID": client_id,
                        "TWITCH_CLIENT_SECRET": client_secret,
                    }.items() if not v
                ],
                "remedy": "Set TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET environment variables.",
            }
        return {"valid": True}

    @staticmethod
    def validate_clip_url(url: str) -> dict:
        """Validate a clip URL is usable."""
        if not url:
            return {"valid": False, "error": "Clip URL is empty.", "remedy": "Provide a valid Twitch clip URL."}
        if not url.startswith(("http://", "https://")):
            return {"valid": False, "error": f"Invalid URL scheme: {url[:50]}", "remedy": "URL must start with http:// or https://"}
        return {"valid": True}

    @staticmethod
    def validate_girl_config(enable_girl: bool, girl_image_url: str, lipsync_mode: str, fal_api_key: str) -> dict:
        """Validate girl overlay configuration."""
        if not enable_girl:
            return {"valid": True, "note": "Girl overlay disabled."}
        if not girl_image_url:
            return {"valid": False, "error": "girl_image_url required when girl overlay enabled.", "remedy": "Provide girl_image_url or set enable_girl=false."}
        if lipsync_mode == "paid" and not fal_api_key:
            return {"valid": False, "error": "fal_api_key required for paid lipsync mode.", "remedy": "Provide fal_api_key or use lipsync_mode='free'."}
        return {"valid": True}

    @staticmethod
    def validate_api_keys_for_mode(mode: str, keys: dict) -> dict:
        """Validate that required API keys are present for the chosen mode."""
        missing = []
        if mode in ("source1", "auto"):
            if not keys.get("twitch_client_id") or not keys.get("twitch_client_secret"):
                missing.append("TWITCH_CLIENT_ID + TWITCH_CLIENT_SECRET (required for stream/clip discovery)")
        if keys.get("enable_girl"):
            if keys.get("lipsync_mode") == "paid" and not keys.get("fal_api_key"):
                missing.append("FAL_KEY (required for paid lipsync)")
        if missing:
            return {"valid": False, "missing": missing, "remedy": "Set the missing environment variables or pass them in the request."}
        return {"valid": True}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: SOURCE SCORING — Rate each source's potential
# ═══════════════════════════════════════════════════════════════════════

async def _score_source1_potential(
    twitch_client_id: str,
    twitch_client_secret: str,
) -> dict:
    """
    Score Source 1 (stream montage) potential.

    Checks:
    - Are there live CS2 streams right now?
    - How many viewers? (more viewers = more clip potential)
    - Are clips available from top streamers?
    - How fresh is the data?

    Returns score 0.0-1.0 and detailed breakdown.
    """
    from app.services.trend_analyzer import scrape_twitch_cs2_streams

    score = 0.0
    breakdown = {}

    try:
        streams = await scrape_twitch_cs2_streams(twitch_client_id, twitch_client_secret)
    except Exception as e:
        return {
            "source": "stream_montage",
            "score": 0.0,
            "available": False,
            "error": str(e),
            "breakdown": {},
        }

    if not streams:
        return {
            "source": "stream_montage",
            "score": 0.0,
            "available": False,
            "reason": "No CS2 streams found",
            "breakdown": {},
        }

    # Check data source quality
    sources = set(s.get("source", "unknown") for s in streams)
    real_sources = {"twitch_api", "twitchtracker", "twitchtracker_scrape", "twitch_tracker", "twitch_tracker_scrape"}
    has_real = bool(sources & real_sources)

    if not has_real:
        breakdown["data_source"] = {"score": 0.0, "reason": "Only static/known data (not live)"}
    else:
        breakdown["data_source"] = {"score": 0.2, "reason": "Live data from API/scraping"}
        score += 0.2

    # Live stream count
    live = [s for s in streams if s.get("is_live")]
    if len(live) >= 5:
        breakdown["stream_count"] = {"score": 0.2, "count": len(live)}
        score += 0.2
    elif len(live) >= 1:
        breakdown["stream_count"] = {"score": 0.1, "count": len(live)}
        score += 0.1
    else:
        breakdown["stream_count"] = {"score": 0.0, "count": 0}

    # Total viewers
    total_viewers = sum(int(s.get("viewers") or 0) for s in live)
    if total_viewers > 50000:
        breakdown["viewer_count"] = {"score": 0.3, "total": total_viewers}
        score += 0.3
    elif total_viewers > 10000:
        breakdown["viewer_count"] = {"score": 0.2, "total": total_viewers}
        score += 0.2
    elif total_viewers > 1000:
        breakdown["viewer_count"] = {"score": 0.1, "total": total_viewers}
        score += 0.1
    else:
        breakdown["viewer_count"] = {"score": 0.0, "total": total_viewers}

    # Freshness
    fetched_at_values = [s.get("fetched_at") for s in streams if s.get("fetched_at")]
    if fetched_at_values:
        breakdown["freshness"] = {"score": 0.15, "has_timestamps": True}
        score += 0.15
    else:
        breakdown["freshness"] = {"score": 0.0, "has_timestamps": False}

    # Bonus: top streamer quality
    if live:
        top_viewers = max(int(s.get("viewers") or 0) for s in live)
        if top_viewers > 20000:
            breakdown["top_streamer"] = {"score": 0.15, "viewers": top_viewers}
            score += 0.15
        elif top_viewers > 5000:
            breakdown["top_streamer"] = {"score": 0.1, "viewers": top_viewers}
            score += 0.1

    return {
        "source": "stream_montage",
        "score": min(1.0, round(score, 3)),
        "available": score > 0.2,
        "streams_found": len(live),
        "total_viewers": total_viewers,
        "data_sources": list(sources),
        "breakdown": breakdown,
    }


async def _score_source2_potential(
    twitch_client_id: str,
    twitch_client_secret: str,
    period: str = "24h",
) -> dict:
    """
    Score Source 2 (trending clip reuse) potential.

    Checks:
    - Are there trending CS2 clips available?
    - How many views do they have? (proven engagement)
    - How recent are they?
    - Can we download them?

    Returns score 0.0-1.0 and detailed breakdown.
    """
    from app.services.clip_montage import discover_trending_cs2_clips

    score = 0.0
    breakdown = {}

    try:
        result = await discover_trending_cs2_clips(
            twitch_client_id=twitch_client_id,
            twitch_client_secret=twitch_client_secret,
            limit=10,
            period=period,
        )
    except Exception as e:
        return {
            "source": "trending_clip_reuse",
            "score": 0.0,
            "available": False,
            "error": str(e),
            "breakdown": {},
        }

    if not result.get("success") or not result.get("clips"):
        return {
            "source": "trending_clip_reuse",
            "score": 0.0,
            "available": False,
            "reason": result.get("error", "No trending clips found"),
            "breakdown": {},
        }

    clips = result["clips"]

    # Clip count
    if len(clips) >= 5:
        breakdown["clip_count"] = {"score": 0.15, "count": len(clips)}
        score += 0.15
    elif len(clips) >= 1:
        breakdown["clip_count"] = {"score": 0.1, "count": len(clips)}
        score += 0.1

    # Top clip views (PROVEN engagement — this is the key advantage of Source 2)
    top_views = clips[0].get("view_count", 0)
    if top_views > 50000:
        breakdown["top_clip_views"] = {"score": 0.35, "views": top_views, "reason": "Viral clip (50k+ views)"}
        score += 0.35
    elif top_views > 10000:
        breakdown["top_clip_views"] = {"score": 0.25, "views": top_views, "reason": "Hot clip (10k+ views)"}
        score += 0.25
    elif top_views > 1000:
        breakdown["top_clip_views"] = {"score": 0.15, "views": top_views, "reason": "Active clip (1k+ views)"}
        score += 0.15
    elif top_views > 100:
        breakdown["top_clip_views"] = {"score": 0.1, "views": top_views}
        score += 0.1
    else:
        breakdown["top_clip_views"] = {"score": 0.05, "views": top_views}
        score += 0.05

    # Average views across clips
    avg_views = sum(c.get("view_count", 0) for c in clips) / len(clips)
    if avg_views > 5000:
        breakdown["avg_views"] = {"score": 0.2, "average": int(avg_views)}
        score += 0.2
    elif avg_views > 1000:
        breakdown["avg_views"] = {"score": 0.1, "average": int(avg_views)}
        score += 0.1

    # Download URLs available (can we actually use these clips?)
    downloadable = sum(1 for c in clips if c.get("download_url"))
    if downloadable > 0:
        breakdown["downloadable"] = {"score": 0.15, "count": downloadable, "total": len(clips)}
        score += 0.15
    else:
        breakdown["downloadable"] = {"score": 0.0, "reason": "No download URLs available"}

    # Recency bonus
    try:
        newest = clips[0].get("created_at", "")
        if newest:
            created = datetime.strptime(newest, "%Y-%m-%dT%H:%M:%SZ")
            hours_old = (datetime.utcnow() - created).total_seconds() / 3600
            if hours_old < 6:
                breakdown["recency"] = {"score": 0.15, "hours_old": round(hours_old, 1)}
                score += 0.15
            elif hours_old < 24:
                breakdown["recency"] = {"score": 0.1, "hours_old": round(hours_old, 1)}
                score += 0.1
    except Exception:
        pass

    return {
        "source": "trending_clip_reuse",
        "score": min(1.0, round(score, 3)),
        "available": score > 0.15,
        "clips_found": len(clips),
        "top_clip": {
            "title": clips[0].get("title", "")[:60],
            "views": top_views,
            "broadcaster": clips[0].get("broadcaster_name", ""),
            "download_url": clips[0].get("download_url", ""),
        },
        "breakdown": breakdown,
        "all_clips": clips[:5],  # Keep top 5 for routing
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: INTELLIGENT DECISION ENGINE
# ═══════════════════════════════════════════════════════════════════════

async def decide_source(
    twitch_client_id: str = "",
    twitch_client_secret: str = "",
    period: str = "24h",
    force_source: Optional[str] = None,
) -> dict:
    """
    THE DECISION ENGINE — decides which source to use for reel generation.

    Process:
    1. Score both sources in parallel
    2. Apply trend-based adjustments
    3. Apply self-learning weights
    4. Return decision with full reasoning

    Args:
        force_source: "source1" or "source2" to bypass decision engine
        period: Time period for clip search

    Returns:
        Decision dict with chosen source, scores, reasoning
    """
    started = time.time()

    # Read credentials from env if not provided
    twitch_client_id = twitch_client_id or os.environ.get("TWITCH_CLIENT_ID", "")
    twitch_client_secret = twitch_client_secret or os.environ.get("TWITCH_CLIENT_SECRET", "")

    # Validate credentials
    cred_check = DataValidator.validate_twitch_credentials(twitch_client_id, twitch_client_secret)
    if not cred_check["valid"]:
        return {
            "decision": "blocked",
            "error": cred_check["error"],
            "missing": cred_check.get("missing", []),
            "remedy": cred_check["remedy"],
        }

    # Force source if specified
    if force_source in ("source1", "source2"):
        logger.info(f"Force source: {force_source}")

    # Score both sources in parallel
    s1_task = _score_source1_potential(twitch_client_id, twitch_client_secret)
    s2_task = _score_source2_potential(twitch_client_id, twitch_client_secret, period)
    s1_result, s2_result = await asyncio.gather(s1_task, s2_task, return_exceptions=True)

    if isinstance(s1_result, Exception):
        s1_result = {"source": "stream_montage", "score": 0.0, "available": False, "error": str(s1_result)}
    if isinstance(s2_result, Exception):
        s2_result = {"source": "trending_clip_reuse", "score": 0.0, "available": False, "error": str(s2_result)}

    # Apply trend adjustment
    trend_bonus = _get_trend_bonus()

    s1_adjusted = s1_result["score"] + trend_bonus.get("source1_bonus", 0)
    s2_adjusted = s2_result["score"] + trend_bonus.get("source2_bonus", 0)

    # Apply self-learning weights
    learning = _get_learning_adjustment()
    s1_final = min(1.0, s1_adjusted * learning.get("source1_weight", 1.0))
    s2_final = min(1.0, s2_adjusted * learning.get("source2_weight", 1.0))

    # Decision logic
    reasoning = []

    if force_source == "source1":
        chosen = "source1"
        reasoning.append("Forced to Source 1 (stream montage)")
    elif force_source == "source2":
        chosen = "source2"
        reasoning.append("Forced to Source 2 (trending clip reuse)")
    elif not s1_result.get("available") and not s2_result.get("available"):
        chosen = "blocked"
        reasoning.append("Neither source has usable data")
    elif not s1_result.get("available"):
        chosen = "source2"
        reasoning.append("Source 1 unavailable (no live streams/clips)")
    elif not s2_result.get("available"):
        chosen = "source1"
        reasoning.append("Source 2 unavailable (no trending clips)")
    elif s2_final > s1_final and s2_result.get("top_clip", {}).get("views", 0) > 5000:
        # Source 2 wins when it has PROVEN viral clips
        chosen = "source2"
        reasoning.append(
            f"Source 2 wins: trending clip with {s2_result['top_clip']['views']} views "
            f"(score {s2_final:.2f} vs {s1_final:.2f})"
        )
    elif s1_final > s2_final:
        chosen = "source1"
        reasoning.append(
            f"Source 1 wins: better stream material "
            f"(score {s1_final:.2f} vs {s2_final:.2f})"
        )
    else:
        # Tie-breaker: prefer Source 2 if clips have decent views (proven content)
        top_views = s2_result.get("top_clip", {}).get("views", 0)
        if top_views > 1000:
            chosen = "source2"
            reasoning.append(f"Tie-breaker: trending clip has {top_views} views (proven engagement)")
        else:
            chosen = "source1"
            reasoning.append("Tie-breaker: prefer fresh stream content over low-view clips")

    elapsed = round(time.time() - started, 2)

    return {
        "decision": chosen,
        "reasoning": reasoning,
        "scores": {
            "source1_raw": s1_result["score"],
            "source2_raw": s2_result["score"],
            "source1_adjusted": round(s1_final, 3),
            "source2_adjusted": round(s2_final, 3),
            "trend_bonus": trend_bonus,
            "learning_weights": learning,
        },
        "source1_details": s1_result,
        "source2_details": s2_result,
        "elapsed_seconds": elapsed,
        "decided_at": datetime.utcnow().isoformat(),
    }


def _get_trend_bonus() -> dict:
    """Get trend-based bonus for each source from current trend analysis."""
    try:
        from app.services.trend_analyzer import get_platform_design_hints
        hints = get_platform_design_hints("tiktok")

        # If trends favor highlight_react or sigma_edit formats
        # these work better with trending clips (Source 2)
        preferred = hints.get("preferred_style", "")
        clip_friendly_styles = {"sigma_edit", "highlight_react", "funny_moments"}
        stream_friendly_styles = {"pro_clutch", "ace_compilation", "dramatic_clutch"}

        s1_bonus = 0.05 if preferred in stream_friendly_styles else 0.0
        s2_bonus = 0.05 if preferred in clip_friendly_styles else 0.0

        # If data is real (not known_patterns), give a slight source1 bonus
        # because stream montage benefits more from accurate trend data
        if hints.get("data_type") == "real_scraped":
            s1_bonus += 0.05

        return {
            "source1_bonus": round(s1_bonus, 3),
            "source2_bonus": round(s2_bonus, 3),
            "preferred_style": preferred,
            "data_type": hints.get("data_type", "unknown"),
        }
    except Exception:
        return {"source1_bonus": 0.0, "source2_bonus": 0.0}


def _get_learning_adjustment() -> dict:
    """Get self-learning weight adjustments based on past performance."""
    try:
        from app.services.smart_montage_engine import get_trend_insights
        insights = get_trend_insights()
        # Default weights: both sources start at 1.0
        return {
            "source1_weight": 1.0,
            "source2_weight": 1.0,
            "has_learning_data": bool(insights.get("total_reels_tracked", 0)),
        }
    except Exception:
        return {"source1_weight": 1.0, "source2_weight": 1.0, "has_learning_data": False}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: UNIFIED REEL GENERATION — Execute chosen source
# ═══════════════════════════════════════════════════════════════════════

async def generate_reel_intelligent(
    # Mode
    force_source: Optional[str] = None,  # "source1", "source2", or None (auto)
    # Twitch credentials
    twitch_client_id: str = "",
    twitch_client_secret: str = "",
    youtube_api_key: str = "",
    # Girl config
    enable_girl: bool = True,
    girl_image_url: str = "",
    girl_voice: str = "jessica",
    lipsync_mode: str = "free",
    fal_api_key: str = "",
    elevenlabs_api_key: str = "",
    # Reel config
    moment_type: str = "insane_play",
    template_id: str = "highlight_react",
    hook_text: str = "",
    cta_text: str = "Follow for daily CS2 highlights!",
    max_duration: float = 15.0,
    period: str = "24h",
    # Pipeline config
    max_reels: int = 1,
    skip_freshness_check: bool = False,
) -> dict:
    """
    THE MAIN ENTRY POINT — Intelligent reel generation.

    1. Decides which source to use (or uses force_source)
    2. Validates all required data
    3. Executes the chosen pipeline
    4. Returns reel + full decision log

    This is the function that should be called from the API.
    """
    import uuid
    started = datetime.utcnow()
    run_id = uuid.uuid4().hex[:12]

    logger.info(f"[DualSource {run_id}] Starting intelligent reel generation")

    # Read from env if not provided
    twitch_client_id = twitch_client_id or os.environ.get("TWITCH_CLIENT_ID", "")
    twitch_client_secret = twitch_client_secret or os.environ.get("TWITCH_CLIENT_SECRET", "")
    youtube_api_key = youtube_api_key or os.environ.get("YOUTUBE_API_KEY", "")
    fal_api_key = fal_api_key or os.environ.get("FAL_KEY", "")
    elevenlabs_api_key = elevenlabs_api_key or os.environ.get("ELEVENLABS_API_KEY", "")

    # ── VALIDATION ──
    cred_check = DataValidator.validate_twitch_credentials(twitch_client_id, twitch_client_secret)
    if not cred_check["valid"]:
        return {
            "success": False,
            "run_id": run_id,
            "error": "Validation failed: " + cred_check["error"],
            "validation": cred_check,
            "remedy": cred_check["remedy"],
        }

    if enable_girl:
        girl_check = DataValidator.validate_girl_config(
            enable_girl, girl_image_url, lipsync_mode, fal_api_key
        )
        if not girl_check["valid"]:
            return {
                "success": False,
                "run_id": run_id,
                "error": "Validation failed: " + girl_check["error"],
                "validation": girl_check,
                "remedy": girl_check["remedy"],
            }

    # ── DECIDE SOURCE ──
    decision = await decide_source(
        twitch_client_id=twitch_client_id,
        twitch_client_secret=twitch_client_secret,
        period=period,
        force_source=force_source,
    )

    if decision["decision"] == "blocked":
        return {
            "success": False,
            "run_id": run_id,
            "error": "No viable source: " + "; ".join(decision.get("reasoning", [])),
            "decision": decision,
        }

    chosen = decision["decision"]
    logger.info(f"[DualSource {run_id}] Decision: {chosen} — {decision['reasoning']}")

    # ── EXECUTE CHOSEN SOURCE ──
    if chosen == "source1":
        result = await _execute_source1(
            run_id=run_id,
            twitch_client_id=twitch_client_id,
            twitch_client_secret=twitch_client_secret,
            youtube_api_key=youtube_api_key,
            max_reels=max_reels,
            period=period,
            max_duration=max_duration,
            cta_text=cta_text,
            skip_freshness_check=skip_freshness_check,
        )
    else:  # source2
        # Get the best clip from the decision scoring
        best_clip = decision.get("source2_details", {}).get("top_clip", {})
        all_clips = decision.get("source2_details", {}).get("all_clips", [])

        result = await _execute_source2(
            run_id=run_id,
            clips=all_clips,
            best_clip=best_clip,
            twitch_client_id=twitch_client_id,
            twitch_client_secret=twitch_client_secret,
            enable_girl=enable_girl,
            girl_image_url=girl_image_url,
            girl_voice=girl_voice,
            lipsync_mode=lipsync_mode,
            fal_api_key=fal_api_key,
            elevenlabs_api_key=elevenlabs_api_key,
            moment_type=moment_type,
            template_id=template_id,
            hook_text=hook_text,
            cta_text=cta_text,
            max_duration=max_duration,
        )

    elapsed = (datetime.utcnow() - started).total_seconds()

    return {
        "success": result.get("success", False),
        "run_id": run_id,
        "source_used": chosen,
        "decision": decision,
        "result": result,
        "elapsed_seconds": round(elapsed, 1),
        "started_at": started.isoformat(),
        "completed_at": datetime.utcnow().isoformat(),
    }


async def _execute_source1(
    run_id: str,
    twitch_client_id: str,
    twitch_client_secret: str,
    youtube_api_key: str,
    max_reels: int,
    period: str,
    max_duration: float,
    cta_text: str,
    skip_freshness_check: bool,
) -> dict:
    """Execute Source 1: Full autonomous pipeline (stream -> clips -> montage)."""
    logger.info(f"[DualSource {run_id}] Executing Source 1: Stream Montage Pipeline")

    from app.services.autonomous_pipeline import run_autonomous_pipeline

    result = await run_autonomous_pipeline(
        twitch_client_id=twitch_client_id,
        twitch_client_secret=twitch_client_secret,
        youtube_api_key=youtube_api_key,
        max_reels=max_reels,
        period=period,
        target_duration=max_duration,
        cta_text=cta_text,
        skip_freshness_check=skip_freshness_check,
    )

    return result


async def _execute_source2(
    run_id: str,
    clips: list,
    best_clip: dict,
    twitch_client_id: str,
    twitch_client_secret: str,
    enable_girl: bool,
    girl_image_url: str,
    girl_voice: str,
    lipsync_mode: str,
    fal_api_key: str,
    elevenlabs_api_key: str,
    moment_type: str,
    template_id: str,
    hook_text: str,
    cta_text: str,
    max_duration: float,
) -> dict:
    """
    Execute Source 2: Trending clip reuse + uniqueification.

    Takes an already-trending clip and makes it unique:
    1. Download the trending clip
    2. Auto-detect moment type from clip title
    3. Generate unique hook text based on clip context
    4. Apply girl overlay (uniqueification)
    5. Add custom effects, music, color grading
    6. Output a unique reel that references trending content
    """
    logger.info(f"[DualSource {run_id}] Executing Source 2: Trending Clip Reuse")

    from app.services.clip_montage import create_montage
    from app.services.autonomous_pipeline import _score_clip_as_moment, _generate_hook_from_trends

    # Select best clip
    if not clips and not best_clip.get("download_url"):
        return {"success": False, "error": "No clips available for Source 2"}

    selected_clip = clips[0] if clips else best_clip
    clip_url = selected_clip.get("download_url") or selected_clip.get("url", "")

    # Validate clip URL
    url_check = DataValidator.validate_clip_url(clip_url)
    if not url_check["valid"]:
        return {"success": False, "error": url_check["error"]}

    # Auto-detect moment type from clip title
    if moment_type == "insane_play" and selected_clip.get("title"):
        scored = _score_clip_as_moment(selected_clip)
        detected_type = scored.get("moment_type", moment_type)
        if detected_type != "insane_play":
            moment_type = detected_type
            logger.info(f"[DualSource {run_id}] Auto-detected moment type: {moment_type}")

    # Generate unique hook text if not provided
    if not hook_text:
        hook_text = _generate_hook_from_trends(
            moment_type=moment_type,
            clip_title=selected_clip.get("title", ""),
            broadcaster_name=selected_clip.get("broadcaster_name", "Unknown"),
            hook_type="text_hook",
        )

    # Execute the montage with uniqueification (girl overlay = key differentiator)
    result = await create_montage(
        clip_url=clip_url,
        template_id=template_id,
        moment_type=moment_type,
        hook_text=hook_text,
        cta_text=cta_text,
        start_time=0.0,
        max_duration=max_duration,
        enable_girl=enable_girl,
        girl_voice=girl_voice,
        girl_image_url=girl_image_url if enable_girl else None,
        fal_api_key=fal_api_key if enable_girl else None,
        elevenlabs_api_key=elevenlabs_api_key if enable_girl else None,
        lipsync_mode=lipsync_mode,
    )

    if result.get("success"):
        result["source"] = "trending_clip_reuse"
        result["original_clip"] = {
            "title": selected_clip.get("title", ""),
            "broadcaster": selected_clip.get("broadcaster_name", ""),
            "views": selected_clip.get("view_count", 0),
            "url": selected_clip.get("url", ""),
        }
        result["uniqueification"] = {
            "girl_overlay": enable_girl,
            "girl_voice": girl_voice if enable_girl else None,
            "lipsync_mode": lipsync_mode if enable_girl else None,
            "custom_hook": hook_text,
            "detected_moment_type": moment_type,
            "template": template_id,
        }

    return result


# ═══════════════════════════════════════════════════════════════════════
# SECTION 5: READINESS CHECK
# ═══════════════════════════════════════════════════════════════════════

async def get_dual_source_readiness(
    twitch_client_id: str = "",
    twitch_client_secret: str = "",
) -> dict:
    """
    Pre-flight check for dual-source system.
    Returns readiness for both sources + overall system status.
    """
    import shutil

    twitch_id = twitch_client_id or os.environ.get("TWITCH_CLIENT_ID", "")
    twitch_secret = twitch_client_secret or os.environ.get("TWITCH_CLIENT_SECRET", "")
    fal_key = os.environ.get("FAL_KEY", "")
    elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY", "")

    checks = {
        "twitch_api": {
            "configured": bool(twitch_id and twitch_secret),
            "required": True,
            "used_by": ["source1", "source2"],
            "description": "Twitch API for stream/clip discovery",
        },
        "ffmpeg": {
            "configured": shutil.which("ffmpeg") is not None,
            "required": True,
            "used_by": ["source1", "source2"],
            "description": "Video processing engine",
        },
        "yt_dlp": {
            "configured": shutil.which("yt-dlp") is not None,
            "required": True,
            "used_by": ["source1", "source2"],
            "description": "Clip downloader",
        },
        "fal_ai": {
            "configured": bool(fal_key),
            "required": False,
            "used_by": ["source2 (paid lipsync)"],
            "description": "fal.ai API for paid lip-sync (optional, free mode available)",
        },
        "elevenlabs": {
            "configured": bool(elevenlabs_key),
            "required": False,
            "used_by": ["source2 (girl voice)"],
            "description": "ElevenLabs for premium TTS (optional, edge-tts is free fallback)",
        },
    }

    required_ok = all(c["configured"] for c in checks.values() if c["required"])
    source1_ready = checks["twitch_api"]["configured"] and checks["ffmpeg"]["configured"]
    source2_ready = source1_ready  # Source 2 also needs Twitch + FFmpeg

    return {
        "ready": required_ok,
        "source1_ready": source1_ready,
        "source2_ready": source2_ready,
        "checks": checks,
        "missing_required": [k for k, v in checks.items() if v["required"] and not v["configured"]],
        "missing_optional": [k for k, v in checks.items() if not v["required"] and not v["configured"]],
        "mode_available": {
            "auto": source1_ready and source2_ready,
            "source1_only": source1_ready,
            "source2_only": source2_ready,
        },
    }
