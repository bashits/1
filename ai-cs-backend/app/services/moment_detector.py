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
from typing import Optional

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


# ─── Trend factor mapping: which trend types boost which moment types ───
# Maps trend format names (from trend_analyzer) to moment types they boost.
_TREND_MOMENT_BOOST: dict[str, list[str]] = {
    "sigma_edit": ["ace", "clutch", "insane_play", "knife_kill"],
    "highlight_react": ["emotional_reaction", "insane_play", "multi_kill", "ace"],
    "pro_clutch": ["clutch", "ace", "wallbang"],
    "funny_moments": ["meme_fail", "toxic_moment", "emotional_reaction"],
    "ace_compilation": ["ace", "multi_kill", "headshot_sequence"],
    "tutorial_tip": ["insane_spray", "wallbang", "headshot_sequence"],
}


def _compute_trend_factor(
    moment_type: str, trend_data: Optional[list[dict]] = None
) -> float:
    """Compute trend factor (0.0–0.30) for a moment type based on last-24h trends.

    This is the DETERMINING FACTOR — it has the highest single weight in the
    final composite score so that trending content types float to the top.

    Logic:
    1. Look at each active trend from the last 24h.
    2. If the trend's format boosts this moment_type, accumulate score.
    3. Normalize to 0.0–0.30 range (capped).

    Returns 0.0 when no trend data is available (never blocks scoring).
    """
    if not trend_data:
        return 0.0

    raw = 0.0
    for trend in trend_data:
        trend_type = trend.get("trend_type", "")
        fmt = trend.get("metadata", {}).get("format", "") if isinstance(trend.get("metadata"), dict) else ""
        trend_score = float(trend.get("score", 0))

        # Direct match: trend title mentions moment type keyword
        title_lower = trend.get("title", "").lower()
        for kw in TYPE_KEYWORDS.get(moment_type, []):
            if kw in title_lower:
                raw += trend_score * 0.04
                break

        # Format-based match: trending format boosts certain moment types
        boosted_types = _TREND_MOMENT_BOOST.get(fmt, [])
        if moment_type in boosted_types:
            raw += trend_score * 0.03

    # Cap at 0.30 — this is the highest single component weight
    return round(min(0.30, raw), 4)


def score_clip(clip: dict, trend_data: Optional[list[dict]] = None) -> dict:
    """
    Score a real Twitch clip deterministically using concrete signals
    PLUS 24h trend data as the determining factor.

    Input clip dict should have:
    - title: str
    - view_count: int
    - duration: float (seconds)
    - broadcaster_name: str
    - broadcaster_viewers: int (optional, stream viewer count at time of clip)
    - created_at: str (ISO timestamp)

    trend_data: list of trend dicts from the trends table (last 24h).
    When provided, the trend_factor becomes the highest-weight component.

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

    # 2. View score — log10 scale, 0 to 0.25
    view_score = min(0.25, math.log10(max(views, 1)) / 20.0)

    # 3. Duration score — 10-35s is ideal for reels, 0 to 0.10
    if 10 <= duration <= 35:
        duration_score = 0.10
    elif 5 <= duration <= 60:
        duration_score = 0.06
    else:
        duration_score = 0.03

    # 4. Broadcaster popularity — real viewer count signal, 0 to 0.10
    broadcaster_score = min(0.10, broadcaster_viewers / 150_000) if broadcaster_viewers else 0.0

    # 5. Moment type base score (deterministic, from MOMENT_SCORING), 0 to ~0.23
    type_score = scoring["base"] * 0.25

    # 6. Recency bonus — newer clips get a small boost, 0 to 0.05
    recency_bonus = 0.0
    if created_at:
        try:
            created = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc
            )
            hours_ago = (datetime.now(timezone.utc) - created).total_seconds() / 3600
            recency_bonus = max(0.0, min(0.05, 0.05 * (1.0 - hours_ago / 168)))
        except (ValueError, TypeError):
            pass

    # 7. TREND FACTOR — the DETERMINING FACTOR (highest weight: 0 to 0.30)
    #    Uses actual 24h trend analytics to boost moments matching current trends.
    trend_factor = _compute_trend_factor(moment_type, trend_data)

    # Composite score — sum of all signals (trend_factor is the biggest component)
    composite = (
        view_score + duration_score + broadcaster_score
        + type_score + recency_bonus + trend_factor
    )

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
            "trend_factor": trend_factor,
        },
        "trend_boosted": trend_factor > 0,
        "detected_type_label": scoring.get("label", moment_type),
        "clip_priority": scoring.get("clip_priority", 99),
        "data_source": "real_clip",
    }


def rank_clips(
    clips: list[dict], trend_data: Optional[list[dict]] = None
) -> list[dict]:
    """Rank a list of real Twitch clips by score. Fully deterministic.

    When trend_data is provided (last 24h trends), the trend_factor becomes
    the highest-weight component in scoring — moments matching current trends
    float to the top.
    """
    if not clips:
        return []
    scored = [score_clip(c, trend_data=trend_data) for c in clips]
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

    # Fetch last 24h trend data from DB to use as determining factor
    trend_data: list[dict] = []
    try:
        cursor = await db.execute(
            "SELECT * FROM trends WHERE is_active = 1 "
            "AND created_at >= datetime('now', '-24 hours') "
            "ORDER BY score DESC LIMIT 50"
        )
        rows = await cursor.fetchall()
        for row in rows:
            d = dict(row)
            if isinstance(d.get("metadata"), str):
                try:
                    d["metadata"] = json.loads(d["metadata"])
                except (json.JSONDecodeError, TypeError):
                    d["metadata"] = {}
            trend_data.append(d)
        logger.info(f"Loaded {len(trend_data)} trends for moment ranking")
    except Exception as e:
        logger.warning(f"Could not load trend data for ranking: {e}")

    ranked = rank_clips(clips, trend_data=trend_data)

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
                        "trend_boosted": moment.get("trend_boosted", False),
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
    twitch_access_token = os.environ.get("TWITCH_ACCESS_TOKEN", "")

    if not twitch_access_token and (not twitch_client_id or not twitch_client_secret):
        logger.warning(
            "No Twitch API credentials — cannot detect real moments. "
            "Set TWITCH_ACCESS_TOKEN or TWITCH_CLIENT_ID + TWITCH_CLIENT_SECRET."
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

    # Fetch last 24h trend data for trend-based ranking
    trend_data: list[dict] = []
    try:
        trend_cursor = await db.execute(
            "SELECT * FROM trends WHERE is_active = 1 "
            "AND created_at >= datetime('now', '-24 hours') "
            "ORDER BY score DESC LIMIT 50"
        )
        trend_rows = await trend_cursor.fetchall()
        for row in trend_rows:
            d = dict(row)
            if isinstance(d.get("metadata"), str):
                try:
                    d["metadata"] = json.loads(d["metadata"])
                except (json.JSONDecodeError, TypeError):
                    d["metadata"] = {}
            trend_data.append(d)
    except Exception as e:
        logger.warning(f"Could not load trend data: {e}")

    # Score real clips deterministically (with trend factor as determining factor)
    ranked = rank_clips(clips, trend_data=trend_data)

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
