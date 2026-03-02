from contextlib import asynccontextmanager
from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.database import init_db
from app.routers import streams, moments, templates, clips, ab_tests, trends, analytics_router, ai_girl, ai_profiles, tool_registry, accounts, generation, clip_executor_router, montage_router, pipeline_router, dual_source_router

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CS2 Reels cleanup — delete files older than 7 days
# ---------------------------------------------------------------------------
CS2_CLIPS_DIRS = [
    Path("/root/projects/ai-cs-backend/clips"),
    Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "clips")),
    Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")),
]
CS2_REEL_EXTENSIONS = {".mp4", ".webm", ".mkv", ".avi", ".mov"}
CLEANUP_MAX_AGE_DAYS = 7


def _cleanup_cs2_reels_sync() -> dict:
    """Scan CS2 clips directories and delete video files older than 7 days.
    Returns summary of cleanup actions."""
    cutoff = time.time() - (CLEANUP_MAX_AGE_DAYS * 86400)
    deleted = []
    errors = []
    scanned = 0

    for clips_dir in CS2_CLIPS_DIRS:
        if not clips_dir.exists():
            continue
        for f in clips_dir.rglob("*"):
            if not f.is_file():
                continue
            if f.suffix.lower() not in CS2_REEL_EXTENSIONS:
                continue
            scanned += 1
            try:
                mtime = f.stat().st_mtime
                if mtime < cutoff:
                    size = f.stat().st_size
                    f.unlink()
                    deleted.append({"path": str(f), "size_bytes": size, "age_days": round((time.time() - mtime) / 86400, 1)})
                    logger.info("CS2 cleanup: deleted %s (%.1f days old)", f, (time.time() - mtime) / 86400)
            except Exception as exc:
                errors.append({"path": str(f), "error": str(exc)})

    total_freed = sum(d["size_bytes"] for d in deleted)
    return {
        "scanned": scanned,
        "deleted_count": len(deleted),
        "freed_bytes": total_freed,
        "freed_human": f"{total_freed / (1024*1024):.1f} MB" if total_freed > 0 else "0 B",
        "errors": errors,
        "deleted_files": deleted,
    }


async def _cleanup_loop():
    """Background task: run CS2 reels cleanup every 24 hours."""
    while True:
        try:
            result = _cleanup_cs2_reels_sync()
            logger.info(
                "CS2 cleanup cycle: scanned=%d, deleted=%d, freed=%s",
                result["scanned"], result["deleted_count"], result["freed_human"],
            )
        except Exception as exc:
            logger.exception("CS2 cleanup error: %s", exc)
        await asyncio.sleep(86400)  # 24 hours


@asynccontextmanager
async def lifespan(application: FastAPI):
    await init_db()
    # Start background CS2 reels cleanup
    cleanup_task = asyncio.create_task(_cleanup_loop())
    logger.info("CS2 reels cleanup task started (TTL=%d days)", CLEANUP_MAX_AGE_DAYS)
    yield
    cleanup_task.cancel()


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
app.include_router(dual_source_router.router)

# Serve static files (demo reels, generated content)
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Storage management endpoints
# ---------------------------------------------------------------------------
@app.get("/api/storage")
async def get_storage_overview():
    """Overall server storage status + CS2 clips breakdown."""
    import shutil

    # Disk usage
    total, used, free = shutil.disk_usage("/")

    # CS2 clips stats
    cs2_total = 0
    cs2_files = 0
    cs2_oldest = None
    now = time.time()
    for clips_dir in CS2_CLIPS_DIRS:
        if not clips_dir.exists():
            continue
        for f in clips_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() in CS2_REEL_EXTENSIONS:
                cs2_files += 1
                cs2_total += f.stat().st_size
                age = (now - f.stat().st_mtime) / 86400
                if cs2_oldest is None or age > cs2_oldest:
                    cs2_oldest = age

    def _fmt(b: int) -> str:
        if b < 1024:
            return f"{b} B"
        if b < 1024 * 1024:
            return f"{b / 1024:.1f} KB"
        if b < 1024 * 1024 * 1024:
            return f"{b / (1024 * 1024):.1f} MB"
        return f"{b / (1024 * 1024 * 1024):.2f} GB"

    return {
        "disk": {
            "total": _fmt(total),
            "used": _fmt(used),
            "free": _fmt(free),
            "used_pct": round(used / total * 100, 1),
        },
        "cs2_reels": {
            "files": cs2_files,
            "total_size": _fmt(cs2_total),
            "total_bytes": cs2_total,
            "oldest_days": round(cs2_oldest, 1) if cs2_oldest else 0,
            "ttl_days": CLEANUP_MAX_AGE_DAYS,
            "policy": "auto-delete after 7 days",
        },
        "ai_girl_content": {
            "policy": "permanent — never auto-deleted",
            "note": "Per-profile storage visible at GET /api/ai-profiles/ and GET /api/ai-profiles/{id}",
        },
    }


@app.post("/api/storage/cleanup-cs2")
async def run_cs2_cleanup():
    """Manually trigger CS2 reels cleanup (delete files > 7 days)."""
    result = _cleanup_cs2_reels_sync()
    return result


@app.post("/api/reseed")
async def reseed_data():
    """Clear all data and reseed with Russian demo data."""
    import aiosqlite
    from app.database import DB_PATH

    db = await aiosqlite.connect(DB_PATH)
    try:
        await db.execute("PRAGMA journal_mode=WAL")

        # Clear all existing data
        for table in ["clips", "ab_tests", "moments", "streams", "trends", "region_analysis"]:
            await db.execute(f"DELETE FROM {table}")

        await db.commit()
    finally:
        await db.close()

    # Re-seed region_analysis
    import json as _json
    from app.services.ai_profile_generator import REGION_ANALYSIS_DATA
    db2 = await aiosqlite.connect(DB_PATH)
    try:
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
    finally:
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
    try:
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
    finally:
        await db.close()

    return {
        "seeded": True,
        "streams": len(demo_streams),
        "moments": len(moment_ids),
        "clips": "multiple per moment",
        "trends": len(trend_data),
    }
