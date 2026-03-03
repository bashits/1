"""AI Profiles Router — Full AI Girl Management System.

Supports:
- Profile CRUD with expanded fields (voice persona, memory, social, costs)
- ElevenLabs v3 voice generation with audio tags per girl
- Content generation (photo, video, voice) with cost tracking
- Social media scheduling (Instagram, TikTok, Telegram)
- Memory/learning system per girl
- Content gallery & voice samples per girl
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
import aiosqlite

from app.database import get_db
from app.services.ai_profile_generator import (
    generate_profile_config,
    generate_image_prompt,
    generate_voice_script,
    estimate_generation_cost,
    generate_unique_persona,
    APPEARANCE_PRESETS,
    PERSONALITY_PRESETS,
    VOICE_PRESETS,
)
from app.services.voice_engine import (
    generate_voice_elevenlabs,
    generate_girl_voice,
    list_elevenlabs_voices,
    build_expressive_script,
    get_voice_personas,
    get_audio_tags,
    VOICE_PERSONAS,
    VOICE_ENHANCEMENT_TIPS,
)
from app.services.lora_service import (
    generate_training_dataset,
    start_lora_training,
    check_training_status,
    wait_for_training,
    generate_photo_with_lora,
    build_lora_prompt,
    LORA_TRAINING_CONFIG,
    LORA_INFERENCE_CONFIG,
)
from app.services.real_photo_sourcer import source_photos_with_fallback
from app.services.content_generation import calculate_video_cost, get_all_pricing, VIDEO_DURATION_OPTIONS

router = APIRouter(prefix="/api/ai-profiles", tags=["ai-profiles"])


# ─── Helper ──────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


async def _get_profile_storage_size(db: aiosqlite.Connection, profile_id: int) -> dict:
    """Calculate total storage used by an AI girl profile.

    Scans content_items, voice_samples, and profile_gallery for local file paths,
    sums file sizes on disk. Returns breakdown by content type + total.
    """
    storage: dict[str, dict] = {}
    total_bytes = 0
    total_files = 0

    # content_items (photos, videos, audio)
    cursor = await db.execute(
        "SELECT content_type, file_path FROM content_items WHERE profile_id = ? AND file_path IS NOT NULL",
        (profile_id,),
    )
    for row in await cursor.fetchall():
        ct = row["content_type"] or "other"
        fp = row["file_path"]
        if fp and os.path.exists(fp):
            size = os.path.getsize(fp)
            if ct not in storage:
                storage[ct] = {"files": 0, "bytes": 0}
            storage[ct]["files"] += 1
            storage[ct]["bytes"] += size
            total_bytes += size
            total_files += 1

    # voice_samples
    cursor2 = await db.execute(
        "SELECT file_path FROM voice_samples WHERE profile_id = ? AND file_path IS NOT NULL",
        (profile_id,),
    )
    for row in await cursor2.fetchall():
        fp = row["file_path"]
        if fp and os.path.exists(fp):
            size = os.path.getsize(fp)
            if "voice" not in storage:
                storage["voice"] = {"files": 0, "bytes": 0}
            storage["voice"]["files"] += 1
            storage["voice"]["bytes"] += size
            total_bytes += size
            total_files += 1

    # Format human-readable sizes
    def _fmt(b: int) -> str:
        if b < 1024:
            return f"{b} B"
        if b < 1024 * 1024:
            return f"{b / 1024:.1f} KB"
        if b < 1024 * 1024 * 1024:
            return f"{b / (1024 * 1024):.1f} MB"
        return f"{b / (1024 * 1024 * 1024):.2f} GB"

    breakdown = {}
    for ct, info in storage.items():
        breakdown[ct] = {
            "files": info["files"],
            "bytes": info["bytes"],
            "human": _fmt(info["bytes"]),
        }

    return {
        "total_bytes": total_bytes,
        "total_human": _fmt(total_bytes),
        "total_files": total_files,
        "breakdown": breakdown,
    }


def _parse_profile(row: aiosqlite.Row) -> dict:
    d = dict(row)
    for key in ("appearance", "voice_config", "personality", "elevenlabs_voice_settings",
                "memory", "content_style", "social_config"):
        if key in d and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except Exception:
                d[key] = {}
    for key in ("reference_images", "voice_audio_tags"):
        if key in d and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except Exception:
                d[key] = []
    if "is_active" in d:
        d["is_active"] = bool(d["is_active"])
    return d


# ─── Request Schemas ─────────────────────────────────────────────────
class ProfileCreateRequest(BaseModel):
    name: Optional[str] = None  # Optional — auto-generated if not provided
    style: str = "realistic"
    description: Optional[str] = None
    auto_generate: bool = True  # NEW: auto-generate unique persona
    auto_generate_photo: bool = True  # NEW: auto-gen first identity photo on creation
    appearance_preset: str = "realistic_european"
    personality_preset: str = "energetic_gamer"
    voice_preset: str = "energetic_female"
    voice_persona: str = "jessica_fire"
    custom_appearance: Optional[dict] = None
    custom_personality: Optional[dict] = None
    custom_voice: Optional[dict] = None
    instagram_handle: Optional[str] = None
    tiktok_handle: Optional[str] = None
    telegram_channel: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    style: Optional[str] = None
    description: Optional[str] = None
    appearance: Optional[dict] = None
    voice_config: Optional[dict] = None
    personality: Optional[dict] = None
    reference_images: Optional[list[str]] = None
    instagram_handle: Optional[str] = None
    tiktok_handle: Optional[str] = None
    telegram_channel: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None
    elevenlabs_voice_settings: Optional[dict] = None
    voice_audio_tags: Optional[list] = None
    memory: Optional[dict] = None
    content_style: Optional[dict] = None
    social_config: Optional[dict] = None
    is_active: Optional[bool] = None


class GenerateVoiceRequest(BaseModel):
    text: str
    moment_type: str = "generic"
    use_audio_tags: bool = True
    voice_name_override: Optional[str] = None
    settings_override: Optional[dict] = None


class GeneratePhotoRequest(BaseModel):
    prompt: Optional[str] = None
    content_type: str = "instagram_post"
    num_images: int = 1
    width: int = 1024
    height: int = 1024
    model_key: str = "flux2_realism"
    use_reference_images: bool = True
    set_as_reference: bool = False
    use_lora: bool = True  # Auto-use LoRA if trained
    lora_scale: float = 0.95
    custom_scene: Optional[str] = None


class TrainLoraRequest(BaseModel):
    num_photos: int = 15  # Training dataset size (10-20 optimal)
    steps: int = 1000  # Training steps
    trigger_word: Optional[str] = None  # Auto-generated if not provided
    use_real_photos: bool = True  # Use real model photos from Pexels (recommended)


class GenerateVideoRequest(BaseModel):
    text: str
    moment_type: str = "generic"
    base_video_url: Optional[str] = None  # optional: provide own base video URL


class SchedulePostRequest(BaseModel):
    content_item_id: Optional[int] = None
    platform: str = "instagram"
    caption: str = ""
    hashtags: list[str] = []
    scheduled_at: Optional[str] = None


class UpdateMemoryRequest(BaseModel):
    personality_notes: Optional[str] = None
    style_preferences: Optional[dict] = None
    audience_insights: Optional[dict] = None
    content_performance: Optional[dict] = None
    voice_preferences: Optional[dict] = None
    custom_data: Optional[dict] = None


# ─── Presets & Config ─────────────────────────────────────────────────

@router.get("/presets")
async def get_presets():
    """Get all available presets including voice personas and audio tags."""
    return {
        "appearance": APPEARANCE_PRESETS,
        "personality": PERSONALITY_PRESETS,
        "voice": VOICE_PRESETS,
        "voice_personas": get_voice_personas(),
        "audio_tags": get_audio_tags(),
        "enhancement_tips": VOICE_ENHANCEMENT_TIPS,
    }


@router.get("/elevenlabs-voices")
async def get_elevenlabs_voices_endpoint():
    """List all ElevenLabs voices available in your account."""
    return await list_elevenlabs_voices()


@router.post("/set-elevenlabs-key")
async def set_elevenlabs_key(
    data: dict,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Set and persist ElevenLabs API key."""
    api_key = data.get("api_key", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="api_key is required")
    os.environ["ELEVENLABS_API_KEY"] = api_key
    await db.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("elevenlabs_api_key", api_key),
    )
    await db.commit()
    return {"success": True, "message": "ElevenLabs API key saved"}


# ─── Pricing & Cost Estimates (MUST be before /{profile_id} routes) ───

@router.get("/cost-estimates/{task_type}")
async def get_cost_estimate(task_type: str):
    costs = estimate_generation_cost(task_type)
    if not costs:
        raise HTTPException(status_code=404, detail=f"Unknown task type: {task_type}")
    return {"task_type": task_type, "estimates": costs}


@router.get("/pricing")
async def get_pricing():
    """Pricing & allowed durations for frontend real-time cost calculator."""
    return get_all_pricing()


@router.get("/video-cost-estimate")
async def get_video_cost_estimate(
    duration_seconds: float = Query(default=3.0, ge=1.0, le=60.0),
    lipsync_model_key: str = "omnihuman",
    include_i2v: bool = False,
    i2v_model_key: str = "kling",
    voice_engine: str = "elevenlabs",
):
    # Validate against our discrete UI options
    allowed = {float(d) for d in VIDEO_DURATION_OPTIONS}
    if duration_seconds not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid duration_seconds={duration_seconds}. Allowed: {sorted(VIDEO_DURATION_OPTIONS)}",
        )
    return calculate_video_cost(
        duration_seconds=duration_seconds,
        lipsync_model_key=lipsync_model_key,
        photo_model_key="lora",
        include_i2v=include_i2v,
        i2v_model_key=i2v_model_key,
        voice_engine=voice_engine,
    )


# ─── Profile CRUD ─────────────────────────────────────────────────────

@router.get("/")
async def list_profiles(db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM ai_profiles ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    profiles = []
    for row in rows:
        p = _parse_profile(row)
        p["storage"] = await _get_profile_storage_size(db, p["id"])
        profiles.append(p)
    return profiles


@router.post("/generate-persona")
async def generate_persona_preview(data: dict | None = None):
    """Generate a random unique persona preview (no DB save).

    Call this to show the user a preview of the auto-generated girl
    before they confirm creation. Returns full persona details.
    """
    name = (data or {}).get("name")
    persona = generate_unique_persona(name=name)
    return persona


@router.post("/")
async def create_profile(
    data: ProfileCreateRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create a new AI girl profile.

    If auto_generate=True (default), generates a unique persona with
    randomized appearance, personality, and voice. Each girl is truly unique.
    If auto_generate=False, uses legacy preset-based config.
    """
    if data.auto_generate:
        # ═══ SMART UNIQUE PERSONA GENERATION ═══
        persona_data = generate_unique_persona(name=data.name)
        profile_name = persona_data["name"]
        appearance = persona_data["appearance"]
        personality = persona_data["personality"]
        voice_config = persona_data["voice_config"]
        bio = persona_data["bio"]
        voice_persona_id = persona_data["voice_persona_id"]

        # Get ElevenLabs persona for audio tags
        el_persona = VOICE_PERSONAS.get(voice_persona_id, VOICE_PERSONAS["jessica_fire"])

        # Voice settings from the unique generator
        elevenlabs_settings = voice_config.get("elevenlabs_settings", el_persona["default_settings"])
        audio_tags = el_persona.get("signature_tags", [])

        memory = {
            "personality_notes": bio,
            "archetype": personality.get("archetype", ""),
            "identity_seed": persona_data.get("identity_seed", ""),
            "content_count": 0,
            "favorite_tags": audio_tags,
            "audience_insights": {},
            "performance_history": [],
        }

        content_style = {
            "photo_style": "realistic",
            "video_format": "vertical_9_16",
            "caption_language": "en",
            "emoji_usage": personality.get("emoji_style", "moderate"),
            "hashtag_strategy": "trending_mix",
        }

        description = data.description or bio

    else:
        # ═══ LEGACY PRESET-BASED CREATION ═══
        config = generate_profile_config(
            name=data.name or "AI Girl",
            appearance_preset=data.appearance_preset,
            personality_preset=data.personality_preset,
            voice_preset=data.voice_preset,
            custom_appearance=data.custom_appearance,
            custom_personality=data.custom_personality,
            custom_voice=data.custom_voice,
        )
        profile_name = data.name or "AI Girl"
        appearance = config["appearance"]
        personality = config["personality"]
        voice_config = config["voice_config"]

        el_persona = VOICE_PERSONAS.get(data.voice_persona, VOICE_PERSONAS["jessica_fire"])
        voice_config["persona_id"] = data.voice_persona
        voice_config["elevenlabs_voice_name"] = el_persona["elevenlabs_voice"]
        voice_config["style_guide"] = el_persona["style_guide"]

        elevenlabs_settings = el_persona["default_settings"]
        audio_tags = el_persona["signature_tags"]

        memory = {
            "personality_notes": f"AI girl: {profile_name}. Persona: {el_persona['name']}. {el_persona['description']}",
            "content_count": 0,
            "favorite_tags": audio_tags,
            "audience_insights": {},
            "performance_history": [],
        }

        content_style = {
            "photo_style": appearance.get("style", "realistic"),
            "video_format": "vertical_9_16",
            "caption_language": "en",
            "emoji_usage": "moderate",
            "hashtag_strategy": "trending_mix",
        }

        description = data.description or f"AI girl: {profile_name} — {el_persona['description']}"

    # ═══ INSERT INTO DB ═══
    cursor = await db.execute(
        """INSERT INTO ai_profiles (
            name, style, description, appearance, voice_config, personality,
            instagram_handle, tiktok_handle, telegram_channel,
            elevenlabs_voice_settings, voice_audio_tags,
            memory, content_style, social_config
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            profile_name, data.style,
            description,
            json.dumps(appearance), json.dumps(voice_config), json.dumps(personality),
            data.instagram_handle, data.tiktok_handle, data.telegram_channel,
            json.dumps(elevenlabs_settings), json.dumps(audio_tags),
            json.dumps(memory), json.dumps(content_style),
            json.dumps({"posting_schedule": {"instagram": "10:00,14:00,19:00", "tiktok": "12:00,17:00,21:00"}}),
        ),
    )
    await db.commit()
    profile_id = cursor.lastrowid

    # ═══ SKIP INITIAL PHOTO — REQUIRE LoRA TRAINING FIRST ═══
    # We don't generate AI photos on creation anymore.
    # The user must first train LoRA (using real model photos from Pexels),
    # then ALL photos will be generated through LoRA for maximum realism.
    first_photo_url = None

    # ═══ AUTO-CREATE VOICE IDENTITY ═══
    try:
        el_voice_name = voice_config.get("elevenlabs_voice_name", "Jessica")
        el_persona_id = voice_config.get("persona_id", "jessica_fire")
        el_persona_for_vi = VOICE_PERSONAS.get(el_persona_id, VOICE_PERSONAS["jessica_fire"])
        vi_audio_tags = el_persona_for_vi.get("signature_tags", [])
        vi_personality_traits = [personality.get("archetype", ""), personality.get("tone", "")]
        vi_speaking_style = voice_config.get("style_guide", personality.get("speaking_style", "natural"))

        await db.execute(
            """INSERT OR IGNORE INTO voice_identity
               (profile_id, provider, voice_name, voice_settings, audio_tags, personality_traits, speaking_style, language)
               VALUES (?, 'elevenlabs', ?, ?, ?, ?, ?, 'en')""",
            (
                profile_id,
                el_voice_name,
                json.dumps(elevenlabs_settings),
                json.dumps(vi_audio_tags),
                json.dumps(vi_personality_traits),
                vi_speaking_style,
            ),
        )
        await db.commit()
    except Exception as e:
        import logging
        logging.warning(f"Auto voice identity creation failed for profile {profile_id}: {e}")

    cursor2 = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor2.fetchone()
    result = _parse_profile(row)
    result["auto_generated_photo"] = first_photo_url
    return result


@router.get("/{profile_id}")
async def get_profile(profile_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    p = _parse_profile(row)
    p["storage"] = await _get_profile_storage_size(db, profile_id)
    return p


@router.put("/{profile_id}")
async def update_profile(
    profile_id: int,
    update: ProfileUpdateRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    updates: list[str] = []
    params: list = []

    for field in ("name", "style", "description", "instagram_handle",
                  "tiktok_handle", "telegram_channel", "elevenlabs_voice_id"):
        val = getattr(update, field, None)
        if val is not None:
            updates.append(f"{field} = ?")
            params.append(val)

    for field in ("appearance", "voice_config", "personality",
                  "elevenlabs_voice_settings", "memory", "content_style", "social_config"):
        val = getattr(update, field, None)
        if val is not None:
            updates.append(f"{field} = ?")
            params.append(json.dumps(val))

    if update.voice_audio_tags is not None:
        updates.append("voice_audio_tags = ?")
        params.append(json.dumps(update.voice_audio_tags))

    if update.reference_images is not None:
        updates.append("reference_images = ?")
        params.append(json.dumps(update.reference_images))

    if update.is_active is not None:
        updates.append("is_active = ?")
        params.append(1 if update.is_active else 0)

    if updates:
        updates.append("updated_at = datetime('now')")
        params.append(profile_id)
        await db.execute(
            f"UPDATE ai_profiles SET {', '.join(updates)} WHERE id = ?", params
        )
        await db.commit()

    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _parse_profile(row)


@router.delete("/{profile_id}")
async def delete_profile(profile_id: int, db: aiosqlite.Connection = Depends(get_db)):
    await db.execute("DELETE FROM ai_profiles WHERE id = ?", (profile_id,))
    await db.commit()
    return {"deleted": True}


# ─── Voice Generation ─────────────────────────────────────────────────

@router.post("/{profile_id}/generate-voice")
async def generate_voice(
    profile_id: int,
    req: GenerateVoiceRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Generate voice audio using this girl's unique voice persona + ElevenLabs v3."""
    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = _parse_profile(row)

    if req.voice_name_override:
        script = req.text
        if req.use_audio_tags:
            persona_id = profile.get("voice_config", {}).get("persona_id", "jessica_fire")
            script = build_expressive_script(req.text, req.moment_type, persona_id)
        result = await generate_voice_elevenlabs(
            text=script, voice_name=req.voice_name_override, voice_settings=req.settings_override,
        )
    else:
        result = await generate_girl_voice(
            profile_data=profile, text=req.text,
            moment_type=req.moment_type, use_audio_tags=req.use_audio_tags,
        )

    if result.get("success"):
        cost = result.get("cost", 0.0)
        await db.execute(
            """INSERT INTO voice_samples (profile_id, text, audio_tags, file_path, duration, cost, voice_settings)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (profile_id, req.text, json.dumps([]), result.get("file_path"),
             result.get("duration"), cost, json.dumps(result.get("settings", {}))),
        )
        await db.execute(
            """INSERT INTO content_items (profile_id, content_type, title, prompt, file_path, cost, status, metadata)
               VALUES (?, 'voice', ?, ?, ?, ?, 'completed', ?)""",
            (profile_id, f"Voice: {req.moment_type}", req.text,
             result.get("file_path"), cost,
             json.dumps({"moment_type": req.moment_type, "persona": result.get("persona")})),
        )
        await db.execute(
            "UPDATE ai_profiles SET total_cost = total_cost + ?, updated_at = datetime('now') WHERE id = ?",
            (cost, profile_id),
        )
        await db.commit()

    return result


@router.get("/{profile_id}/voice-samples")
async def get_voice_samples(
    profile_id: int,
    limit: int = Query(default=20, le=100),
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute(
        "SELECT * FROM voice_samples WHERE profile_id = ? ORDER BY created_at DESC LIMIT ?",
        (profile_id, limit),
    )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        for k in ("audio_tags", "voice_settings"):
            if k in d and isinstance(d[k], str):
                try:
                    d[k] = json.loads(d[k])
                except Exception:
                    d[k] = {} if k == "voice_settings" else []
        result.append(d)
    return result


@router.post("/{profile_id}/preview-script")
async def preview_script(
    profile_id: int,
    req: GenerateVoiceRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Preview expressive script with audio tags (no audio generation)."""
    cursor = await db.execute("SELECT voice_config FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    vc = json.loads(row["voice_config"]) if isinstance(row["voice_config"], str) else row["voice_config"]
    persona_id = vc.get("persona_id", "jessica_fire")
    expressive = build_expressive_script(req.text, req.moment_type, persona_id)
    persona = VOICE_PERSONAS.get(persona_id, {})

    return {
        "original_text": req.text,
        "expressive_text": expressive,
        "persona": persona_id,
        "persona_name": persona.get("name", "Unknown"),
        "moment_type": req.moment_type,
        "tags_used": [t for t in persona.get("signature_tags", []) if t.lower() in expressive.lower()],
    }


# ─── Content Generation ──────────────────────────────────────────────

@router.post("/{profile_id}/generate-photo")
async def generate_photo(
    profile_id: int,
    req: GeneratePhotoRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Generate photo(s) for this girl.

    LoRA-first approach:
    - If LoRA is trained → use fal-ai/flux-lora (100% face consistency from real photos)
    - If LoRA is NOT trained → block generation and require training first
    - This ensures every generated photo looks like a real person, not AI art
    """
    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = _parse_profile(row)

    reference_images = profile.get("reference_images") or []
    if not isinstance(reference_images, list):
        reference_images = []

    from app.services.content_generation import (
        generate_photo as fal_generate_photo,
        generate_photo_with_face as fal_generate_photo_with_face,
    )

    lora_url = profile.get("lora_model_url")
    trigger_word = profile.get("lora_trigger_word")
    lora_status = profile.get("lora_training_status", "not_trained")

    # ═══ BLOCK GENERATION WITHOUT LoRA ═══
    # LoRA must be trained first (on real model photos) for realistic results
    if lora_status != "trained":
        status_messages = {
            "not_trained": "Сначала обучите LoRA! Нажмите 'Обучить LoRA' в табе Обзор. Это обучит модель на реальных фото модели для максимального реализма.",
            "generating_dataset": "LoRA: идёт поиск реальных фото модели... Подождите 1-2 минуты.",
            "sourcing_photos": "LoRA: идёт поиск реальных фото модели в открытом доступе... Подождите.",
            "training": "LoRA обучается... Подождите 5-15 минут. После этого генерация будет доступна.",
            "failed": "LoRA обучение не удалось. Попробуйте обучить заново.",
        }
        msg = status_messages.get(lora_status, f"LoRA статус: {lora_status}. Сначала обучите LoRA.")
        raise HTTPException(
            status_code=400,
            detail=msg,
        )

    used_reference_images = False
    used_lora = False

    # LoRA-based generation (face identity from real model photos)
    if req.use_lora and lora_url and trigger_word and lora_status == "trained":
        appearance = profile.get("appearance", {})
        if req.prompt:
            # Smart prompt: detect Russian text and interpret into pro EN prompt
            from app.services.smart_prompt_interpreter import is_russian_text, smart_prompt
            if is_russian_text(req.prompt):
                prompt = smart_prompt(req.prompt, appearance=appearance, trigger_word=trigger_word)
            else:
                prompt = f"{trigger_word}, {req.prompt}"
        else:
            prompt = build_lora_prompt(
                trigger_word=trigger_word,
                appearance=appearance,
                content_type=req.content_type,
                custom_scene=req.custom_scene or "",
            )
        result = await generate_photo_with_lora(
            prompt=prompt,
            lora_url=lora_url,
            lora_scale=req.lora_scale,
            width=req.width,
            height=req.height,
            num_images=req.num_images,
            guidance_scale=LORA_INFERENCE_CONFIG["default_guidance_scale"],
            num_inference_steps=LORA_INFERENCE_CONFIG["default_num_inference_steps"],
        )
        used_lora = result.get("lora_used", False)
    # Priority 2: Reference image based generation
    elif req.use_reference_images and reference_images:
        prompt = req.prompt or generate_image_prompt(profile, req.content_type)
        used_reference_images = True
        result = await fal_generate_photo_with_face(
            prompt=prompt,
            face_image_url=reference_images[0],
            reference_images=reference_images[:4],
            width=req.width,
            height=req.height,
            method="flux2_pro",
        )
    # Priority 3: Standard generation
    else:
        prompt = req.prompt or generate_image_prompt(profile, req.content_type)
        result = await fal_generate_photo(
            prompt=prompt,
            width=req.width,
            height=req.height,
            num_images=req.num_images,
            model_key=req.model_key,
        )

    if result.get("success"):
        images = result.get("images", [])
        total_cost = round(float(result.get("cost_estimate", 0.0) or 0.0), 4)
        per_image_cost = round(total_cost / max(len(images), req.num_images, 1), 4)

        gallery_ids = []
        for img in images:
            img_url = img.get("url", "")
            # Save to content_items (legacy)
            await db.execute(
                """INSERT INTO content_items (profile_id, content_type, title, prompt, file_url, cost, status, metadata)
                   VALUES (?, 'photo', ?, ?, ?, ?, 'completed', ?)""",
                (
                    profile_id,
                    f"Photo: {req.content_type}",
                    prompt,
                    img_url,
                    per_image_cost,
                    json.dumps(
                        {
                            "content_type": req.content_type,
                            "model": result.get("model"),
                            "model_key": req.model_key,
                            "used_reference_images": used_reference_images,
                        }
                    ),
                ),
            )
            # Save to profile_gallery (cloud URL only — no local files)
            if img_url:
                cursor_g = await db.execute(
                    """INSERT INTO profile_gallery (profile_id, image_url, content_type, prompt, model_key, is_reference, cost, metadata)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        profile_id, img_url, req.content_type, prompt,
                        req.model_key, 1 if req.set_as_reference else 0,
                        per_image_cost,
                        json.dumps({"model": result.get("model"), "used_reference_images": used_reference_images}),
                    ),
                )
                gallery_ids.append(cursor_g.lastrowid)

            # Record in prompt_learning for auto-improvement
            try:
                await db.execute(
                    """INSERT INTO prompt_learning (profile_id, prompt_type, original_prompt, model_key, content_type, success_score)
                       VALUES (?, 'photo', ?, ?, ?, 0.5)""",
                    (profile_id, prompt, req.model_key, req.content_type),
                )
            except Exception:
                pass

        if req.set_as_reference and images:
            new_ref = images[0].get("url")
            if new_ref:
                merged = [new_ref] + [u for u in reference_images if u != new_ref]
                merged = merged[:4]
                await db.execute(
                    "UPDATE ai_profiles SET reference_images = ?, updated_at = datetime('now') WHERE id = ?",
                    (json.dumps(merged), profile_id),
                )

        # Update profile memory with generation history
        try:
            cursor_m = await db.execute("SELECT memory FROM ai_profiles WHERE id = ?", (profile_id,))
            mem_row = await cursor_m.fetchone()
            memory = json.loads(mem_row["memory"]) if mem_row and isinstance(mem_row["memory"], str) else {}
            gen_history = memory.get("generation_history", [])
            gen_history.insert(0, {
                "type": "photo", "content_type": req.content_type,
                "model": req.model_key, "cost": total_cost,
                "count": len(images), "timestamp": datetime.utcnow().isoformat(),
                "gallery_ids": gallery_ids,
            })
            memory["generation_history"] = gen_history[:100]  # Keep last 100
            memory["last_photo_generated"] = datetime.utcnow().isoformat()
            memory["total_photos_generated"] = memory.get("total_photos_generated", 0) + len(images)
            await db.execute(
                "UPDATE ai_profiles SET memory = ? WHERE id = ?",
                (json.dumps(memory), profile_id),
            )
        except Exception:
            pass

        await db.execute(
            "UPDATE ai_profiles SET total_photos = total_photos + ?, total_cost = total_cost + ?, updated_at = datetime('now') WHERE id = ?",
            (len(images), total_cost, profile_id),
        )
        await db.commit()

        result["used_reference_images"] = used_reference_images
        result["used_lora"] = used_lora
        result["total_cost"] = total_cost
        result["gallery_ids"] = gallery_ids

    return result


@router.post("/{profile_id}/generate-video")
async def generate_video(
    profile_id: int,
    req: GenerateVideoRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """RunPod LatentSync 1.6 video generation pipeline.

    Single path — no LoRA needed:
      1. edge-tts voice (free) → 2. Pexels base video (free) → 3. LatentSync 1.6 lipsync (RunPod ~$0.009/3s)

    Profile settings used:
      - voice_config.persona_id → voice persona for edge-tts
      - appearance → Pexels video search queries (ethnicity, hair_color)
    """
    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = _parse_profile(row)

    # Extract profile settings for pipeline
    from app.services.content_generation import run_full_pipeline
    appearance = profile.get("appearance", {})
    voice_config = profile.get("voice_config", {})
    persona_id = voice_config.get("persona_id", "jessica_fire")

    result = await run_full_pipeline(
        text=req.text,
        voice_id=persona_id,
        moment_type=req.moment_type,
        appearance=appearance,
        base_video_url=req.base_video_url,
    )

    total_cost = result.get("total_cost", 0)
    if result.get("success"):
        # Save to content_items
        lipsync_step = next((s for s in result.get("steps", []) if s.get("step") == "lipsync"), None)
        video_data = (lipsync_step or {}).get("result", {}).get("video", {})
        await db.execute(
            """INSERT INTO content_items (profile_id, content_type, title, prompt, file_path, file_url, cost, status, metadata)
               VALUES (?, 'video', ?, ?, ?, ?, ?, 'completed', ?)""",
            (
                profile_id,
                f"Video: {req.moment_type}",
                req.text,
                video_data.get("file_path") if isinstance(video_data, dict) else None,
                video_data.get("url") if isinstance(video_data, dict) else None,
                total_cost,
                json.dumps({
                    "moment_type": req.moment_type,
                    "engine": "runpod_latentsync",
                    "persona": persona_id,
                }),
            ),
        )
        await db.execute(
            "UPDATE ai_profiles SET total_videos = total_videos + 1, total_cost = total_cost + ?, updated_at = datetime('now') WHERE id = ?",
            (total_cost, profile_id),
        )
        await db.commit()

    return result


# ─── Content Gallery ──────────────────────────────────────────────────

class SaveContentRequest(BaseModel):
    content_type: str = "reel"
    title: Optional[str] = None
    prompt: Optional[str] = None
    file_path: Optional[str] = None
    file_url: Optional[str] = None
    thumbnail_path: Optional[str] = None
    duration: Optional[float] = None
    cost: float = 0.0
    status: str = "completed"
    metadata: Optional[dict] = None


@router.post("/{profile_id}/content")
async def save_content(
    profile_id: int,
    req: SaveContentRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Save content (reel, photo, video, voice) to a girl's profile."""
    cursor = await db.execute("SELECT id FROM ai_profiles WHERE id = ?", (profile_id,))
    if not await cursor.fetchone():
        raise HTTPException(404, "Profile not found")

    metadata_str = json.dumps(req.metadata or {})
    cursor = await db.execute(
        """INSERT INTO content_items
           (profile_id, content_type, title, prompt, file_path, file_url,
            thumbnail_path, duration, cost, status, metadata)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (profile_id, req.content_type, req.title, req.prompt,
         req.file_path, req.file_url, req.thumbnail_path,
         req.duration, req.cost, req.status, metadata_str),
    )
    content_id = cursor.lastrowid

    # Update profile counters
    if req.content_type in ("reel", "video", "lipsync"):
        await db.execute(
            "UPDATE ai_profiles SET total_videos = total_videos + 1, total_cost = total_cost + ?, updated_at = datetime('now') WHERE id = ?",
            (req.cost, profile_id),
        )
    elif req.content_type == "photo":
        await db.execute(
            "UPDATE ai_profiles SET total_photos = total_photos + 1, total_cost = total_cost + ?, updated_at = datetime('now') WHERE id = ?",
            (req.cost, profile_id),
        )
    else:
        await db.execute(
            "UPDATE ai_profiles SET total_cost = total_cost + ?, updated_at = datetime('now') WHERE id = ?",
            (req.cost, profile_id),
        )
    await db.commit()

    return {
        "success": True,
        "content_id": content_id,
        "profile_id": profile_id,
        "content_type": req.content_type,
        "title": req.title,
        "file_url": req.file_url,
    }


@router.get("/{profile_id}/content")
async def get_content(
    profile_id: int,
    content_type: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    db: aiosqlite.Connection = Depends(get_db),
):
    query = "SELECT * FROM content_items WHERE profile_id = ?"
    params: list = [profile_id]
    if content_type:
        query += " AND content_type = ?"
        params.append(content_type)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        if "metadata" in d and isinstance(d["metadata"], str):
            try:
                d["metadata"] = json.loads(d["metadata"])
            except Exception:
                d["metadata"] = {}
        result.append(d)
    return result


@router.get("/{profile_id}/costs")
async def get_costs(profile_id: int, db: aiosqlite.Connection = Depends(get_db)):
    """Cost breakdown for this girl."""
    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = _parse_profile(row)

    cursor2 = await db.execute(
        "SELECT content_type, COUNT(*) as count, SUM(cost) as total_cost FROM content_items WHERE profile_id = ? GROUP BY content_type",
        (profile_id,),
    )
    breakdown = [{"type": r["content_type"], "count": r["count"], "cost": round(r["total_cost"] or 0, 4)} for r in await cursor2.fetchall()]

    return {
        "profile_id": profile_id, "name": profile["name"],
        "total_cost": round(profile.get("total_cost", 0), 4),
        "total_photos": profile.get("total_photos", 0),
        "total_videos": profile.get("total_videos", 0),
        "total_posts": profile.get("total_posts", 0),
        "breakdown": breakdown,
        "cost_estimates": {"voice_3s": "$0.018", "photo_1x": "$0.021-0.04", "video_3s_omnihuman": "$0.48+photo", "video_5s_kling_i2v": "$0.28", "lipsync_5s_kling": "$0.07"},
    }


# ─── Social Media ─────────────────────────────────────────────────────

@router.post("/{profile_id}/schedule-post")
async def schedule_post(
    profile_id: int,
    req: SchedulePostRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute("SELECT id FROM ai_profiles WHERE id = ?", (profile_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Profile not found")

    await db.execute(
        """INSERT INTO social_posts (profile_id, content_item_id, platform, caption, hashtags, scheduled_at, status)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (profile_id, req.content_item_id, req.platform, req.caption, json.dumps(req.hashtags),
         req.scheduled_at or datetime.utcnow().isoformat(), "scheduled" if req.scheduled_at else "draft"),
    )
    await db.commit()
    return {"success": True, "message": f"Post scheduled for {req.platform}"}


@router.get("/{profile_id}/social-posts")
async def get_social_posts(
    profile_id: int,
    platform: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    db: aiosqlite.Connection = Depends(get_db),
):
    query = "SELECT * FROM social_posts WHERE profile_id = ?"
    params: list = [profile_id]
    if platform:
        query += " AND platform = ?"
        params.append(platform)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        for k in ("hashtags", "engagement"):
            if k in d and isinstance(d[k], str):
                try:
                    d[k] = json.loads(d[k])
                except Exception:
                    d[k] = [] if k == "hashtags" else {}
        result.append(d)
    return result


# ─── Memory / Brain ───────────────────────────────────────────────────

@router.get("/{profile_id}/memory")
async def get_memory(profile_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = _parse_profile(row)

    cursor2 = await db.execute("SELECT COUNT(*) as cnt FROM content_items WHERE profile_id = ?", (profile_id,))
    content_count = (await cursor2.fetchone())["cnt"]
    cursor3 = await db.execute("SELECT COUNT(*) as cnt FROM voice_samples WHERE profile_id = ?", (profile_id,))
    voice_count = (await cursor3.fetchone())["cnt"]
    cursor4 = await db.execute("SELECT COUNT(*) as cnt FROM social_posts WHERE profile_id = ?", (profile_id,))
    post_count = (await cursor4.fetchone())["cnt"]

    memory = profile.get("memory", {})
    if not isinstance(memory, dict):
        memory = {}
    memory["stats"] = {
        "total_content": content_count, "total_voice_samples": voice_count,
        "total_social_posts": post_count, "total_cost": round(profile.get("total_cost", 0), 4),
    }

    return {
        "profile_id": profile_id, "name": profile["name"],
        "memory": memory, "personality": profile.get("personality", {}),
        "content_style": profile.get("content_style", {}),
        "voice_config": profile.get("voice_config", {}),
        "social_config": profile.get("social_config", {}),
    }


@router.put("/{profile_id}/memory")
async def update_memory(
    profile_id: int,
    req: UpdateMemoryRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute("SELECT memory FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    raw = row["memory"]
    memory = json.loads(raw) if isinstance(raw, str) else (raw if isinstance(raw, dict) else {})

    if req.personality_notes is not None:
        memory["personality_notes"] = req.personality_notes
    if req.style_preferences is not None:
        memory["style_preferences"] = req.style_preferences
    if req.audience_insights is not None:
        memory["audience_insights"] = req.audience_insights
    if req.content_performance is not None:
        memory["content_performance"] = req.content_performance
    if req.voice_preferences is not None:
        memory["voice_preferences"] = req.voice_preferences
    if req.custom_data is not None:
        memory.update(req.custom_data)
    memory["last_updated"] = datetime.utcnow().isoformat()

    await db.execute(
        "UPDATE ai_profiles SET memory = ?, updated_at = datetime('now') WHERE id = ?",
        (json.dumps(memory), profile_id),
    )
    await db.commit()
    return {"success": True, "memory": memory}


# ─── Pipeline & Prompts ───────────────────────────────────────────────

@router.get("/{profile_id}/pipeline")
async def get_profile_pipeline(profile_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = _parse_profile(row)
    persona_id = profile.get("voice_config", {}).get("persona_id", "jessica_fire")
    persona = VOICE_PERSONAS.get(persona_id, VOICE_PERSONAS["jessica_fire"])

    return {
        "profile_id": profile_id, "name": profile["name"],
        "voice_persona": {
            "id": persona_id, "name": persona["name"], "description": persona["description"],
            "voice": persona["elevenlabs_voice"], "signature_tags": persona["signature_tags"],
            "style_guide": persona["style_guide"],
        },
        "pipeline": {
            "step_1_voice": {"tool": "ElevenLabs v3", "description": "Voice with audio tags", "cost": "$0.03/1000 chars"},
            "step_2_photo": {"tool": "fal.ai Flux/SDXL", "description": "Character photo", "cost": "$0.01/image"},
            "step_3_lipsync": {"tool": "VEED/Sync Lipsync", "description": "Lip-sync animation", "cost": "$0.02-0.035/3s"},
        },
        "content_types": {
            "voice": "Voice commentary with audio tags",
            "photo": "Character photo for Instagram/Telegram",
            "video": "Full lip-synced video",
            "reel": "Instagram/TikTok reel with montage",
        },
        "cost_summary": {
            "voice_only": "$0.003", "photo_only": "$0.01", "video_3s": "$0.03-0.05",
            "full_reel": "$0.10-0.15", "monthly_50_reels": "$5-7.50",
        },
    }


# ─── RunPod / Pexels / Kokoro TTS Endpoints ──────────────────────────

@router.get("/runpod-status")
async def get_runpod_status():
    """Check RunPod Serverless endpoint status and pricing."""
    from app.services.runpod_lipsync_service import get_runpod_status, get_runpod_pricing
    return {
        "status": await get_runpod_status(),
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
async def source_base_videos(data: dict | None = None):
    """Source new base videos from Pexels for LatentSync."""
    from app.services.smart_girl_video_sourcer import source_base_videos
    appearance = (data or {}).get("appearance")
    count = (data or {}).get("count", 5)
    result = await source_base_videos(appearance=appearance, max_videos=count)
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


@router.post("/{profile_id}/generate-prompt")
async def generate_prompt(
    profile_id: int, content_type: str = "clip_reaction", context: str = "",
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = _parse_profile(row)
    prompt = generate_image_prompt(profile, content_type, context)
    return {"prompt": prompt, "content_type": content_type}


@router.post("/{profile_id}/interpret-prompt")
async def interpret_prompt_endpoint(
    profile_id: int,
    text: str = "",
    db: aiosqlite.Connection = Depends(get_db),
):
    """Smart prompt interpreter: takes casual Russian text and returns structured EN prompt.

    Example input: "красное платье на пляже"
    Returns: full English prompt + detected elements (clothing, location, mood, etc.)
    """
    from app.services.smart_prompt_interpreter import interpret_prompt, is_russian_text

    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = _parse_profile(row)
    appearance = profile.get("appearance", {})
    trigger_word = profile.get("lora_trigger_word")

    if is_russian_text(text):
        result = interpret_prompt(text, appearance=appearance, trigger_word=trigger_word)
    else:
        result = {
            "prompt": f"{trigger_word}, {text}" if trigger_word else text,
            "content_type": "portrait",
            "detected": {},
            "original_text": text,
        }

    return result


@router.post("/{profile_id}/generate-script")
async def generate_script(
    profile_id: int, moment_type: str = "clutch", moment_description: str = "",
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = _parse_profile(row)
    script = generate_voice_script(profile, moment_type, moment_description)
    return {"script": script, "moment_type": moment_type}


# ─── Generation Tasks (legacy) ────────────────────────────────────────

@router.get("/{profile_id}/tasks")
async def list_tasks(profile_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute(
        "SELECT * FROM generation_tasks WHERE profile_id = ? ORDER BY created_at DESC LIMIT 50",
        (profile_id,),
    )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        for k in ("config", "result"):
            if k in d and isinstance(d[k], str):
                try:
                    d[k] = json.loads(d[k])
                except Exception:
                    d[k] = {}
        result.append(d)
    return result


# ─── Profile Gallery (Cloud URLs, no local storage) ──────────────────

@router.get("/{profile_id}/gallery")
async def get_gallery(
    profile_id: int,
    content_type: Optional[str] = None,
    favorites_only: bool = False,
    references_only: bool = False,
    limit: int = Query(default=50, le=200),
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get all generated photos for this girl. Stored as cloud URLs — no server storage used."""
    query = "SELECT * FROM profile_gallery WHERE profile_id = ?"
    params: list = [profile_id]
    if content_type:
        query += " AND content_type = ?"
        params.append(content_type)
    if favorites_only:
        query += " AND is_favorite = 1"
    if references_only:
        query += " AND is_reference = 1"
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        if "metadata" in d and isinstance(d["metadata"], str):
            try:
                d["metadata"] = json.loads(d["metadata"])
            except Exception:
                d["metadata"] = {}
        result.append(d)
    return {"gallery": result, "total": len(result)}


@router.post("/{profile_id}/gallery/{photo_id}/approve")
async def approve_gallery_photo(
    profile_id: int, photo_id: int,
    set_as_reference: bool = False,
    is_favorite: bool = False,
    quality_rating: Optional[int] = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Approve/rate a generated photo. Optionally set as reference for identity lock."""
    cursor = await db.execute(
        "SELECT * FROM profile_gallery WHERE id = ? AND profile_id = ?",
        (photo_id, profile_id),
    )
    photo = await cursor.fetchone()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    updates = ["is_approved = 1"]
    params: list = []
    if is_favorite:
        updates.append("is_favorite = 1")
    if quality_rating is not None:
        updates.append("quality_rating = ?")
        params.append(quality_rating)

    params.append(photo_id)
    await db.execute(f"UPDATE profile_gallery SET {', '.join(updates)} WHERE id = ?", params)

    # Set as reference image for identity lock
    if set_as_reference:
        await db.execute(
            "UPDATE profile_gallery SET is_reference = 1 WHERE id = ? AND profile_id = ?",
            (photo_id, profile_id),
        )
        # Update profile reference_images array
        cursor2 = await db.execute("SELECT reference_images FROM ai_profiles WHERE id = ?", (profile_id,))
        row2 = await cursor2.fetchone()
        if row2:
            refs = json.loads(row2["reference_images"]) if isinstance(row2["reference_images"], str) else []
            photo_url = dict(photo)["image_url"]
            if photo_url not in refs:
                refs.insert(0, photo_url)
                refs = refs[:4]  # Max 4 reference images
            await db.execute(
                "UPDATE ai_profiles SET reference_images = ?, updated_at = datetime('now') WHERE id = ?",
                (json.dumps(refs), profile_id),
            )

    # Record in prompt_learning for auto-improvement
    photo_dict = dict(photo)
    if quality_rating and quality_rating >= 4:
        try:
            await db.execute(
                """INSERT INTO prompt_learning (profile_id, prompt_type, original_prompt, model_key, content_type, success_score, user_rating)
                   VALUES (?, 'photo', ?, ?, ?, ?, ?)""",
                (profile_id, photo_dict.get("prompt", ""), photo_dict.get("model_key", ""),
                 photo_dict.get("content_type", ""), quality_rating / 5.0, quality_rating),
            )
        except Exception:
            pass

    await db.commit()
    return {"success": True, "message": "Photo approved", "set_as_reference": set_as_reference}


@router.delete("/{profile_id}/gallery/{photo_id}")
async def delete_gallery_photo(
    profile_id: int, photo_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Delete a photo from gallery (just removes DB record, cloud URL stays)."""
    await db.execute(
        "DELETE FROM profile_gallery WHERE id = ? AND profile_id = ?",
        (photo_id, profile_id),
    )
    await db.commit()
    return {"success": True}


# ─── Voice Identity (unique voice per girl) ──────────────────────────

@router.get("/{profile_id}/voice-identity")
async def get_voice_identity(
    profile_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get the unique voice identity for this girl."""
    cursor = await db.execute(
        "SELECT * FROM voice_identity WHERE profile_id = ?", (profile_id,)
    )
    row = await cursor.fetchone()
    if not row:
        # Return default from profile
        cursor2 = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
        profile_row = await cursor2.fetchone()
        if not profile_row:
            raise HTTPException(status_code=404, detail="Profile not found")
        profile = _parse_profile(profile_row)
        vc = profile.get("voice_config", {})
        return {
            "profile_id": profile_id,
            "has_identity": False,
            "provider": "elevenlabs",
            "voice_id": profile.get("elevenlabs_voice_id"),
            "voice_settings": vc,
            "audio_tags": profile.get("voice_audio_tags", []),
        }

    d = dict(row)
    for k in ("voice_settings", "audio_tags", "sample_urls", "personality_traits"):
        if k in d and isinstance(d[k], str):
            try:
                d[k] = json.loads(d[k])
            except Exception:
                d[k] = [] if k != "voice_settings" else {}
    d["has_identity"] = True
    return d


@router.put("/{profile_id}/voice-identity")
async def update_voice_identity(
    profile_id: int,
    voice_id: Optional[str] = None,
    voice_name: Optional[str] = None,
    speaking_style: Optional[str] = None,
    language: Optional[str] = None,
    personality_traits: Optional[list[str]] = None,
    audio_tags: Optional[list[str]] = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Create or update voice identity for this girl."""
    cursor = await db.execute("SELECT id FROM ai_profiles WHERE id = ?", (profile_id,))
    if not await cursor.fetchone():
        raise HTTPException(status_code=404, detail="Profile not found")

    cursor2 = await db.execute("SELECT id FROM voice_identity WHERE profile_id = ?", (profile_id,))
    existing = await cursor2.fetchone()

    if existing:
        updates = []
        params: list = []
        if voice_id is not None:
            updates.append("voice_id = ?")
            params.append(voice_id)
        if voice_name is not None:
            updates.append("voice_name = ?")
            params.append(voice_name)
        if speaking_style is not None:
            updates.append("speaking_style = ?")
            params.append(speaking_style)
        if language is not None:
            updates.append("language = ?")
            params.append(language)
        if personality_traits is not None:
            updates.append("personality_traits = ?")
            params.append(json.dumps(personality_traits))
        if audio_tags is not None:
            updates.append("audio_tags = ?")
            params.append(json.dumps(audio_tags))
        updates.append("updated_at = datetime('now')")
        params.append(profile_id)
        await db.execute(
            f"UPDATE voice_identity SET {', '.join(updates)} WHERE profile_id = ?",
            params,
        )
    else:
        await db.execute(
            """INSERT INTO voice_identity (profile_id, voice_id, voice_name, speaking_style, language, personality_traits, audio_tags)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (profile_id, voice_id, voice_name, speaking_style or "natural",
             language or "en", json.dumps(personality_traits or []),
             json.dumps(audio_tags or [])),
        )

    # Also update main profile
    if voice_id:
        await db.execute(
            "UPDATE ai_profiles SET elevenlabs_voice_id = ?, updated_at = datetime('now') WHERE id = ?",
            (voice_id, profile_id),
        )
    if audio_tags:
        await db.execute(
            "UPDATE ai_profiles SET voice_audio_tags = ?, updated_at = datetime('now') WHERE id = ?",
            (json.dumps(audio_tags), profile_id),
        )

    await db.commit()
    return {"success": True, "message": "Voice identity updated"}


# ─── Prompt Learning / Auto-improvement ──────────────────────────────

@router.get("/{profile_id}/learning")
async def get_learning(
    profile_id: int,
    prompt_type: Optional[str] = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get prompt learning data for this girl — what works best."""
    query = "SELECT * FROM prompt_learning WHERE profile_id = ?"
    params: list = [profile_id]
    if prompt_type:
        query += " AND prompt_type = ?"
        params.append(prompt_type)
    query += " ORDER BY success_score DESC, generation_count DESC LIMIT 50"

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        if "auto_features" in d and isinstance(d["auto_features"], str):
            try:
                d["auto_features"] = json.loads(d["auto_features"])
            except Exception:
                d["auto_features"] = {}
        result.append(d)

    # Build summary of best performing content types
    type_scores: dict = {}
    for r in result:
        ct = r.get("content_type", "unknown")
        if ct not in type_scores:
            type_scores[ct] = {"count": 0, "total_score": 0.0, "best_prompt": ""}
        type_scores[ct]["count"] += r.get("generation_count", 1)
        current_score = r.get("success_score", 0.0)
        if current_score > type_scores[ct]["total_score"] / max(type_scores[ct]["count"] - r.get("generation_count", 1), 1):
            type_scores[ct]["best_prompt"] = r.get("original_prompt", "")
        type_scores[ct]["total_score"] += current_score

    return {
        "profile_id": profile_id,
        "learning_data": result,
        "content_type_performance": type_scores,
        "total_learned_prompts": len(result),
    }


# ─── LoRA Training & Management ─────────────────────────────────────

@router.post("/{profile_id}/train-lora")
async def train_lora(
    profile_id: int,
    req: TrainLoraRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Train a LoRA model for this girl's face identity.

    Flow (Real Photo approach):
    1. Search Pexels for 10-20 real photos of a model matching appearance
    2. If Pexels unavailable, fall back to AI-generated hyper-realistic photos
    3. Pack photos into zip with captions
    4. Upload to fal.ai and start training (~$2, 5-15 min)
    5. Store LoRA URL when complete

    After training, all photo generation uses LoRA trained on REAL photos
    for maximum realism. No AI-generated photos until LoRA is trained.
    """
    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = _parse_profile(row)

    # Check if already training
    current_status = profile.get("lora_training_status", "not_trained")
    if current_status == "training":
        raise HTTPException(status_code=409, detail="LoRA training already in progress")

    appearance = profile.get("appearance", {})
    if not appearance:
        raise HTTPException(status_code=400, detail="Profile has no appearance data")

    # Generate trigger word from profile name
    trigger_word = req.trigger_word
    if not trigger_word:
        name_slug = profile.get("name", "girl").lower().replace(" ", "_")[:10]
        trigger_word = f"{name_slug}_{profile_id}G"

    # Step 1: Source real model photos (Pexels) or AI fallback
    await db.execute(
        "UPDATE ai_profiles SET lora_training_status = 'sourcing_photos', lora_trigger_word = ?, updated_at = datetime('now') WHERE id = ?",
        (trigger_word, profile_id),
    )
    await db.commit()

    if req.use_real_photos:
        # Try real photos from Pexels first, fall back to AI
        source_result = await source_photos_with_fallback(
            appearance=appearance,
            trigger_word=trigger_word,
            target_count=req.num_photos,
        )
        if source_result.get("success"):
            photos = source_result["photos"]
            photo_source = source_result.get("source", "unknown")
            photographer = source_result.get("photographer", "")
        else:
            await db.execute(
                "UPDATE ai_profiles SET lora_training_status = 'failed', updated_at = datetime('now') WHERE id = ?",
                (profile_id,),
            )
            await db.commit()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to source photos: {source_result.get('error', 'Unknown error')}",
            )
    else:
        # Legacy: AI-generated training photos only
        photos = await generate_training_dataset(
            appearance=appearance,
            trigger_word=trigger_word,
            num_photos=req.num_photos,
        )
        photo_source = "ai_generated"
        photographer = "AI (FLUX Realism)"

    if len(photos) < 5:
        await db.execute(
            "UPDATE ai_profiles SET lora_training_status = 'failed', updated_at = datetime('now') WHERE id = ?",
            (profile_id,),
        )
        await db.commit()
        raise HTTPException(
            status_code=500,
            detail=f"Only generated {len(photos)} photos, need at least 5 for training",
        )

    # Save training photos to gallery
    for photo in photos:
        await db.execute(
            """INSERT INTO profile_gallery (profile_id, image_url, content_type, prompt, model_key, is_reference, metadata)
               VALUES (?, ?, 'lora_training', ?, ?, 1, ?)""",
            (
                profile_id,
                photo["url"],
                photo.get("caption", ""),
                "pexels_real" if photo_source == "pexels" else "flux2_realism",
                json.dumps({
                    "type": photo.get("type", "real_photo"),
                    "purpose": "lora_training",
                    "source": photo_source,
                    "photographer": photo.get("photographer", photographer),
                }),
            ),
        )

    # Save training photos as reference images
    ref_urls = [p["url"] for p in photos[:4]]
    await db.execute(
        "UPDATE ai_profiles SET reference_images = ?, updated_at = datetime('now') WHERE id = ?",
        (json.dumps(ref_urls), profile_id),
    )
    await db.commit()

    # Step 2: Start LoRA training
    await db.execute(
        "UPDATE ai_profiles SET lora_training_status = 'training', updated_at = datetime('now') WHERE id = ?",
        (profile_id,),
    )
    await db.commit()

    training_result = await start_lora_training(
        profile_id=profile_id,
        trigger_word=trigger_word,
        photos=photos,
        steps=req.steps,
    )

    if not training_result.get("success"):
        await db.execute(
            "UPDATE ai_profiles SET lora_training_status = 'failed', updated_at = datetime('now') WHERE id = ?",
            (profile_id,),
        )
        await db.commit()
        raise HTTPException(status_code=500, detail=training_result.get("error", "Training failed"))

    # Save training record to lora_models table
    request_id = training_result.get("request_id", "")
    await db.execute(
        """INSERT INTO lora_models (profile_id, trigger_word, training_status, training_steps,
           training_images_count, training_cost, training_started_at, fal_request_id, metadata)
           VALUES (?, ?, 'training', ?, ?, ?, datetime('now'), ?, ?)""",
        (
            profile_id,
            trigger_word,
            req.steps,
            len(photos),
            LORA_TRAINING_CONFIG["cost_per_training"],
            request_id,
            json.dumps({"zip_url": training_result.get("zip_url")}),
        ),
    )
    await db.commit()

    return {
        "success": True,
        "profile_id": profile_id,
        "trigger_word": trigger_word,
        "request_id": request_id,
        "training_photos": len(photos),
        "photo_source": photo_source,
        "photographer": photographer,
        "steps": req.steps,
        "estimated_cost": LORA_TRAINING_CONFIG["cost_per_training"],
        "status": "training",
        "message": (
            f"LoRA training started with {len(photos)} {'real model' if photo_source == 'pexels' else 'AI-generated'} photos. "
            f"Training will take 5-15 minutes."
        ),
    }


@router.get("/{profile_id}/lora-status")
async def get_lora_status(
    profile_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Check LoRA training status and update DB when complete."""
    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = _parse_profile(row)
    lora_status = profile.get("lora_training_status", "not_trained")

    # Get latest lora_models record
    cursor_lora = await db.execute(
        "SELECT * FROM lora_models WHERE profile_id = ? ORDER BY id DESC LIMIT 1",
        (profile_id,),
    )
    lora_row = await cursor_lora.fetchone()
    lora_record = dict(lora_row) if lora_row else None

    # If training in progress, poll fal.ai for status
    if lora_status == "training" and lora_record:
        request_id = lora_record.get("fal_request_id", "")
        if request_id:
            fal_status = await check_training_status(request_id)
            fal_state = fal_status.get("status", "")

            if fal_state == "completed":
                lora_url = fal_status.get("lora_url", "")
                lora_weights_url = fal_status.get("lora_weights_url", "")
                config_url = fal_status.get("config_url", "")

                # Update ai_profiles
                await db.execute(
                    """UPDATE ai_profiles SET
                       lora_model_url = ?, lora_training_status = 'trained',
                       lora_trained_at = datetime('now'), updated_at = datetime('now')
                       WHERE id = ?""",
                    (lora_weights_url or lora_url, profile_id),
                )

                # Update lora_models
                await db.execute(
                    """UPDATE lora_models SET
                       lora_url = ?, lora_weights_url = ?, config_url = ?,
                       training_status = 'completed', training_completed_at = datetime('now')
                       WHERE id = ?""",
                    (lora_url, lora_weights_url, config_url, lora_record["id"]),
                )
                await db.commit()

                lora_status = "trained"

            elif fal_state == "failed":
                error = fal_status.get("error", "Unknown error")
                await db.execute(
                    "UPDATE ai_profiles SET lora_training_status = 'failed', updated_at = datetime('now') WHERE id = ?",
                    (profile_id,),
                )
                await db.execute(
                    "UPDATE lora_models SET training_status = 'failed', error = ? WHERE id = ?",
                    (error, lora_record["id"]),
                )
                await db.commit()
                lora_status = "failed"

    return {
        "profile_id": profile_id,
        "lora_status": lora_status,
        "lora_model_url": profile.get("lora_model_url"),
        "lora_trigger_word": profile.get("lora_trigger_word"),
        "lora_trained_at": profile.get("lora_trained_at"),
        "training_record": lora_record,
        "config": {
            "training_cost": LORA_TRAINING_CONFIG["cost_per_training"],
            "inference_cost": LORA_INFERENCE_CONFIG["cost_per_image"],
        },
    }


@router.post("/{profile_id}/complete-lora-training")
async def complete_lora_training(
    profile_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Wait for LoRA training to finish and return result.

    Blocks until training completes (up to 15 min) or fails.
    Use /lora-status for non-blocking polling instead.
    """
    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = _parse_profile(row)

    if profile.get("lora_training_status") == "trained":
        return {
            "success": True,
            "status": "already_trained",
            "lora_model_url": profile.get("lora_model_url"),
            "lora_trigger_word": profile.get("lora_trigger_word"),
        }

    # Get latest lora_models record
    cursor_lora = await db.execute(
        "SELECT * FROM lora_models WHERE profile_id = ? ORDER BY id DESC LIMIT 1",
        (profile_id,),
    )
    lora_row = await cursor_lora.fetchone()
    if not lora_row:
        raise HTTPException(status_code=404, detail="No LoRA training found for this profile")

    lora_record = dict(lora_row)
    request_id = lora_record.get("fal_request_id", "")
    if not request_id:
        raise HTTPException(status_code=400, detail="No training request ID found")

    # Wait for training to complete (blocking)
    result = await wait_for_training(request_id, timeout_seconds=900)
    status = result.get("status", "")

    if status == "completed":
        lora_url = result.get("lora_url", "")
        lora_weights_url = result.get("lora_weights_url", "")
        config_url = result.get("config_url", "")

        await db.execute(
            """UPDATE ai_profiles SET
               lora_model_url = ?, lora_training_status = 'trained',
               lora_trained_at = datetime('now'), updated_at = datetime('now')
               WHERE id = ?""",
            (lora_weights_url or lora_url, profile_id),
        )
        await db.execute(
            """UPDATE lora_models SET
               lora_url = ?, lora_weights_url = ?, config_url = ?,
               training_status = 'completed', training_completed_at = datetime('now')
               WHERE id = ?""",
            (lora_url, lora_weights_url, config_url, lora_record["id"]),
        )
        await db.commit()

        return {
            "success": True,
            "status": "trained",
            "lora_model_url": lora_weights_url or lora_url,
            "lora_trigger_word": lora_record.get("trigger_word"),
            "config_url": config_url,
        }
    else:
        error = result.get("error", "Training did not complete")
        await db.execute(
            "UPDATE ai_profiles SET lora_training_status = 'failed', updated_at = datetime('now') WHERE id = ?",
            (profile_id,),
        )
        await db.execute(
            "UPDATE lora_models SET training_status = 'failed', error = ? WHERE id = ?",
            (error, lora_record["id"]),
        )
        await db.commit()

        return {"success": False, "status": status, "error": error}


# ─── Smart Identity Lock ─────────────────────────────────────────────

@router.post("/{profile_id}/lock-identity")
async def lock_identity(
    profile_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Lock visual identity — find and save consistent base videos from Pexels.

    Searches for videos matching the girl's appearance, groups by photographer
    (same photographer = same model = visual consistency), and locks the best
    set to this profile. All future video generation uses these locked videos.
    """
    from app.services.smart_identity import lock_identity_videos

    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = _parse_profile(row)
    appearance = profile.get("appearance", {})

    result = await lock_identity_videos(db, profile_id, appearance, target_count=8)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message", "Failed to lock identity"))

    return result


@router.get("/{profile_id}/base-videos")
async def get_base_videos(
    profile_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get all locked base videos for a profile."""
    from app.services.smart_identity import get_profile_base_videos

    videos = await get_profile_base_videos(db, profile_id)
    return {
        "profile_id": profile_id,
        "videos": videos,
        "count": len(videos),
        "identity_locked": len(videos) > 0,
    }


@router.delete("/{profile_id}/unlock-identity")
async def unlock_identity_endpoint(
    profile_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Unlock visual identity — remove locked videos so new ones can be selected."""
    from app.services.smart_identity import unlock_identity
    return await unlock_identity(db, profile_id)


@router.post("/{profile_id}/generate-backstory")
async def generate_backstory_endpoint(
    profile_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Generate a unique backstory for the AI character."""
    from app.services.smart_identity import generate_backstory
    backstory = await generate_backstory(db, profile_id)
    return {"profile_id": profile_id, "backstory": backstory}


# ─── Instagram Autopilot ─────────────────────────────────────────────

@router.get("/{profile_id}/autopilot")
async def get_autopilot(
    profile_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get Instagram autopilot configuration for a profile."""
    from app.services.instagram_autopilot import get_autopilot_config
    return await get_autopilot_config(db, profile_id)


@router.put("/{profile_id}/autopilot")
async def update_autopilot(
    profile_id: int,
    data: dict,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Update Instagram autopilot configuration."""
    from app.services.instagram_autopilot import update_autopilot_config
    return await update_autopilot_config(db, profile_id, data)


@router.post("/{profile_id}/autopilot/calendar")
async def generate_calendar(
    profile_id: int,
    data: dict | None = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Generate a content calendar for the next N days."""
    from app.services.instagram_autopilot import generate_content_calendar

    days = (data or {}).get("days", 7)
    posts_per_day = (data or {}).get("posts_per_day", 2)

    entries = await generate_content_calendar(db, profile_id, days=days, posts_per_day=posts_per_day)
    return {
        "profile_id": profile_id,
        "entries": entries,
        "total": len(entries),
        "days": days,
    }


@router.get("/{profile_id}/autopilot/calendar")
async def get_calendar(
    profile_id: int,
    status: Optional[str] = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get content calendar entries."""
    from app.services.instagram_autopilot import get_content_calendar

    entries = await get_content_calendar(db, profile_id, status=status)
    return {
        "profile_id": profile_id,
        "entries": entries,
        "total": len(entries),
    }


@router.get("/{profile_id}/autopilot/analytics")
async def get_analytics(
    profile_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get autopilot analytics summary."""
    from app.services.instagram_autopilot import get_autopilot_analytics
    return await get_autopilot_analytics(db, profile_id)


@router.post("/{profile_id}/autopilot/caption")
async def generate_caption_endpoint(
    profile_id: int,
    data: dict | None = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Generate a personality-matched Instagram caption."""
    from app.services.instagram_autopilot import generate_caption

    cursor = await db.execute("SELECT personality, content_style FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    personality = json.loads(row["personality"]) if row["personality"] else {}
    content_style = json.loads(row["content_style"]) if row["content_style"] else {}

    moment_type = (data or {}).get("moment_type", "generic")
    emoji_level = content_style.get("emoji_usage", "moderate")

    return generate_caption(
        moment_type=moment_type,
        personality=personality,
        emoji_level=emoji_level,
    )


# ─── Character Memory ────────────────────────────────────────────────

@router.get("/{profile_id}/character-memory")
async def get_character_memories(
    profile_id: int,
    memory_type: Optional[str] = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get character memory entries."""
    from app.services.instagram_autopilot import get_memories
    memories = await get_memories(db, profile_id, memory_type=memory_type)
    return {"profile_id": profile_id, "memories": memories, "count": len(memories)}


@router.post("/{profile_id}/character-memory")
async def add_character_memory(
    profile_id: int,
    data: dict,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Add a memory entry for the AI character."""
    from app.services.instagram_autopilot import add_memory

    memory_id = await add_memory(
        db,
        profile_id,
        memory_type=data.get("memory_type", "general"),
        content=data.get("content", ""),
        importance=data.get("importance", 0.5),
        context=data.get("context"),
    )
    return {"success": True, "memory_id": memory_id}


@router.get("/{profile_id}/character-context")
async def get_character_context(
    profile_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get full character context (profile + memories + performance)."""
    from app.services.instagram_autopilot import build_character_context
    return await build_character_context(db, profile_id)
