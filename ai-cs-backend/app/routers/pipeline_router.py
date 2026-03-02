"""
Autonomous Pipeline API Router

Endpoints for the full autonomous CS2 reel generation pipeline:
- /readiness — pre-flight check (are all systems configured?)
- /run — execute the full pipeline (Twitch → clips → moments → trends → reel)
- /smart-reel — intelligent reel generation with all 7 improvements
- /gates — check freshness gates status
"""

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import os

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


class RunPipelineRequest(BaseModel):
    top_streams_count: int = 3
    clips_per_stream: int = 5
    period: str = "24h"                    # "24h", "7d", "30d"
    max_reels: int = 1                     # How many reels to produce
    target_duration: float = 15.0          # Reel duration in seconds
    cta_text: str = "Follow for daily CS2 highlights!"
    skip_freshness_check: bool = False     # Bypass gates (for testing only)
    twitch_client_id: Optional[str] = None
    twitch_client_secret: Optional[str] = None
    youtube_api_key: Optional[str] = None


@router.get("/readiness")
async def pipeline_readiness():
    """
    Pre-flight check: verify all systems are ready before running pipeline.

    Returns status for each required component:
    - Twitch API credentials
    - FFmpeg available
    - yt-dlp available
    - Trend cache populated
    """
    from app.services.autonomous_pipeline import get_pipeline_readiness
    return await get_pipeline_readiness()


@router.post("/run")
async def run_pipeline(req: RunPipelineRequest):
    """
    Execute the FULL autonomous pipeline.

    Chain:
    1. Fetch Twitch CS2 streams (last 24h) → GATE: validate freshness
    2. Select top N streams by viewer count
    3. Discover best clips from those streams → GATE: validate clips exist
    4. Score clips as moments (real data, not simulated)
    5. Analyze current trends → GATE: validate trend freshness
    6. Select best template for top moment based on trends
    7. Generate hook text from trends + moment type
    8. Assemble final reel (music + effects, no voice)

    If any freshness gate fails (and skip_freshness_check=false),
    the pipeline stops and returns detailed error explaining what's missing.

    Returns:
        Complete pipeline result with reel output paths, or gate failure details.
    """
    from app.services.autonomous_pipeline import run_autonomous_pipeline

    result = await run_autonomous_pipeline(
        twitch_client_id=req.twitch_client_id or "",
        twitch_client_secret=req.twitch_client_secret or "",
        youtube_api_key=req.youtube_api_key or "",
        top_streams_count=req.top_streams_count,
        clips_per_stream=req.clips_per_stream,
        period=req.period,
        max_reels=req.max_reels,
        target_duration=req.target_duration,
        cta_text=req.cta_text,
        skip_freshness_check=req.skip_freshness_check,
    )

    return result


@router.get("/gates")
async def check_gates():
    """
    Check freshness gate status without running the full pipeline.

    Returns current state of each validation gate:
    - Twitch data freshness
    - Clip availability
    - Trend analysis freshness
    """
    from app.services.trend_analyzer import get_cache_status, get_system_status
    import os

    cache = get_cache_status()
    system = get_system_status()

    twitch_fresh = cache.get("twitch_streams", {}).get("is_fresh", False)
    youtube_fresh = cache.get("youtube_trending", {}).get("is_fresh", False)
    combined_fresh = cache.get("combined_insights", {}).get("is_fresh", False)

    return {
        "all_gates_ready": twitch_fresh and combined_fresh,
        "gates": {
            "twitch_data": {
                "fresh": twitch_fresh,
                "age_seconds": cache.get("twitch_streams", {}).get("age_seconds"),
                "max_age_seconds": 3600,
            },
            "youtube_data": {
                "fresh": youtube_fresh,
                "age_seconds": cache.get("youtube_trending", {}).get("age_seconds"),
                "max_age_seconds": 7200,
            },
            "trend_analysis": {
                "fresh": combined_fresh,
                "age_seconds": cache.get("combined_insights", {}).get("age_seconds"),
                "max_age_seconds": 7200,
            },
        },
        "api_keys_configured": system.get("env_keys", {}),
        "known_streamers": system.get("known_streamers_count", 0),
        "learning_status": system.get("learning_status", {}),
    }


class SmartReelRequest(BaseModel):
    clip_url: Optional[str] = None         # Direct clip URL (auto-discovers if empty)
    streamer: Optional[str] = None         # Twitch streamer for clip search
    search_query: str = "CS2 highlights ace clutch today"
    hook_text: Optional[str] = None        # Auto-generated if empty
    cta_text: str = "Follow for daily CS2 highlights!"
    subtitle_text: Optional[str] = None    # Auto-generated from clip title if empty
    platform: str = "tiktok"               # tiktok / youtube_shorts / instagram


@router.post("/smart-reel")
async def generate_smart_reel_endpoint(req: SmartReelRequest):
    """
    SMART REEL — Intelligent CS2 reel generation with 7 improvements:

    1. Smart clip cutting (audio peak detection, full moment preservation)
    2. Trend-driven processing (color, pacing, effects from real scraping)
    3. Real-time trend refresh (YouTube RSS + yt-dlp search)
    4. Auto-select best clip (trend-matched scoring)
    5. Royalty-free music overlay (Pixabay, mixed with gameplay)
    6. Dynamic word-by-word subtitles
    7. Full pipeline logging (human-readable data source documentation)

    Returns the reel file + full pipeline log documenting every data source.
    """
    from app.services.smart_reel_engine import generate_smart_reel

    result = await generate_smart_reel(
        clip_url=req.clip_url,
        streamer=req.streamer,
        search_query=req.search_query,
        hook_text=req.hook_text,
        cta_text=req.cta_text,
        subtitle_text=req.subtitle_text,
        platform=req.platform,
    )

    return result


@router.get("/smart-reel/download/{filename}")
async def download_smart_reel(filename: str):
    """Download a generated smart reel file."""
    from app.services.smart_reel_engine import CLIPS_DIR

    file_path = CLIPS_DIR / "processed" / filename
    if not file_path.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Reel file not found")
    return FileResponse(str(file_path), media_type="video/mp4", filename=filename)


@router.get("/architecture")
async def pipeline_architecture():
    """
    Return the full pipeline architecture documentation.
    Useful for understanding the system flow.
    """
    return {
        "pipeline_name": "Autonomous CS2 Reel Generator",
        "version": "1.0",
        "steps": [
            {
                "step": 1,
                "name": "Twitch Stream Discovery",
                "description": "Fetch top CS2 streams from Twitch (API → TwitchTracker → known DB fallback)",
                "data_source": "Twitch Helix API / TwitchTracker scraping",
                "gate": "GATE 1+2: Real data required, minimum 1 live stream",
                "output": "List of top N streams sorted by viewers",
            },
            {
                "step": 2,
                "name": "Clip Discovery",
                "description": "Get best clips from top streamers via Twitch Clips API",
                "data_source": "Twitch Clips API (OAuth)",
                "gate": "GATE 3: At least 1 clip must be found",
                "output": "List of clips with download URLs, view counts, durations",
            },
            {
                "step": 3,
                "name": "Moment Scoring",
                "description": "Score each clip using multi-signal approach (views, duration, broadcaster popularity, title keywords)",
                "signals": [
                    "view_count (log scale popularity)",
                    "duration (15-30s optimal for reels)",
                    "broadcaster_viewers (stream popularity)",
                    "title keywords (detect ace, clutch, fail, etc.)",
                    "viral multiplier for exceptional clips",
                ],
                "output": "Ranked moments with composite scores and detected types",
            },
            {
                "step": 4,
                "name": "Trend Analysis",
                "description": "Analyze what formats, hooks, pacing, music are trending right now",
                "data_source": "Twitch + YouTube scraping (cached 5-30min)",
                "gate": "GATE 4: Trend data must be current (< 2h old)",
                "output": "Design recommendations: pacing, color grade, music style, hook type",
            },
            {
                "step": 5,
                "name": "Template Selection",
                "description": "Match each moment to the best montage template based on trends",
                "logic": "moment_type → base affinity + trend boost → selected template + config",
                "templates": [
                    "highlight_react", "dramatic_ace", "quick_kill",
                    "girl_commentary", "meme_edit", "fail_compilation",
                ],
                "output": "Template config with duration, color, music, pacing per moment",
            },
            {
                "step": 6,
                "name": "Reel Assembly",
                "description": "Download clip (stream, no local storage), process vertical 9:16, add effects + music, output final reel",
                "processing": "FFmpeg: crop → color grade → text overlays → music mix → export MP4",
                "output": "Final reel MP4 file ready to publish",
            },
        ],
        "validation_gates": {
            "gate_1": "Twitch data must be from live API (not static fallback)",
            "gate_2": "At least 1 CS2 stream must be live",
            "gate_3": "At least 1 clip must be found from top streamers",
            "gate_4": "Trend analysis must have current data (< 2h old)",
        },
        "data_flow": "Twitch API → Streams → Clips → Moments (scored) → Trends → Template → FFmpeg → Final Reel",
    }
