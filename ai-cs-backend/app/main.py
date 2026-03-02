from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.database import init_db
from app.routers import streams, moments, templates, clips, ab_tests, trends, analytics_router, ai_girl, ai_profiles, tool_registry, accounts, generation, clip_executor_router, montage_router, pipeline_router


@asynccontextmanager
async def lifespan(application: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="AI CS Viral Content Engine",
    description="Autonomous AI media engine for CS2 streamer content",
    version="1.0.0",
    lifespan=lifespan,
)

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include all routers
app.include_router(streams.router)
app.include_router(moments.router)
app.include_router(templates.router)
app.include_router(clips.router)
app.include_router(ab_tests.router)
app.include_router(trends.router)
app.include_router(analytics_router.router)
app.include_router(ai_girl.router)
app.include_router(ai_profiles.router)
app.include_router(tool_registry.router)
app.include_router(accounts.router)
app.include_router(generation.router)
app.include_router(clip_executor_router.router)
app.include_router(montage_router.router)
app.include_router(pipeline_router.router)

# Serve static files (demo reels, generated content)
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/api/reseed")
async def reseed_data():
    """Clear all data and reseed with Russian demo data."""
    import aiosqlite
    from app.database import DB_PATH

    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL")

    # Clear all existing data
    for table in ["clips", "ab_tests", "moments", "streams", "trends", "region_analysis"]:
        await db.execute(f"DELETE FROM {table}")

    await db.commit()
    await db.close()

    # Re-seed region_analysis
    import json as _json
    from app.services.ai_profile_generator import REGION_ANALYSIS_DATA
    db2 = await aiosqlite.connect(DB_PATH)
    await db2.execute("PRAGMA journal_mode=WAL")
    for region in REGION_ANALYSIS_DATA:
        await db2.execute(
            """INSERT INTO region_analysis (region, platform, audience_size, competition_level,
               avg_views_per_reel, top_languages, top_content_types, growth_potential, recommendation)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                region["region"], region["platform"], region["audience_size"],
                region["competition_level"], region["avg_views_per_reel"],
                _json.dumps(region["top_languages"]), _json.dumps(region["top_content_types"]),
                region["growth_potential"], region["recommendation"],
            ),
        )
    await db2.commit()
    await db2.close()

    # Now reseed with Russian data
    result = await seed_demo_data()
    return {"cleared": True, "reseeded": result}


@app.post("/api/seed-demo-data")
async def seed_demo_data():
    """Seed database with demo data for testing."""
    import json
    import random
    import aiosqlite
    from app.database import DB_PATH

    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")

    # Create demo streams — real CS2 Twitch streamers
    demo_streams = [
        ("CS2 FPL Grind — Ночной рейтинг", "twitch", "https://www.twitch.tv/gaules", "gaules", "2026-02-27T20:00:00", "2026-02-28T02:00:00"),
        ("CS2 Ranked Session #128", "twitch", "https://www.twitch.tv/s1mple", "s1mple", "2026-02-27T18:00:00", "2026-02-27T23:30:00"),
        ("CS2 Pro Matches Watch Party", "twitch", "https://www.twitch.tv/shroud", "shroud", "2026-02-26T16:00:00", "2026-02-26T22:00:00"),
        ("CS2 Premier Mode — Road to 30K", "twitch", "https://www.twitch.tv/donk_cs", "donk", "2026-02-26T19:00:00", "2026-02-27T01:00:00"),
        ("CS2 Турнирный стрим IEM", "twitch", "https://www.twitch.tv/eaboriginal", "El1an", "2026-02-25T14:00:00", "2026-02-25T20:00:00"),
        ("CS2 FPL с комментариями", "twitch", "https://www.twitch.tv/forg1", "forg1", "2026-02-25T21:00:00", "2026-02-26T03:00:00"),
        ("CS2 Ranked LATAM — Rumo ao Global", "twitch", "https://www.twitch.tv/yuurih", "yuurih", "2026-02-24T22:00:00", "2026-02-25T04:00:00"),
        ("CS2 Night Session — Premier", "twitch", "https://www.twitch.tv/ohnePixel", "ohnePixel", "2026-02-24T20:00:00", "2026-02-25T02:00:00"),
    ]
    stream_ids = []
    for s in demo_streams:
        cursor = await db.execute(
            "INSERT INTO streams (title, platform, url, streamer_name, started_at, ended_at, status) VALUES (?, ?, ?, ?, ?, ?, 'analyzed')",
            s,
        )
        stream_ids.append(cursor.lastrowid)

    # Create demo moments
    moment_types = ["clutch", "ace", "multi_kill", "headshot_sequence", "emotional_reaction", "toxic_moment", "meme_fail"]
    moment_type_names_ru = {
        "clutch": "Клатч",
        "ace": "Эйс",
        "multi_kill": "Мульти-килл",
        "headshot_sequence": "Серия хедшотов",
        "emotional_reaction": "Эмоциональная реакция",
        "toxic_moment": "Токсичный момент",
        "meme_fail": "Фейл/мем",
    }
    moment_ids = []
    for sid in stream_ids:
        ts = 0.0
        for _ in range(random.randint(4, 8)):
            mtype = random.choice(moment_types)
            ts += random.uniform(60, 300)
            dur = random.uniform(10, 40)
            score = round(random.uniform(0.5, 1.0), 3)
            map_name = random.choice(["Dust2", "Mirage", "Inferno", "Nuke", "Ancient"])
            metadata = json.dumps({
                "weapon": random.choice(["AK-47", "M4A1-S", "AWP", "Deagle"]),
                "map": map_name,
                "kills": random.randint(1, 5),
            })
            desc_ru = f"{moment_type_names_ru.get(mtype, mtype)} на {map_name}"
            cursor = await db.execute(
                "INSERT INTO moments (stream_id, moment_type, timestamp_start, timestamp_end, score, description, metadata, status) VALUES (?, ?, ?, ?, ?, ?, ?, 'detected')",
                (sid, mtype, round(ts, 2), round(ts + dur, 2), score, desc_ru, metadata),
            )
            moment_ids.append(cursor.lastrowid)

    # Create demo clips with metrics
    formats = ["clean_highlight", "highlight_reaction", "highlight_subtitles", "highlight_ai_girl",
               "meme_format", "dramatic_clutch", "provocative", "hard_fragmovie", "fail_format"]
    format_names_ru = {
        "clean_highlight": "Чистый хайлайт",
        "highlight_reaction": "Хайлайт + реакция",
        "highlight_subtitles": "Хайлайт + субтитры",
        "highlight_ai_girl": "Хайлайт + AI девушка",
        "meme_format": "Мем-формат",
        "dramatic_clutch": "Драматичный клатч",
        "provocative": "Провокация",
        "hard_fragmovie": "Жёсткий фрагмуви",
        "fail_format": "Фейл-формат",
    }
    clip_platforms = ["youtube", "tiktok", "instagram"]

    for mid in moment_ids[:10]:
        cursor = await db.execute(
            "INSERT INTO ab_tests (name, moment_id, status) VALUES (?, ?, ?)",
            (f"A/B Тест момент #{mid}", mid, random.choice(["running", "completed"])),
        )
        ab_id = cursor.lastrowid

        for fmt in random.sample(formats, k=random.randint(3, 6)):
            views = random.randint(500, 500000)
            cursor = await db.execute(
                """INSERT INTO clips (moment_id, template_id, ab_test_id, title, format_type, duration, status,
                   hook_text, cta_text, has_ai_girl, has_subtitles, has_face_cam, platform,
                   views, likes, comments, shares, ctr, retention_rate, watch_through_rate, published_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'published', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
                (
                    mid, None, ab_id,
                    f"Топовый {format_names_ru.get(fmt, fmt)} момент",
                    fmt, round(random.uniform(12, 60), 1),
                    random.choice(["Сможет ли он клатч?", "Это должно быть ЗАПРЕЩЕНО", "Смотри до конца...", "POV: ты невероятен"]),
                    random.choice(["Подпишись!", "Он СЕЙЧАС в эфире!", "Больше клипов →"]),
                    1 if "ai_girl" in fmt else 0,
                    1 if "subtitles" in fmt or random.random() > 0.5 else 0,
                    1 if "reaction" in fmt else 0,
                    random.choice(clip_platforms),
                    views,
                    int(views * random.uniform(0.02, 0.15)),
                    int(views * random.uniform(0.005, 0.05)),
                    int(views * random.uniform(0.001, 0.02)),
                    round(random.uniform(2.0, 15.0), 2),
                    round(random.uniform(20.0, 85.0), 2),
                    round(random.uniform(15.0, 70.0), 2),
                ),
            )

    # Create demo trends
    trend_data = [
        ("youtube", "format", "Компиляции клатчей 1v5", "Подборки лучших клатчей 1 против 5 с драматичной музыкой, тренд на YT Shorts", 9.2),
        ("youtube", "moment", "AWP Флик Монтаж", "Монтажи флик-шотов с AWP под бит-дропы", 8.5),
        ("tiktok", "format", "Скоростной монтаж хайлайтов", "Ультра-быстрые нарезки с бит-дропами", 9.5),
        ("tiktok", "style", "AI Комментарий Оверлей", "AI-девушка комментирует моменты поверх геймплея", 8.3),
        ("instagram", "format", "Чистые хайлайт рилсы", "Минималистичные нарезки без лишнего, фокус на геймплее", 8.8),
        ("instagram", "moment", "Эмоциональные реакции", "Клипы с яркими эмоциями стримера в кульминации", 8.5),
        ("youtube", "hook", "Провокационные хуки-вопросы", "Заголовки-вопросы для максимального CTR", 7.8),
        ("tiktok", "format", "Из фейла в клатч", "Нарратив от провала к эпическому камбэку", 7.9),
    ]
    for t in trend_data:
        await db.execute(
            "INSERT INTO trends (platform, trend_type, title, description, score, metadata, is_active) VALUES (?, ?, ?, ?, ?, ?, 1)",
            (t[0], t[1], t[2], t[3], t[4], json.dumps({"categories": ["cs2"], "avg_video_length": round(random.uniform(15, 45), 1)})),
        )

    await db.commit()
    await db.close()

    return {
        "seeded": True,
        "streams": len(demo_streams),
        "moments": len(moment_ids),
        "clips": "multiple per moment",
        "trends": len(trend_data),
    }
