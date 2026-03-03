"""Instagram Autopilot Service — Autonomous Instagram Management for AI Girls.

Manages:
- Content calendar generation (weekly/monthly planning)
- Smart caption generation with personality-matched style
- Hashtag strategy (trending + niche + brand)
- Posting schedule optimization
- Engagement tracking & analytics
- Content queue management

Note: Actual Instagram API posting requires Instagram Graph API or
third-party tools. This service manages the planning & content pipeline.
The user can manually post or connect their preferred posting tool.
"""

import json
import logging
import random
from datetime import datetime, timedelta
from typing import Optional

import aiosqlite

logger = logging.getLogger(__name__)


# ─── Hashtag Strategy ────────────────────────────────────────────────

HASHTAG_POOLS = {
    "cs2_gaming": [
        "#cs2", "#counterstrike2", "#csgo", "#cs2clips", "#cs2highlights",
        "#gaming", "#esports", "#fps", "#gamergirl", "#pcgaming",
        "#cs2moments", "#clutch", "#ace", "#headshot", "#cs2pro",
        "#gamingcommunity", "#streamer", "#twitchstreamer", "#gaminglife",
    ],
    "girl_gaming": [
        "#gamergirl", "#girlgamer", "#gaminggirl", "#femalegamer",
        "#womeningaming", "#girlswhoplay", "#gamergirls", "#egirl",
        "#streamergirl", "#twitchgirl", "#gamergirlmoments",
    ],
    "viral_reels": [
        "#reels", "#reelsinstagram", "#reelsviral", "#viral",
        "#trending", "#explore", "#explorepage", "#fyp",
        "#instareels", "#viralreels", "#trendingreels",
    ],
    "lifestyle": [
        "#lifestyle", "#mood", "#vibes", "#aesthetic",
        "#content", "#contentcreator", "#influencer",
        "#dailycontent", "#instagood", "#photooftheday",
    ],
    "engagement": [
        "#follow", "#like", "#comment", "#share",
        "#followforfollowback", "#likeforlikes",
    ],
}

CAPTION_TEMPLATES = {
    "clutch": [
        "1v{n} clutch and I literally SCREAMED {emoji}\n\n{reaction}\n\n{cta}",
        "When the clutch hits different {emoji}\n\n{reaction}\n\n{cta}",
        "POV: you just witnessed the play of the year {emoji}\n\n{reaction}\n\n{cta}",
        "This clutch made me lose my voice {emoji}\n\n{reaction}\n\n{cta}",
    ],
    "ace": [
        "5 KILLS. 0 DEATHS. ABSOLUTE DESTRUCTION {emoji}\n\n{reaction}\n\n{cta}",
        "ACE. That's it. That's the caption {emoji}\n\n{reaction}\n\n{cta}",
        "When every bullet finds its target {emoji}\n\n{reaction}\n\n{cta}",
    ],
    "highlight": [
        "This play broke my brain {emoji}\n\n{reaction}\n\n{cta}",
        "Save this for when someone says CS2 is dead {emoji}\n\n{reaction}\n\n{cta}",
        "My jaw is STILL on the floor {emoji}\n\n{reaction}\n\n{cta}",
    ],
    "generic": [
        "CS2 hits different when plays like this happen {emoji}\n\n{reaction}\n\n{cta}",
        "Another day, another insane CS2 moment {emoji}\n\n{reaction}\n\n{cta}",
        "This is why I can't stop watching CS2 {emoji}\n\n{reaction}\n\n{cta}",
    ],
    "meme": [
        "When the Silver thinks he's s1mple {emoji}\n\n{reaction}\n\n{cta}",
        "My teammates vs the enemy team {emoji}\n\n{reaction}\n\n{cta}",
        "CS2 moment of the day {emoji}\n\n{reaction}\n\n{cta}",
    ],
}

CTA_TEMPLATES = [
    "Follow for daily CS2 highlights!",
    "Drop a {emoji} if you've ever hit a shot like this!",
    "Tag someone who needs to see this!",
    "Save this for later {emoji}",
    "Comment your rank below!",
    "Follow for more insane CS2 content!",
    "Turn on notifications so you never miss a clip!",
    "Share with your CS2 squad!",
]

EMOJI_SETS = {
    "heavy": ["", "", "", "", "", "", "", "", "", ""],
    "moderate": ["", "", "", "", "", ""],
    "minimal": ["", ""],
}


# ─── Caption Generator ───────────────────────────────────────────────

def generate_caption(
    moment_type: str = "generic",
    personality: Optional[dict] = None,
    custom_reactions: Optional[list] = None,
    emoji_level: str = "moderate",
) -> dict:
    """Generate a personality-matched Instagram caption.

    Returns: {caption, hashtags: [...], cta}
    """
    # Select template
    templates = CAPTION_TEMPLATES.get(moment_type, CAPTION_TEMPLATES["generic"])
    template = random.choice(templates)

    # Select emoji based on personality
    emojis = EMOJI_SETS.get(emoji_level, EMOJI_SETS["moderate"])
    emoji = random.choice(emojis)

    # Generate reaction text from personality
    if custom_reactions:
        reaction = random.choice(custom_reactions)
    elif personality:
        reactions = personality.get("reactions", ["Amazing play!"])
        reaction = random.choice(reactions)
    else:
        reaction = random.choice([
            "I can't believe what I just saw!",
            "This is INSANE!",
            "My jaw literally dropped!",
            "HOW?! Just HOW?!",
        ])

    # Generate CTA
    cta_template = random.choice(CTA_TEMPLATES)
    cta = cta_template.format(emoji=emoji)

    # Fill template
    caption = template.format(
        emoji=emoji,
        reaction=reaction,
        cta=cta,
        n=random.choice([2, 3, 4, 5]),
    )

    # Generate hashtag mix
    hashtags = _generate_hashtag_mix(moment_type)

    return {
        "caption": caption,
        "hashtags": hashtags,
        "hashtags_text": " ".join(f"#{h}" if not h.startswith("#") else h for h in hashtags),
        "cta": cta,
        "moment_type": moment_type,
    }


def _generate_hashtag_mix(
    moment_type: str = "generic",
    max_hashtags: int = 20,
) -> list[str]:
    """Generate a strategic mix of hashtags."""
    tags: list[str] = []

    # Core gaming tags (5-7)
    tags.extend(random.sample(HASHTAG_POOLS["cs2_gaming"], min(6, len(HASHTAG_POOLS["cs2_gaming"]))))

    # Girl gamer tags (3-4)
    tags.extend(random.sample(HASHTAG_POOLS["girl_gaming"], min(3, len(HASHTAG_POOLS["girl_gaming"]))))

    # Viral/reach tags (4-5)
    tags.extend(random.sample(HASHTAG_POOLS["viral_reels"], min(4, len(HASHTAG_POOLS["viral_reels"]))))

    # Lifestyle/engagement (2-3)
    tags.extend(random.sample(HASHTAG_POOLS["lifestyle"], min(3, len(HASHTAG_POOLS["lifestyle"]))))

    # Deduplicate and limit
    seen: set[str] = set()
    unique: list[str] = []
    for tag in tags:
        t = tag.lower().strip()
        if t not in seen:
            seen.add(t)
            unique.append(tag)

    return unique[:max_hashtags]


# ─── Content Calendar ────────────────────────────────────────────────

CONTENT_THEMES = [
    {"type": "reel", "theme": "clutch_highlight", "description": "Epic clutch moment with girl reaction"},
    {"type": "reel", "theme": "ace_highlight", "description": "Ace compilation with dramatic commentary"},
    {"type": "reel", "theme": "fail_funny", "description": "Funny fail moment with sarcastic reaction"},
    {"type": "reel", "theme": "pro_analysis", "description": "Pro player analysis with smart commentary"},
    {"type": "reel", "theme": "trending_play", "description": "Trending/viral play with hype reaction"},
    {"type": "story", "theme": "behind_scenes", "description": "Behind the scenes / daily life content"},
    {"type": "story", "theme": "poll_engagement", "description": "Interactive poll or question sticker"},
    {"type": "carousel", "theme": "top_plays", "description": "Top 5 plays of the week carousel"},
    {"type": "reel", "theme": "meme_edit", "description": "Meme-style edited clip with trending audio"},
]

POSTING_TIMES_BY_AUDIENCE = {
    "global": ["09:00", "12:00", "15:00", "18:00", "21:00"],
    "us": ["10:00", "13:00", "17:00", "20:00"],
    "eu": ["08:00", "12:00", "16:00", "19:00", "21:00"],
    "asia": ["07:00", "11:00", "14:00", "19:00", "22:00"],
    "ru": ["09:00", "13:00", "17:00", "20:00", "22:00"],
}


async def generate_content_calendar(
    db: aiosqlite.Connection,
    profile_id: int,
    days: int = 7,
    posts_per_day: int = 2,
) -> list[dict]:
    """Generate a content calendar for the next N days.

    Creates planned content entries with themes, captions, and optimal posting times.
    """
    # Get profile personality
    cursor = await db.execute(
        "SELECT personality, memory, content_style, name FROM ai_profiles WHERE id = ?",
        (profile_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return []

    personality = json.loads(row["personality"]) if row["personality"] else {}
    content_style = json.loads(row["content_style"]) if row["content_style"] else {}
    profile_name = row["name"]

    # Determine posting times
    audience = content_style.get("target_audience", "global")
    times = POSTING_TIMES_BY_AUDIENCE.get(audience, POSTING_TIMES_BY_AUDIENCE["global"])

    calendar_entries: list[dict] = []
    today = datetime.utcnow().date()

    for day_offset in range(days):
        date = today + timedelta(days=day_offset)
        date_str = date.isoformat()

        # Select random themes for this day
        day_themes = random.sample(CONTENT_THEMES, min(posts_per_day, len(CONTENT_THEMES)))
        day_times = random.sample(times, min(posts_per_day, len(times)))
        day_times.sort()

        for i, theme in enumerate(day_themes):
            post_time = day_times[i] if i < len(day_times) else times[0]
            planned_datetime = f"{date_str}T{post_time}:00Z"

            # Generate caption for this theme
            moment_type = theme["theme"].split("_")[0]
            if moment_type not in CAPTION_TEMPLATES:
                moment_type = "generic"

            caption_data = generate_caption(
                moment_type=moment_type,
                personality=personality,
                emoji_level=content_style.get("emoji_usage", "moderate"),
            )

            entry = {
                "profile_id": profile_id,
                "planned_date": planned_datetime,
                "content_type": theme["type"],
                "topic": theme["description"],
                "caption_draft": caption_data["caption"],
                "hashtags": json.dumps(caption_data["hashtags"]),
                "status": "planned",
            }

            # Insert into DB
            await db.execute(
                """INSERT INTO content_calendar
                   (profile_id, planned_date, content_type, topic, caption_draft, hashtags, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry["profile_id"], entry["planned_date"], entry["content_type"],
                    entry["topic"], entry["caption_draft"], entry["hashtags"], entry["status"],
                ),
            )

            calendar_entries.append(entry)

    await db.commit()
    logger.info(f"Generated {len(calendar_entries)} calendar entries for profile '{profile_name}'")

    # Parse hashtags back to arrays for JSON response (stored as JSON strings in DB)
    for entry in calendar_entries:
        if isinstance(entry.get("hashtags"), str):
            try:
                entry["hashtags"] = json.loads(entry["hashtags"])
            except Exception:
                entry["hashtags"] = []
    return calendar_entries


async def get_content_calendar(
    db: aiosqlite.Connection,
    profile_id: int,
    status: Optional[str] = None,
    limit: int = 30,
) -> list[dict]:
    """Get content calendar entries for a profile."""
    query = "SELECT * FROM content_calendar WHERE profile_id = ?"
    params: list = [profile_id]

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY planned_date ASC LIMIT ?"
    params.append(limit)

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    entries = []
    for row in rows:
        entry = dict(row)
        if isinstance(entry.get("hashtags"), str):
            try:
                entry["hashtags"] = json.loads(entry["hashtags"])
            except Exception:
                entry["hashtags"] = []
        if isinstance(entry.get("performance"), str):
            try:
                entry["performance"] = json.loads(entry["performance"])
            except Exception:
                entry["performance"] = {}
        entries.append(entry)

    return entries


# ─── Instagram Autopilot Config ──────────────────────────────────────

async def get_autopilot_config(
    db: aiosqlite.Connection,
    profile_id: int,
) -> dict:
    """Get or create Instagram autopilot configuration."""
    cursor = await db.execute(
        "SELECT * FROM instagram_autopilot WHERE profile_id = ?",
        (profile_id,),
    )
    row = await cursor.fetchone()

    if not row:
        # Create default config
        await db.execute(
            "INSERT INTO instagram_autopilot (profile_id) VALUES (?)",
            (profile_id,),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT * FROM instagram_autopilot WHERE profile_id = ?",
            (profile_id,),
        )
        row = await cursor.fetchone()

    config = dict(row)
    for key in ("posting_schedule", "content_queue", "caption_style",
                "hashtag_groups", "engagement_rules", "stats"):
        if isinstance(config.get(key), str):
            try:
                config[key] = json.loads(config[key])
            except Exception:
                config[key] = {}

    config["is_active"] = bool(config.get("is_active"))
    return config


async def update_autopilot_config(
    db: aiosqlite.Connection,
    profile_id: int,
    updates: dict,
) -> dict:
    """Update Instagram autopilot configuration."""
    allowed_fields = {
        "instagram_username", "is_active", "posting_schedule",
        "caption_style", "hashtag_groups", "engagement_rules",
    }

    set_parts: list[str] = []
    params: list = []

    for key, value in updates.items():
        if key in allowed_fields:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            if key == "is_active":
                value = 1 if value else 0
            set_parts.append(f"{key} = ?")
            params.append(value)

    if not set_parts:
        return await get_autopilot_config(db, profile_id)

    set_parts.append("updated_at = datetime('now')")
    params.append(profile_id)

    await db.execute(
        f"UPDATE instagram_autopilot SET {', '.join(set_parts)} WHERE profile_id = ?",
        params,
    )

    # Also update the profile flag
    is_active = updates.get("is_active")
    if is_active is not None:
        await db.execute(
            "UPDATE ai_profiles SET instagram_autopilot_active = ? WHERE id = ?",
            (1 if is_active else 0, profile_id),
        )

    await db.commit()
    return await get_autopilot_config(db, profile_id)


# ─── Autopilot Analytics ─────────────────────────────────────────────

async def get_autopilot_analytics(
    db: aiosqlite.Connection,
    profile_id: int,
) -> dict:
    """Get analytics summary for Instagram autopilot."""
    # Content stats
    cursor = await db.execute(
        """SELECT
            COUNT(*) as total_content,
            SUM(CASE WHEN content_type='video' THEN 1 ELSE 0 END) as total_videos,
            SUM(CASE WHEN content_type='photo' THEN 1 ELSE 0 END) as total_photos,
            SUM(CASE WHEN content_type='voice' THEN 1 ELSE 0 END) as total_voice,
            SUM(cost) as total_cost
           FROM content_items WHERE profile_id = ?""",
        (profile_id,),
    )
    content_stats = dict(await cursor.fetchone())

    # Calendar stats
    cursor = await db.execute(
        """SELECT
            COUNT(*) as total_planned,
            SUM(CASE WHEN status='posted' THEN 1 ELSE 0 END) as total_posted,
            SUM(CASE WHEN status='planned' THEN 1 ELSE 0 END) as total_upcoming
           FROM content_calendar WHERE profile_id = ?""",
        (profile_id,),
    )
    calendar_stats = dict(await cursor.fetchone())

    # Social posts
    cursor = await db.execute(
        """SELECT
            COUNT(*) as total_posts,
            SUM(CASE WHEN platform='instagram' THEN 1 ELSE 0 END) as instagram_posts,
            SUM(CASE WHEN platform='tiktok' THEN 1 ELSE 0 END) as tiktok_posts
           FROM social_posts WHERE profile_id = ?""",
        (profile_id,),
    )
    social_stats = dict(await cursor.fetchone())

    # Memory entries
    cursor = await db.execute(
        "SELECT COUNT(*) as total FROM character_memory WHERE profile_id = ?",
        (profile_id,),
    )
    memory_count = (await cursor.fetchone())["total"]

    return {
        "content": content_stats,
        "calendar": calendar_stats,
        "social": social_stats,
        "memory_entries": memory_count,
        "generated_at": datetime.utcnow().isoformat(),
    }


# ─── Character Memory System ─────────────────────────────────────────

async def add_memory(
    db: aiosqlite.Connection,
    profile_id: int,
    memory_type: str,
    content: str,
    importance: float = 0.5,
    context: Optional[dict] = None,
) -> int:
    """Add a memory entry for the AI character."""
    cursor = await db.execute(
        """INSERT INTO character_memory (profile_id, memory_type, content, importance, context)
           VALUES (?, ?, ?, ?, ?)""",
        (profile_id, memory_type, content, importance, json.dumps(context or {})),
    )
    await db.commit()
    return cursor.lastrowid


async def get_memories(
    db: aiosqlite.Connection,
    profile_id: int,
    memory_type: Optional[str] = None,
    min_importance: float = 0.0,
    limit: int = 50,
) -> list[dict]:
    """Get character memories, optionally filtered."""
    query = "SELECT * FROM character_memory WHERE profile_id = ? AND importance >= ?"
    params: list = [profile_id, min_importance]

    if memory_type:
        query += " AND memory_type = ?"
        params.append(memory_type)

    query += " ORDER BY importance DESC, created_at DESC LIMIT ?"
    params.append(limit)

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    memories = []
    for row in rows:
        m = dict(row)
        if isinstance(m.get("context"), str):
            try:
                m["context"] = json.loads(m["context"])
            except Exception:
                m["context"] = {}
        memories.append(m)

    return memories


async def build_character_context(
    db: aiosqlite.Connection,
    profile_id: int,
) -> dict:
    """Build full character context from profile + memories.

    Used for generating personality-consistent content.
    """
    # Get profile
    cursor = await db.execute(
        "SELECT * FROM ai_profiles WHERE id = ?",
        (profile_id,),
    )
    row = await cursor.fetchone()
    if not row:
        return {}

    profile = dict(row)
    for key in ("appearance", "voice_config", "personality", "memory",
                "content_style", "social_config"):
        if isinstance(profile.get(key), str):
            try:
                profile[key] = json.loads(profile[key])
            except Exception:
                profile[key] = {}

    # Get important memories
    memories = await get_memories(db, profile_id, min_importance=0.3, limit=20)

    # Get recent content performance
    cursor = await db.execute(
        """SELECT content_type, COUNT(*) as count, AVG(cost) as avg_cost
           FROM content_items WHERE profile_id = ?
           GROUP BY content_type""",
        (profile_id,),
    )
    content_stats = [dict(r) for r in await cursor.fetchall()]

    return {
        "name": profile.get("name", "AI Girl"),
        "personality": profile.get("personality", {}),
        "appearance": profile.get("appearance", {}),
        "voice_config": profile.get("voice_config", {}),
        "backstory": profile.get("backstory", ""),
        "catchphrases": json.loads(profile.get("catchphrases", "[]")) if isinstance(profile.get("catchphrases"), str) else profile.get("catchphrases", []),
        "memories": memories,
        "content_performance": content_stats,
        "memory_profile": profile.get("memory", {}),
    }
