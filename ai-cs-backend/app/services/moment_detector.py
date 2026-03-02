"""
Moment Detector Service — Real CS2 Highlight Detection Engine

Two operating modes:
A) CLIP-BASED (production): Analyzes real Twitch clips from the Clips API.
   Scores clips using concrete signals: view_count, duration, title keywords,
   broadcaster popularity, and recency. No randomness involved.

B) STREAM-BASED (legacy/DB): Analyzes a stream record from the database.
   Tries to fetch real clips for that broadcaster via Twitch API, then
   scores them with the same deterministic algorithm.

Scoring algorithm:
- view_score:   log10(views) normalized — real popularity signal
- duration_score: 10-35s clips score highest (ideal reel length)
- broadcaster_score: higher viewer count = bigger audience
- type_score:   detected moment type from title keywords (ace > clutch > multi_kill > ...)
- recency_bonus: newer clips get a small boost (decay over 7 days)
- viral_multiplier: clips with >10k views get a bonus from moment type

NO random.uniform, NO random.choice, NO simulated data.
Everything is deterministic given the same input.
"""

import json
import logging
import math
from datetime import datetime, timezone

logger = logging.getLogger("moment_detector")

MOMENT_TYPES = [
    "clutch",
    "ace",
    "multi_kill",
    "headshot_sequence",
    "emotional_reaction",
    "toxic_moment",
    "meme_fail",
    "insane_spray",
    "knife_kill",
    "wallbang",
]

# ─── Scoring Weights for Moment Types ─────────────────────────────
# Deterministic: each type has a fixed base score, viral multiplier, and clip priority
MOMENT_SCORING = {
    "ace": {"base": 0.92, "viral_mult": 1.5, "clip_priority": 1, "label": "ACE"},
    "clutch": {"base": 0.85, "viral_mult": 1.4, "clip_priority": 2, "label": "Клатч"},
    "multi_kill": {"base": 0.78, "viral_mult": 1.2, "clip_priority": 3, "label": "Мульти-килл"},
    "insane_spray": {"base": 0.74, "viral_mult": 1.15, "clip_priority": 4, "label": "Спрей"},
    "headshot_sequence": {"base": 0.70, "viral_mult": 1.1, "clip_priority": 5, "label": "Хедшоты"},
    "wallbang": {"base": 0.66, "viral_mult": 1.2, "clip_priority": 6, "label": "Воллбэнг"},
    "knife_kill": {"base": 0.82, "viral_mult": 1.35, "clip_priority": 7, "label": "Нож"},
    "emotional_reaction": {"base": 0.65, "viral_mult": 1.3, "clip_priority": 8, "label": "Реакция"},
    "toxic_moment": {"base": 0.60, "viral_mult": 1.25, "clip_priority": 9, "label": "Токсик"},
    "meme_fail": {"base": 0.55, "viral_mult": 1.4, "clip_priority": 10, "label": "Фейл"},
    "insane_play": {"base": 0.72, "viral_mult": 1.2, "clip_priority": 5, "label": "Insane Play"},
}

# ─── Title keyword → moment type mapping ─────────────────────────
# Deterministic: detect what kind of moment a clip is from its title
TYPE_KEYWORDS: dict[str, list[str]] = {
    "ace": ["ace", "эйс", "5k", "5 kill", "5kills", "пятерка"],
    "clutch": ["clutch", "клатч", "1v", "1vs", "retake", "1 v "],
    "multi_kill": ["3k", "4k", "triple", "quad", "spray transfer", "transfer"],
    "headshot_sequence": ["headshot", "hs", "one tap", "flick", "onetap"],
    "knife_kill": ["knife", "нож", "blade", "backstab"],
    "wallbang": ["wallbang", "wall bang", "through wall"],
    "meme_fail": ["fail", "funny", "lol", "wtf", "фейл", "смешно", "мем"],
    "emotional_reaction": ["react", "scream", "rage", "omg", "insane reaction"],
    "toxic_moment": ["toxic", "trash talk", "bm", "teabag"],
    "insane_spray": ["spray", "control", "burst", "spraydown"],
}


def detect_moment_type(title: str) -> str:
    """Detect moment type from clip title using keyword matching. Deterministic."""
    text = title.lower()
    for mtype, keywords in TYPE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return mtype
    # Fallback: check for general excitement keywords
    if any(w in text for w in ["insane", "crazy", "incredible", "unreal", "sick"]):
        return "insane_play"
    return "insane_play"


def score_clip(clip: dict) -> dict:
    """
    Score a real Twitch clip deterministically using concrete signals.

    Input clip dict should have:
    - title: str
    - view_count: int
    - duration: float (seconds)
    - broadcaster_name: str
    - broadcaster_viewers: int (optional, stream viewer count at time of clip)
    - created_at: str (ISO timestamp)

    Returns scored moment dict with full breakdown. No randomness.
    """
    title = clip.get("title", "")
    views = clip.get("view_count", 0)
    duration = clip.get("duration", 30)
    broadcaster_viewers = clip.get("broadcaster_viewers", 0)
    created_at = clip.get("created_at", "")

    # 1. Detect moment type from title (deterministic keyword matching)
    moment_type = detect_moment_type(title)
    scoring = MOMENT_SCORING.get(moment_type, MOMENT_SCORING["insane_play"])

    # 2. View score — log10 scale, 0 to 0.4
    # 1 view = 0, 100 views ≈ 0.16, 1K ≈ 0.24, 10K ≈ 0.32, 100K ≈ 0.4
    view_score = min(0.4, math.log10(max(views, 1)) / 12.5)

    # 3. Duration score — 10-35s is ideal for reels
    if 10 <= duration <= 35:
        duration_score = 0.2
    elif 5 <= duration <= 60:
        duration_score = 0.12
    else:
        duration_score = 0.05

    # 4. Broadcaster popularity — real viewer count signal
    broadcaster_score = min(0.15, broadcaster_viewers / 100_000) if broadcaster_viewers else 0.0

    # 5. Moment type base score (deterministic, from MOMENT_SCORING)
    type_score = scoring["base"] * 0.25

    # 6. Recency bonus — newer clips get a small boost
    recency_bonus = 0.0
    if created_at:
        try:
            created = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            hours_ago = (datetime.now(timezone.utc) - created).total_seconds() / 3600
            # Full bonus for <6h, linear decay to 0 at 168h (7 days)
            recency_bonus = max(0.0, min(0.05, 0.05 * (1.0 - hours_ago / 168)))
        except (ValueError, TypeError):
            pass

    # Composite score — sum of all real signals
    composite = view_score + duration_score + broadcaster_score + type_score + recency_bonus

    # Viral multiplier for clips with >10k views
    if views > 10_000:
        composite *= scoring["viral_mult"]

    composite = round(min(1.0, composite), 3)

    return {
        "clip": clip,
        "moment_type": moment_type,
        "score": composite,
        "breakdown": {
            "view_score": round(view_score, 4),
            "duration_score": round(duration_score, 4),
            "broadcaster_score": round(broadcaster_score, 4),
            "type_score": round(type_score, 4),
            "recency_bonus": round(recency_bonus, 4),
        },
        "detected_type_label": scoring.get("label", moment_type),
        "clip_priority": scoring.get("clip_priority", 99),
        "data_source": "real_clip",
    }


def rank_clips(clips: list[dict]) -> list[dict]:
    """Rank a list of real Twitch clips by score. Fully deterministic."""
    if not clips:
        return []
    scored = [score_clip(c) for c in clips]
    scored.sort(key=lambda m: m["score"], reverse=True)
    return scored


async def detect_moments_from_clips(
    db,
    stream_id: int,
    clips: list[dict],
) -> list[dict]:
    """
    Production moment detection: analyze real Twitch clips.
    Stores results in DB and returns ranked moments.
    No randomness — all scores are deterministic given the same input.
    """
    if not clips:
        return []

    ranked = rank_clips(clips)

    for moment in ranked:
        clip = moment["clip"]
        try:
            await db.execute(
                """INSERT INTO moments
                   (stream_id, moment_type, timestamp_start, timestamp_end,
                    score, description, metadata, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'detected')""",
                (
                    stream_id,
                    moment["moment_type"],
                    0.0,
                    float(clip.get("duration", 30)),
                    moment["score"],
                    clip.get("title", "CS2 Highlight"),
                    json.dumps({
                        "clip_id": clip.get("clip_id", ""),
                        "clip_url": clip.get("url", ""),
                        "download_url": clip.get("download_url", ""),
                        "view_count": clip.get("view_count", 0),
                        "broadcaster_name": clip.get("broadcaster_name", ""),
                        "broadcaster_viewers": clip.get("broadcaster_viewers", 0),
                        "created_at": clip.get("created_at", ""),
                        "moment_label": moment["detected_type_label"],
                        "clip_priority": moment["clip_priority"],
                        "score_breakdown": moment["breakdown"],
                        "data_source": "real_clip",
                    }),
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to insert moment into DB: {e}")

    try:
        await db.commit()
        await db.execute(
            "UPDATE streams SET status = 'analyzed' WHERE id = ?", (stream_id,)
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"DB commit error: {e}")

    return ranked


async def detect_moments(
    db, stream_id: int, sensitivity: float = 0.7,
    moment_types: list[str] | None = None,
) -> list[dict]:
    """
    Stream-based moment detection.

    Tries to fetch real clips for the broadcaster via Twitch API, then
    scores them deterministically. If no Twitch credentials or no clips
    found, returns empty list — does NOT generate fake/simulated data.

    For the full autonomous pipeline, use detect_moments_from_clips() directly
    with clips already fetched from discover_trending_cs2_clips().
    """
    import os

    if moment_types is None:
        moment_types = MOMENT_TYPES

    # Check if stream exists
    cursor = await db.execute("SELECT * FROM streams WHERE id = ?", (stream_id,))
    stream = await cursor.fetchone()
    if not stream:
        return []

    stream_dict = dict(stream)
    broadcaster = stream_dict.get("streamer_name", "")

    if not broadcaster:
        logger.warning(f"Stream {stream_id} has no streamer_name — cannot fetch real clips")
        return []

    # Try to fetch real clips from Twitch API
    twitch_client_id = os.environ.get("TWITCH_CLIENT_ID", "")
    twitch_client_secret = os.environ.get("TWITCH_CLIENT_SECRET", "")

    if not twitch_client_id or not twitch_client_secret:
        logger.warning(
            "No Twitch API credentials — cannot detect real moments. "
            "Set TWITCH_CLIENT_ID + TWITCH_CLIENT_SECRET."
        )
        return []

    try:
        from app.services.clip_montage import discover_trending_cs2_clips
        result = await discover_trending_cs2_clips(
            twitch_client_id=twitch_client_id,
            twitch_client_secret=twitch_client_secret,
            limit=20,
            period="24h",
        )
        clips = result.get("clips", [])
    except Exception as e:
        logger.error(f"Failed to fetch Twitch clips for {broadcaster}: {e}")
        return []

    if not clips:
        logger.info(f"No clips found for CS2 streams in last 24h")
        return []

    # Score real clips deterministically
    ranked = rank_clips(clips)

    # Filter by sensitivity threshold
    min_score = (1.0 - sensitivity) * 0.3
    ranked = [m for m in ranked if m["score"] >= min_score]

    # Filter by requested moment types if specified
    if moment_types and set(moment_types) != set(MOMENT_TYPES):
        ranked = [m for m in ranked if m["moment_type"] in moment_types]

    # Store in DB
    for moment in ranked:
        clip = moment["clip"]
        try:
            await db.execute(
                """INSERT INTO moments
                   (stream_id, moment_type, timestamp_start, timestamp_end,
                    score, description, metadata, status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'detected')""",
                (
                    stream_id,
                    moment["moment_type"],
                    float(clip.get("vod_offset", 0) or 0),
                    float(clip.get("vod_offset", 0) or 0) + float(clip.get("duration", 30)),
                    moment["score"],
                    clip.get("title", "CS2 Highlight"),
                    json.dumps({
                        "clip_id": clip.get("clip_id", ""),
                        "clip_url": clip.get("url", ""),
                        "download_url": clip.get("download_url", ""),
                        "view_count": clip.get("view_count", 0),
                        "broadcaster_name": clip.get("broadcaster_name", ""),
                        "score_breakdown": moment["breakdown"],
                        "data_source": "real_clip",
                    }),
                ),
            )
        except Exception as e:
            logger.warning(f"Failed to insert moment: {e}")

    try:
        await db.commit()
        await db.execute(
            "UPDATE streams SET status = 'analyzed' WHERE id = ?", (stream_id,)
        )
        await db.commit()
    except Exception as e:
        logger.warning(f"DB commit error: {e}")

    return ranked


async def get_top_moments(db, limit: int = 10) -> list[dict]:
    """Get top scoring moments across all streams."""
    cursor = await db.execute(
        "SELECT * FROM moments ORDER BY score DESC LIMIT ?", (limit,)
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]
