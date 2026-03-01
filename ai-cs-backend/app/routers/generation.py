"""Content Generation Router — Smart AI Woman Factory.

Endpoints for the AI content generation pipeline:
- Smart photo generation (FLUX 2 Realism / Pro / Dev)
- Face consistency (FLUX 2 Pro refs / IP-Adapter)
- TTS voice generation (edge-tts free / ElevenLabs premium)
- Lip-sync video (OmniHuman 1.5 / Kling Avatar / VEED)
- Image-to-video (Kling 2.1 / Wan 2.1)
- Full smart pipeline (prompt → photo → voice → lipsync → video)
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.content_generation import (
    generate_tts,
    list_tts_voices,
    generate_photo,
    generate_photo_with_face,
    generate_lipsync_video,
    generate_video_from_image,
    run_full_pipeline,
    get_pipeline_status,
    build_photo_prompt,
    select_image_model,
    select_lipsync_model,
    IMAGE_MODELS,
    LIPSYNC_MODELS,
    VIDEO_MODELS,
    CHARACTER_PHOTO_PROMPTS,
    REACTION_SCRIPTS,
    GENERATED_DIR,
)

router = APIRouter(prefix="/api/generate", tags=["generation"])


# ─── Schemas ────────────────────────────────────────────────────────
class TTSRequest(BaseModel):
    text: str
    voice_id: str = "en_female_cheerful"


class PhotoRequest(BaseModel):
    prompt: str
    negative_prompt: Optional[str] = None
    width: int = 1024
    height: int = 1024
    num_images: int = 1
    model_key: str = "flux2_realism"  # Best photorealism by default
    num_inference_steps: Optional[int] = None
    guidance_scale: Optional[float] = None
    seed: Optional[int] = None


class SmartPhotoRequest(BaseModel):
    """Generate photo using smart prompt engineering."""
    content_type: str = "gaming_reaction"
    appearance: Optional[dict] = None
    context: str = ""
    custom_additions: str = ""
    realism_level: str = "maximum"
    model_key: str = "flux2_realism"
    width: int = 1024
    height: int = 1024


class FacePhotoRequest(BaseModel):
    prompt: str
    face_image_url: str
    reference_images: Optional[list[str]] = None
    negative_prompt: Optional[str] = None
    width: int = 1024
    height: int = 1024
    method: str = "auto"  # auto / flux2_pro / ip_adapter


class LipsyncRequest(BaseModel):
    image_url: str
    audio_url: str
    model_key: str = "omnihuman"  # Film-grade by default
    duration_seconds: float = 3.0


class VideoFromImageRequest(BaseModel):
    image_url: str
    prompt: str = ""
    model_key: str = "kling"  # Best for realistic humans
    duration: str = "5"


class FullPipelineRequest(BaseModel):
    text: str
    photo_prompt: Optional[str] = None
    content_type: str = "gaming_reaction"
    appearance: Optional[dict] = None
    voice_id: str = "en_female_cheerful"
    face_image_url: Optional[str] = None
    reference_images: Optional[list[str]] = None
    quality: str = "maximum"
    lipsync_model_key: str = "omnihuman"
    photo_model_key: str = "flux2_realism"
    generate_i2v: bool = False


class SetAPIKeyRequest(BaseModel):
    fal_key: str


# ─── Pipeline Status ───────────────────────────────────────────────
@router.get("/status")
async def pipeline_status():
    """Get current pipeline configuration and available services."""
    return get_pipeline_status()


# ─── Set API Key ────────────────────────────────────────────────────
@router.post("/set-api-key")
async def set_api_key(req: SetAPIKeyRequest):
    """Set fal.ai API key for generation services (persisted to SQLite)."""
    import aiosqlite
    from app.database import DB_PATH

    # content_generation reads FAL_KEY dynamically from the environment.
    os.environ["FAL_KEY"] = req.fal_key

    # Persist to SQLite
    db = await aiosqlite.connect(DB_PATH)
    try:
        await db.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES ('fal_api_key', ?, datetime('now')) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
            (req.fal_key,),
        )
        await db.commit()
    finally:
        await db.close()

    return {
        "success": True,
        "message": "API key saved and activated",
        "fal_configured": True,
    }


@router.get("/api-key-status")
async def api_key_status():
    """Check if a fal.ai API key is persisted."""
    import aiosqlite
    from app.database import DB_PATH
    db = await aiosqlite.connect(DB_PATH)
    try:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT value FROM settings WHERE key='fal_api_key'")
        row = await cursor.fetchone()
    finally:
        await db.close()
    return {"has_key": row is not None, "key_preview": (row["value"][:3] + "***") if row else None}


# ─── TTS Endpoints ─────────────────────────────────────────────────
@router.get("/voices")
async def get_voices():
    """List available TTS voices."""
    return await list_tts_voices()


@router.post("/tts")
async def create_tts(req: TTSRequest):
    """Generate speech audio from text (FREE - edge-tts)."""
    result = await generate_tts(req.text, req.voice_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "TTS generation failed"))
    return result


# ─── Photo Generation Endpoints ────────────────────────────────────
@router.get("/photo-presets")
async def get_photo_presets():
    """Get available character photo prompt presets."""
    return {
        "presets": {k: {"prompt": v} for k, v in CHARACTER_PHOTO_PROMPTS.items()},
        "reaction_scripts": REACTION_SCRIPTS,
    }


@router.post("/photo")
async def create_photo(req: PhotoRequest):
    """Generate character photo using smart model selection.

    Default: FLUX 2 Realism LoRA (best photorealism).
    """
    result = await generate_photo(
        prompt=req.prompt,
        negative_prompt=req.negative_prompt or "",
        width=req.width,
        height=req.height,
        num_images=req.num_images,
        model_key=req.model_key,
        num_inference_steps=req.num_inference_steps,
        guidance_scale=req.guidance_scale,
        seed=req.seed,
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Photo generation failed"))
    return result


@router.post("/smart-photo")
async def create_smart_photo(req: SmartPhotoRequest):
    """Generate photo using intelligent prompt engineering.

    Content types: gaming_reaction, gaming_chill, instagram_lifestyle,
    instagram_glam, selfie_mirror, intimate_cozy, intimate_lingerie,
    portrait, full_body, bikini_beach
    """
    prompt_data = build_photo_prompt(
        content_type=req.content_type,
        appearance=req.appearance,
        context=req.context,
        custom_additions=req.custom_additions,
        realism_level=req.realism_level,
    )
    result = await generate_photo(
        prompt=prompt_data["prompt"],
        negative_prompt=prompt_data["negative_prompt"],
        width=req.width,
        height=req.height,
        model_key=req.model_key,
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Smart photo generation failed"))
    result["content_type"] = req.content_type
    result["realism_level"] = req.realism_level
    return result


@router.post("/photo-face")
async def create_photo_with_face(req: FacePhotoRequest):
    """Generate photo with face consistency.

    Methods: auto, flux2_pro (best, $0.05), ip_adapter (budget, $0.001)
    """
    result = await generate_photo_with_face(
        prompt=req.prompt,
        face_image_url=req.face_image_url,
        reference_images=req.reference_images,
        negative_prompt=req.negative_prompt or "",
        width=req.width,
        height=req.height,
        method=req.method,
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Face photo generation failed"))
    return result


# ─── Lipsync Endpoints ─────────────────────────────────────────────
@router.post("/lipsync")
async def create_lipsync(req: LipsyncRequest):
    """Generate lip-synced video from image + audio.

    Models: omnihuman (film-grade), kling_avatar (fast), veed (budget)
    """
    result = await generate_lipsync_video(
        image_url=req.image_url,
        audio_url=req.audio_url,
        model_key=req.model_key,
        duration_seconds=req.duration_seconds,
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Lipsync generation failed"))
    return result


@router.post("/video-from-image")
async def create_video_from_image(req: VideoFromImageRequest):
    """Generate video from a static image (I2V).

    Models: kling (best for realistic humans), wan21 (general)
    """
    result = await generate_video_from_image(
        image_url=req.image_url,
        prompt=req.prompt,
        model_key=req.model_key,
        duration=req.duration,
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Video generation failed"))
    return result


@router.get("/models")
async def list_all_models():
    """List all available models with capabilities and costs."""
    return {
        "image_models": IMAGE_MODELS,
        "lipsync_models": LIPSYNC_MODELS,
        "video_models": VIDEO_MODELS,
    }


@router.get("/recommend")
async def recommend_model(
    task: str = "photo",
    quality: str = "maximum",
    budget: str = "normal",
    needs_references: bool = False,
):
    """Get smart model recommendation based on requirements."""
    if task == "photo":
        model = select_image_model(
            quality=quality, budget=budget, needs_references=needs_references
        )
    elif task == "lipsync":
        model = select_lipsync_model(quality=quality)
    else:
        raise HTTPException(status_code=400, detail="Unknown task. Use: photo, lipsync")
    return {"recommendation": model}


# ─── Full Smart Pipeline ───────────────────────────────────────────
@router.post("/full-pipeline")
async def create_full_pipeline(req: FullPipelineRequest):
    """Run the complete smart pipeline: Prompt → TTS → Photo → Lipsync → (optional) I2V."""
    return await run_full_pipeline(
        text=req.text,
        photo_prompt=req.photo_prompt,
        content_type=req.content_type,
        appearance=req.appearance,
        voice_id=req.voice_id,
        face_image_url=req.face_image_url,
        reference_images=req.reference_images,
        quality=req.quality,
        lipsync_model_key=req.lipsync_model_key,
        photo_model_key=req.photo_model_key,
        generate_i2v=req.generate_i2v,
    )


# ─── File serving ───────────────────────────────────────────────────
@router.get("/files/{file_type}/{filename}")
async def serve_generated_file(file_type: str, filename: str):
    """Serve a generated file (photo/audio/video)."""
    from fastapi.responses import FileResponse

    if file_type not in ("photos", "audio", "video", "references", "profiles"):
        raise HTTPException(status_code=400, detail="Invalid file type")

    file_path = GENERATED_DIR / file_type / filename
    if not file_path.resolve().is_relative_to((GENERATED_DIR / file_type).resolve()):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    media_types = {
        "photos": "image/png",
        "audio": "audio/mpeg",
        "video": "video/mp4",
        "references": "image/jpeg",
    }

    return FileResponse(str(file_path), media_type=media_types.get(file_type, "application/octet-stream"))


# ─── Generated content listing ──────────────────────────────────────
@router.get("/gallery")
async def list_generated_content():
    """List all generated content files."""
    gallery = {"photos": [], "audio": [], "video": [], "profiles": []}

    for file_type in gallery:
        dir_path = GENERATED_DIR / file_type
        if dir_path.exists():
            for f in sorted(dir_path.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.is_file():
                    gallery[file_type].append({
                        "filename": f.name,
                        "size_bytes": f.stat().st_size,
                        "created_at": f.stat().st_mtime,
                        "url": f"/api/generate/files/{file_type}/{f.name}",
                    })

    return gallery
