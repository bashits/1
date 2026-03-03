"""
Dual-Source Reel Generation API Router

The intelligent routing layer that decides between:
- Source 1: Stream Montage (autonomous pipeline from full Twitch streams)
- Source 2: Trending Clip Reuse (discover viral clips → uniqueify with girl overlay)

Endpoints:
- /readiness — pre-flight check for both sources
- /decide — show what the engine would choose (without running)
- /generate — run the full intelligent pipeline
- /generate/source1 — force Source 1 (stream montage)
- /generate/source2 — force Source 2 (trending clip reuse)
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/dual", tags=["dual-source"])


class IntelligentReelRequest(BaseModel):
    """Request for intelligent reel generation."""
    # Mode
    force_source: Optional[str] = None  # "source1", "source2", or None (auto)
    # Twitch
    twitch_client_id: Optional[str] = None
    twitch_client_secret: Optional[str] = None
    youtube_api_key: Optional[str] = None
    # Girl config
    enable_girl: bool = True
    girl_image_url: str = ""
    girl_voice: str = "jessica"
    lipsync_mode: str = "free"  # "free" (FFmpeg, $0), "paid" (fal.ai), "auto"
    fal_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    # Reel config
    moment_type: str = "insane_play"
    template_id: str = "highlight_react"
    hook_text: str = ""
    cta_text: str = "Follow for daily CS2 highlights!"
    max_duration: float = 15.0
    period: str = "24h"
    # Pipeline config
    max_reels: int = 1
    skip_freshness_check: bool = False


class DecideRequest(BaseModel):
    """Request to see which source the engine would choose."""
    twitch_client_id: Optional[str] = None
    twitch_client_secret: Optional[str] = None
    period: str = "24h"
    force_source: Optional[str] = None


@router.get("/readiness")
async def dual_source_readiness():
    """
    Pre-flight check for the dual-source system.

    Returns readiness status for both sources:
    - Source 1: Stream Montage (Twitch streams → clips → montage)
    - Source 2: Trending Clip Reuse (viral clips → uniqueify)

    Plus required/optional API keys and system tools.
    """
    from app.services.dual_source_engine import get_dual_source_readiness
    return await get_dual_source_readiness()


@router.post("/decide")
async def decide_source(req: DecideRequest):
    """
    Show what the decision engine would choose WITHOUT running the pipeline.

    Scores both sources in parallel and returns:
    - Decision (source1 / source2 / blocked)
    - Detailed reasoning
    - Score breakdown for each source
    - Trend adjustments applied
    - Self-learning weights

    Use this to understand the engine's decision before committing to generation.
    """
    from app.services.dual_source_engine import decide_source as _decide
    return await _decide(
        twitch_client_id=req.twitch_client_id or "",
        twitch_client_secret=req.twitch_client_secret or "",
        period=req.period,
        force_source=req.force_source,
    )


@router.post("/generate")
async def generate_intelligent_reel(req: IntelligentReelRequest):
    """
    THE MAIN ENDPOINT — Intelligent dual-source reel generation.

    Pipeline:
    1. Scores both sources (streams vs trending clips)
    2. Applies trend analysis + self-learning weights
    3. Chooses the optimal source
    4. Executes the chosen pipeline
    5. Returns reel + full decision log

    Sources:
    - Source 1 (stream_montage): Full pipeline — Twitch streams → clip discovery →
      moment scoring → trend-based template → FFmpeg montage
    - Source 2 (trending_clip_reuse): Viral clips → auto-detect moment → girl overlay →
      custom effects → unique reel

    force_source: Set to "source1" or "source2" to bypass the decision engine.
    Set to None (default) for auto-routing.

    Validation:
    - Refuses to run if Twitch credentials missing
    - Validates girl config if enable_girl=true
    - Every step validates inputs before proceeding
    """
    from app.services.dual_source_engine import generate_reel_intelligent

    return await generate_reel_intelligent(
        force_source=req.force_source,
        twitch_client_id=req.twitch_client_id or "",
        twitch_client_secret=req.twitch_client_secret or "",
        youtube_api_key=req.youtube_api_key or "",
        enable_girl=req.enable_girl,
        girl_image_url=req.girl_image_url,
        girl_voice=req.girl_voice,
        lipsync_mode=req.lipsync_mode,
        fal_api_key=req.fal_api_key or "",
        elevenlabs_api_key=req.elevenlabs_api_key or "",
        moment_type=req.moment_type,
        template_id=req.template_id,
        hook_text=req.hook_text,
        cta_text=req.cta_text,
        max_duration=req.max_duration,
        period=req.period,
        max_reels=req.max_reels,
        skip_freshness_check=req.skip_freshness_check,
    )


@router.post("/generate/source1")
async def generate_source1(req: IntelligentReelRequest):
    """
    Force Source 1: Stream Montage pipeline.

    Bypasses the decision engine and runs the full autonomous pipeline:
    Twitch streams → clip discovery → moment scoring → trend analysis → montage
    """
    from app.services.dual_source_engine import generate_reel_intelligent

    return await generate_reel_intelligent(
        force_source="source1",
        twitch_client_id=req.twitch_client_id or "",
        twitch_client_secret=req.twitch_client_secret or "",
        youtube_api_key=req.youtube_api_key or "",
        enable_girl=req.enable_girl,
        girl_image_url=req.girl_image_url,
        girl_voice=req.girl_voice,
        lipsync_mode=req.lipsync_mode,
        fal_api_key=req.fal_api_key or "",
        elevenlabs_api_key=req.elevenlabs_api_key or "",
        moment_type=req.moment_type,
        template_id=req.template_id,
        hook_text=req.hook_text,
        cta_text=req.cta_text,
        max_duration=req.max_duration,
        period=req.period,
        max_reels=req.max_reels,
        skip_freshness_check=req.skip_freshness_check,
    )


@router.post("/generate/source2")
async def generate_source2(req: IntelligentReelRequest):
    """
    Force Source 2: Trending Clip Reuse + Uniqueification.

    Bypasses the decision engine and runs:
    Discover trending clips → pick best → girl overlay → custom effects → unique reel
    """
    from app.services.dual_source_engine import generate_reel_intelligent

    return await generate_reel_intelligent(
        force_source="source2",
        twitch_client_id=req.twitch_client_id or "",
        twitch_client_secret=req.twitch_client_secret or "",
        youtube_api_key=req.youtube_api_key or "",
        enable_girl=req.enable_girl,
        girl_image_url=req.girl_image_url,
        girl_voice=req.girl_voice,
        lipsync_mode=req.lipsync_mode,
        fal_api_key=req.fal_api_key or "",
        elevenlabs_api_key=req.elevenlabs_api_key or "",
        moment_type=req.moment_type,
        template_id=req.template_id,
        hook_text=req.hook_text,
        cta_text=req.cta_text,
        max_duration=req.max_duration,
        period=req.period,
        max_reels=req.max_reels,
        skip_freshness_check=req.skip_freshness_check,
    )


@router.get("/architecture")
async def dual_source_architecture():
    """Return the full dual-source system architecture documentation."""
    return {
        "system": "Dual-Source Intelligent Reel Generator",
        "version": "1.0",
        "description": (
            "Automatically decides between two reel generation approaches "
            "based on real-time trend analysis and content availability."
        ),
        "sources": {
            "source1_stream_montage": {
                "name": "Stream Montage",
                "pipeline": [
                    "Fetch live CS2 streams from Twitch",
                    "Discover best clips from top streamers",
                    "Score clips as moments (views, duration, type, recency)",
                    "Analyze current trends (formats, pacing, music)",
                    "Select best template based on trends",
                    "Generate hook text",
                    "Assemble reel (FFmpeg: crop + color + overlays + music)",
                ],
                "best_when": [
                    "Fresh live streams available",
                    "Need unique content (not reusing existing clips)",
                    "Specific moment types needed",
                ],
                "data_source": "Twitch Helix API (live streams + clips)",
            },
            "source2_trending_reuse": {
                "name": "Trending Clip Reuse + Uniqueification",
                "pipeline": [
                    "Discover already-trending CS2 clips on Twitch",
                    "Pick best clip by views × recency score",
                    "Auto-detect moment type from clip title",
                    "Generate unique hook text",
                    "Apply girl overlay (voice + lip-sync)",
                    "Add custom effects, music, color grading",
                    "Output unique reel referencing trending content",
                ],
                "best_when": [
                    "Viral clips exist (proven engagement)",
                    "Fast production needed",
                    "Riding existing trends",
                ],
                "data_source": "Twitch Clips API (trending clips)",
                "uniqueification": [
                    "AI girl voice commentary (ElevenLabs / edge-tts)",
                    "Lip-sync overlay (FFmpeg free / fal.ai paid)",
                    "Custom hook text and CTA",
                    "Template-based effects and color grading",
                    "Background music matching moment energy",
                ],
            },
        },
        "decision_engine": {
            "factors": [
                "Trending clip views (proven viral = Source 2 advantage)",
                "Live stream count & viewer counts (active scene = Source 1 advantage)",
                "Data freshness (both sources checked)",
                "Current trend alignment (what formats work NOW)",
                "Self-learning weights from past performance",
            ],
            "scoring": "Both sources scored 0.0-1.0, adjusted by trend bonus + learning weights",
            "tie_breaker": "Prefer Source 2 if clips have >1k views (proven content)",
        },
        "validation_gates": {
            "twitch_credentials": "REQUIRED — both sources need Twitch API",
            "girl_config": "REQUIRED if enable_girl=true — needs image URL",
            "clip_url": "Validated before download attempt",
            "ffmpeg": "REQUIRED — video processing engine",
            "yt_dlp": "REQUIRED — clip downloader",
        },
        "endpoints": {
            "GET /api/dual/readiness": "Pre-flight check for both sources",
            "POST /api/dual/decide": "Preview decision without running",
            "POST /api/dual/generate": "Auto-route to best source",
            "POST /api/dual/generate/source1": "Force stream montage",
            "POST /api/dual/generate/source2": "Force trending clip reuse",
        },
    }
