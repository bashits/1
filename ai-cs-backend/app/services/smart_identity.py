"""Smart Identity Service — Consistent Girl Selection & Identity Lock.

When creating an AI profile, this service:
1. Searches Pexels for videos matching the girl's appearance
2. Groups by photographer (same photographer = same model = same girl)
3. Selects the best group with the most videos
4. Locks these videos to the profile (profile_base_videos table)
5. All future video generation uses ONLY these locked base videos

This ensures visual consistency — the same girl appears in every video.
"""

import json
import logging
import random
from typing import Optional

import aiosqlite

from app.services.smart_girl_video_sourcer import (
    build_video_search_queries,
    search_videos_multi,
    select_best_video_set,
    download_video,
    _score_video_quality,
    group_videos_by_user,
    _get_pexels_key,
)

logger = logging.getLogger(__name__)


async def lock_identity_videos(
    db: aiosqlite.Connection,
    profile_id: int,
    appearance: Optional[dict] = None,
    target_count: int = 8,
) -> dict:
    """Search Pexels and lock a set of base videos to this profile.

    This is the core identity lock — once locked, the profile always uses
    these same videos for lip-sync generation, ensuring the same girl appears.

    Returns: {success, videos_locked, pexels_user, message}
    """
    if not _get_pexels_key():
        return {
            "success": False,
            "videos_locked": 0,
            "message": "PEXELS_API_KEY not configured",
        }

    # Check if already locked
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM profile_base_videos WHERE profile_id = ?",
        (profile_id,),
    )
    existing = (await cursor.fetchone())["cnt"]
    if existing > 0:
        return {
            "success": True,
            "videos_locked": existing,
            "message": f"Identity already locked with {existing} videos",
            "already_locked": True,
        }

    # Build search queries from appearance
    queries = build_video_search_queries(appearance, max_queries=6)
    logger.info(f"[Identity Lock] Searching Pexels for profile {profile_id}: {queries[:3]}...")

    # Search with multiple queries
    all_videos = await search_videos_multi(queries, videos_per_query=20)
    logger.info(f"[Identity Lock] Found {len(all_videos)} candidate videos")

    if not all_videos:
        return {
            "success": False,
            "videos_locked": 0,
            "message": "No suitable videos found on Pexels for this appearance",
        }

    # Group by photographer and find the best group
    # Same photographer = very likely same model = visual consistency
    groups = group_videos_by_user(all_videos)
    sorted_groups = sorted(groups.items(), key=lambda x: len(x[1]), reverse=True)

    best_group: list[dict] = []
    best_user = ""
    best_user_id = 0

    for uid, group_videos in sorted_groups:
        # Score each video in group
        scored = [(v, _score_video_quality(v)) for v in group_videos]
        scored = [(v, s) for v, s in scored if s >= 0.3]
        scored.sort(key=lambda x: x[1], reverse=True)

        quality_videos = [v for v, _ in scored]

        if len(quality_videos) >= 2:
            best_group = quality_videos[:target_count]
            best_user = quality_videos[0].get("user", "unknown")
            best_user_id = uid
            logger.info(
                f"[Identity Lock] Selected {len(best_group)} videos from '{best_user}' (user_id={uid})"
            )
            break

    if not best_group:
        # Fallback: take top videos regardless of photographer
        scored = [(v, _score_video_quality(v)) for v in all_videos]
        scored.sort(key=lambda x: x[1], reverse=True)
        best_group = [v for v, _ in scored[:target_count]]
        best_user = "mixed"
        best_user_id = 0
        logger.info(f"[Identity Lock] Using mixed sources: {len(best_group)} videos")

    # Download and lock videos to profile
    locked_count = 0
    is_first = True

    for video in best_group:
        # Download video
        fname = f"profile_{profile_id}_base_{video['id']}.mp4"
        local_path = await download_video(video["url"], fname)

        # Insert into profile_base_videos
        await db.execute(
            """INSERT INTO profile_base_videos
               (profile_id, pexels_id, video_url, local_path, preview_url,
                duration, width, height, pexels_user, pexels_user_id,
                is_primary, quality_score)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                profile_id,
                video.get("id"),
                video.get("url", ""),
                local_path,
                video.get("preview_url", ""),
                video.get("duration", 0),
                video.get("width", 0),
                video.get("height", 0),
                video.get("user", ""),
                video.get("user_id", 0),
                1 if is_first else 0,
                _score_video_quality(video),
            ),
        )
        locked_count += 1
        is_first = False

    # Update profile with identity lock info
    await db.execute(
        """UPDATE ai_profiles SET
            identity_locked = 1,
            pexels_user_id = ?,
            base_videos_count = ?,
            updated_at = datetime('now')
           WHERE id = ?""",
        (best_user_id, locked_count, profile_id),
    )

    await db.commit()

    logger.info(
        f"[Identity Lock] Locked {locked_count} videos for profile {profile_id} "
        f"(photographer: {best_user})"
    )

    return {
        "success": True,
        "videos_locked": locked_count,
        "pexels_user": best_user,
        "pexels_user_id": best_user_id,
        "message": f"Identity locked: {locked_count} videos from '{best_user}'",
    }


async def get_profile_base_video(
    db: aiosqlite.Connection,
    profile_id: int,
    prefer_unused: bool = True,
) -> Optional[dict]:
    """Get a base video for this profile from its locked set.

    If identity is locked, returns from locked videos.
    If not locked, falls back to general Pexels search.
    """
    # Check if profile has locked videos
    if prefer_unused:
        # Prefer least-used video for variety
        cursor = await db.execute(
            """SELECT * FROM profile_base_videos
               WHERE profile_id = ? AND local_path IS NOT NULL
               ORDER BY use_count ASC, quality_score DESC
               LIMIT 1""",
            (profile_id,),
        )
    else:
        # Random selection
        cursor = await db.execute(
            """SELECT * FROM profile_base_videos
               WHERE profile_id = ? AND local_path IS NOT NULL
               ORDER BY RANDOM()
               LIMIT 1""",
            (profile_id,),
        )

    row = await cursor.fetchone()
    if not row:
        return None

    video = dict(row)

    # Increment use count
    await db.execute(
        "UPDATE profile_base_videos SET use_count = use_count + 1 WHERE id = ?",
        (video["id"],),
    )
    await db.commit()

    return video


async def get_profile_base_videos(
    db: aiosqlite.Connection,
    profile_id: int,
) -> list[dict]:
    """Get all locked base videos for a profile."""
    cursor = await db.execute(
        "SELECT * FROM profile_base_videos WHERE profile_id = ? ORDER BY is_primary DESC, quality_score DESC",
        (profile_id,),
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def unlock_identity(
    db: aiosqlite.Connection,
    profile_id: int,
) -> dict:
    """Unlock identity — remove locked videos so new ones can be selected."""
    cursor = await db.execute(
        "DELETE FROM profile_base_videos WHERE profile_id = ?",
        (profile_id,),
    )
    deleted = cursor.rowcount

    await db.execute(
        """UPDATE ai_profiles SET
            identity_locked = 0,
            pexels_user_id = NULL,
            base_videos_count = 0,
            updated_at = datetime('now')
           WHERE id = ?""",
        (profile_id,),
    )
    await db.commit()

    return {
        "success": True,
        "videos_removed": deleted,
        "message": f"Identity unlocked, {deleted} videos removed",
    }


async def generate_backstory(
    db: aiosqlite.Connection,
    profile_id: int,
) -> str:
    """Generate a unique backstory for the AI character based on her traits.

    Creates a rich character backstory from appearance, personality, and voice data.
    """
    cursor = await db.execute(
        "SELECT name, appearance, personality, voice_config, description FROM ai_profiles WHERE id = ?",
        (profile_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return ""

    name = row["name"]
    appearance = json.loads(row["appearance"]) if row["appearance"] else {}
    personality = json.loads(row["personality"]) if row["personality"] else {}
    description = row["description"] or ""

    # Build backstory from traits
    archetype = personality.get("archetype", "gamer girl")
    tone = personality.get("tone", "energetic")
    ethnicity = appearance.get("ethnicity", "")
    hair = appearance.get("hair_color", "")
    age_range = appearance.get("age_range", "20-25")

    backstory_templates = [
        f"{name} is a {age_range}-year-old content creator who lives and breathes CS2. "
        f"With her {hair} hair and {tone} personality, she's built a following that loves her "
        f"authentic reactions to insane gameplay. She started watching CS when she was 16 and "
        f"never looked back. Her friends say she's the {archetype.lower()} of the gaming world.",

        f"Growing up as a competitive gamer, {name} found her calling in content creation. "
        f"Her {tone} style and genuine reactions made her stand out. She doesn't just clip "
        f"highlights — she LIVES them. Every clutch feels personal, every ace makes her scream. "
        f"That's why her audience keeps coming back.",

        f"{name} turned her obsession with CS2 into a full-time gig. Known for her {tone} "
        f"commentary and {archetype.lower()} energy, she creates content that feels like watching "
        f"the game with your best friend. She's not just a narrator — she's your hype partner.",
    ]

    backstory = random.choice(backstory_templates)

    # Save backstory
    await db.execute(
        "UPDATE ai_profiles SET backstory = ?, updated_at = datetime('now') WHERE id = ?",
        (backstory, profile_id),
    )
    await db.commit()

    return backstory
