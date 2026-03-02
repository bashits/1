"""Accounts & Region Analysis Router.

Manages platform accounts and provides region analysis
for optimal account strategy (which SIM to buy, which region to target).
"""

import json
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.database import get_db
from app.models.schemas import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    RegionAnalysisResponse,
)
from app.services.ai_profile_generator import REGION_ANALYSIS_DATA

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


# ─── Accounts CRUD ─────────────────────────────────────────────────────

@router.get("/", response_model=list[AccountResponse])
async def list_accounts(
    platform: str | None = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    if platform:
        cursor = await db.execute(
            "SELECT * FROM accounts WHERE platform = ? ORDER BY created_at DESC",
            (platform,),
        )
    else:
        cursor = await db.execute("SELECT * FROM accounts ORDER BY created_at DESC")
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["target_audience"] = json.loads(d["target_audience"]) if isinstance(d["target_audience"], str) else d["target_audience"]
        d["streamer_names"] = json.loads(d["streamer_names"]) if isinstance(d["streamer_names"], str) else d["streamer_names"]
        result.append(d)
    return result


@router.post("/", response_model=AccountResponse)
async def create_account(
    data: AccountCreate,
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute(
        """INSERT INTO accounts (platform, handle, account_type, region, language, target_audience, streamer_names)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            data.platform,
            data.handle,
            data.account_type,
            data.region,
            data.language,
            json.dumps(data.target_audience or {}),
            json.dumps(data.streamer_names or []),
        ),
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM accounts WHERE id = ?", (cursor.lastrowid,))
    row = await cursor.fetchone()
    d = dict(row)
    d["target_audience"] = json.loads(d["target_audience"])
    d["streamer_names"] = json.loads(d["streamer_names"])
    return d


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int,
    update: AccountUpdate,
    db: aiosqlite.Connection = Depends(get_db),
):
    updates = []
    params = []
    if update.handle is not None:
        updates.append("handle = ?")
        params.append(update.handle)
    if update.region is not None:
        updates.append("region = ?")
        params.append(update.region)
    if update.language is not None:
        updates.append("language = ?")
        params.append(update.language)
    if update.target_audience is not None:
        updates.append("target_audience = ?")
        params.append(json.dumps(update.target_audience))
    if update.streamer_names is not None:
        updates.append("streamer_names = ?")
        params.append(json.dumps(update.streamer_names))
    if update.status is not None:
        updates.append("status = ?")
        params.append(update.status)
    if update.total_posts is not None:
        updates.append("total_posts = ?")
        params.append(update.total_posts)
    if update.total_followers is not None:
        updates.append("total_followers = ?")
        params.append(update.total_followers)

    if updates:
        updates.append("updated_at = datetime('now')")
        params.append(account_id)
        await db.execute(
            f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?", params
        )
        await db.commit()

    cursor = await db.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Account not found")
    d = dict(row)
    d["target_audience"] = json.loads(d["target_audience"]) if isinstance(d["target_audience"], str) else d["target_audience"]
    d["streamer_names"] = json.loads(d["streamer_names"]) if isinstance(d["streamer_names"], str) else d["streamer_names"]
    return d


@router.delete("/{account_id}")
async def delete_account(
    account_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    await db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    await db.commit()
    return {"deleted": True}


# ─── Region Analysis ───────────────────────────────────────────────────

@router.get("/regions", response_model=list[RegionAnalysisResponse])
async def list_regions(
    platform: str | None = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    if platform:
        cursor = await db.execute(
            "SELECT * FROM region_analysis WHERE platform = ? ORDER BY growth_potential DESC",
            (platform,),
        )
    else:
        cursor = await db.execute("SELECT * FROM region_analysis ORDER BY growth_potential DESC")
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["top_languages"] = json.loads(d["top_languages"]) if isinstance(d["top_languages"], str) else d["top_languages"]
        d["top_content_types"] = json.loads(d["top_content_types"]) if isinstance(d["top_content_types"], str) else d["top_content_types"]
        result.append(d)
    return result


@router.post("/regions/refresh")
async def refresh_region_analysis(
    db: aiosqlite.Connection = Depends(get_db),
):
    """Collect live data from Twitch/YouTube and refresh region_analysis table.

    Scrapes current viewer counts per region from Twitch CS2 streams,
    estimates competition and growth potential, and updates the DB.
    Returns a simple recommendation table: where to post now.
    """
    from app.services.trend_analyzer import scrape_twitch_cs2_streams, scrape_youtube_cs2_trending

    # Collect live data
    twitch_streams = await scrape_twitch_cs2_streams()
    youtube_videos = await scrape_youtube_cs2_trending()

    # Aggregate viewers per language/region from live Twitch data
    lang_viewers: dict[str, int] = {}
    lang_streams: dict[str, int] = {}
    for s in twitch_streams:
        lang = s.get("language", "en")
        lang_viewers[lang] = lang_viewers.get(lang, 0) + s.get("viewers", 0)
        lang_streams[lang] = lang_streams.get(lang, 0) + 1

    # Map languages to regions
    LANG_REGION = {
        "en": ("Global EN", ["en"], ["highlights", "reactions", "memes"]),
        "ru": ("CIS/Russia", ["ru", "en"], ["highlights", "clutch_edits"]),
        "pt": ("Brazil/LATAM", ["pt", "es"], ["highlights", "reactions", "memes"]),
        "tr": ("Turkey/MENA", ["tr", "en"], ["highlights", "dramatic_clutch"]),
        "de": ("Western Europe", ["de", "en"], ["highlights", "fragmovies"]),
        "fr": ("Western Europe", ["fr", "en"], ["highlights", "reactions"]),
        "es": ("LATAM/Spain", ["es", "pt"], ["highlights", "memes", "reactions"]),
        "ko": ("South Korea", ["ko", "en"], ["highlights", "pro_plays"]),
        "ja": ("Japan", ["ja", "en"], ["highlights", "reactions"]),
        "zh": ("China/SEA", ["zh", "en"], ["highlights", "pro_plays"]),
    }

    # Build region analysis from live data
    regions_data: dict[str, dict] = {}
    for lang, viewers in lang_viewers.items():
        region_name, top_langs, content_types = LANG_REGION.get(
            lang, (f"Other ({lang})", [lang], ["highlights"])
        )
        if region_name not in regions_data:
            regions_data[region_name] = {
                "audience_size": 0,
                "stream_count": 0,
                "top_languages": top_langs,
                "top_content_types": content_types,
            }
        regions_data[region_name]["audience_size"] += viewers
        regions_data[region_name]["stream_count"] += lang_streams.get(lang, 0)

    # Calculate competition & growth potential
    total_viewers = max(sum(r["audience_size"] for r in regions_data.values()), 1)
    youtube_count = len(youtube_videos)

    now = datetime.utcnow().isoformat()
    updated_regions = []

    for region_name, data in regions_data.items():
        audience = data["audience_size"]
        streams = data["stream_count"]
        share = audience / total_viewers

        # Competition: more streams = higher competition
        if streams >= 8:
            competition = "high"
        elif streams >= 3:
            competition = "medium"
        else:
            competition = "low"

        # Growth potential: high audience + low competition = high potential
        if competition == "low" and audience > 1000:
            growth = round(min(1.0, 0.7 + share * 2), 2)
        elif competition == "medium":
            growth = round(min(1.0, 0.4 + share), 2)
        else:
            growth = round(min(1.0, 0.2 + share * 0.5), 2)

        avg_views = int(audience / max(streams, 1) * 0.15)  # estimated reel views

        # Recommendation text
        if growth >= 0.7:
            rec = f"РЕКОМЕНДУЕМ — высокий потенциал роста, {'низкая' if competition == 'low' else 'средняя'} конкуренция"
        elif growth >= 0.4:
            rec = f"Можно пробовать — средний потенциал, {competition} конкуренция"
        else:
            rec = f"Осторожно — {'высокая' if competition == 'high' else competition} конкуренция, рост медленный"

        # Upsert into DB
        for platform in ["instagram", "youtube_shorts"]:
            await db.execute(
                """INSERT INTO region_analysis
                   (region, platform, audience_size, competition_level,
                    avg_views_per_reel, top_languages, top_content_types,
                    growth_potential, recommendation, analyzed_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(region, platform) DO UPDATE SET
                    audience_size = excluded.audience_size,
                    competition_level = excluded.competition_level,
                    avg_views_per_reel = excluded.avg_views_per_reel,
                    growth_potential = excluded.growth_potential,
                    recommendation = excluded.recommendation,
                    analyzed_at = excluded.analyzed_at""",
                (
                    region_name, platform, audience, competition,
                    avg_views, json.dumps(data["top_languages"]),
                    json.dumps(data["top_content_types"]),
                    growth, rec, now,
                ),
            )

        updated_regions.append({
            "region": region_name,
            "audience_size": audience,
            "competition": competition,
            "growth_potential": growth,
            "avg_views_per_reel": avg_views,
            "recommendation": rec,
        })

    await db.commit()

    # Sort by growth potential descending
    updated_regions.sort(key=lambda r: r["growth_potential"], reverse=True)

    return {
        "refreshed": True,
        "analyzed_at": now,
        "data_sources": {
            "twitch_streams": len(twitch_streams),
            "youtube_videos": youtube_count,
            "twitch_source": twitch_streams[0].get("source", "none") if twitch_streams else "none",
        },
        "regions": updated_regions,
        "recommendation_table": {
            "best_to_post_now": updated_regions[:3] if updated_regions else [],
            "total_regions_analyzed": len(updated_regions),
        },
    }


@router.get("/regions/recommendations")
async def get_region_recommendations(
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get top region recommendations for account creation."""
    cursor = await db.execute(
        "SELECT * FROM region_analysis ORDER BY growth_potential DESC LIMIT 5"
    )
    rows = await cursor.fetchall()
    recommendations = []
    for row in rows:
        d = dict(row)
        d["top_languages"] = json.loads(d["top_languages"]) if isinstance(d["top_languages"], str) else d["top_languages"]
        d["top_content_types"] = json.loads(d["top_content_types"]) if isinstance(d["top_content_types"], str) else d["top_content_types"]
        recommendations.append(d)

    return {
        "top_regions": recommendations,
        "strategy": {
            "recommended_accounts": [
                {
                    "platform": "instagram",
                    "type": "cs2_highlights",
                    "region": "Бразилия/LATAM",
                    "language": "pt",
                    "streamers_per_account": 2,
                    "reason": "СКРЫТЫЙ ГЕМ #1: огромная CS2-база (18M), очень низкая конкуренция, 35K ср. просмотры",
                },
                {
                    "platform": "instagram",
                    "type": "cs2_highlights",
                    "region": "Турция/Ближний Восток",
                    "language": "tr",
                    "streamers_per_account": 2,
                    "reason": "СКРЫТЫЙ ГЕМ #2: самая низкая конкуренция, 40K ср. просмотры, страстное CS2-коммьюнити",
                },
                {
                    "platform": "youtube_shorts",
                    "type": "cs2_highlights",
                    "region": "Бразилия/LATAM",
                    "language": "pt",
                    "streamers_per_account": 2,
                    "reason": "YouTube — платформа #1 в Бразилии, CS2-контент собирает 45K ср. просмотры",
                },
                {
                    "platform": "instagram",
                    "type": "ai_girl",
                    "region": "Глобально (EN)",
                    "language": "en",
                    "reason": "AI-девушка на EN охватывает весь мир. Instagram Reels + приват-канал = монетизация",
                },
                {
                    "platform": "youtube_shorts",
                    "type": "cs2_highlights",
                    "region": "Юго-Восточная Азия",
                    "language": "en",
                    "streamers_per_account": 2,
                    "reason": "Растущий рынок, низкая конкуренция, EN-контент работает отлично",
                },
                {
                    "platform": "youtube_shorts",
                    "type": "cs2_highlights",
                    "region": "Западная Европа",
                    "language": "en",
                    "streamers_per_account": 2,
                    "reason": "Крупнейшая EN-аудитория (30M), YouTube Shorts #1 платформа для CS2 в Европе",
                },
            ],
            "sim_card_strategy": {
                "primary_region": "Бразилия / Турция (приоритет — низкая конкуренция)",
                "sim_type": "Виртуальная eSIM или SMS-сервис",
                "services": ["5sim.net", "sms-activate.org", "onlinesim.io"],
                "cost": "$1-5 за номер",
                "note": "Используй разные IP для каждого аккаунта. VPN должен совпадать с регионом SIM. Для LATAM — бразильский IP, для Турции — турецкий.",
            },
            "account_warming": {
                "day_1_3": "Подписаться на 50-100 CS2-аккаунтов целевого региона, лайки/комменты на EN/PT/TR",
                "day_4_7": "2-3 репоста/сторис в день с хештегами целевого региона",
                "day_8_14": "Начинаем оригинальный контент на языке региона, 1 рилс/день",
                "day_15_plus": "Полный график: 2-3 рилса/день, анализ метрик по регионам",
            },
        },
    }


@router.get("/strategy")
async def get_full_strategy():
    """Get complete multi-platform, multi-streamer strategy."""
    return {
        "overview": {
            "platforms": ["instagram", "youtube_shorts"],
            "total_accounts_recommended": 8,
            "streamers_per_account": 2,
            "content_per_day": "2-3 рилса/шортса на аккаунт",
            "total_content_per_day": "16-24 единицы контента",
            "target_markets": "Бразилия/LATAM, Турция/Ближний Восток, Юго-Восточная Азия, Западная Европа, Северная Америка",
            "strategy_focus": "Иностранные рынки — максимальный рост при минимальной конкуренции",
        },
        "account_structure": {
            "instagram": [
                {
                    "name": "CS2 Highlights LATAM",
                    "type": "highlights",
                    "region": "Бразилия/LATAM",
                    "language": "pt",
                    "streamers": 2,
                    "content_types": ["clean_highlight", "highlight_subtitles", "meme_format", "reactions"],
                    "priority": "ВЫСШИЙ — скрытый гем, 35K ср. просмотры, низкая конкуренция",
                },
                {
                    "name": "CS2 Highlights Turkey",
                    "type": "highlights",
                    "region": "Турция/Ближний Восток",
                    "language": "tr",
                    "streamers": 2,
                    "content_types": ["highlights", "reactions", "dramatic_clutch"],
                    "priority": "ВЫСШИЙ — 40K ср. просмотры, самая низкая конкуренция",
                },
                {
                    "name": "AI Girl Global",
                    "type": "ai_girl",
                    "region": "Глобально",
                    "language": "en",
                    "content_types": ["highlight_ai_girl", "instagram_post", "instagram_reel", "private_content"],
                    "monetization": ["приват-канал", "бренд-сделки", "партнёрка"],
                    "priority": "ВЫСОКИЙ — уникальный формат, EN для максимального охвата",
                },
                {
                    "name": "CS2 Highlights EU",
                    "type": "highlights",
                    "region": "Западная Европа",
                    "language": "en",
                    "streamers": 2,
                    "content_types": ["clean_highlight", "provocative", "reactions"],
                    "priority": "СРЕДНИЙ — большая аудитория, но высокая конкуренция",
                },
            ],
            "youtube_shorts": [
                {
                    "name": "CS2 Highlights LATAM",
                    "type": "highlights",
                    "region": "Бразилия/LATAM",
                    "language": "pt",
                    "streamers": 2,
                    "content_types": ["clean_highlight", "highlight_subtitles", "fragmovies"],
                    "priority": "ВЫСШИЙ — YouTube #1 платформа в Бразилии, 45K ср. просмотры",
                },
                {
                    "name": "CS2 Highlights SEA",
                    "type": "highlights",
                    "region": "Юго-Восточная Азия",
                    "language": "en",
                    "streamers": 2,
                    "content_types": ["highlights", "meme_format", "fail_format"],
                    "priority": "ВЫСОКИЙ — растущий рынок, низкая конкуренция, EN работает",
                },
                {
                    "name": "CS2 Highlights EU/NA",
                    "type": "highlights",
                    "region": "Западная Европа / Северная Америка",
                    "language": "en",
                    "streamers": 2,
                    "content_types": ["clean_highlight", "dramatic_clutch", "hard_fragmovie"],
                    "priority": "СРЕДНИЙ — огромный охват, жёсткая конкуренция",
                },
                {
                    "name": "AI Girl Reactions",
                    "type": "ai_girl",
                    "region": "Глобально",
                    "language": "en",
                    "content_types": ["highlight_ai_girl", "reactions"],
                    "priority": "ВЫСОКИЙ — уникальный формат выделяет из конкуренции",
                },
            ],
        },
        "market_analysis": {
            "tier_1_easy_win": {
                "regions": ["Бразилия/LATAM", "Турция/Ближний Восток"],
                "why": "Огромная CS2-аудитория + минимальная конкуренция = быстрый органический рост",
                "languages": ["pt", "tr", "es"],
                "expected_growth": "5-10x быстрее чем в EN-зоне",
            },
            "tier_2_growth": {
                "regions": ["Юго-Восточная Азия"],
                "why": "Растущий CS2-рынок, EN-контент работает, мемы = вирал",
                "languages": ["en"],
                "expected_growth": "3-5x быстрее чем в NA/EU",
            },
            "tier_3_scale": {
                "regions": ["Западная Европа", "Северная Америка"],
                "why": "Максимальный охват и монетизация, но нужен объём для пробива",
                "languages": ["en"],
                "expected_growth": "Стабильный, но конкурентный",
            },
        },
        "content_calendar": {
            "понедельник": {"posts_per_account": 2, "focus": "Лучшие моменты с викендовых стримов → PT/TR/EN версии"},
            "вторник": {"posts_per_account": 3, "focus": "A/B тесты форматов по регионам (LATAM vs Turkey vs SEA)"},
            "среда": {"posts_per_account": 2, "focus": "Трендовые моменты + AI-девушка (EN глобально)"},
            "четверг": {"posts_per_account": 3, "focus": "Максимальный объём — масштабируем лучшие форматы"},
            "пятница": {"posts_per_account": 2, "focus": "Компиляции + хайлайты под каждый рынок"},
            "суббота": {"posts_per_account": 3, "focus": "Клипы с лайв-стримов → мгновенная локализация"},
            "воскресенье": {"posts_per_account": 3, "focus": "Лучшее за неделю + спецвыпуск AI-девушки"},
        },
        "growth_targets": {
            "месяц_1": {"followers_per_account": "500-2000", "views_per_reel": "1K-10K", "focus": "LATAM + Turkey (лёгкий вход)"},
            "месяц_2": {"followers_per_account": "2000-10000", "views_per_reel": "5K-50K", "focus": "+ SEA + AI Girl Global"},
            "месяц_3": {"followers_per_account": "10000-50000", "views_per_reel": "10K-100K", "focus": "+ EU/NA (масштабирование)"},
            "месяц_6": {"followers_per_account": "50000+", "views_per_reel": "50K-500K", "focus": "Все рынки, монетизация"},
        },
    }
