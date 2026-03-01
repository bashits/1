"""Content Generation Service — Smart AI Woman Factory.

Architecture:
1. Photo generation: fal.ai FLUX 2 Realism LoRA (best photorealism) / FLUX Dev / FLUX Pro
2. Face consistency: FLUX 2 Pro with reference images (up to 4 refs) / IP-Adapter Face ID
3. Voice generation: ElevenLabs v3 (premium) / edge-tts (free fallback)
4. Lip-sync video: OmniHuman 1.5 (film-grade) / Kling Avatar v2 / VEED
5. Video generation: Kling 2.1 / Wan2.1 via fal.ai

Smart features:
- Dynamic model selection based on quality/cost/speed
- Intelligent prompt engineering for maximum realism
- Face identity preservation across all generations
- Context-aware content (gaming, lifestyle, intimate, etc.)
- Cost tracking and budget management
"""

import asyncio
import json
import math
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import fal_client
import httpx

# Storage directory for generated content
GENERATED_DIR = Path("/data/generated") if os.path.exists("/data") else Path(
    os.path.join(os.path.dirname(__file__), "..", "..", "generated")
)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
for _subdir in ("photos", "audio", "video", "references", "profiles"):
    (GENERATED_DIR / _subdir).mkdir(exist_ok=True)


def _get_fal_key() -> str:
    """Get FAL_KEY dynamically (supports runtime updates via set-api-key)."""
    return os.environ.get("FAL_KEY", "")


# ─── Model Registry ──────────────────────────────────────────────────
# ─── ACTUAL fal.ai pricing (verified March 2026) ─────────────────────
# Image models: billed per megapixel (MP). 1024×1024 = ~1MP.
# Video models: billed per second or per video.
# Lipsync models: billed per second or flat rate.
# All prices from official fal.ai model pages.

IMAGE_MODELS = {
    "flux2_realism": {
        "id": "fal-ai/flux-realism",
        "name": "FLUX Realism",
        "quality": 10,
        "cost_per_image": 0.021,  # $0.021/MP — private model, same as FLUX 2 LoRA Realism
        "best_for": ["portraits", "photorealism", "humans"],
        "default_steps": 35,
        "default_guidance": 3.5,
    },
    "flux2_pro": {
        "id": "fal-ai/flux-pro/v1.1",
        "name": "FLUX 1.1 Pro",
        "quality": 10,
        "cost_per_image": 0.04,  # $0.04/MP — official fal.ai pricing
        "best_for": ["premium", "commercial", "multi-reference"],
        "supports_reference_images": True,
    },
    "flux_dev": {
        "id": "fal-ai/flux/dev",
        "name": "FLUX Dev",
        "quality": 8,
        "cost_per_image": 0.025,  # $0.025/MP — official fal.ai pricing
        "best_for": ["general", "prototyping"],
    },
    "flux_schnell": {
        "id": "fal-ai/flux/schnell",
        "name": "FLUX Schnell",
        "quality": 7,
        "cost_per_image": 0.003,  # $0.003/MP — official fal.ai pricing
        "best_for": ["fast_iteration", "previews"],
    },
    "flux_pro_ultra": {
        "id": "fal-ai/flux-pro/v1.1-ultra",
        "name": "FLUX Pro 1.1 Ultra",
        "quality": 9,
        "cost_per_image": 0.06,  # $0.06/image — official fal.ai pricing
        "best_for": ["2K", "ultra_quality"],
    },
}

LIPSYNC_MODELS = {
    "omnihuman": {
        "id": "fal-ai/bytedance/omnihuman/v1.5",
        "name": "OmniHuman 1.5 (ByteDance)",
        "quality": 10,
        "cost_per_second": 0.16,  # $0.16/sec — official fal.ai pricing
        "input_type": "image",  # image + audio → video
        "best_for": ["film_grade", "full_body", "expressions"],
    },
    "kling_avatar": {
        "id": "fal-ai/kling-video/ai-avatar/v2/pro",
        "name": "Kling AI Avatar v2 Pro",
        "quality": 9,
        # Kling AI Avatar v2 Pro: $0.115/sec (image + audio → talking video)
        "cost_per_second": 0.115,
        "input_type": "image",  # image + audio → video
        "best_for": ["talking_head", "realistic", "natural"],
    },
    "kling_lipsync_v2v": {
        "id": "fal-ai/kling-video/lipsync/audio-to-video",
        "name": "Kling LipSync (Video-to-Video)",
        "quality": 9,
        # Kling LipSync V2V: $0.014/sec, rounds UP to nearest 5s increment
        "cost_per_second": 0.014,
        "billing_increment": 5,
        "input_type": "video",  # video + audio → lip-synced video
        "best_for": ["v2v_lipsync", "fast", "cheap"],
    },
    "veed_fabric": {
        "id": "veed/fabric-1.0",
        "name": "VEED Fabric 1.0 (Cheapest Image→Video)",
        "quality": 7,
        "cost_per_second": 0.08,  # $0.08/sec at 480p
        "input_type": "image",  # image + audio → talking video
        "best_for": ["budget", "circle_overlay", "social_media"],
    },
    "latentsync": {
        "id": "fal-ai/latentsync",
        "name": "LatentSync (Budget V2V)",
        "quality": 6,
        # LatentSync: $0.20 flat for videos ≤40s, $0.005/sec for longer
        "cost_flat_under_40s": 0.20,
        "cost_per_second_over_40s": 0.005,
        "input_type": "video",  # video + audio → lip-synced video
        "best_for": ["budget", "quick", "testing"],
    },
}

VIDEO_MODELS = {
    "kling": {
        "id": "fal-ai/kling-video/v2.1/standard/image-to-video",
        "name": "Kling 2.1 Standard I2V",
        "quality": 9,
        # Kling 2.1 Standard: $0.28 for 5s, +$0.056/extra sec
        "cost_base_5s": 0.28,
        "cost_per_extra_second": 0.056,
        "best_for": ["realistic_humans", "movement"],
        "durations": [5, 10],
    },
    "wan21": {
        "id": "fal-ai/wan-i2v",
        "name": "Wan 2.1 I2V",
        "quality": 8,
        # Wan 2.1: $0.20 at 480p, $0.40 at 720p per video (~5s)
        "cost_per_video_480p": 0.20,
        "cost_per_video_720p": 0.40,
        "best_for": ["general", "animation"],
        "durations": [5],
    },
}

# ─── Duration options for video generation ────────────────────────────
VIDEO_DURATION_OPTIONS = [3, 5, 10, 15]


def _calc_lipsync_cost(model_key: str, duration_seconds: float) -> float:
    """Calculate lipsync cost based on actual fal.ai billing rules."""
    ls_model = LIPSYNC_MODELS.get(model_key, LIPSYNC_MODELS["omnihuman"])

    if model_key == "kling_lipsync_v2v":
        # Kling LipSync V2V: $0.014/sec, rounds UP to nearest 5s
        increment = ls_model.get("billing_increment", 5)
        billed_seconds = math.ceil(duration_seconds / increment) * increment
        return round(ls_model["cost_per_second"] * billed_seconds, 4)

    if model_key == "latentsync":
        # LatentSync: $0.20 flat for ≤40s, $0.005/sec for longer
        if duration_seconds <= 40:
            return ls_model.get("cost_flat_under_40s", 0.20)
        return round(0.20 + ls_model.get("cost_per_second_over_40s", 0.005) * (duration_seconds - 40), 4)

    # All other models (omnihuman, kling_avatar, veed_fabric): simple per-second
    cost_per_sec = ls_model.get("cost_per_second", 0.0)
    return round(cost_per_sec * duration_seconds, 4)


def _calc_i2v_cost(model_key: str, duration_seconds: float) -> float:
    """Calculate image-to-video cost based on actual fal.ai billing rules."""
    model = VIDEO_MODELS.get(model_key, VIDEO_MODELS["kling"])

    if model_key == "kling":
        # Kling 2.1 Standard: $0.28 for first 5s, +$0.056/extra sec
        base = model.get("cost_base_5s", 0.28)
        if duration_seconds <= 5:
            return base
        extra = duration_seconds - 5
        return round(base + model.get("cost_per_extra_second", 0.056) * extra, 4)

    if model_key == "wan21":
        # Wan 2.1: flat per video, 720p default
        return model.get("cost_per_video_720p", 0.40)

    return 0.0


def calculate_video_cost(
    duration_seconds: float = 3.0,
    lipsync_model_key: str = "omnihuman",
    photo_model_key: str = "lora",
    include_i2v: bool = False,
    i2v_model_key: str = "kling",
    voice_engine: str = "elevenlabs",
) -> dict:
    """Calculate estimated cost for video generation pipeline BEFORE running it.

    Returns detailed breakdown so user sees exact cost before spending money.
    All prices verified against official fal.ai model pages (March 2026).
    """
    # Photo cost (LoRA inference or standard)
    if photo_model_key == "lora":
        photo_cost = 0.025  # LoRA inference via fal-ai/flux-lora (~$0.025/MP)
    else:
        model = IMAGE_MODELS.get(photo_model_key, IMAGE_MODELS["flux2_realism"])
        photo_cost = model.get("cost_per_image", 0.021)

    # Voice cost (ElevenLabs or free edge-tts)
    if voice_engine == "elevenlabs":
        # ElevenLabs charges ~$0.30/1000 chars, avg 3s clip ~ 50-80 chars
        estimated_chars = max(50, duration_seconds * 20)  # ~20 chars per second
        voice_cost = round(estimated_chars * 0.0003, 4)  # $0.30/1000 chars
    else:
        voice_cost = 0.0  # edge-tts is free

    # Lipsync cost (using accurate billing rules per model)
    lipsync_cost = _calc_lipsync_cost(lipsync_model_key, duration_seconds)
    ls_model = LIPSYNC_MODELS.get(lipsync_model_key, LIPSYNC_MODELS["omnihuman"])

    # Optional I2V cost (using accurate billing rules per model)
    i2v_cost = 0.0
    if include_i2v:
        i2v_cost = _calc_i2v_cost(i2v_model_key, duration_seconds)

    total = round(photo_cost + voice_cost + lipsync_cost + i2v_cost, 4)

    return {
        "duration_seconds": duration_seconds,
        "breakdown": {
            "photo": {"model": photo_model_key, "cost": photo_cost},
            "voice": {"engine": voice_engine, "cost": voice_cost},
            "lipsync": {
                "model": lipsync_model_key,
                "model_name": ls_model.get("name", lipsync_model_key),
                "cost": lipsync_cost,
            },
            "i2v": {"model": i2v_model_key, "cost": i2v_cost, "included": include_i2v},
        },
        "total_estimated": total,
        "currency": "USD",
    }


def get_all_pricing() -> dict:
    """Return full pricing info for all models — used by frontend cost calculator.

    All prices verified against official fal.ai model pages (March 2026).
    """
    return {
        "duration_options": VIDEO_DURATION_OPTIONS,
        "image_models": {
            k: {"name": v["name"], "cost_per_image": v.get("cost_per_image", 0), "quality": v.get("quality", 5)}
            for k, v in IMAGE_MODELS.items()
        },
        "lipsync_models": {
            "omnihuman": {
                "name": "OmniHuman 1.5 (ByteDance)",
                "pricing_type": "per_second",
                "cost_per_second": 0.16,
                "quality": 10,
                "best_for": ["film_grade", "full_body", "expressions"],
                "note": "$0.16/sec of output video",
            },
            "kling_avatar": {
                "name": "Kling LipSync Audio-to-Video",
                "pricing_type": "per_second_rounded",
                "cost_per_second": 0.014,
                "billing_increment": 5,
                "quality": 9,
                "best_for": ["talking_head", "fast", "natural"],
                "note": "$0.014/sec, billed in 5s increments (3s→$0.07)",
            },
            "latentsync": {
                "name": "LatentSync (Budget)",
                "pricing_type": "flat",
                "cost_flat_under_40s": 0.20,
                "cost_per_second_over_40s": 0.005,
                "quality": 6,
                "best_for": ["budget", "quick", "testing"],
                "note": "$0.20 flat for ≤40s, +$0.005/sec after",
            },
        },
        "video_models": {
            "kling": {
                "name": "Kling 2.1 Standard I2V",
                "pricing_type": "base_plus_extra",
                "cost_base_5s": 0.28,
                "cost_per_extra_second": 0.056,
                "quality": 9,
                "durations": [5, 10],
                "note": "$0.28 for 5s, +$0.056/extra sec",
            },
            "wan21": {
                "name": "Wan 2.1 I2V",
                "pricing_type": "per_video",
                "cost_per_video_480p": 0.20,
                "cost_per_video_720p": 0.40,
                "quality": 8,
                "durations": [5],
                "note": "$0.20 (480p) / $0.40 (720p) per video",
            },
        },
        "lora": {
            "training_cost": 2.00,  # $2 per training run (official fal.ai)
            "inference_cost": 0.025,  # ~$0.025/MP via fal-ai/flux-lora
        },
        "voice": {
            "elevenlabs": {"cost_per_1000_chars": 0.30, "note": "Premium quality"},
            "edge_tts": {"cost": 0.0, "note": "Free, lower quality"},
        },
        "cost_examples": {
            "photo_only": {
                "description": "1 photo (LoRA)",
                "cost": 0.025,
            },
            "video_3s_omnihuman": {
                "description": "Photo + 3s OmniHuman lipsync",
                "cost": round(0.025 + 0.0150 + 0.16 * 3, 4),
            },
            "video_5s_kling_lipsync": {
                "description": "Photo + 5s Kling lipsync",
                "cost": round(0.025 + 0.0150 + 0.014 * 5, 4),
            },
            "video_5s_kling_i2v": {
                "description": "Photo + 5s Kling I2V",
                "cost": round(0.025 + 0.28, 4),
            },
        },
    }


# ─── Smart Prompt Engineering ─────────────────────────────────────────
REALISM_BOOSTERS = (
    "RAW photo, shot on Sony A7IV 85mm f/1.4 GM, natural skin texture with visible pores "
    "and micro-imperfections, subsurface scattering on skin, individual hair strands visible, "
    "real catchlight reflections in eyes, shallow depth of field with natural bokeh, "
    "professional color grading with lifted blacks, subtle film grain, "
    "no airbrushing, no plastic skin, no beauty filter, "
    "photojournalistic quality, editorial magazine photography, "
    "ultra detailed 8K UHD, natural ambient occlusion, micro-contrast"
)

NEGATIVE_QUALITY = (
    "illustration, painting, drawing, anime, cartoon, CGI, 3D render, digital art, "
    "plastic skin, airbrushed, smooth skin, porcelain skin, wax figure, mannequin, "
    "unrealistic, deformed, bad anatomy, bad hands, missing fingers, extra fingers, "
    "extra limbs, disfigured, mutated, ugly, blurry eyes, cross-eyed, "
    "text, watermark, logo, blurry, low quality, overexposed, underexposed, "
    "oversaturated, beauty filter, face app, facetune, snapchat filter, "
    "stock photo, clip art, render, fake, artificial, "
    "HDR tonemapping, over-sharpened, chromatic aberration, lens flare, "
    "doll-like, uncanny valley, symmetrical face, perfect skin, "
    "instagram filter, VSCO preset, over-processed, neon glow on skin"
)


def build_photo_prompt(
    content_type: str = "portrait",
    appearance: Optional[dict] = None,
    context: str = "",
    custom_additions: str = "",
    realism_level: str = "maximum",
) -> dict:
    """Build an intelligent photo prompt optimized for maximum realism."""
    app = appearance or {}
    age = app.get("age_range", "22-25")
    ethnicity = app.get("ethnicity", "european")
    hair_color = app.get("hair_color", "dark blonde")
    hair_style = app.get("hair_style", "long slightly wavy")
    eye_color = app.get("eye_color", "green")
    skin_tone = app.get("skin_tone", "fair with natural freckles")
    body_type = app.get("body_type", "athletic slim")

    identity = (
        f"A beautiful {age} year old {ethnicity} woman, "
        f"{hair_color} {hair_style} hair, {eye_color} eyes, "
        f"{skin_tone} skin, {body_type} build"
    )

    scenes = {
        "gaming_reaction": (
            f"{identity}, wearing a sleek gaming headset around neck, "
            "at her RGB-lit gaming setup with dual monitors, "
            "leaning toward camera with excited surprised expression, mouth slightly open, "
            "wide eyes, webcam selfie angle from slightly above, "
            "dim room lit by screen glow and LED strips, "
            "natural flyaway hairs, genuine emotion"
        ),
        "gaming_chill": (
            f"{identity}, casual oversized gaming hoodie, "
            "relaxed at her desk, hand on chin, slight smirk, "
            "monitor showing game in background (out of focus), "
            "cozy neon ambient lighting, natural pose, "
            "messy hair bun, headset on desk"
        ),
        "instagram_lifestyle": (
            f"{identity}, trendy casual outfit, "
            "golden hour natural lighting, aesthetic urban background, "
            "candid moment looking slightly away from camera, "
            "wind in hair, genuine relaxed smile, "
            "shot through cafe window with reflections"
        ),
        "instagram_glam": (
            f"{identity}, elegant evening outfit, "
            "soft studio lighting with butterfly pattern, "
            "professional makeup (natural style), subtle jewelry, "
            "confident direct gaze at camera, slight head tilt, "
            "dark moody background with bokeh lights"
        ),
        "selfie_mirror": (
            f"{identity}, taking a mirror selfie with phone, "
            "bathroom mirror with soft vanity lighting, "
            "casual home outfit, hair slightly messy, "
            "authentic mirror selfie angle, phone visible, "
            "natural no-makeup look, relaxed expression"
        ),
        "intimate_cozy": (
            f"{identity}, cozy oversized sweater, "
            "lying on bed with soft duvet, warm lamp lighting, "
            "looking at camera with soft playful expression, "
            "pillows and fairy lights in background, "
            "hair spread on pillow, intimate atmosphere"
        ),
        "intimate_lingerie": (
            f"{identity}, elegant lace lingerie set, "
            "sitting on bed edge, soft directional lighting from window, "
            "confident sensual pose, looking at camera, "
            "tasteful composition, luxury bedroom interior, "
            "silk sheets, golden hour window light"
        ),
        "portrait": (
            f"{identity}, "
            "soft natural window lighting, neutral background, "
            "slight genuine smile, direct eye contact, "
            "head and shoulders composition, shallow DOF"
        ),
        "full_body": (
            f"{identity}, "
            "standing in natural relaxed pose, "
            "fashionable outfit, clean minimal background, "
            "full body visible, natural proportions, "
            "professional fashion photography lighting"
        ),
        "bikini_beach": (
            f"{identity}, stylish bikini, "
            "tropical beach at golden hour, waves in background, "
            "natural relaxed pose walking along shoreline, "
            "wind in hair, sun-kissed skin, "
            "natural body, warm sunset lighting"
        ),
    }

    base_prompt = scenes.get(content_type, scenes["portrait"])
    if context:
        base_prompt += f", {context}"
    if custom_additions:
        base_prompt += f", {custom_additions}"
    if realism_level == "maximum":
        base_prompt += f", {REALISM_BOOSTERS}"
    elif realism_level == "high":
        base_prompt += ", ultra realistic, natural skin, professional photography, 8K"
    else:
        base_prompt += ", photorealistic, high quality"

    return {"prompt": base_prompt, "negative_prompt": NEGATIVE_QUALITY}


# ─── Edge-TTS (Free voice generation) ──────────────────────────────
EDGE_TTS_VOICES = {
    "en_female_cheerful": "en-US-JennyNeural",
    "en_female_friendly": "en-US-AriaNeural",
    "en_female_warm": "en-US-SaraNeural",
    "en_female_british": "en-GB-SoniaNeural",
    "en_female_australian": "en-AU-NatashaNeural",
    "en_male_casual": "en-US-GuyNeural",
    "ru_female": "ru-RU-SvetlanaNeural",
    "ru_male": "ru-RU-DmitryNeural",
}


async def generate_tts(
    text: str,
    voice_id: str = "en_female_cheerful",
    output_filename: str | None = None,
) -> dict:
    """Generate speech audio using edge-tts (completely free).

    Returns dict with file path and metadata.
    """
    import edge_tts

    voice = EDGE_TTS_VOICES.get(voice_id, voice_id)
    if output_filename is None:
        output_filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"

    output_path = GENERATED_DIR / "audio" / output_filename

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(output_path))

    file_size = output_path.stat().st_size if output_path.exists() else 0

    return {
        "success": True,
        "file_path": str(output_path),
        "filename": output_filename,
        "voice": voice,
        "text": text,
        "file_size_bytes": file_size,
        "cost": 0.0,
        "engine": "edge-tts",
    }


async def list_tts_voices() -> list[dict]:
    """List available edge-tts voices."""
    return [
        {"id": k, "name": v, "language": k.split("_")[0]}
        for k, v in EDGE_TTS_VOICES.items()
    ]


# ─── fal.ai Smart API Layer ───────────────────────────────────────


async def _fal_run(model_id: str, input_data: dict) -> dict:
    """Run a fal.ai model using the official fal_client SDK (queue-based, reliable).

    Uses fal_client.subscribe which handles submit → poll → result automatically.
    Falls back to httpx if fal_client fails.
    """
    key = _get_fal_key()
    if not key:
        return {"success": False, "error": "FAL_KEY not set. Use /generation/set-api-key first."}

    os.environ["FAL_KEY"] = key  # Ensure fal_client picks it up

    try:
        # Use fal_client SDK — handles queueing, polling, retries
        result = await asyncio.to_thread(
            fal_client.subscribe,
            model_id,
            arguments=input_data,
            with_logs=False,
        )
        return {"success": True, "data": result}
    except Exception as sdk_err:
        # Fallback to httpx direct call
        try:
            return await _fal_request_httpx(model_id, input_data, key)
        except Exception as http_err:
            return {
                "success": False,
                "error": f"SDK: {sdk_err} | HTTP: {http_err}",
            }


async def _fal_request_httpx(
    model_id: str, input_data: dict, api_key: str, timeout: float = 180.0
) -> dict:
    """Fallback: direct HTTP request to fal.ai queue API."""
    headers = {"Authorization": f"Key {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"https://queue.fal.run/{model_id}", json=input_data, headers=headers
        )
        if resp.status_code != 200:
            return {"success": False, "error": f"fal.ai {resp.status_code}: {resp.text}"}

        result = resp.json()
        if "images" in result or "image" in result or "video" in result or "audio" in result:
            return {"success": True, "data": result}

        request_id = result.get("request_id")
        if not request_id:
            return {"success": True, "data": result}

        status_url = f"https://queue.fal.run/{model_id}/requests/{request_id}/status"
        result_url = f"https://queue.fal.run/{model_id}/requests/{request_id}"

        for _ in range(90):
            await asyncio.sleep(2)
            s = await client.get(status_url, headers=headers)
            if s.status_code == 200:
                sd = s.json()
                if sd.get("status") == "COMPLETED":
                    r = await client.get(result_url, headers=headers)
                    if r.status_code == 200:
                        return {"success": True, "data": r.json()}
                elif sd.get("status") == "FAILED":
                    return {"success": False, "error": f"Failed: {sd}"}

        return {"success": False, "error": "Timed out after 180s"}


def select_image_model(
    quality: str = "maximum",
    budget: str = "normal",
    needs_references: bool = False,
) -> dict:
    """Intelligently select the best image model based on requirements."""
    if needs_references:
        return IMAGE_MODELS["flux2_pro"]
    if quality == "maximum" and budget != "minimal":
        return IMAGE_MODELS["flux2_realism"]
    if quality == "maximum" and budget == "minimal":
        return IMAGE_MODELS["flux_dev"]
    if quality == "high":
        return IMAGE_MODELS["flux_dev"]
    if quality == "fast" or budget == "minimal":
        return IMAGE_MODELS["flux_schnell"]
    return IMAGE_MODELS["flux2_realism"]  # Default: best quality


def select_lipsync_model(quality: str = "maximum") -> dict:
    """Select the best lipsync model.

    Quality tiers:
    - maximum: OmniHuman 1.5 (film-grade, expensive)
    - high: Kling AI Avatar v2 Pro (high quality)
    - budget/circle: VEED Fabric 1.0 (cheapest image→video, great for small circle overlay)
    """
    if quality == "maximum":
        return LIPSYNC_MODELS["omnihuman"]
    if quality == "high":
        return LIPSYNC_MODELS["kling_avatar"]
    if quality in ("budget", "circle"):
        return LIPSYNC_MODELS["veed_fabric"]
    return LIPSYNC_MODELS["veed_fabric"]  # sensible default for montage overlay


async def generate_photo(
    prompt: str,
    negative_prompt: str = NEGATIVE_QUALITY,
    width: int = 1024,
    height: int = 1024,
    num_images: int = 1,
    model_key: str = "flux2_realism",
    model_override: Optional[str] = None,
    num_inference_steps: Optional[int] = None,
    guidance_scale: Optional[float] = None,
    seed: Optional[int] = None,
) -> dict:
    """Generate photo using fal.ai with smart model selection.

    Default: FLUX 2 Realism LoRA (best photorealism).
    """
    if model_override:
        model_id = model_override
        model_info = {"name": model_override, "cost_per_image": 0.01}
    else:
        model_info = IMAGE_MODELS.get(model_key, IMAGE_MODELS["flux2_realism"])
        model_id = model_info["id"]

    input_data: dict = {
        "prompt": prompt,
        "image_size": {"width": width, "height": height},
        "num_images": num_images,
        "enable_safety_checker": False,
    }

    # Model-specific params
    if "realism" in model_id or "lora" in model_id:
        input_data["num_inference_steps"] = num_inference_steps or model_info.get("default_steps", 35)
    # Use explicit guidance_scale, or model default, or skip
    effective_guidance = guidance_scale if guidance_scale is not None else model_info.get("default_guidance")
    if effective_guidance is not None:
        input_data["guidance_scale"] = effective_guidance
    if seed is not None:
        input_data["seed"] = seed
    if negative_prompt:
        input_data["negative_prompt"] = negative_prompt

    result = await _fal_run(model_id, input_data)

    if not result.get("success"):
        return result

    data = result.get("data", {})
    images = data.get("images", [])

    # Cloud-only storage: use fal.ai CDN URLs directly, NO local downloads
    cloud_files = []
    for img in images:
        img_url = img.get("url", "")
        if img_url:
            cloud_files.append({
                "url": img_url,
                "width": img.get("width", width),
                "height": img.get("height", height),
            })

    cost = model_info.get("cost_per_image", 0.01) * num_images
    return {
        "success": True,
        "images": cloud_files,
        "model": model_id,
        "model_name": model_info.get("name", model_id),
        "prompt": prompt,
        "cost_estimate": cost,
        "engine": "fal.ai",
    }


async def generate_photo_with_face(
    prompt: str,
    face_image_url: str,
    reference_images: Optional[list[str]] = None,
    negative_prompt: str = NEGATIVE_QUALITY,
    width: int = 1024,
    height: int = 1024,
    method: str = "auto",
) -> dict:
    """Generate photo with face consistency.

    Methods:
    - 'flux2_pro': FLUX 2 Pro with reference images (best, $0.05)
    - 'ip_adapter': IP-Adapter Face ID (cheap, $0.001)
    - 'auto': Uses flux2_pro if reference_images provided, else ip_adapter
    """
    all_refs = [face_image_url]
    if reference_images:
        all_refs.extend(reference_images[:3])  # Max 4 total

    use_flux2 = method == "flux2_pro" or (method == "auto" and len(all_refs) >= 2)

    if use_flux2:
        # FLUX 2 Pro with reference images — best quality
        model_id = IMAGE_MODELS["flux2_pro"]["id"]
        input_data: dict = {
            "prompt": prompt,
            "image_size": {"width": width, "height": height},
            "num_images": 1,
            "enable_safety_checker": False,
            "reference_images": [{"image_url": url} for url in all_refs],
        }
        if negative_prompt:
            input_data["negative_prompt"] = negative_prompt
        cost = 0.04  # FLUX 1.1 Pro: $0.04/MP
    else:
        # IP-Adapter Face ID — budget option
        model_id = "fal-ai/ip-adapter-face-id"
        input_data = {
            "prompt": prompt,
            "face_image_url": face_image_url,
            "negative_prompt": negative_prompt,
            "image_size": {"width": width, "height": height},
            "num_images": 1,
        }
        cost = 0.001

    result = await _fal_run(model_id, input_data)

    if not result.get("success"):
        return result

    data = result.get("data", {})
    # Handle both single image and images array
    images = data.get("images", [])
    image = data.get("image") or (images[0] if images else {})
    img_url = image.get("url", "") if isinstance(image, dict) else ""

    # Cloud-only: use fal.ai CDN URL directly, NO local download
    cloud_file = None
    if img_url:
        cloud_file = {
            "url": img_url,
            "width": image.get("width", width) if isinstance(image, dict) else width,
            "height": image.get("height", height) if isinstance(image, dict) else height,
        }

    return {
        "success": True,
        "image": cloud_file,
        "images": [cloud_file] if cloud_file else [],
        "model": model_id,
        "method": "flux2_pro" if use_flux2 else "ip_adapter",
        "prompt": prompt,
        "cost_estimate": cost,
        "engine": "fal.ai",
    }


# ─── Lip-sync Video Generation ─────────────────────────────────────
async def generate_lipsync_video(
    image_url: str,
    audio_url: str,
    model_key: str = "omnihuman",
    duration_seconds: float = 3.0,
) -> dict:
    """Generate lip-synced video from image + audio.

    Models:
    - omnihuman: OmniHuman 1.5 — film-grade, $0.16/sec
    - kling_avatar: Kling LipSync — $0.014/sec (billed in 5s increments)
    - latentsync: LatentSync — $0.20 flat for ≤40s
    """
    model_info = LIPSYNC_MODELS.get(model_key, LIPSYNC_MODELS["omnihuman"])
    model_id = model_info["id"]

    input_data: dict = {}
    input_type = model_info.get("input_type", "image")

    if input_type == "image":
        # Models that accept image + audio (omnihuman, kling_avatar, veed_fabric)
        input_data = {
            "image_url": image_url,
            "audio_url": audio_url,
        }
        # Kling Avatar v2 Pro requires a prompt field
        if model_key == "kling_avatar":
            input_data["prompt"] = "."
    else:
        # Models that accept video + audio (kling_lipsync_v2v, latentsync)
        input_data = {
            "video_url": image_url,  # caller must pass a video URL for v2v models
            "audio_url": audio_url,
        }

    result = await _fal_run(model_id, input_data)

    if not result.get("success"):
        return result

    data = result.get("data", {})
    video = data.get("video", data.get("output", {}))
    video_url = video.get("url", "") if isinstance(video, dict) else ""

    saved_file = None
    if video_url:
        fname = f"lipsync_{uuid.uuid4().hex[:8]}.mp4"
        fpath = GENERATED_DIR / "video" / fname
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                vid_resp = await client.get(video_url)
                if vid_resp.status_code == 200:
                    fpath.write_bytes(vid_resp.content)
                    saved_file = {
                        "filename": fname,
                        "file_path": str(fpath),
                        "url": video_url,
                    }
            except Exception as e:
                saved_file = {"url": video_url, "error": str(e)}

    cost = _calc_lipsync_cost(model_key, duration_seconds)
    return {
        "success": True,
        "video": saved_file,
        "model": model_id,
        "model_name": model_info["name"],
        "cost_estimate": round(cost, 4),
        "engine": "fal.ai",
    }


# ─── Image-to-Video Generation ────────────────────────────────────
async def generate_video_from_image(
    image_url: str,
    prompt: str = "",
    model_key: str = "kling",
    duration: str = "5",
) -> dict:
    """Generate video from a static image (I2V).

    Models:
    - kling: Kling 2.1 Standard — best for realistic humans ($0.28/5s + $0.056/extra sec)
    - wan21: Wan 2.1 — general purpose ($0.20-$0.40/video)
    """
    model_info = VIDEO_MODELS.get(model_key, VIDEO_MODELS["kling"])
    model_id = model_info["id"]

    input_data: dict = {
        "image_url": image_url,
        "duration": duration,
    }
    if prompt:
        input_data["prompt"] = prompt

    result = await _fal_run(model_id, input_data)

    if not result.get("success"):
        return result

    data = result.get("data", {})
    video = data.get("video", {})
    video_url = video.get("url", "") if isinstance(video, dict) else ""

    saved_file = None
    if video_url:
        fname = f"i2v_{uuid.uuid4().hex[:8]}.mp4"
        fpath = GENERATED_DIR / "video" / fname
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                vid_resp = await client.get(video_url)
                if vid_resp.status_code == 200:
                    fpath.write_bytes(vid_resp.content)
                    saved_file = {
                        "filename": fname,
                        "file_path": str(fpath),
                        "url": video_url,
                    }
            except Exception as e:
                saved_file = {"url": video_url, "error": str(e)}

    try:
        duration_s = float(duration)
    except Exception:
        duration_s = 5.0

    cost_estimate = _calc_i2v_cost(model_key, duration_s)

    return {
        "success": True,
        "video": saved_file,
        "model": model_id,
        "model_name": model_info["name"],
        "duration_seconds": duration_s,
        "cost_estimate": cost_estimate,
        "engine": "fal.ai",
    }


# ─── Full Smart Pipeline ──────────────────────────────────────────
async def run_full_pipeline(
    text: str,
    photo_prompt: Optional[str] = None,
    content_type: str = "gaming_reaction",
    appearance: Optional[dict] = None,
    voice_id: str = "en_female_cheerful",
    face_image_url: Optional[str] = None,
    reference_images: Optional[list[str]] = None,
    quality: str = "maximum",
    lipsync_model_key: str = "omnihuman",
    photo_model_key: str = "flux2_realism",
    generate_i2v: bool = False,
) -> dict:
    """Run the complete smart generation pipeline:

    1. Build smart prompt (if photo_prompt not provided)
    2. Generate TTS audio (edge-tts free / ElevenLabs premium)
    3. Generate character photo (FLUX 2 Realism / Pro)
    4. Generate lip-synced video (OmniHuman 1.5 / Kling / VEED)
    5. Optional: Generate I2V movement video
    """
    results: dict = {"steps": [], "total_cost": 0.0, "pipeline_id": uuid.uuid4().hex[:12]}

    # Step 1: Build smart prompt if needed
    if not photo_prompt:
        prompt_data = build_photo_prompt(
            content_type=content_type,
            appearance=appearance,
            realism_level="maximum" if quality == "maximum" else "high",
        )
        photo_prompt = prompt_data["prompt"]
        neg_prompt = prompt_data["negative_prompt"]
    else:
        neg_prompt = NEGATIVE_QUALITY

    results["steps"].append({"step": "prompt", "prompt": photo_prompt})

    # Step 2: Generate voice (FREE with edge-tts)
    tts_result = await generate_tts(text, voice_id)
    results["steps"].append({"step": "tts", "result": tts_result})
    results["total_cost"] += tts_result.get("cost", 0)

    if not tts_result.get("success"):
        results["success"] = False
        results["error"] = f"TTS failed: {tts_result.get('error')}"
        return results

    # Step 3: Generate photo
    if face_image_url:
        photo_result = await generate_photo_with_face(
            prompt=photo_prompt,
            face_image_url=face_image_url,
            reference_images=reference_images,
            negative_prompt=neg_prompt,
        )
        img_data = photo_result.get("image", {})
    else:
        photo_result = await generate_photo(
            prompt=photo_prompt,
            negative_prompt=neg_prompt,
            model_key=photo_model_key,
        )
        images = photo_result.get("images", [])
        img_data = images[0] if images else {}

    results["steps"].append({"step": "photo", "result": photo_result})
    results["total_cost"] += photo_result.get("cost_estimate", 0)

    if not photo_result.get("success"):
        results["success"] = False
        results["error"] = f"Photo failed: {photo_result.get('error')}"
        return results

    image_url = img_data.get("url", "") if isinstance(img_data, dict) else ""
    if not image_url:
        results["success"] = False
        results["error"] = "No image URL available for lipsync"
        return results

    # Step 4: Upload audio to fal.ai storage
    audio_path = tts_result.get("file_path", "")
    audio_url = await _upload_file_to_fal(audio_path)
    if not audio_url:
        results["success"] = False
        results["error"] = "Failed to upload audio to fal.ai storage"
        return results

    # Step 5: Generate lipsync video
    lipsync_result = await generate_lipsync_video(
        image_url=image_url,
        audio_url=audio_url,
        model_key=lipsync_model_key,
    )
    results["steps"].append({"step": "lipsync", "result": lipsync_result})
    results["total_cost"] += lipsync_result.get("cost_estimate", 0)

    if not lipsync_result.get("success", False):
        results["success"] = False
        results["error"] = f"Lipsync failed: {lipsync_result.get('error')}"
        return results

    # Step 6 (optional): Generate I2V movement
    if generate_i2v:
        i2v_result = await generate_video_from_image(
            image_url=image_url,
            prompt=f"{content_type} scene, natural movement, realistic",
        )
        results["steps"].append({"step": "i2v", "result": i2v_result})
        results["total_cost"] += i2v_result.get("cost_estimate", 0)

    results["success"] = True
    return results


async def _upload_file_to_fal(file_path: str) -> Optional[str]:
    """Upload a local file to fal.ai storage and return the URL.

    Uses fal_client.upload_file first, falls back to REST API.
    """
    key = _get_fal_key()
    if not key:
        return None

    os.environ["FAL_KEY"] = key

    # Try fal_client SDK upload first
    try:
        url = await asyncio.to_thread(fal_client.upload_file, file_path)
        if url:
            return url
    except Exception:
        pass

    # Fallback: REST API upload
    headers = {"Authorization": f"Key {key}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(
                "https://rest.alpha.fal.ai/storage/upload/initiate",
                json={"content_type": "audio/mpeg", "file_name": os.path.basename(file_path)},
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                upload_url = data.get("upload_url", "")
                file_url = data.get("file_url", "")
                if upload_url:
                    with open(file_path, "rb") as f:
                        file_bytes = f.read()
                    put_resp = await client.put(
                        upload_url,
                        content=file_bytes,
                        headers={"Content-Type": "audio/mpeg"},
                    )
                    if put_resp.status_code in (200, 201):
                        return file_url
        except Exception:
            pass

    return None


# ─── Demo/Preview generation (no API key needed) ───────────────────
async def generate_demo_tts(text: str, voice_id: str = "en_female_cheerful") -> dict:
    """Generate TTS demo - always works, no API key needed."""
    return await generate_tts(text, voice_id)


def get_pipeline_status() -> dict:
    """Get current pipeline configuration and status."""
    has_fal_key = bool(_get_fal_key())

    return {
        "fal_api_configured": has_fal_key,
        "tts_available": True,
        "photo_generation_available": has_fal_key,
        "lipsync_available": has_fal_key,
        "video_generation_available": has_fal_key,
        "available_voices": list(EDGE_TTS_VOICES.keys()),
        "available_photo_models": [
            {
                "key": k,
                "name": v["name"],
                "quality": v["quality"],
                "cost": f"${v.get('cost_per_image', '?')}/image",
                "best_for": v.get("best_for", []),
            }
            for k, v in IMAGE_MODELS.items()
        ],
        "available_lipsync_models": [
            {
                "key": k,
                "name": v["name"],
                "quality": v["quality"],
                "cost": f"${v.get('cost_per_second', v.get('cost_flat_under_40s', '?'))}/{'sec' if 'cost_per_second' in v else 'flat'}",
                "best_for": v.get("best_for", []),
            }
            for k, v in LIPSYNC_MODELS.items()
        ],
        "available_video_models": [
            {
                "key": k,
                "name": v["name"],
                "quality": v["quality"],
                "cost": f"${v.get('cost_base_5s', v.get('cost_per_video_720p', '?'))}/{'5s' if 'cost_base_5s' in v else 'video'}",
                "best_for": v.get("best_for", []),
            }
            for k, v in VIDEO_MODELS.items()
        ],
        "content_types": [
            "gaming_reaction", "gaming_chill", "instagram_lifestyle",
            "instagram_glam", "selfie_mirror", "intimate_cozy",
            "intimate_lingerie", "portrait", "full_body", "bikini_beach",
        ],
        "budget_estimate": {
            "budget_9_dollars": {
                "photos_realism": f"~{int(9/0.021)} images (FLUX 2 Realism @ $0.021)",
                "photos_dev": f"~{int(9/0.025)} images (FLUX Dev @ $0.025)",
                "voice_clips": "unlimited (edge-tts free)",
                "lipsync_omnihuman_3s": f"~{int(9/(0.16*3))} clips (OmniHuman @ $0.16/s)",
                "lipsync_kling_5s": f"~{int(9/0.07)} clips (Kling LipSync @ $0.07/5s)",
                "videos_kling_5s": f"~{int(9/0.28)} clips (Kling 2.1 I2V @ $0.28/5s)",
            }
        },
        "storage_dir": str(GENERATED_DIR),
        "generated_files": {
            d: len(list((GENERATED_DIR / d).glob("*"))) if (GENERATED_DIR / d).exists() else 0
            for d in ("photos", "audio", "video", "profiles")
        },
    }


# ─── Character presets for quick generation ─────────────────────────
CHARACTER_PHOTO_PROMPTS = {
    "gaming_selfie": (
        "photorealistic portrait of a beautiful 22 year old woman, "
        "wearing gaming headset, RGB gaming setup background, "
        "looking at camera with confident smile, webcam angle, "
        "close-up face, perfect skin, studio lighting, "
        "masterpiece, best quality, ultra detailed, 8k"
    ),
    "instagram_casual": (
        "photorealistic full body photo of a beautiful 22 year old woman, "
        "trendy casual outfit, aesthetic cafe background, "
        "natural lighting, instagram style, perfect skin, "
        "masterpiece, best quality, ultra detailed, 8k"
    ),
    "instagram_glam": (
        "photorealistic portrait of a beautiful 22 year old woman, "
        "glamorous makeup, evening dress, city lights background, "
        "professional photography, soft bokeh, perfect skin, "
        "masterpiece, best quality, ultra detailed, 8k"
    ),
    "reaction_excited": (
        "photorealistic close-up portrait of a beautiful 22 year old woman, "
        "excited surprised expression, mouth open, wide eyes, "
        "gaming room background with monitors, ring light, "
        "webcam selfie angle, perfect skin, "
        "masterpiece, best quality, ultra detailed, 8k"
    ),
    "private_intimate": (
        "photorealistic portrait of a beautiful 22 year old woman, "
        "casual home outfit, cozy bedroom setting, "
        "soft warm lighting, intimate atmosphere, "
        "looking at camera with flirty smile, perfect skin, "
        "masterpiece, best quality, ultra detailed, 8k"
    ),
}

REACTION_SCRIPTS = {
    "clutch_hype": "Oh my God! Did you just see that?! A one-v-five clutch! That was absolutely insane! This is why you need to watch live!",
    "ace_reaction": "FIVE KILLS! An ace! He just wiped the entire team! I'm literally shaking right now!",
    "fail_laugh": "Wait... what just happened?! Oh no no no! I can't believe he actually did that! I'm dying!",
    "headshot_wow": "Head, head, HEAD! The aim is absolutely unreal! How does he do that every single time?!",
    "promo_follow": "Hey! If you're not following yet, you're missing out on plays like this every single day. Hit that follow button!",
}
