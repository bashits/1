from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.database import get_db
from app.models.schemas import StreamCreate, StreamResponse

router = APIRouter(prefix="/api/streams", tags=["streams"])


# ─── Top CS2 Twitch Streamers Database ─────────────────────────────
# Real streamers tracked for content analysis and clipping
TOP_CS2_STREAMERS = [
    {
        "username": "s1mple",
        "display_name": "s1mple",
        "twitch_url": "https://www.twitch.tv/s1mple",
        "region": "CIS",
        "language": "ru/en",
        "avg_viewers": 25000,
        "followers": 4200000,
        "content_style": "FPL, рейтинг, про-матчи",
        "clip_potential": 9.5,
        "description": "Легенда CS — невероятный аим, эмоциональные реакции, огромная база фанатов",
    },
    {
        "username": "gaules",
        "display_name": "Gaules",
        "twitch_url": "https://www.twitch.tv/gaules",
        "region": "Brazil/LATAM",
        "language": "pt",
        "avg_viewers": 15000,
        "followers": 4250000,
        "content_style": "Watch parties, CS2 турниры, комментарии",
        "clip_potential": 9.0,
        "description": "Крупнейший бразильский CS-стример. Watch party = вирусные реакции аудитории",
    },
    {
        "username": "shroud",
        "display_name": "shroud",
        "twitch_url": "https://www.twitch.tv/shroud",
        "region": "North America",
        "language": "en",
        "avg_viewers": 20000,
        "followers": 10500000,
        "content_style": "Ranked, шутеры, казуальный стиль",
        "clip_potential": 9.0,
        "description": "Легенда CS + король шутеров. Спокойный стиль, невероятный аим = чистые клипы",
    },
    {
        "username": "donk_cs",
        "display_name": "donk",
        "twitch_url": "https://www.twitch.tv/donk_cs",
        "region": "CIS",
        "language": "ru",
        "avg_viewers": 18000,
        "followers": 850000,
        "content_style": "FPL, Premier, про-тренировки",
        "clip_potential": 9.5,
        "description": "Молодая суперзвезда CS2 — безумный аим, быстрые клатчи, хайповый контент",
    },
    {
        "username": "forg1",
        "display_name": "forg1",
        "twitch_url": "https://www.twitch.tv/forg1",
        "region": "Western Europe",
        "language": "es",
        "avg_viewers": 14000,
        "followers": 190000,
        "content_style": "FPL, рейтинг, про-матчи",
        "clip_potential": 8.5,
        "description": "Топ испаноязычный CS2 стример — высокий скилл, эмоциональные моменты",
    },
    {
        "username": "ohnePixel",
        "display_name": "ohnePixel",
        "twitch_url": "https://www.twitch.tv/ohnePixel",
        "region": "Western Europe",
        "language": "en",
        "avg_viewers": 12000,
        "followers": 1200000,
        "content_style": "CS2 скины, кейсы, рейтинг",
        "clip_potential": 8.0,
        "description": "CS2 скины + геймплей. Открытие кейсов = вирусные моменты",
    },
    {
        "username": "yuurih",
        "display_name": "yuurih",
        "twitch_url": "https://www.twitch.tv/yuurih",
        "region": "Brazil/LATAM",
        "language": "pt",
        "avg_viewers": 8000,
        "followers": 420000,
        "content_style": "FPL, Premier, про-тренировки",
        "clip_potential": 8.5,
        "description": "Бразильский про-игрок FURIA — технический геймплей, клатчи, LATAM аудитория",
    },
    {
        "username": "fl0m",
        "display_name": "fl0m",
        "twitch_url": "https://www.twitch.tv/fl0m",
        "region": "North America",
        "language": "en",
        "avg_viewers": 5000,
        "followers": 900000,
        "content_style": "Ranked, развлекательный CS2",
        "clip_potential": 7.5,
        "description": "NA CS2 ветеран — расслабленный стиль, безумные клипы с AWP",
    },
    {
        "username": "ESLCS",
        "display_name": "ESL Counter-Strike",
        "twitch_url": "https://www.twitch.tv/esl_csgo",
        "region": "Global",
        "language": "en",
        "avg_viewers": 50000,
        "followers": 6500000,
        "content_style": "Про-турниры, IEM, ESL Pro League",
        "clip_potential": 9.5,
        "description": "Официальный канал ESL — все крупные турниры CS2. Максимальный охват клипов",
    },
    {
        "username": "BLASTPremier",
        "display_name": "BLAST Premier",
        "twitch_url": "https://www.twitch.tv/blastpremier",
        "region": "Global",
        "language": "en",
        "avg_viewers": 40000,
        "followers": 2100000,
        "content_style": "BLAST турниры, про-матчи",
        "clip_potential": 9.0,
        "description": "BLAST серия турниров — драматичные моменты, хайлайты финалов",
    },
    {
        "username": "restt",
        "display_name": "restt",
        "twitch_url": "https://www.twitch.tv/restt",
        "region": "Western Europe",
        "language": "sk",
        "avg_viewers": 4000,
        "followers": 62000,
        "content_style": "FPL, рейтинг",
        "clip_potential": 7.5,
        "description": "Центральноевропейский CS2 стример — механически сильный, клатч-моменты",
    },
    {
        "username": "rybsonlol",
        "display_name": "rybsonlol",
        "twitch_url": "https://www.twitch.tv/rybsonlol",
        "region": "Western Europe",
        "language": "pl",
        "avg_viewers": 9000,
        "followers": 89000,
        "content_style": "FPL, развлекательный стрим",
        "clip_potential": 8.0,
        "description": "Польский CS2 стример — высокий пик зрителей, эмоциональные реакции",
    },
]


# ─── Clipping Pipeline Configuration ───────────────────────────────
CLIPPING_PIPELINE = {
    "auto_detection": {
        "enabled": True,
        "description": "Автоматическое определение ключевых моментов из стримов",
        "triggers": {
            "kill_feed_spike": {
                "description": "Серия киллов за короткое время (3+ за 10 сек)",
                "weight": 0.9,
                "min_kills": 3,
                "time_window_sec": 10,
            },
            "audio_peak": {
                "description": "Пик громкости голоса стримера (крик, эмоция)",
                "weight": 0.85,
                "threshold_db": -10,
            },
            "chat_spike": {
                "description": "Резкий скачок сообщений в чате (вирусный момент)",
                "weight": 0.8,
                "messages_per_sec": 50,
            },
            "round_win_clutch": {
                "description": "Выигранный клатч (1vN ситуация)",
                "weight": 0.95,
                "min_enemies": 2,
            },
            "ace_detection": {
                "description": "ACE — 5 киллов одним игроком в раунде",
                "weight": 1.0,
            },
        },
    },
    "clip_settings": {
        "default_duration_sec": 30,
        "pre_moment_buffer_sec": 5,
        "post_moment_buffer_sec": 10,
        "max_clip_duration_sec": 60,
        "min_clip_duration_sec": 10,
        "output_formats": {
            "youtube_shorts": {"aspect_ratio": "9:16", "max_duration": 60, "resolution": "1080x1920"},
            "instagram_reels": {"aspect_ratio": "9:16", "max_duration": 90, "resolution": "1080x1920"},
            "tiktok": {"aspect_ratio": "9:16", "max_duration": 60, "resolution": "1080x1920"},
        },
    },
    "post_processing": {
        "add_subtitles": {"enabled": True, "model": "whisper-large-v3", "languages": ["en", "pt", "tr"]},
        "add_ai_girl_reaction": {"enabled": False, "trigger": "high_score_moments", "min_score": 0.8},
        "add_music": {"enabled": True, "style": "dramatic_beat_drop", "volume_mix": 0.3},
        "add_hook_text": {"enabled": True, "position": "top", "duration_sec": 3},
        "add_cta": {"enabled": True, "position": "bottom", "text": "Подпишись!", "duration_sec": 5},
        "color_grade": {"enabled": True, "preset": "cinematic_gaming"},
    },
    "publishing": {
        "auto_publish": False,
        "schedule_optimal_time": True,
        "platforms": ["instagram", "youtube_shorts"],
        "a_b_test_before_publish": True,
        "generate_variants": 3,
    },
}


# ─── Twitch Streamer Discovery (MUST come before /{stream_id}) ─────

@router.get("/twitch/top-streamers")
async def get_top_cs2_streamers(
    region: str | None = None,
    sort_by: str = "clip_potential",
    limit: int = 20,
):
    """Get ranked list of top CS2 Twitch streamers for content creation."""
    streamers = TOP_CS2_STREAMERS[:]

    if region:
        streamers = [s for s in streamers if s["region"].lower() == region.lower()]

    valid_sorts = {"clip_potential", "avg_viewers", "followers"}
    key = sort_by if sort_by in valid_sorts else "clip_potential"
    streamers.sort(key=lambda s: s[key], reverse=True)

    return {
        "total": len(streamers),
        "streamers": streamers[:limit],
        "regions_available": sorted({s["region"] for s in TOP_CS2_STREAMERS}),
        "recommendation": "Приоритет: ESLCS/BLASTPremier (турниры = максимум хайлайтов), "
                          "gaules/yuurih (LATAM — низкая конкуренция), "
                          "s1mple/donk (CIS звёзды — глобальный аппил)",
    }


@router.get("/twitch/clipping-pipeline")
async def get_clipping_pipeline():
    """Get the auto-clipping pipeline configuration."""
    return CLIPPING_PIPELINE


@router.post("/twitch/add-streamer")
async def add_streamer_to_tracking(
    username: str,
    twitch_url: str | None = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Add a Twitch streamer to tracking — creates a pending stream entry."""
    url = twitch_url or f"https://www.twitch.tv/{username}"
    cursor = await db.execute(
        """INSERT INTO streams (title, platform, url, streamer_name, status)
           VALUES (?, 'twitch', ?, ?, 'pending')""",
        (f"CS2 Стрим — {username}", url, username),
    )
    await db.commit()
    stream_id = cursor.lastrowid
    cursor = await db.execute("SELECT * FROM streams WHERE id = ?", (stream_id,))
    row = await cursor.fetchone()
    return {"added": True, "stream": dict(row)}


@router.get("/twitch/streamer-stats")
async def get_streamer_stats(
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get aggregate stats per streamer from tracked streams."""
    cursor = await db.execute(
        """SELECT s.streamer_name, s.url, COUNT(DISTINCT s.id) as total_streams,
                  COUNT(m.id) as total_moments,
                  COALESCE(AVG(m.score), 0) as avg_moment_score,
                  MAX(m.score) as best_moment_score,
                  s.status as last_status
           FROM streams s
           LEFT JOIN moments m ON m.stream_id = s.id
           GROUP BY s.streamer_name
           ORDER BY total_moments DESC"""
    )
    rows = await cursor.fetchall()
    stats = []
    for row in rows:
        d = dict(row)
        d["twitch_url"] = d.pop("url", None) or f"https://www.twitch.tv/{d['streamer_name']}"
        d["avg_moment_score"] = round(d["avg_moment_score"], 3)
        # Find matching info from TOP_CS2_STREAMERS
        match = next((s for s in TOP_CS2_STREAMERS if s["username"] == d["streamer_name"]), None)
        if match:
            d["region"] = match["region"]
            d["language"] = match["language"]
            d["clip_potential"] = match["clip_potential"]
            d["followers"] = match["followers"]
        stats.append(d)
    return {"streamers": stats}


# ─── Core CRUD Endpoints ───────────────────────────────────────────

@router.get("", response_model=list[StreamResponse])
async def list_streams(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: aiosqlite.Connection = Depends(get_db),
):
    if status:
        cursor = await db.execute(
            "SELECT * FROM streams WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (status, limit, offset),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM streams ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.post("", response_model=StreamResponse)
async def create_stream(
    stream: StreamCreate,
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute(
        """INSERT INTO streams (title, platform, url, streamer_name, started_at, ended_at, status)
           VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
        (stream.title, stream.platform, stream.url, stream.streamer_name, stream.started_at, stream.ended_at),
    )
    await db.commit()
    stream_id = cursor.lastrowid
    cursor = await db.execute("SELECT * FROM streams WHERE id = ?", (stream_id,))
    row = await cursor.fetchone()
    return dict(row)


@router.get("/{stream_id}", response_model=StreamResponse)
async def get_stream(
    stream_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute("SELECT * FROM streams WHERE id = ?", (stream_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Stream not found")
    return dict(row)
