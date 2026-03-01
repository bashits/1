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
import os
from datetime import datetime
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

router = APIRouter(prefix="/api/ai-profiles", tags=["ai-profiles"])


# ─── Helper ──────────────────────────────────────────────────────────
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
    name: str
    style: str = "realistic"
    description: Optional[str] = None
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


class GenerateVideoRequest(BaseModel):
    text: str
    moment_type: str = "generic"
    photo_prompt: Optional[str] = None
    photo_model_key: str = "flux2_realism"
    lipsync_model_key: str = "omnihuman"
    generate_i2v: bool = False
    i2v_model_key: str = "kling"
    i2v_prompt: str = ""


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


# ─── Profile CRUD ─────────────────────────────────────────────────────

@router.get("/")
async def list_profiles(db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM ai_profiles ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    return [_parse_profile(row) for row in rows]


@router.post("/")
async def create_profile(
    data: ProfileCreateRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    config = generate_profile_config(
        name=data.name,
        appearance_preset=data.appearance_preset,
        personality_preset=data.personality_preset,
        voice_preset=data.voice_preset,
        custom_appearance=data.custom_appearance,
        custom_personality=data.custom_personality,
        custom_voice=data.custom_voice,
    )

    # Enrich voice_config with persona info
    voice_config = config["voice_config"]
    persona = VOICE_PERSONAS.get(data.voice_persona, VOICE_PERSONAS["jessica_fire"])
    voice_config["persona_id"] = data.voice_persona
    voice_config["elevenlabs_voice_name"] = persona["elevenlabs_voice"]
    voice_config["style_guide"] = persona["style_guide"]

    memory = {
        "personality_notes": f"AI girl: {data.name}. Persona: {persona['name']}. {persona['description']}",
        "content_count": 0,
        "favorite_tags": persona["signature_tags"],
        "audience_insights": {},
        "performance_history": [],
    }

    content_style = {
        "photo_style": config["appearance"].get("style", "realistic"),
        "video_format": "vertical_9_16",
        "caption_language": "en",
        "emoji_usage": "moderate",
        "hashtag_strategy": "trending_mix",
    }

    cursor = await db.execute(
        """INSERT INTO ai_profiles (
            name, style, description, appearance, voice_config, personality,
            instagram_handle, tiktok_handle, telegram_channel,
            elevenlabs_voice_settings, voice_audio_tags,
            memory, content_style, social_config
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.name, data.style,
            data.description or f"AI girl: {data.name} — {persona['description']}",
            json.dumps(config["appearance"]), json.dumps(voice_config), json.dumps(config["personality"]),
            data.instagram_handle, data.tiktok_handle, data.telegram_channel,
            json.dumps(persona["default_settings"]), json.dumps(persona["signature_tags"]),
            json.dumps(memory), json.dumps(content_style),
            json.dumps({"posting_schedule": {"instagram": "10:00,14:00,19:00", "tiktok": "12:00,17:00,21:00"}}),
        ),
    )
    await db.commit()

    cursor2 = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (cursor.lastrowid,))
    row = await cursor2.fetchone()
    return _parse_profile(row)


@router.get("/{profile_id}")
async def get_profile(profile_id: int, db: aiosqlite.Connection = Depends(get_db)):
    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return _parse_profile(row)


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

    If the profile has reference_images and use_reference_images=true, we use FLUX 2 Pro
    multi-reference to keep the same identity.
    """
    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = _parse_profile(row)
    prompt = req.prompt or generate_image_prompt(profile, req.content_type)

    reference_images = profile.get("reference_images") or []
    if not isinstance(reference_images, list):
        reference_images = []

    from app.services.content_generation import (
        generate_photo as fal_generate_photo,
        generate_photo_with_face as fal_generate_photo_with_face,
    )

    used_reference_images = False
    if req.use_reference_images and reference_images:
        used_reference_images = True
        result = await fal_generate_photo_with_face(
            prompt=prompt,
            face_image_url=reference_images[0],
            reference_images=reference_images[:4],
            width=req.width,
            height=req.height,
            method="flux2_pro",
        )
    else:
        result = await fal_generate_photo(
            prompt=prompt,
            width=req.width,
            height=req.height,
            num_images=req.num_images,
            model_key=req.model_key,
        )

    if result.get("success"):
        images = result.get("images", [])
        per_image_cost = float(result.get("cost_estimate", 0.0) or 0.0)
        total_cost = round(per_image_cost * max(len(images), req.num_images), 4)

        for img in images:
            await db.execute(
                """INSERT INTO content_items (profile_id, content_type, title, prompt, file_path, file_url, cost, status, metadata)
                   VALUES (?, 'photo', ?, ?, ?, ?, ?, 'completed', ?)""",
                (
                    profile_id,
                    f"Photo: {req.content_type}",
                    prompt,
                    img.get("file_path"),
                    img.get("url"),
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

        if req.set_as_reference and images:
            new_ref = images[0].get("url")
            if new_ref:
                merged = [new_ref] + [u for u in reference_images if u != new_ref]
                merged = merged[:4]
                await db.execute(
                    "UPDATE ai_profiles SET reference_images = ?, updated_at = datetime('now') WHERE id = ?",
                    (json.dumps(merged), profile_id),
                )

        await db.execute(
            "UPDATE ai_profiles SET total_photos = total_photos + ?, total_cost = total_cost + ?, updated_at = datetime('now') WHERE id = ?",
            (len(images) or req.num_images, total_cost, profile_id),
        )
        await db.commit()

        result["used_reference_images"] = used_reference_images
        result["total_cost"] = total_cost

    return result


@router.post("/{profile_id}/generate-video")
async def generate_video(
    profile_id: int,
    req: GenerateVideoRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Full pipeline: voice (ElevenLabs v3) + photo (fal.ai) + lip-sync (+ optional I2V)."""
    cursor = await db.execute("SELECT * FROM ai_profiles WHERE id = ?", (profile_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    profile = _parse_profile(row)

    # Step 1: Voice
    voice_result = await generate_girl_voice(
        profile_data=profile, text=req.text, moment_type=req.moment_type
    )
    if not voice_result.get("success"):
        return {
            "success": False,
            "error": f"Voice failed: {voice_result.get('error')}",
            "steps": [{"step": "voice", "result": voice_result}],
        }

    # Step 2: Photo (use reference_images for identity if available)
    photo_prompt = req.photo_prompt or generate_image_prompt(profile, "clip_reaction")

    reference_images = profile.get("reference_images") or []
    if not isinstance(reference_images, list):
        reference_images = []

    from app.services.content_generation import (
        generate_photo as fal_photo,
        generate_photo_with_face as fal_photo_with_face,
        _upload_file_to_fal,
        generate_lipsync_video,
        generate_video_from_image,
    )

    used_reference_images = False
    if reference_images:
        used_reference_images = True
        photo_result = await fal_photo_with_face(
            prompt=photo_prompt,
            face_image_url=reference_images[0],
            reference_images=reference_images[:4],
            width=1024,
            height=1024,
            method="flux2_pro",
        )
    else:
        photo_result = await fal_photo(prompt=photo_prompt, model_key=req.photo_model_key)

    if not photo_result.get("success"):
        return {
            "success": False,
            "error": f"Photo failed: {photo_result.get('error')}",
            "steps": [
                {"step": "voice", "result": voice_result},
                {"step": "photo", "result": photo_result},
            ],
        }

    images = photo_result.get("images", [])
    image_url = images[0].get("url") if images else None
    if not image_url:
        return {"success": False, "error": "No image URL from photo generation"}

    # Step 3: Lip-sync
    audio_url = await _upload_file_to_fal(voice_result.get("file_path", ""))
    if not audio_url:
        return {"success": False, "error": "Failed to upload audio for lip-sync"}

    duration_seconds = float(voice_result.get("duration") or 3.0)
    lipsync_result = await generate_lipsync_video(
        image_url=image_url,
        audio_url=audio_url,
        model_key=req.lipsync_model_key,
        duration_seconds=duration_seconds,
    )

    # Step 4 (optional): I2V from the same identity image
    i2v_result = None
    if req.generate_i2v:
        i2v_result = await generate_video_from_image(
            image_url=image_url,
            prompt=req.i2v_prompt,
            model_key=req.i2v_model_key,
        )

    total_cost = round(
        float(voice_result.get("cost") or 0)
        + float(photo_result.get("cost_estimate") or 0)
        + float(lipsync_result.get("cost_estimate") or 0)
        + float((i2v_result or {}).get("cost_estimate") or 0),
        4,
    )

    if lipsync_result.get("success"):
        video_data = lipsync_result.get("video", {})
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
                json.dumps(
                    {
                        "moment_type": req.moment_type,
                        "persona": profile.get("voice_config", {}).get("persona_id"),
                        "photo_model_key": req.photo_model_key,
                        "lipsync_model_key": req.lipsync_model_key,
                        "used_reference_images": used_reference_images,
                        "i2v": i2v_result,
                    }
                ),
            ),
        )
        await db.execute(
            "UPDATE ai_profiles SET total_videos = total_videos + 1, total_cost = total_cost + ?, updated_at = datetime('now') WHERE id = ?",
            (total_cost, profile_id),
        )
        await db.commit()

    steps = [
        {"step": "voice", "result": voice_result},
        {"step": "photo", "result": photo_result},
        {"step": "lipsync", "result": lipsync_result},
    ]
    if i2v_result is not None:
        steps.append({"step": "i2v", "result": i2v_result})

    return {
        "success": lipsync_result.get("success", False),
        "total_cost": total_cost,
        "steps": steps,
    }


# ─── Content Gallery ──────────────────────────────────────────────────

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
        "cost_estimates": {"voice_3s": "$0.003", "photo_1x": "$0.01", "video_3s_lipsync": "$0.03-0.05", "full_reel_15s": "$0.10-0.15"},
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


@router.get("/cost-estimates/{task_type}")
async def get_cost_estimate(task_type: str):
    costs = estimate_generation_cost(task_type)
    if not costs:
        raise HTTPException(status_code=404, detail=f"Unknown task type: {task_type}")
    return {"task_type": task_type, "estimates": costs}
