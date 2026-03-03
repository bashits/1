"""Real Photo Sourcer — Fetches real model photos from Pexels for LoRA training.

Instead of training LoRA on AI-generated photos (which look artificial),
this service finds real stock photos of models matching the girl's appearance.
Training LoRA on real photos = output looks like a real living person.

Flow:
1. Build smart search queries from appearance traits (ethnicity, hair, etc.)
2. Search Pexels API for matching model photos
3. Group photos by photographer (same photographer = likely same model)
4. Select best group of 10-20 photos of one model
5. Return photo URLs ready for LoRA training

Pexels API is free (200 req/month) — https://www.pexels.com/api/
"""

import logging
import os
import random
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


def _get_pexels_key() -> str:
    return os.environ.get("PEXELS_API_KEY", "")


# ─── Search Query Building ──────────────────────────────────────────

# Maps our appearance traits to Pexels-friendly search terms
ETHNICITY_SEARCH_MAP = {
    "european": "european woman",
    "slavic": "slavic woman",
    "scandinavian": "scandinavian blonde woman",
    "mediterranean": "mediterranean woman",
    "latina": "latina woman",
    "east_asian": "asian woman",
    "southeast_asian": "asian woman",
    "south_asian": "indian woman",
    "middle_eastern": "middle eastern woman",
    "african": "african woman",
    "mixed_asian_european": "eurasian woman",
    "mixed_african_european": "mixed race woman",
    "brazilian": "brazilian woman",
    "korean": "korean woman",
    "japanese": "japanese woman",
    "persian": "persian woman",
    "turkish": "turkish woman",
}

HAIR_COLOR_SEARCH_MAP = {
    "platinum blonde": "platinum blonde",
    "golden blonde": "blonde",
    "honey blonde": "blonde",
    "strawberry blonde": "strawberry blonde",
    "light brown": "light brown hair",
    "dark brown": "brunette",
    "chestnut": "brunette",
    "auburn": "auburn hair",
    "copper red": "red hair",
    "fiery red": "redhead",
    "jet black": "black hair",
    "soft black": "black hair",
    "ash blonde": "ash blonde",
    "caramel": "caramel hair",
    "chocolate": "brunette",
    "silver": "silver hair",
    "rose gold": "rose gold hair",
    "dark blonde": "dark blonde",
    "white blonde": "platinum blonde",
    "burgundy": "burgundy hair",
}


def build_search_queries(appearance: dict) -> list[str]:
    """Build multiple search queries from appearance traits for Pexels.

    Returns 3-5 different queries to maximize chances of finding matching photos.
    """
    ethnicity = appearance.get("ethnicity", "european")
    hair_color = appearance.get("hair_color", "dark blonde")
    hair_style = appearance.get("hair_style", "long wavy")
    age = appearance.get("age", 23)

    # Get search-friendly terms
    ethnicity_term = ETHNICITY_SEARCH_MAP.get(ethnicity, "woman")
    hair_term = HAIR_COLOR_SEARCH_MAP.get(hair_color, hair_color)

    # Determine age bracket for search
    if age < 22:
        age_term = "young"
    elif age < 28:
        age_term = ""
    else:
        age_term = "woman"

    queries = []

    # Query 1: Most specific — ethnicity + hair + portrait
    q1 = f"{ethnicity_term} {hair_term} portrait model"
    queries.append(q1)

    # Query 2: Hair focus — hair color + style
    hair_length = "long" if "long" in hair_style.lower() else "short" if "short" in hair_style.lower() else ""
    q2 = f"{hair_term} {hair_length} hair woman portrait"
    queries.append(q2.strip())

    # Query 3: Broad ethnicity + model
    q3 = f"{age_term} {ethnicity_term} model photo".strip()
    queries.append(q3)

    # Query 4: Studio portrait style
    q4 = f"{ethnicity_term} {hair_term} studio portrait"
    queries.append(q4)

    # Query 5: Casual/lifestyle (different angles)
    q5 = f"{ethnicity_term} {hair_term} lifestyle photo"
    queries.append(q5)

    return queries


# ─── Pexels API Integration ─────────────────────────────────────────

async def search_pexels(
    query: str,
    per_page: int = 40,
    page: int = 1,
    orientation: str = "portrait",
) -> list[dict]:
    """Search Pexels API for photos matching query.

    Returns list of {url, photographer, photographer_id, width, height, id}.
    """
    key = _get_pexels_key()
    if not key:
        logger.warning("PEXELS_API_KEY not set, skipping Pexels search")
        return []

    headers = {"Authorization": key}
    params = {
        "query": query,
        "per_page": per_page,
        "page": page,
        "orientation": orientation,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                "https://api.pexels.com/v1/search",
                headers=headers,
                params=params,
            )
            if resp.status_code != 200:
                logger.warning(f"Pexels API error: {resp.status_code} — {resp.text[:200]}")
                return []

            data = resp.json()
            photos = []
            for photo in data.get("photos", []):
                # Get the large2x or original size for LoRA training quality
                src = photo.get("src", {})
                photo_url = src.get("large2x") or src.get("original") or src.get("large", "")
                if not photo_url:
                    continue

                photos.append({
                    "id": photo.get("id"),
                    "url": photo_url,
                    "photographer": photo.get("photographer", ""),
                    "photographer_id": photo.get("photographer_id", 0),
                    "width": photo.get("width", 0),
                    "height": photo.get("height", 0),
                    "avg_color": photo.get("avg_color", ""),
                    "alt": photo.get("alt", ""),
                })

            return photos
        except Exception as e:
            logger.error(f"Pexels search failed: {e}")
            return []


async def search_pexels_multi(
    queries: list[str],
    photos_per_query: int = 30,
) -> list[dict]:
    """Search Pexels with multiple queries and merge results.

    Deduplicates by photo ID.
    """
    all_photos = {}

    for query in queries:
        results = await search_pexels(query, per_page=photos_per_query)
        for photo in results:
            pid = photo["id"]
            if pid not in all_photos:
                all_photos[pid] = photo

    return list(all_photos.values())


# ─── Smart Photo Selection (Single-Typazh Filter) ───────────────────


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color (#RRGGBB) to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) != 6:
        return (128, 128, 128)
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))


def _color_distance(c1: tuple[int, int, int], c2: tuple[int, int, int]) -> float:
    """Euclidean distance between two RGB colors (0-441 range)."""
    return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2) ** 0.5


def _compute_skin_tone_bucket(avg_color: str) -> str:
    """Classify avg_color into a skin-tone bucket for consistency filtering.

    Groups photos by approximate skin-tone warmth to avoid mixing
    very different models (e.g., pale redhead vs dark brunette).
    """
    r, g, b = _hex_to_rgb(avg_color)
    brightness = (r + g + b) / 3.0
    warmth = r - b  # positive = warm skin tones

    if brightness > 180:
        return "light"
    elif brightness > 130:
        if warmth > 30:
            return "warm_medium"
        return "cool_medium"
    elif brightness > 80:
        if warmth > 20:
            return "warm_dark"
        return "cool_dark"
    else:
        return "very_dark"


def group_by_photographer(photos: list[dict]) -> dict[int, list[dict]]:
    """Group photos by photographer — same photographer often = same model."""
    groups: dict[int, list[dict]] = {}
    for photo in photos:
        pid = photo.get("photographer_id", 0)
        if pid not in groups:
            groups[pid] = []
        groups[pid].append(photo)
    return groups


def _score_photo_quality(photo: dict) -> float:
    """Score a single photo's quality for LoRA training (0-1).

    Higher score = better for training.
    """
    score = 0.5  # baseline

    w = photo.get("width", 0)
    h = photo.get("height", 0)

    # Resolution: prefer 1000+ px on shortest side
    min_dim = min(w, h) if w and h else 0
    if min_dim >= 1200:
        score += 0.2
    elif min_dim >= 800:
        score += 0.1
    elif min_dim < 400:
        score -= 0.3  # too small for LoRA

    # Aspect ratio: prefer portrait (3:4, 2:3) or square — NOT ultra-wide
    if w and h:
        ratio = w / h
        if 0.6 <= ratio <= 0.85:  # portrait orientation
            score += 0.15
        elif 0.85 < ratio <= 1.15:  # square-ish
            score += 0.05
        elif ratio > 1.8 or ratio < 0.4:  # extreme aspect ratio
            score -= 0.2

    # Alt text hints (Pexels provides alt descriptions)
    alt = (photo.get("alt") or "").lower()
    positive_keywords = ["woman", "girl", "portrait", "face", "model", "beauty"]
    negative_keywords = ["group", "crowd", "couple", "man", "boy", "child", "kid", "baby", "animal", "dog", "cat"]
    for kw in positive_keywords:
        if kw in alt:
            score += 0.05
    for kw in negative_keywords:
        if kw in alt:
            score -= 0.3  # strong penalty for non-solo-female photos

    return max(0.0, min(1.0, score))


def _score_group_consistency(photos: list[dict]) -> float:
    """Score how consistent a group of photos is (likely same model).

    Uses color palette similarity + resolution consistency.
    Higher = more likely same person.
    """
    if len(photos) < 2:
        return 0.5

    # Color consistency: photos of same model tend to have similar avg colors
    colors = []
    for p in photos:
        avg = p.get("avg_color", "")
        if avg:
            colors.append(_hex_to_rgb(avg))

    color_consistency = 1.0
    if len(colors) >= 2:
        # Compute avg pairwise distance
        distances = []
        for i in range(min(len(colors), 10)):
            for j in range(i + 1, min(len(colors), 10)):
                distances.append(_color_distance(colors[i], colors[j]))
        avg_dist = sum(distances) / len(distances) if distances else 0
        # avg_dist 0-50 = very consistent, 50-100 = ok, 100+ = mixed models
        if avg_dist < 40:
            color_consistency = 1.0
        elif avg_dist < 80:
            color_consistency = 0.7
        elif avg_dist < 120:
            color_consistency = 0.4
        else:
            color_consistency = 0.2

    # Skin tone bucket consistency
    buckets = [_compute_skin_tone_bucket(p.get("avg_color", "")) for p in photos if p.get("avg_color")]
    if buckets:
        most_common = max(set(buckets), key=buckets.count)
        bucket_consistency = buckets.count(most_common) / len(buckets)
    else:
        bucket_consistency = 0.5

    # Resolution consistency
    widths = [p.get("width", 0) for p in photos if p.get("width")]
    if widths:
        avg_w = sum(widths) / len(widths)
        res_variance = sum((w - avg_w) ** 2 for w in widths) / len(widths)
        res_consistency = 1.0 if res_variance < 100000 else 0.5
    else:
        res_consistency = 0.5

    return 0.4 * color_consistency + 0.4 * bucket_consistency + 0.2 * res_consistency


def select_best_photo_set(
    photos: list[dict],
    target_count: int = 15,
    min_count: int = 10,
    appearance: Optional[dict] = None,
) -> list[dict]:
    """Select the best set of photos for LoRA training with SINGLE-TYPAZH filter.

    Smart strategy:
    1. Filter out low-quality / non-portrait photos
    2. Group by photographer (same photographer = likely same model)
    3. Score each group for visual consistency (color palette, skin tone)
    4. Pick the most consistent group with enough photos
    5. If no single group is big enough, combine 2 most similar groups
    6. Final filter: remove outliers by skin tone bucket

    This ensures all training photos show the SAME type of person.
    """
    if not photos:
        return []

    # Step 1: Filter out bad quality photos
    scored = []
    for photo in photos:
        quality = _score_photo_quality(photo)
        if quality >= 0.3:  # reject obviously bad ones
            scored.append((photo, quality))

    if not scored:
        logger.warning("All photos filtered out by quality check")
        return photos[:target_count]  # fallback: return raw

    # Sort by quality score
    scored.sort(key=lambda x: x[1], reverse=True)
    quality_photos = [p for p, _ in scored]

    logger.info(f"Quality filter: {len(photos)} → {len(quality_photos)} photos")

    # Step 2: Group by photographer
    groups = group_by_photographer(quality_photos)
    sorted_groups = sorted(groups.items(), key=lambda x: len(x[1]), reverse=True)

    # Step 3: Score each group for consistency
    group_scores = []
    for pid, group_photos in sorted_groups:
        consistency = _score_group_consistency(group_photos)
        # Bonus for having more photos (bigger group = more likely professional set)
        size_bonus = min(0.3, len(group_photos) * 0.03)
        total_score = consistency + size_bonus
        group_scores.append((pid, group_photos, total_score, consistency))

    group_scores.sort(key=lambda x: x[2], reverse=True)

    # Step 4: Find best single group
    for pid, group_photos, score, consistency in group_scores:
        if len(group_photos) >= min_count and consistency >= 0.5:
            logger.info(
                f"Single-typazh match: photographer '{group_photos[0]['photographer']}' "
                f"({len(group_photos)} photos, consistency={consistency:.2f})"
            )
            selected = group_photos[:target_count]
            return _filter_outliers_by_skin_tone(selected)

    # Step 5: Combine top 2-3 most similar groups
    selected = []
    primary_bucket = None
    for pid, group_photos, score, consistency in group_scores:
        if not selected:
            # First group sets the typazh
            selected.extend(group_photos)
            buckets = [_compute_skin_tone_bucket(p.get("avg_color", "")) for p in group_photos if p.get("avg_color")]
            if buckets:
                primary_bucket = max(set(buckets), key=buckets.count)
            continue

        if len(selected) >= target_count:
            break

        # Only add groups that match the primary skin tone
        if primary_bucket:
            group_buckets = [_compute_skin_tone_bucket(p.get("avg_color", "")) for p in group_photos if p.get("avg_color")]
            if group_buckets:
                group_primary = max(set(group_buckets), key=group_buckets.count)
                if group_primary != primary_bucket:
                    logger.info(f"Skipping photographer (skin tone mismatch: {group_primary} vs {primary_bucket})")
                    continue

        remaining = target_count - len(selected)
        selected.extend(group_photos[:remaining])

    # Step 6: If still not enough, add remaining quality photos that match typazh
    if len(selected) < min_count:
        seen_ids = {p["id"] for p in selected}
        for photo in quality_photos:
            if photo["id"] not in seen_ids:
                if primary_bucket:
                    bucket = _compute_skin_tone_bucket(photo.get("avg_color", ""))
                    if bucket != primary_bucket:
                        continue
                selected.append(photo)
                seen_ids.add(photo["id"])
            if len(selected) >= target_count:
                break

    result = selected[:target_count]
    return _filter_outliers_by_skin_tone(result)


def _filter_outliers_by_skin_tone(photos: list[dict]) -> list[dict]:
    """Remove photos whose skin tone bucket doesn't match the majority.

    This is the final consistency check to ensure single-typazh.
    """
    if len(photos) < 5:
        return photos

    buckets = [(p, _compute_skin_tone_bucket(p.get("avg_color", ""))) for p in photos]
    bucket_counts: dict[str, int] = {}
    for _, b in buckets:
        bucket_counts[b] = bucket_counts.get(b, 0) + 1

    if not bucket_counts:
        return photos

    primary = max(bucket_counts, key=bucket_counts.get)  # type: ignore[arg-type]
    filtered = [p for p, b in buckets if b == primary]

    # Only filter if we still have enough photos
    if len(filtered) >= 5:
        if len(filtered) < len(photos):
            logger.info(
                f"Skin-tone filter removed {len(photos) - len(filtered)} outlier photos "
                f"(kept {len(filtered)} with tone '{primary}')"
            )
        return filtered

    return photos  # not enough after filter, keep all


def build_captions_for_training(
    photos: list[dict],
    trigger_word: str,
    appearance: dict,
) -> list[dict]:
    """Add LoRA training captions to photos.

    Each photo gets a caption with the trigger word + detailed appearance.
    Captions are varied with different angles/lighting/poses to help LoRA
    generalize across scenes while locking identity.
    """
    ethnicity = appearance.get("ethnicity", "european")
    hair_color = appearance.get("hair_color", "dark blonde")
    hair_style = appearance.get("hair_style", "long wavy")
    eye_color = appearance.get("eye_color", "green")
    skin_tone = appearance.get("skin_tone", "fair")
    body_type = appearance.get("body_type", "slim fit")
    age = appearance.get("age", 23)

    base_desc = (
        f"{age} year old {ethnicity} woman, {hair_color} {hair_style} hair, "
        f"{eye_color} eyes, {skin_tone} skin, {body_type} body"
    )

    # Diverse captions that teach LoRA identity across many conditions
    caption_templates = [
        # Portraits (identity lock)
        f"{trigger_word}, {base_desc}, professional portrait, soft studio lighting, RAW photo",
        f"{trigger_word}, {base_desc}, close-up face, natural window light, shallow DOF, RAW photo",
        f"{trigger_word}, {base_desc}, three-quarter angle portrait, slight smile, RAW photo",
        f"{trigger_word}, {base_desc}, headshot, neutral expression, clean background, RAW photo",
        f"{trigger_word}, {base_desc}, beauty portrait, dewy skin, soft focus background, RAW photo",
        # Different lighting conditions
        f"{trigger_word}, {base_desc}, golden hour outdoor portrait, warm light, bokeh, RAW photo",
        f"{trigger_word}, {base_desc}, overcast natural light, muted tones, editorial style, RAW photo",
        f"{trigger_word}, {base_desc}, dramatic side lighting, moody portrait, RAW photo",
        f"{trigger_word}, {base_desc}, bright and airy, high-key lighting, fresh look, RAW photo",
        # Different poses/angles
        f"{trigger_word}, {base_desc}, side profile, elegant neck line, rim light, RAW photo",
        f"{trigger_word}, {base_desc}, looking over shoulder, confident expression, RAW photo",
        f"{trigger_word}, {base_desc}, full body standing pose, fashion editorial, RAW photo",
        f"{trigger_word}, {base_desc}, sitting pose, relaxed posture, lifestyle photo, RAW photo",
        # Different settings
        f"{trigger_word}, {base_desc}, casual indoor photo, natural daylight from window, RAW photo",
        f"{trigger_word}, {base_desc}, outdoor in park, natural sunlight, green background, RAW photo",
        f"{trigger_word}, {base_desc}, urban street portrait, city background, natural light, RAW photo",
        f"{trigger_word}, {base_desc}, luxury setting, professional photography, RAW photo",
        # Expressions variety
        f"{trigger_word}, {base_desc}, candid laugh, authentic expression, natural moment, RAW photo",
        f"{trigger_word}, {base_desc}, serious expression, model pose, editorial, RAW photo",
        f"{trigger_word}, {base_desc}, warm genuine smile, approachable look, RAW photo",
    ]

    result = []
    for i, photo in enumerate(photos):
        caption = caption_templates[i % len(caption_templates)]
        result.append({
            "url": photo["url"],
            "caption": caption,
            "type": f"real_photo_{i}",
            "source": "pexels",
            "photographer": photo.get("photographer", ""),
            "source_id": photo.get("id", 0),
        })

    return result


# ─── Main Entry Point ────────────────────────────────────────────────

async def source_real_model_photos(
    appearance: dict,
    trigger_word: str,
    target_count: int = 15,
) -> dict:
    """Main function: Find real model photos for LoRA training.

    1. Builds smart search queries from appearance
    2. Searches Pexels for matching photos
    3. Selects best 10-20 photos (preferring same model)
    4. Adds training captions
    5. Returns photos ready for LoRA training

    Returns: {
        success: bool,
        photos: list[{url, caption, type, source}],
        source: "pexels",
        photographer: str,
        message: str,
    }
    """
    key = _get_pexels_key()
    if not key:
        return {
            "success": False,
            "photos": [],
            "source": "none",
            "error": "PEXELS_API_KEY not configured. Get free key at pexels.com/api",
        }

    # Step 1: Build search queries
    queries = build_search_queries(appearance)
    logger.info(f"Searching Pexels with {len(queries)} queries: {queries}")

    # Step 2: Search Pexels
    all_photos = await search_pexels_multi(queries, photos_per_query=30)
    logger.info(f"Found {len(all_photos)} total photos from Pexels")

    if not all_photos:
        return {
            "success": False,
            "photos": [],
            "source": "pexels",
            "error": "No matching photos found on Pexels",
        }

    # Step 3: Select best photo set
    selected = select_best_photo_set(all_photos, target_count=target_count)
    logger.info(f"Selected {len(selected)} photos for LoRA training")

    if len(selected) < 5:
        return {
            "success": False,
            "photos": [],
            "source": "pexels",
            "error": f"Only found {len(selected)} suitable photos, need at least 5",
        }

    # Step 4: Add training captions
    captioned = build_captions_for_training(selected, trigger_word, appearance)

    # Determine primary photographer
    photographers = {}
    for p in selected:
        name = p.get("photographer", "Unknown")
        photographers[name] = photographers.get(name, 0) + 1
    primary_photographer = max(photographers, key=photographers.get) if photographers else "Various"

    return {
        "success": True,
        "photos": captioned,
        "photos_count": len(captioned),
        "source": "pexels",
        "photographer": primary_photographer,
        "photographer_stats": photographers,
        "queries_used": queries,
        "message": f"Found {len(captioned)} real model photos (primary: {primary_photographer})",
    }


async def source_photos_with_fallback(
    appearance: dict,
    trigger_word: str,
    target_count: int = 15,
) -> dict:
    """Source real photos with AI-generated fallback.

    Priority:
    1. Real photos from Pexels (best for LoRA — real human features)
    2. AI-generated hyper-realistic photos (fallback if no Pexels key)

    The AI fallback generates photos with stock-photography-style prompts
    to maximize realism.
    """
    # Try real photos first
    result = await source_real_model_photos(appearance, trigger_word, target_count)
    if result.get("success"):
        return result

    # Fallback: Use AI-generated hyper-realistic photos
    logger.info("Falling back to AI-generated hyper-realistic training photos")
    from app.services.lora_service import generate_training_dataset

    ai_photos = await generate_training_dataset(
        appearance=appearance,
        trigger_word=trigger_word,
        num_photos=target_count,
    )

    if len(ai_photos) >= 5:
        return {
            "success": True,
            "photos": ai_photos,
            "photos_count": len(ai_photos),
            "source": "ai_generated",
            "photographer": "AI (FLUX Realism)",
            "message": f"Generated {len(ai_photos)} hyper-realistic training photos (Pexels unavailable)",
            "fallback_reason": result.get("error", "Pexels not available"),
        }

    return {
        "success": False,
        "photos": [],
        "source": "none",
        "error": f"Could not source enough photos. Pexels: {result.get('error')}. AI: only {len(ai_photos)} generated.",
    }
