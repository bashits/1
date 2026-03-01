"""
Montage Engine API Router — Intelligent Clip Production

Endpoints for the full montage pipeline:
- Status & configuration
- Create montage (full pipeline)
- Generate individual assets (SFX, music, TTS)
- List generated clips
- Serve files
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import json
import os
import aiosqlite

from app.database import get_db

from app.services.clip_montage import (
    create_montage,
    get_montage_status,
    list_generated_montages,
    generate_sfx,
    generate_music_track,
    generate_girl_audio,
    ensure_assets_ready,
    DRAMATURGY_TEMPLATES,
    SFX_CATALOG,
    MUSIC_TRACKS,
    GIRL_VOICES,
    GIRL_SCRIPTS,
    MONTAGE_DIR,
)

router = APIRouter(prefix="/api/montage", tags=["montage"])


# ─── Request Models ───────────────────────────────────────────────────

class CreateMontageRequest(BaseModel):
    clip_url: str
    template_id: str = "highlight_react"
    moment_type: str = "insane_play"
    hook_text: str = "WAIT FOR IT..."
    cta_text: str = "Follow for daily CS2 highlights!"
    subtitle_text: str = ""
    start_time: float = 0.0
    max_duration: float = 15.0
    action_timestamp: Optional[float] = None
    enable_girl: bool = False
    girl_voice: str = "jessica"
    girl_image_url: Optional[str] = None
    girl_profile_id: Optional[int] = None  # Auto-save reel to girl's content
    fal_api_key: Optional[str] = None
    elevenlabs_api_key: Optional[str] = None
    color_grade: str = "cinematic"
    music_track: Optional[str] = None


class GenerateSFXRequest(BaseModel):
    sfx_id: str


class GenerateMusicRequest(BaseModel):
    track_id: str
    duration: float = 30.0


class GenerateGirlAudioRequest(BaseModel):
    text: str
    voice: str = "jessica"
    elevenlabs_api_key: Optional[str] = None


class PreviewAssetsRequest(BaseModel):
    template_id: str = "highlight_react"
    duration: float = 15.0


class PerformanceFeedbackRequest(BaseModel):
    reel_id: str
    plan_snapshot: dict = {}
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    watch_time_pct: float = 0.0
    completion_rate: float = 0.0


# ─── Endpoints ────────────────────────────────────────────────────────

@router.get("/status")
async def montage_status():
    """Get montage engine status, capabilities, and configuration."""
    return get_montage_status()


@router.get("/templates")
async def list_templates():
    """List all dramaturgy templates with details."""
    return {
        tid: {
            "name": t["name"],
            "description": t["description"],
            "total_duration": t["total_duration"],
            "phases": [
                {
                    "name": p["name"],
                    "start": p["start"],
                    "end": p["end"],
                    "purpose": p["purpose"],
                    "girl_visible": p.get("girl_visible", False),
                    "girl_speaks": p.get("girl_speaks", False),
                    "sfx": p.get("sfx"),
                    "has_zoom": p.get("zoom", False),
                    "has_slow_mo": p.get("slow_mo", False),
                }
                for p in t["phases"]
            ],
        }
        for tid, t in DRAMATURGY_TEMPLATES.items()
    }


@router.get("/sfx-library")
async def list_sfx():
    """List all available sound effects."""
    return {
        sid: {
            "name": s["name"],
            "category": s["category"],
            "duration": s["duration"],
        }
        for sid, s in SFX_CATALOG.items()
    }


@router.get("/music-library")
async def list_music():
    """List all available music tracks."""
    return {
        mid: {
            "name": m["name"],
            "category": m["category"],
            "bpm": m["bpm"],
            "mood": m["mood"],
        }
        for mid, m in MUSIC_TRACKS.items()
    }


@router.get("/girl-config")
async def girl_config():
    """Get AI girl voice and script configuration."""
    return {
        "voices": {
            vid: {"desc": v["desc"], "style": v["style"]}
            for vid, v in GIRL_VOICES.items()
        },
        "scripts": {
            sid: {k: v for k, v in s.items()}
            for sid, s in GIRL_SCRIPTS.items()
        },
    }


@router.post("/create")
async def create_montage_endpoint(
    req: CreateMontageRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """
    Create a full montage clip.
    
    This is the main endpoint — runs the complete pipeline:
    1. Download source clip from URL
    2. Process game clip (vertical 9:16, color grade, text overlays)
    3. Generate SFX and background music
    4. (Optional) Generate AI girl voice + lip-sync video
    5. Assemble everything into final clip with multi-track audio
    6. (Optional) Auto-save to girl's content if girl_profile_id provided
    
    Returns: file paths, duration, resolution, cost, and step-by-step results.
    """
    result = await create_montage(
        clip_url=req.clip_url,
        template_id=req.template_id,
        moment_type=req.moment_type,
        hook_text=req.hook_text,
        cta_text=req.cta_text,
        subtitle_text=req.subtitle_text,
        start_time=req.start_time,
        max_duration=req.max_duration,
        action_timestamp=req.action_timestamp,
        enable_girl=req.enable_girl,
        girl_voice=req.girl_voice,
        girl_image_url=req.girl_image_url,
        fal_api_key=req.fal_api_key,
        elevenlabs_api_key=req.elevenlabs_api_key,
        color_grade=req.color_grade,
        music_track=req.music_track,
    )

    # Auto-save to girl's content_items if profile_id provided and montage succeeded
    if req.girl_profile_id and result.get("success"):
        try:
            file_path = result.get("output_path") or result.get("output", {}).get("file_path") or result.get("file_path")
            filename = file_path.split("/")[-1] if file_path else None
            serve_url = f"/api/montage/files/output/{filename}" if filename else None
            duration = result.get("output", {}).get("duration") or result.get("duration", 0)
            total_cost = result.get("total_cost", 0.0)

            metadata = json.dumps({
                "moment_type": req.moment_type,
                "template_id": req.template_id,
                "voice": req.girl_voice,
                "voice_engine": "elevenlabs_v3",
                "girl_overlay": True,
                "color_grade": req.color_grade,
                "hook_text": req.hook_text,
                "auto_saved": True,
            })

            cursor = await db.execute(
                """INSERT INTO content_items
                   (profile_id, content_type, title, prompt, file_path, file_url, duration, cost, status, metadata)
                   VALUES (?, 'reel', ?, ?, ?, ?, ?, ?, 'completed', ?)""",
                (
                    req.girl_profile_id,
                    f"CS2 {req.moment_type} Reel",
                    req.hook_text,
                    file_path,
                    serve_url,
                    duration,
                    total_cost,
                    metadata,
                ),
            )
            content_id = cursor.lastrowid
            await db.execute(
                "UPDATE ai_profiles SET total_videos = total_videos + 1, total_cost = total_cost + ?, updated_at = datetime('now') WHERE id = ?",
                (total_cost, req.girl_profile_id),
            )
            await db.commit()
            result["saved_to_profile"] = {
                "profile_id": req.girl_profile_id,
                "content_id": content_id,
            }
        except Exception as e:
            result["save_error"] = str(e)

    return result


@router.post("/generate-sfx")
async def generate_sfx_endpoint(req: GenerateSFXRequest):
    """Generate a specific sound effect."""
    if req.sfx_id not in SFX_CATALOG:
        raise HTTPException(status_code=404, detail=f"SFX '{req.sfx_id}' not found")
    path = await generate_sfx(req.sfx_id)
    if path:
        return {"success": True, "sfx_id": req.sfx_id, "file_path": path}
    raise HTTPException(status_code=500, detail="Failed to generate SFX")


@router.post("/generate-music")
async def generate_music_endpoint(req: GenerateMusicRequest):
    """Generate a background music track."""
    if req.track_id not in MUSIC_TRACKS:
        raise HTTPException(status_code=404, detail=f"Track '{req.track_id}' not found")
    path = await generate_music_track(req.track_id, req.duration)
    if path:
        return {"success": True, "track_id": req.track_id, "file_path": path, "duration": req.duration}
    raise HTTPException(status_code=500, detail="Failed to generate music")


@router.post("/generate-girl-audio")
async def generate_girl_audio_endpoint(req: GenerateGirlAudioRequest):
    """Generate AI girl TTS audio. Uses ElevenLabs v3 if API key provided, edge-tts as free fallback."""
    result = await generate_girl_audio(req.text, req.voice, elevenlabs_api_key=req.elevenlabs_api_key)
    return result


@router.post("/preview-assets")
async def preview_assets_endpoint(req: PreviewAssetsRequest):
    """Pre-generate all assets needed for a template."""
    result = await ensure_assets_ready(req.template_id, req.duration)
    return result


@router.get("/clips")
async def list_clips():
    """List all generated montage clips."""
    clips = list_generated_montages()
    return {"clips": clips, "total": len(clips)}


@router.get("/files/{subdir}/{filename}")
async def serve_file(subdir: str, filename: str):
    """Serve generated files (output, assets, temp, voice)."""
    from pathlib import Path
    voice_dir = Path("/data/generated/voice") if os.path.exists("/data") else Path(
        os.path.join(os.path.dirname(__file__), "..", "..", "generated", "voice")
    )
    allowed_dirs = {
        "output": MONTAGE_DIR / "output",
        "sfx": MONTAGE_DIR / "assets" / "sfx",
        "music": MONTAGE_DIR / "assets" / "music",
        "temp": MONTAGE_DIR / "temp",
        "voice": voice_dir,
    }
    base_dir = allowed_dirs.get(subdir)
    if not base_dir:
        raise HTTPException(status_code=404, detail="Invalid directory")

    file_path = base_dir / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    media_types = {
        ".mp4": "video/mp4",
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".jpg": "image/jpeg",
        ".png": "image/png",
    }
    ext = file_path.suffix.lower()
    media_type = media_types.get(ext, "application/octet-stream")

    return FileResponse(str(file_path), media_type=media_type)


@router.post("/feedback")
async def performance_feedback(req: PerformanceFeedbackRequest):
    """
    Feed clip performance data back into the self-learning engine.

    This closes the feedback loop:
    Trends → Engine → Video → Published → Metrics → THIS ENDPOINT → Engine learns

    Call this when you have performance data (views, likes, etc.) for a generated reel.
    The engine will adjust its weights to prefer design combinations that perform well.
    """
    from app.services.smart_montage_engine import learn_from_performance, get_trend_insights
    result = learn_from_performance(
        reel_id=req.reel_id,
        plan_snapshot=req.plan_snapshot,
        views=req.views,
        likes=req.likes,
        comments=req.comments,
        shares=req.shares,
        watch_time_pct=req.watch_time_pct,
        completion_rate=req.completion_rate,
    )
    insights = get_trend_insights()
    return {
        "learned": True,
        "engagement_score": result["engagement_score"],
        "learned_adjustments": result["learned_adjustments"],
        "current_insights": insights,
    }


@router.get("/insights")
async def engine_insights():
    """
    Get current self-learning insights — what design choices are performing best.

    Returns best/worst performers, trending up/down patterns, and weight adjustments.
    """
    from app.services.smart_montage_engine import get_trend_insights
    return get_trend_insights()


@router.get("/trend-hints/{platform}")
async def trend_design_hints(platform: str = "tiktok"):
    """
    Get platform-specific design hints from trend analyzer.

    Shows what the Producer will use when making design decisions for this platform.
    This is the bridge between trend_analyzer and the montage engine.
    """
    from app.services.trend_analyzer import get_platform_design_hints
    return get_platform_design_hints(platform)


@router.get("/trends/live")
async def live_trend_analysis():
    """
    Run LIVE trend analysis - scrapes Twitch + YouTube for real CS2 data.

    This is the main endpoint that triggers actual scraping:
    1. Twitch: API -> TwitchTracker scraping -> known DB (fallback chain)
    2. YouTube: API -> RSS feeds -> search page -> known patterns (fallback chain)
    3. Analyzes formats, hooks, pacing from scraped data
    4. Returns design recommendations for the montage engine

    Results are cached (Twitch: 5min, YouTube: 30min, combined: 10min).
    """
    from app.services.trend_analyzer import analyze_current_trends
    return await analyze_current_trends()


@router.get("/trends/system-status")
async def trend_system_status():
    """
    Get full trend system status: cache freshness, learning weights, env keys.
    Use this to debug what data sources are active and whether caches are fresh.
    """
    from app.services.trend_analyzer import get_system_status
    return get_system_status()


@router.get("/trends/learning")
async def trend_learning_insights():
    """
    Get self-learning insights - what the system has learned from feedback.
    Shows best/worst formats, hooks, music and their weights.
    """
    from app.services.trend_analyzer import get_learning_insights
    return get_learning_insights()


@router.post("/trends/learn")
async def trend_learn_feedback(
    format_used: str = "highlight_react",
    hook_used: str = "text_hook",
    music_used: str = "electronic",
    performance_score: float = 5.0,
    views: int = 0,
    likes: int = 0,
    shares: int = 0,
    watch_time_pct: float = 0.0,
):
    """
    Feed performance data into the trend learning engine.
    Updates weights so future recommendations improve.
    performance_score: 0-10 (10 = viral, 0 = flopped)
    """
    from app.services.trend_analyzer import learn_from_feedback
    return learn_from_feedback(
        format_used=format_used,
        hook_used=hook_used,
        music_used=music_used,
        performance_score=performance_score,
        views=views,
        likes=likes,
        shares=shares,
        watch_time_pct=watch_time_pct,
    )


@router.get("/trends/formats")
async def trend_available_formats():
    """List all known format templates with their properties."""
    from app.services.trend_analyzer import get_available_formats
    return get_available_formats()


@router.post("/trends/clear-cache")
async def trend_clear_cache():
    """Clear all cached trend data (forces fresh scraping on next request)."""
    from app.services.trend_analyzer import clear_cache
    clear_cache()
    return {"status": "cache_cleared"}


class ProduceAndEditRequest(BaseModel):
    moment_type: str = "insane_play"
    player_name: str = "unknown"
    situation: str = ""
    weapon: str = ""
    kills: int = 0
    health: int = 100
    platform: str = "tiktok"
    has_girl: bool = True
    video_duration: float = 20.0


@router.post("/produce-and-edit")
async def produce_and_edit_endpoint(req: ProduceAndEditRequest):
    """
    Run the full Producer → Editor pipeline.

    1. Fetches live trend data for the target platform
    2. Producer analyzes material quality and selects style
    3. Editor builds 3 versions with different approaches
    4. Returns best version with full analysis and trend influence
    """
    from app.services.smart_montage_engine import produce_and_edit
    result = produce_and_edit(
        moment_type=req.moment_type,
        player_name=req.player_name,
        situation=req.situation,
        weapon=req.weapon,
        kills=req.kills,
        health=req.health,
        has_girl=req.has_girl,
        platform=req.platform,
        video_duration=req.video_duration,
    )
    return result


@router.post("/upload-clip")
async def upload_clip(file: UploadFile = File(...)):
    """Upload a pre-generated montage clip to the server."""
    output_dir = MONTAGE_DIR / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_filename = os.path.basename(file.filename) if file.filename else f"upload_{__import__('uuid').uuid4().hex[:8]}.mp4"
    dest = output_dir / safe_filename
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    return {
        "success": True,
        "filename": safe_filename,
        "file_path": str(dest),
        "file_size": len(content),
        "serve_url": f"/api/montage/files/output/{safe_filename}",
    }
