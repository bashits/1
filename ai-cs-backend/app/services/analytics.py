"""
Analytics & Auto-adaptation Service
Tracks metrics, identifies winning formats, adjusts strategy.
"""
import json
import random
from datetime import datetime, timedelta


PHASE_CONFIG = {
    1: {"name": "max_testing", "label": "Максимальное тестирование", "min_clips": 0, "description": "Тестируем все форматы на максимальных объёмах"},
    2: {"name": "focus_top", "label": "Фокус на топ-2–3 формата", "min_clips": 50, "description": "Удваиваем ставку на лучшие форматы"},
    3: {"name": "scale", "label": "Масштабирование", "min_clips": 150, "description": "Масштабируем лучшие форматы на все платформы"},
    4: {"name": "branding", "label": "Брендинг", "min_clips": 500, "description": "Строим узнаваемый бренд и стиль"},
    5: {"name": "ad_integration", "label": "Интеграция рекламы", "min_clips": 1000, "description": "Интегрируем рекламу и спонсорство"},
}


async def get_overview(db) -> dict:
    """Get analytics dashboard overview."""
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt, COALESCE(SUM(views),0) as views, COALESCE(SUM(likes),0) as likes, "
        "COALESCE(SUM(comments),0) as comments, COALESCE(AVG(retention_rate),0) as avg_ret, "
        "COALESCE(AVG(ctr),0) as avg_ctr, COALESCE(AVG(watch_through_rate),0) as avg_wt "
        "FROM clips"
    )
    stats = await cursor.fetchone()

    cursor = await db.execute("SELECT COUNT(*) as cnt FROM ab_tests WHERE status = 'running'")
    ab_row = await cursor.fetchone()

    cursor = await db.execute("SELECT COUNT(*) as cnt FROM trends WHERE is_active = 1")
    trends_row = await cursor.fetchone()

    cursor = await db.execute("SELECT current_phase FROM strategy LIMIT 1")
    phase_row = await cursor.fetchone()

    # Top format by average score
    cursor = await db.execute(
        """SELECT format_type, AVG(retention_rate * 0.4 + ctr * 0.3 + watch_through_rate * 0.3) as score
           FROM clips WHERE views > 0 GROUP BY format_type ORDER BY score DESC LIMIT 1"""
    )
    top_fmt = await cursor.fetchone()

    # This week stats
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    cursor = await db.execute(
        "SELECT COUNT(*) as cnt, COALESCE(SUM(views),0) as views FROM clips WHERE created_at >= ?",
        (week_ago,),
    )
    week_row = await cursor.fetchone()

    return {
        "total_clips": stats["cnt"],
        "total_views": stats["views"],
        "total_likes": stats["likes"],
        "total_comments": stats["comments"],
        "avg_retention": round(stats["avg_ret"], 2),
        "avg_ctr": round(stats["avg_ctr"], 2),
        "avg_watch_through": round(stats["avg_wt"], 2),
        "active_ab_tests": ab_row["cnt"],
        "active_trends": trends_row["cnt"],
        "top_format": top_fmt["format_type"] if top_fmt else None,
        "current_phase": phase_row["current_phase"] if phase_row else 1,
        "clips_this_week": week_row["cnt"],
        "views_this_week": week_row["views"],
    }


async def get_format_performance(db) -> list[dict]:
    """Get performance metrics broken down by format type."""
    cursor = await db.execute(
        """SELECT format_type,
           COUNT(*) as total_clips,
           COALESCE(SUM(views),0) as total_views,
           COALESCE(AVG(ctr),0) as avg_ctr,
           COALESCE(AVG(retention_rate),0) as avg_retention,
           COALESCE(AVG(watch_through_rate),0) as avg_watch_through,
           COALESCE(AVG(comments),0) as avg_comments
           FROM clips
           GROUP BY format_type
           ORDER BY total_views DESC"""
    )
    rows = await cursor.fetchall()

    # Get previous period data for real trend comparison
    week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
    two_weeks_ago = (datetime.utcnow() - timedelta(days=14)).isoformat()

    prev_cursor = await db.execute(
        """SELECT format_type,
           COALESCE(AVG(retention_rate),0) as avg_retention,
           COALESCE(AVG(ctr),0) as avg_ctr,
           COALESCE(AVG(watch_through_rate),0) as avg_watch_through,
           COALESCE(AVG(comments),0) as avg_comments,
           COALESCE(SUM(views),0) as total_views
           FROM clips
           WHERE created_at >= ? AND created_at < ?
           GROUP BY format_type""",
        (two_weeks_ago, week_ago),
    )
    prev_rows = await prev_cursor.fetchall()
    prev_data = {r["format_type"]: dict(r) for r in prev_rows}

    results = []
    for row in rows:
        score = round(
            row["avg_retention"] * 0.35
            + row["avg_ctr"] * 0.25
            + row["avg_watch_through"] * 0.25
            + (row["avg_comments"] / max(row["total_views"], 1)) * 100 * 0.15,
            2,
        )

        # Determine trend by comparing current score with previous period
        prev = prev_data.get(row["format_type"])
        if prev:
            prev_score = round(
                prev["avg_retention"] * 0.35
                + prev["avg_ctr"] * 0.25
                + prev["avg_watch_through"] * 0.25
                + (prev["avg_comments"] / max(prev["total_views"], 1)) * 100 * 0.15,
                2,
            )
            diff = score - prev_score
            if diff > 0.5:
                trend = "up"
            elif diff < -0.5:
                trend = "down"
            else:
                trend = "stable"
        else:
            # No previous data — treat as new/stable
            trend = "new" if row["total_clips"] <= 5 else "stable"

        results.append({
            "format_type": row["format_type"],
            "total_clips": row["total_clips"],
            "total_views": row["total_views"],
            "avg_ctr": round(row["avg_ctr"], 2),
            "avg_retention": round(row["avg_retention"], 2),
            "avg_watch_through": round(row["avg_watch_through"], 2),
            "avg_comments": round(row["avg_comments"], 1),
            "score": score,
            "trend": trend,
        })

    return results


async def auto_adapt_weights(db) -> dict:
    """
    Automatically adjust template weights based on performance.
    Winners get higher weight, losers get lower.
    """
    format_perf = await get_format_performance(db)
    if not format_perf:
        return {"adapted": False, "reason": "No performance data"}

    # Calculate scores and normalize
    max_score = max(f["score"] for f in format_perf) if format_perf else 1
    min_score = min(f["score"] for f in format_perf) if format_perf else 0
    score_range = max_score - min_score if max_score != min_score else 1

    changes = []
    for fmt in format_perf:
        normalized = (fmt["score"] - min_score) / score_range
        new_weight = round(0.5 + normalized * 1.5, 2)  # Weight range: 0.5 to 2.0

        await db.execute(
            "UPDATE templates SET weight = ?, updated_at = datetime('now') WHERE format_type = ?",
            (new_weight, fmt["format_type"]),
        )
        changes.append({
            "format_type": fmt["format_type"],
            "new_weight": new_weight,
            "score": fmt["score"],
        })

    await db.commit()
    return {"adapted": True, "changes": changes}


async def get_strategy_recommendations(db) -> list[str]:
    """Generate strategic recommendations based on current data."""
    overview = await get_overview(db)
    format_perf = await get_format_performance(db)

    recommendations = []
    phase = overview["current_phase"]

    if phase == 1:
        recommendations.append("Фаза 1: Генерируем максимум вариантов клипов, тестируем все форматы")
        recommendations.append("Используйте все 9 шаблонов для каждого хайлайт-момента")
        recommendations.append("Публикуйте минимум 3 клипа в день на всех платформах")
        if overview["total_clips"] >= PHASE_CONFIG[2]["min_clips"]:
            recommendations.append("⬆️ Можно переходить к Фазе 2 — достаточно данных для выбора форматов")

    elif phase == 2:
        if format_perf:
            top_formats = sorted(format_perf, key=lambda x: x["score"], reverse=True)[:3]
            fmt_names = [f["format_type"] for f in top_formats]
            recommendations.append(f"Фаза 2: Фокус на топ-форматах: {', '.join(fmt_names)}")
            recommendations.append("Увеличьте частоту публикаций побеждающих форматов")
            recommendations.append("Сократите или отключите неэффективные форматы")
        if overview["total_clips"] >= PHASE_CONFIG[3]["min_clips"]:
            recommendations.append("⬆️ Можно переходить к Фазе 3 — готовы к масштабированию")

    elif phase == 3:
        recommendations.append("Фаза 3: Масштабируем лучшие форматы на все платформы одновременно")
        recommendations.append("Кросс-постинг лучших клипов на YouTube, TikTok и Instagram")
        recommendations.append("Поддерживайте стабильный график публикаций")
        if overview["total_clips"] >= PHASE_CONFIG[4]["min_clips"]:
            recommendations.append("⬆️ Можно переходить к Фазе 4 — готовы к брендингу")

    elif phase == 4:
        recommendations.append("Фаза 4: Строим узнаваемый бренд")
        recommendations.append("Стандартизируйте интро/аутро шаблоны")
        recommendations.append("Создайте единый стиль цветокоррекции и оформления")
        recommendations.append("Развивайте вовлечённость через комментарии")
        if overview["total_clips"] >= PHASE_CONFIG[5]["min_clips"]:
            recommendations.append("⬆️ Можно переходить к Фазе 5 — готовы к монетизации")

    elif phase == 5:
        recommendations.append("Фаза 5: Интегрируем рекламу и спонсорство")
        recommendations.append("Подготовьте аналитику для потенциальных спонсоров")
        recommendations.append("A/B тестируйте размещение рекламы в контенте")
        recommendations.append("Сохраняйте органичность при монетизации")

    # FOMO механики
    recommendations.append("🔴 Добавьте FOMO-элементы: 'Он сейчас в эфире!', 'Не пропусти стрим сегодня!'")
    recommendations.append("📊 Отслеживайте онлайн стрима после публикации клипов")

    # Рекомендации по AI-девушке
    cursor = await db.execute("SELECT * FROM ai_girl_config LIMIT 1")
    ai_config = await cursor.fetchone()
    if ai_config:
        if ai_config["avg_retention_with"] > ai_config["avg_retention_without"]:
            recommendations.append("✅ Формат с AI-девушкой показывает лучшее удержание — увеличьте использование")
        elif ai_config["total_clips_with"] < 10:
            recommendations.append("🧪 Нужно больше клипов с AI-девушкой для надёжного сравнения")
        else:
            recommendations.append("⚠️ Формат с AI-девушкой неэффективен — сократите использование")

    return recommendations


async def get_growth_phase(db) -> dict:
    """Get current growth phase details."""
    cursor = await db.execute("SELECT * FROM strategy LIMIT 1")
    row = await cursor.fetchone()
    if not row:
        return {"current_phase": 1, "phase_name": "max_testing", "config": PHASE_CONFIG}

    config = json.loads(row["config"]) if row["config"] else {}
    phase = row["current_phase"]

    return {
        "current_phase": phase,
        "phase_name": row["phase_name"],
        "phase_info": PHASE_CONFIG.get(phase, {}),
        "all_phases": PHASE_CONFIG,
        "started_at": row["started_at"],
        "config": config,
    }


async def update_growth_phase(db, new_phase: int) -> dict:
    """Update the growth phase."""
    if new_phase not in PHASE_CONFIG:
        return {"error": "Invalid phase"}

    phase_info = PHASE_CONFIG[new_phase]
    await db.execute(
        "UPDATE strategy SET current_phase = ?, phase_name = ?, updated_at = datetime('now') WHERE id = 1",
        (new_phase, phase_info["name"]),
    )
    await db.commit()

    return {
        "current_phase": new_phase,
        "phase_name": phase_info["name"],
        "phase_info": phase_info,
    }
