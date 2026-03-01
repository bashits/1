"""LoRA Training & Inference Service — Face Identity Lock for AI Girls.

Flow:
1. Generate ~10-20 base photos of the girl (via FLUX Realism)
2. Pack photos into a zip archive
3. Upload zip to fal.ai storage
4. Train LoRA via fal-ai/flux-lora-fast-training (~$2, 5-15 min)
5. Store LoRA weights URL in DB
6. All subsequent photo generation uses fal-ai/flux-lora with the trained LoRA
   → face stays consistent across all scenes/poses/outfits

Pricing:
- Training: ~$2 per run (1000 steps)
- Inference: ~$0.05 per image (FLUX Dev with LoRA)
"""

import asyncio
import io
import json
import logging
import os
import zipfile
from datetime import datetime
from typing import Optional

import fal_client
import httpx

logger = logging.getLogger(__name__)


def _get_fal_key() -> str:
    return os.environ.get("FAL_KEY", "")


# ─── Training Configuration ──────────────────────────────────────────

LORA_TRAINING_CONFIG = {
    "model_id": "fal-ai/flux-lora-fast-training",
    "default_steps": 1200,  # 1200 steps for better identity lock (was 1000)
    "default_learning_rate": None,  # Let fal.ai choose optimal
    "create_masks": True,  # Face masks for better identity preservation
    "is_style": False,  # We're training a person, not a style
    "cost_per_training": 2.50,  # slightly higher with more steps
}

LORA_INFERENCE_CONFIG = {
    "model_id": "fal-ai/flux-lora",
    "cost_per_image": 0.05,
    "default_guidance_scale": 3.5,
    "default_num_inference_steps": 32,  # 32 steps for sharper details (was 28)
    "default_lora_scale": 0.95,  # 0.95 for naturalness (1.0 can over-fit)
}

# Content types for generating diverse training dataset
TRAINING_PHOTO_TYPES = [
    {
        "type": "portrait_front",
        "scene": "professional studio portrait, front-facing, neutral background, soft studio lighting",
        "count": 3,
    },
    {
        "type": "portrait_angle",
        "scene": "portrait from 3/4 angle, slight smile, natural window lighting, clean background",
        "count": 2,
    },
    {
        "type": "portrait_side",
        "scene": "side profile portrait, elegant pose, soft rim lighting, minimal background",
        "count": 2,
    },
    {
        "type": "casual_indoor",
        "scene": "casual indoor photo, relaxed pose, cozy room setting, natural daylight from window",
        "count": 2,
    },
    {
        "type": "outdoor_natural",
        "scene": "outdoor photo in park, natural sunlight, bokeh background, golden hour",
        "count": 2,
    },
    {
        "type": "closeup_face",
        "scene": "extreme close-up face shot, sharp focus on eyes, studio lighting, shallow DOF",
        "count": 2,
    },
    {
        "type": "full_body",
        "scene": "full body standing pose, clean urban background, professional photography, even lighting",
        "count": 2,
    },
]


def build_training_prompts(appearance: dict, trigger_word: str) -> list[dict]:
    """Build diverse prompts for generating LoRA training dataset.

    Each prompt creates a different angle/scene of the same girl so the
    LoRA learns the face from multiple perspectives.
    """
    ethnicity = appearance.get("ethnicity", "european")
    hair_color = appearance.get("hair_color", "dark blonde")
    hair_style = appearance.get("hair_style", "long wavy")
    eye_color = appearance.get("eye_color", "green")
    skin_tone = appearance.get("skin_tone", "fair")
    body_type = appearance.get("body_type", "slim")
    face_shape = appearance.get("face_shape", "oval")
    nose = appearance.get("nose", "small straight nose")
    lips = appearance.get("lips", "full natural lips")
    unique_feature = appearance.get("unique_feature", "")
    age = appearance.get("age", 23)

    identity_desc = (
        f"A {age} year old {ethnicity} woman, "
        f"{hair_color} {hair_style} hair, {eye_color} eyes, "
        f"{skin_tone} skin, {body_type} build, {face_shape} face, "
        f"{nose}, {lips}"
    )
    if unique_feature:
        identity_desc += f", {unique_feature}"

    realism = (
        "RAW photo, ultra realistic, natural skin texture with visible pores, "
        "subsurface scattering, individual hair strands, catchlight in eyes, "
        "shot on Canon EOS R5 85mm f/1.4, professional color grading"
    )

    prompts = []
    for photo_type in TRAINING_PHOTO_TYPES:
        for i in range(photo_type["count"]):
            prompt = f"{trigger_word}, {identity_desc}, {photo_type['scene']}, {realism}"
            caption = f"{trigger_word}, {identity_desc}, {photo_type['scene']}"
            prompts.append({
                "prompt": prompt,
                "caption": caption,
                "type": photo_type["type"],
                "index": i,
            })

    return prompts


async def generate_training_dataset(
    appearance: dict,
    trigger_word: str,
    num_photos: int = 15,
) -> list[dict]:
    """Generate diverse photos for LoRA training dataset.

    Returns list of {url, caption, type} dicts.
    """
    from app.services.content_generation import generate_photo, NEGATIVE_QUALITY

    prompts = build_training_prompts(appearance, trigger_word)
    # Limit to requested number
    prompts = prompts[:num_photos]

    results = []
    # Generate in batches of 3 to avoid overwhelming the API
    batch_size = 3
    for i in range(0, len(prompts), batch_size):
        batch = prompts[i:i + batch_size]
        tasks = []
        for p in batch:
            tasks.append(
                generate_photo(
                    prompt=p["prompt"],
                    negative_prompt=NEGATIVE_QUALITY,
                    width=1024,
                    height=1024,
                    num_images=1,
                    model_key="flux2_realism",
                )
            )

        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        for p, result in zip(batch, batch_results):
            if isinstance(result, Exception):
                logger.warning(f"Training photo generation failed: {result}")
                continue
            if result.get("success"):
                images = result.get("images", [])
                if images:
                    results.append({
                        "url": images[0]["url"],
                        "caption": p["caption"],
                        "type": p["type"],
                    })

        # Small delay between batches
        if i + batch_size < len(prompts):
            await asyncio.sleep(1)

    logger.info(f"Generated {len(results)}/{num_photos} training photos")
    return results


async def _upload_bytes_to_fal(data: bytes, filename: str, content_type: str) -> Optional[str]:
    """Upload raw bytes to fal.ai storage and return URL."""
    key = _get_fal_key()
    if not key:
        return None

    headers = {"Authorization": f"Key {key}"}
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            # Initiate upload
            resp = await client.post(
                "https://rest.alpha.fal.ai/storage/upload/initiate",
                json={"content_type": content_type, "file_name": filename},
                headers=headers,
            )
            if resp.status_code == 200:
                upload_data = resp.json()
                upload_url = upload_data.get("upload_url", "")
                file_url = upload_data.get("file_url", "")
                if upload_url:
                    put_resp = await client.put(
                        upload_url,
                        content=data,
                        headers={"Content-Type": content_type},
                    )
                    if put_resp.status_code in (200, 201):
                        return file_url
        except Exception as e:
            logger.error(f"fal.ai upload failed: {e}")

    return None


async def create_training_zip(photos: list[dict]) -> Optional[bytes]:
    """Create a zip archive from training photos with caption files.

    Each photo gets:
    - image file (downloaded from URL)
    - .txt caption file with trigger word + description
    """
    buf = io.BytesIO()

    async with httpx.AsyncClient(timeout=30.0) as client:
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for idx, photo in enumerate(photos):
                url = photo["url"]
                caption = photo["caption"]
                filename = f"photo_{idx:03d}"

                # Download image
                try:
                    resp = await client.get(url, timeout=30.0)
                    if resp.status_code == 200:
                        # Determine extension from content type
                        ct = resp.headers.get("content-type", "image/jpeg")
                        ext = "jpg" if "jpeg" in ct or "jpg" in ct else "png"
                        zf.writestr(f"{filename}.{ext}", resp.content)
                        # Write caption file
                        zf.writestr(f"{filename}.txt", caption)
                    else:
                        logger.warning(f"Failed to download photo {idx}: HTTP {resp.status_code}")
                except Exception as e:
                    logger.warning(f"Failed to download photo {idx}: {e}")

    data = buf.getvalue()
    if len(data) < 1000:  # Too small = probably empty
        return None
    return data


async def start_lora_training(
    profile_id: int,
    trigger_word: str,
    photos: list[dict],
    steps: int = 1000,
) -> dict:
    """Start LoRA training on fal.ai.

    1. Creates zip from photos + captions
    2. Uploads zip to fal.ai storage
    3. Submits training job
    4. Returns request info for polling

    Returns: {success, request_id, zip_url, ...}
    """
    key = _get_fal_key()
    if not key:
        return {"success": False, "error": "FAL_KEY not configured"}

    os.environ["FAL_KEY"] = key

    # Step 1: Create zip archive
    logger.info(f"Creating training zip for profile {profile_id} with {len(photos)} photos...")
    zip_data = await create_training_zip(photos)
    if not zip_data:
        return {"success": False, "error": "Failed to create training zip (no photos downloaded)"}

    # Step 2: Upload zip to fal.ai storage
    logger.info(f"Uploading training zip ({len(zip_data)} bytes)...")
    zip_url = await _upload_bytes_to_fal(
        zip_data, f"lora_training_{profile_id}.zip", "application/zip"
    )
    if not zip_url:
        return {"success": False, "error": "Failed to upload training zip to fal.ai"}

    # Step 3: Submit training job
    logger.info(f"Submitting LoRA training job: trigger_word={trigger_word}, steps={steps}")

    training_input = {
        "images_data_url": zip_url,
        "trigger_word": trigger_word,
        "steps": steps,
        "create_masks": True,
        "is_style": False,
        "is_input_format_already_preprocessed": False,
    }

    model_id = LORA_TRAINING_CONFIG["model_id"]

    try:
        # Use fal_client.submit for async training
        handler = await asyncio.to_thread(
            fal_client.submit,
            model_id,
            arguments=training_input,
        )
        request_id = handler.request_id

        return {
            "success": True,
            "request_id": request_id,
            "zip_url": zip_url,
            "trigger_word": trigger_word,
            "steps": steps,
            "photos_count": len(photos),
            "estimated_cost": LORA_TRAINING_CONFIG["cost_per_training"],
            "status": "training",
        }
    except Exception as e:
        logger.error(f"LoRA training submission failed: {e}")
        return {"success": False, "error": str(e)}


async def check_training_status(request_id: str) -> dict:
    """Check the status of a LoRA training job."""
    key = _get_fal_key()
    if not key:
        return {"status": "error", "error": "FAL_KEY not configured"}

    model_id = LORA_TRAINING_CONFIG["model_id"]
    headers = {"Authorization": f"Key {key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            status_url = f"https://queue.fal.run/{model_id}/requests/{request_id}/status"
            resp = await client.get(status_url, headers=headers)

            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status", "unknown")

                if status == "COMPLETED":
                    # Fetch the result
                    result_url = f"https://queue.fal.run/{model_id}/requests/{request_id}"
                    result_resp = await client.get(result_url, headers=headers)
                    if result_resp.status_code == 200:
                        result_data = result_resp.json()
                        return {
                            "status": "completed",
                            "lora_url": result_data.get("diffusers_lora_file", {}).get("url", ""),
                            "lora_weights_url": result_data.get("diffusers_lora_file", {}).get("url", ""),
                            "config_url": result_data.get("config_file", {}).get("url", ""),
                            "raw_result": result_data,
                        }
                elif status == "FAILED":
                    return {"status": "failed", "error": data.get("error", "Training failed")}
                elif status == "IN_PROGRESS":
                    logs = data.get("logs", [])
                    return {"status": "training", "logs": logs}
                elif status == "IN_QUEUE":
                    return {"status": "queued", "position": data.get("queue_position")}
                else:
                    return {"status": status.lower()}

            return {"status": "error", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}


async def wait_for_training(request_id: str, timeout_seconds: int = 900) -> dict:
    """Wait for LoRA training to complete (polling).

    Polls every 10 seconds. Default timeout: 15 minutes.
    """
    start = asyncio.get_event_loop().time()

    while True:
        elapsed = asyncio.get_event_loop().time() - start
        if elapsed > timeout_seconds:
            return {"status": "timeout", "error": f"Training timed out after {timeout_seconds}s"}

        result = await check_training_status(request_id)
        status = result.get("status", "")

        if status == "completed":
            return result
        elif status == "failed":
            return result
        elif status == "error":
            return result

        await asyncio.sleep(10)


async def generate_photo_with_lora(
    prompt: str,
    lora_url: str,
    lora_scale: float = 1.0,
    negative_prompt: str = "",
    width: int = 1024,
    height: int = 1024,
    num_images: int = 1,
    guidance_scale: float = 3.5,
    num_inference_steps: int = 28,
    seed: Optional[int] = None,
) -> dict:
    """Generate photo using FLUX Dev with trained LoRA for face consistency.

    The trigger word should be included in the prompt.
    """
    key = _get_fal_key()
    if not key:
        return {"success": False, "error": "FAL_KEY not configured"}

    os.environ["FAL_KEY"] = key

    model_id = LORA_INFERENCE_CONFIG["model_id"]

    input_data = {
        "prompt": prompt,
        "image_size": {"width": width, "height": height},
        "num_images": num_images,
        "guidance_scale": guidance_scale,
        "num_inference_steps": num_inference_steps,
        "enable_safety_checker": False,
        "loras": [
            {
                "path": lora_url,
                "scale": lora_scale,
            }
        ],
    }

    if seed is not None:
        input_data["seed"] = seed

    try:
        result = await asyncio.to_thread(
            fal_client.subscribe,
            model_id,
            arguments=input_data,
            with_logs=False,
        )

        images = result.get("images", [])
        cloud_files = []
        for img in images:
            img_url = img.get("url", "")
            if img_url:
                cloud_files.append({
                    "url": img_url,
                    "width": img.get("width", width),
                    "height": img.get("height", height),
                })

        cost = LORA_INFERENCE_CONFIG["cost_per_image"] * num_images
        return {
            "success": True,
            "images": cloud_files,
            "model": model_id,
            "model_name": "FLUX Dev + LoRA",
            "prompt": prompt,
            "cost_estimate": cost,
            "engine": "fal.ai",
            "lora_used": True,
        }
    except Exception as e:
        logger.error(f"LoRA inference failed: {e}")
        # Fallback to regular generation
        try:
            result = await asyncio.to_thread(
                fal_client.subscribe,
                model_id,
                arguments={k: v for k, v in input_data.items() if k != "loras"},
                with_logs=False,
            )
            images = result.get("images", [])
            cloud_files = []
            for img in images:
                img_url = img.get("url", "")
                if img_url:
                    cloud_files.append({
                        "url": img_url,
                        "width": img.get("width", width),
                        "height": img.get("height", height),
                    })
            return {
                "success": True,
                "images": cloud_files,
                "model": model_id,
                "model_name": "FLUX Dev (fallback, no LoRA)",
                "prompt": prompt,
                "cost_estimate": 0.025 * num_images,
                "engine": "fal.ai",
                "lora_used": False,
                "lora_fallback_reason": str(e),
            }
        except Exception as fallback_err:
            return {"success": False, "error": f"LoRA: {e} | Fallback: {fallback_err}"}


def build_lora_prompt(
    trigger_word: str,
    appearance: dict,
    content_type: str = "portrait",
    custom_scene: str = "",
) -> str:
    """Build a prompt for LoRA inference — professional influencer quality.

    Optimized for lanna.danger-level output:
    - Natural skin, real photography feel
    - Luxury lifestyle settings (pool, beach, wine, travel)
    - Professional lighting and composition
    - No AI artifacts, no over-processed look
    """
    ethnicity = appearance.get("ethnicity", "european")
    hair_color = appearance.get("hair_color", "dark blonde")
    hair_style = appearance.get("hair_style", "long wavy")
    eye_color = appearance.get("eye_color", "green")
    skin_tone = appearance.get("skin_tone", "fair")
    age = appearance.get("age", 23)
    body_type = appearance.get("body_type", "slim fit")

    identity = (
        f"{trigger_word}, {age} year old {ethnicity} woman, "
        f"{hair_color} {hair_style} hair, {eye_color} eyes, {skin_tone} skin, {body_type} body"
    )

    # Professional photography realism block — maximum quality, no AI look
    realism = (
        "RAW photo, shot on Sony A7IV 85mm f/1.4 GM, natural skin texture with visible pores "
        "and micro-imperfections, subsurface scattering on skin, individual hair strands visible, "
        "real catchlight reflections in eyes, shallow depth of field with natural bokeh, "
        "professional color grading with lifted blacks, subtle film grain, "
        "no airbrushing, no plastic skin, no beauty filter, "
        "photojournalistic quality, editorial magazine photography, "
        "ultra detailed 8K UHD, natural ambient occlusion, micro-contrast"
    )

    scenes = {
        # === PORTRAITS ===
        "portrait": (
            f"{identity}, close-up portrait, soft directional window light, "
            f"shallow depth of field, slight natural smile, dewy skin, {realism}"
        ),
        # === GAMING ===
        "gaming_reaction": (
            f"{identity}, wearing gaming headset, RGB gaming setup background, "
            f"excited expression looking at camera, webcam angle, screen glow on face, {realism}"
        ),
        "gaming_chill": (
            f"{identity}, oversized gaming hoodie, relaxed pose in gaming chair, "
            f"cozy ambient RGB lighting, gaming room, {realism}"
        ),
        # === LUXURY LIFESTYLE (lanna.danger level) ===
        "instagram_lifestyle": (
            f"{identity}, luxury lifestyle photo, designer outfit, "
            f"aesthetic rooftop bar at sunset, golden hour light, "
            f"champagne glass in hand, confident pose, influencer photography, {realism}"
        ),
        "instagram_glam": (
            f"{identity}, glamorous evening look, red lips, "
            f"little black dress, luxury restaurant background, "
            f"warm candlelight, professional event photography, {realism}"
        ),
        "pool_luxury": (
            f"{identity}, bikini, luxury infinity pool, tropical resort, "
            f"bright sunlight, water reflections on skin, relaxed pose, "
            f"vacation photography, turquoise water, palm trees background, {realism}"
        ),
        "beach_sunset": (
            f"{identity}, bikini on sandy beach, golden sunset light, "
            f"ocean waves background, wind in hair, relaxed natural pose, "
            f"tropical paradise, travel photography, {realism}"
        ),
        "wine_evening": (
            f"{identity}, elegant dress, glass of red wine, "
            f"luxury terrace with city view at night, warm string lights, "
            f"intimate atmosphere, soft bokeh background, {realism}"
        ),
        "morning_coffee": (
            f"{identity}, casual chic outfit, holding coffee cup, "
            f"bright modern cafe, large windows with natural light, "
            f"relaxed morning vibe, candid moment, {realism}"
        ),
        "travel_exotic": (
            f"{identity}, summer dress, exotic travel destination, "
            f"ancient architecture or tropical garden background, "
            f"golden hour, travel influencer style, {realism}"
        ),
        "fitness_gym": (
            f"{identity}, sports bra and leggings, gym setting, "
            f"athletic pose, toned body, professional fitness photography, "
            f"dramatic side lighting, {realism}"
        ),
        # === CLASSIC ===
        "selfie": (
            f"{identity}, selfie angle, natural smile, casual trendy outfit, "
            f"soft natural lighting, slightly below eye level, "
            f"authentic iPhone selfie feel, {realism}"
        ),
        "intimate_cozy": (
            f"{identity}, silk pajamas, luxury bedroom, soft morning light, "
            f"white bed sheets, relaxed intimate pose, "
            f"warm tones, boudoir style, {realism}"
        ),
        "full_body": (
            f"{identity}, full body shot, confident standing pose, "
            f"minimalist studio background, fashion editorial lighting, "
            f"high-end fashion photography, {realism}"
        ),
        "outdoor": (
            f"{identity}, sundress, golden hour sunlight in park, "
            f"bokeh background, natural environment, wind in hair, "
            f"lifestyle photography, {realism}"
        ),
    }

    if custom_scene:
        return f"{identity}, {custom_scene}, {realism}"

    return scenes.get(content_type, scenes["portrait"])
