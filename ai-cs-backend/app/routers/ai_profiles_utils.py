"""
Utility endpoints for AI Profiles that don't require a profile_id path parameter.
Separated into own router to avoid FastAPI route matching conflicts with /{profile_id}.
This router MUST be included in main.py BEFORE the main ai_profiles router.
"""
import os

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException

from app.database import get_db

router = APIRouter(prefix="/api/ai-profiles", tags=["AI Profiles — Tools"])


@router.get("/runpod-status")
async def get_runpod_status():
    """Check RunPod Serverless endpoint status and pricing."""
    from app.services.runpod_lipsync_service import get_runpod_status as _get_status, get_runpod_pricing
    return {
        "status": await _get_status(),
        "pricing": get_runpod_pricing(),
    }


@router.post("/set-runpod-key")
async def set_runpod_key(
    data: dict,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Set and persist RunPod API key and endpoint ID."""
    api_key = data.get("api_key", "")
    endpoint_id = data.get("endpoint_id", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="api_key is required")
    os.environ["RUNPOD_API_KEY"] = api_key
    if endpoint_id:
        os.environ["RUNPOD_ENDPOINT_ID"] = endpoint_id
    await db.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("runpod_api_key", api_key),
    )
    if endpoint_id:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            ("runpod_endpoint_id", endpoint_id),
        )
    await db.commit()
    return {"success": True, "message": "RunPod credentials saved"}


@router.post("/set-pexels-key")
async def set_pexels_key(
    data: dict,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Set and persist Pexels API key for free base video sourcing."""
    api_key = data.get("api_key", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="api_key is required")
    os.environ["PEXELS_API_KEY"] = api_key
    await db.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("pexels_api_key", api_key),
    )
    await db.commit()
    return {"success": True, "message": "Pexels API key saved"}


@router.get("/base-videos")
async def list_base_videos():
    """List cached base videos for girl overlay."""
    from app.services.smart_girl_video_sourcer import list_cached_base_videos
    return {"videos": list_cached_base_videos()}


@router.post("/source-base-videos")
async def source_base_videos_endpoint(data: dict | None = None):
    """Source new base videos from Pexels for LatentSync."""
    from app.services.smart_girl_video_sourcer import source_base_videos as _source
    appearance = (data or {}).get("appearance")
    count = (data or {}).get("count", 5)
    result = await _source(appearance=appearance, max_videos=count)
    return result


@router.get("/kokoro-voices")
async def list_kokoro_voices(language: str = "en"):
    """List available free TTS voices (edge-tts based)."""
    from app.services.kokoro_tts_service import list_available_voices
    return list_available_voices(language=language)


@router.get("/voice-engines")
async def get_voice_engines():
    """Get status of all voice engines (free + premium)."""
    from app.services.kokoro_tts_service import get_voice_engines_status
    return get_voice_engines_status()


@router.post("/generate-kokoro-tts")
async def generate_kokoro_tts(data: dict):
    """Generate free TTS audio using edge-tts (Kokoro service)."""
    from app.services.kokoro_tts_service import generate_voice_for_moment
    text = data.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    result = await generate_voice_for_moment(
        text=text,
        moment_type=data.get("moment_type", "generic"),
        voice_key=data.get("voice_key", "en_female_cheerful"),
    )
    return result
