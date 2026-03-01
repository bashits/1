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


# ─── Smart Photo Selection ──────────────────────────────────────────

def group_by_photographer(photos: list[dict]) -> dict[int, list[dict]]:
    """Group photos by photographer — same photographer often = same model."""
    groups: dict[int, list[dict]] = {}
    for photo in photos:
        pid = photo.get("photographer_id", 0)
        if pid not in groups:
            groups[pid] = []
        groups[pid].append(photo)
    return groups


def select_best_photo_set(
    photos: list[dict],
    target_count: int = 15,
    min_count: int = 10,
) -> list[dict]:
    """Select the best set of photos for LoRA training.

    Strategy:
    1. Group by photographer (same model likely)
    2. If a photographer has 10+ photos → use those (best case: same model)
    3. If not, pick top photos from largest groups
    4. Ensure diversity: mix portrait/landscape orientations

    Returns list of photo dicts with URL and caption.
    """
    if not photos:
        return []

    groups = group_by_photographer(photos)

    # Sort groups by size (largest first)
    sorted_groups = sorted(groups.items(), key=lambda x: len(x[1]), reverse=True)

    # Strategy 1: Find a photographer with enough photos (likely same model)
    for photographer_id, group_photos in sorted_groups:
        if len(group_photos) >= min_count:
            logger.info(
                f"Found photographer {group_photos[0]['photographer']} with "
                f"{len(group_photos)} photos (likely same model)"
            )
            # Take up to target_count
            selected = group_photos[:target_count]
            return selected

    # Strategy 2: Combine top photographers' photos
    # Pick from largest groups first
    selected = []
    for photographer_id, group_photos in sorted_groups:
        remaining = target_count - len(selected)
        if remaining <= 0:
            break
        # Take proportionally from each group
        take = min(len(group_photos), max(3, remaining))
        selected.extend(group_photos[:take])

    # Strategy 3: If still not enough, just take all we have
    if len(selected) < min_count:
        # Take all unique photos
        seen_ids = {p["id"] for p in selected}
        for photo in photos:
            if photo["id"] not in seen_ids:
                selected.append(photo)
                seen_ids.add(photo["id"])
            if len(selected) >= target_count:
                break

    return selected[:target_count]


def build_captions_for_training(
    photos: list[dict],
    trigger_word: str,
    appearance: dict,
) -> list[dict]:
    """Add LoRA training captions to photos.

    Each photo gets a caption with the trigger word + appearance description.
    Captions are varied to help LoRA generalize.
    """
    ethnicity = appearance.get("ethnicity", "european")
    hair_color = appearance.get("hair_color", "dark blonde")
    hair_style = appearance.get("hair_style", "long wavy")
    eye_color = appearance.get("eye_color", "green")
    age = appearance.get("age", 23)

    base_desc = f"a {age} year old {ethnicity} woman with {hair_color} {hair_style} hair and {eye_color} eyes"

    caption_templates = [
        f"{trigger_word}, {base_desc}, professional portrait photo",
        f"{trigger_word}, {base_desc}, natural lighting portrait",
        f"{trigger_word}, {base_desc}, studio photo, clean background",
        f"{trigger_word}, {base_desc}, casual photo, natural setting",
        f"{trigger_word}, {base_desc}, close-up portrait, soft lighting",
        f"{trigger_word}, {base_desc}, outdoor photo, natural light",
        f"{trigger_word}, {base_desc}, lifestyle photo, relaxed pose",
        f"{trigger_word}, {base_desc}, fashion portrait, professional",
        f"{trigger_word}, {base_desc}, headshot, neutral expression",
        f"{trigger_word}, {base_desc}, portrait, slight smile",
        f"{trigger_word}, {base_desc}, three-quarter angle portrait",
        f"{trigger_word}, {base_desc}, full body photo, standing",
        f"{trigger_word}, {base_desc}, side profile, elegant pose",
        f"{trigger_word}, {base_desc}, candid photo, natural expression",
        f"{trigger_word}, {base_desc}, beauty portrait, soft focus",
        f"{trigger_word}, {base_desc}, environmental portrait",
        f"{trigger_word}, {base_desc}, editorial style photo",
        f"{trigger_word}, {base_desc}, warm lighting portrait",
        f"{trigger_word}, {base_desc}, moody portrait, dramatic light",
        f"{trigger_word}, {base_desc}, bright and airy portrait",
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
