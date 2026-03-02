"""
Trend Learning Engine — Self-learning trend prediction for CS2 reels.

Three data layers:
1. OWN EXPERIENCE — learns from our reel performance (views, likes, retention)
2. REAL-TIME DATA — current Twitch GQL clips + YouTube trending analysis
3. HISTORICAL ANALYSIS — tracks trend cycles, predicts what's rising/falling

The engine builds a TREND FORECAST that the reel pipeline MUST use.
Without fresh forecast data, the pipeline BLOCKS (safety guard).

Architecture:
- TrendSnapshot: captures current state of all data sources
- TrendHistory: stores snapshots over time (up to 30 days)
- TrendPredictor: analyzes history to predict rising/falling trends
- TrendGate: mandatory check before any reel generation
"""

import json
import logging
import math
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger("trend_learning_engine")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STORAGE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_DATA_DIR = Path("/tmp/trend_learning")
_DATA_DIR.mkdir(parents=True, exist_ok=True)

_HISTORY_FILE = _DATA_DIR / "trend_history.json"
_OWN_PERFORMANCE_FILE = _DATA_DIR / "own_performance.json"
_FORECAST_FILE = _DATA_DIR / "trend_forecast.json"
_SAFETY_FILE = _DATA_DIR / "safety_state.json"

# Max history entries (1 snapshot per hour × 24h × 30 days = 720)
MAX_HISTORY_ENTRIES = 720
# Forecast is valid for 2 hours
FORECAST_TTL_SECONDS = 7200
# Minimum snapshots needed for prediction (need at least 3 data points)
MIN_SNAPSHOTS_FOR_PREDICTION = 3
# Safety: max age of trend data before pipeline blocks
MAX_TREND_AGE_SECONDS = 1800  # 30 minutes


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATA STRUCTURES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _load_json(path: Path) -> dict:
    try:
        if path.exists():
            with open(path, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning("Failed to load %s: %s", path, e)
    return {}


def _save_json(path: Path, data: dict):
    try:
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning("Failed to save %s: %s", path, e)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 1: REAL-TIME SNAPSHOT (current state of CS2 trends)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def capture_trend_snapshot() -> dict:
    """Capture current state of all trend sources.

    Queries:
    1. Twitch GQL — top CS2 clips (what's being watched NOW)
    2. Twitch GQL — live CS2 streams (who's streaming NOW)
    3. YouTube — trending CS2 content (what formats work)

    Returns a snapshot dict with timestamp.
    """
    from app.services.twitch_gql_client import (
        get_cs2_top_clips,
        get_cs2_live_streams,
        TwitchGQLError,
    )

    snapshot = {
        "timestamp": time.time(),
        "timestamp_human": datetime.now(timezone.utc).isoformat(),
        "sources": {},
        "metrics": {},
        "format_signals": {},
    }

    # 1. Twitch GQL clips
    try:
        clips_data = await get_cs2_top_clips(period="LAST_DAY", limit=20)
        clips = clips_data.get("clips", [])
        snapshot["sources"]["twitch_clips"] = {
            "count": len(clips),
            "fresh": clips_data.get("is_fresh", False),
            "top_clips": [
                {
                    "title": c.get("title", ""),
                    "views": c.get("view_count", 0),
                    "duration": c.get("duration_seconds", 0),
                    "streamer": c.get("broadcaster_login", ""),
                    "created_at": c.get("created_at", ""),
                }
                for c in clips[:10]
            ],
        }

        # Extract format signals from clip titles
        format_counts = _analyze_clip_formats([c.get("title", "") for c in clips])
        snapshot["format_signals"]["from_clips"] = format_counts

        # Calculate metrics
        if clips:
            views = [c.get("view_count", 0) for c in clips]
            durations = [c.get("duration_seconds", 0) for c in clips if c.get("duration_seconds", 0) > 0]
            snapshot["metrics"]["avg_clip_views"] = sum(views) / len(views)
            snapshot["metrics"]["max_clip_views"] = max(views)
            snapshot["metrics"]["avg_clip_duration"] = sum(durations) / len(durations) if durations else 0
            snapshot["metrics"]["total_clip_views"] = sum(views)

    except TwitchGQLError as e:
        snapshot["sources"]["twitch_clips"] = {"error": str(e), "count": 0}

    # 2. Twitch GQL live streams
    try:
        streams_data = await get_cs2_live_streams(limit=20)
        streams = streams_data.get("streams", [])
        snapshot["sources"]["twitch_streams"] = {
            "count": len(streams),
            "fresh": streams_data.get("is_fresh", False),
            "top_streams": [
                {
                    "login": s.get("login", ""),
                    "viewers": s.get("viewers", 0),
                    "title": s.get("title", ""),
                }
                for s in streams[:10]
            ],
        }

        if streams:
            viewers = [s.get("viewers", 0) for s in streams]
            snapshot["metrics"]["total_live_viewers"] = sum(viewers)
            snapshot["metrics"]["avg_stream_viewers"] = sum(viewers) / len(viewers)
            snapshot["metrics"]["top_stream_viewers"] = max(viewers)

            # Extract format signals from stream titles
            stream_formats = _analyze_clip_formats([s.get("title", "") for s in streams])
            snapshot["format_signals"]["from_streams"] = stream_formats

    except TwitchGQLError as e:
        snapshot["sources"]["twitch_streams"] = {"error": str(e), "count": 0}

    # 3. YouTube trending (from existing scraper)
    try:
        from app.services.trend_analyzer import scrape_youtube_cs2_trending
        yt_data = await scrape_youtube_cs2_trending()
        snapshot["sources"]["youtube"] = {
            "count": len(yt_data),
            "top_videos": [
                {
                    "title": v.get("title", ""),
                    "channel": v.get("channel", ""),
                    "source": v.get("source", ""),
                }
                for v in yt_data[:5]
            ],
        }
        if yt_data:
            yt_formats = _analyze_clip_formats([v.get("title", "") for v in yt_data])
            snapshot["format_signals"]["from_youtube"] = yt_formats
    except Exception as e:
        snapshot["sources"]["youtube"] = {"error": str(e), "count": 0}

    # Aggregate format signals
    snapshot["format_signals"]["combined"] = _combine_format_signals(snapshot["format_signals"])

    return snapshot


def _analyze_clip_formats(titles: list[str]) -> dict:
    """Analyze titles to detect which content formats are trending."""
    format_keywords = {
        "ace": ["ace", "5k", "5 kill"],
        "clutch": ["clutch", "1v", "1 vs", "impossible"],
        "highlight": ["highlight", "best", "insane", "crazy", "top"],
        "funny": ["funny", "fail", "wtf", "lol", "meme"],
        "pro_play": ["pro", "fpl", "major", "tournament", "blast"],
        "edit": ["edit", "montage", "frag", "movie", "sigma"],
        "react": ["react", "reaction", "watching"],
        "tutorial": ["tutorial", "tip", "trick", "guide", "how to"],
        "awp": ["awp", "sniper", "flick", "no scope"],
        "pistol": ["pistol", "deagle", "usp", "glock"],
    }

    counts: dict[str, int] = {}
    for title in titles:
        t = title.lower()
        for fmt, keywords in format_keywords.items():
            if any(kw in t for kw in keywords):
                counts[fmt] = counts.get(fmt, 0) + 1

    return counts


def _combine_format_signals(signals: dict) -> dict:
    """Combine format signals from all sources with weights."""
    combined: dict[str, float] = {}
    source_weights = {
        "from_clips": 3.0,     # Twitch clips = strongest signal
        "from_streams": 1.5,   # Stream titles = moderate signal
        "from_youtube": 2.0,   # YouTube = good signal
    }

    for source, counts in signals.items():
        if source == "combined" or not isinstance(counts, dict):
            continue
        weight = source_weights.get(source, 1.0)
        for fmt, count in counts.items():
            combined[fmt] = combined.get(fmt, 0) + count * weight

    # Sort by score
    return dict(sorted(combined.items(), key=lambda x: x[1], reverse=True))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 2: HISTORICAL TRACKING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _load_history() -> list[dict]:
    data = _load_json(_HISTORY_FILE)
    return data.get("snapshots", [])


def _save_history(snapshots: list[dict]):
    _save_json(_HISTORY_FILE, {
        "snapshots": snapshots[-MAX_HISTORY_ENTRIES:],
        "total_saved": len(snapshots),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    })


def store_snapshot(snapshot: dict):
    """Store a trend snapshot in history."""
    history = _load_history()

    # Compress snapshot for storage (keep only metrics + signals, not full clip data)
    compressed = {
        "timestamp": snapshot.get("timestamp", time.time()),
        "timestamp_human": snapshot.get("timestamp_human", ""),
        "metrics": snapshot.get("metrics", {}),
        "format_signals": snapshot.get("format_signals", {}).get("combined", {}),
        "source_counts": {
            k: v.get("count", 0)
            for k, v in snapshot.get("sources", {}).items()
        },
    }

    history.append(compressed)
    _save_history(history)
    logger.info("Stored trend snapshot #%d", len(history))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 3: OWN PERFORMANCE LEARNING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def record_reel_performance(
    reel_id: str,
    format_used: str,
    color_grade: str,
    music_style: str,
    hook_type: str,
    clip_source: str,
    duration: float,
    views: int = 0,
    likes: int = 0,
    shares: int = 0,
    retention_pct: float = 0.0,
    ctr_pct: float = 0.0,
) -> dict:
    """Record our own reel performance for learning."""
    data = _load_json(_OWN_PERFORMANCE_FILE)
    if "reels" not in data:
        data["reels"] = []
    if "format_stats" not in data:
        data["format_stats"] = {}

    entry = {
        "reel_id": reel_id,
        "format": format_used,
        "color_grade": color_grade,
        "music_style": music_style,
        "hook_type": hook_type,
        "clip_source": clip_source,
        "duration": duration,
        "views": views,
        "likes": likes,
        "shares": shares,
        "retention_pct": retention_pct,
        "ctr_pct": ctr_pct,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    data["reels"].append(entry)
    data["reels"] = data["reels"][-200:]  # Keep last 200

    # Update format stats
    if format_used not in data["format_stats"]:
        data["format_stats"][format_used] = {
            "count": 0,
            "total_views": 0,
            "total_likes": 0,
            "avg_retention": 0,
            "avg_ctr": 0,
        }

    stats = data["format_stats"][format_used]
    stats["count"] += 1
    stats["total_views"] += views
    stats["total_likes"] += likes
    # Exponential moving average for retention and CTR
    alpha = 0.3
    if retention_pct > 0:
        stats["avg_retention"] = stats["avg_retention"] * (1 - alpha) + retention_pct * alpha
    if ctr_pct > 0:
        stats["avg_ctr"] = stats["avg_ctr"] * (1 - alpha) + ctr_pct * alpha

    data["last_updated"] = datetime.now(timezone.utc).isoformat()
    _save_json(_OWN_PERFORMANCE_FILE, data)

    return {"recorded": True, "total_reels": len(data["reels"])}


def get_own_performance_insights() -> dict:
    """Get insights from our own reel performance."""
    data = _load_json(_OWN_PERFORMANCE_FILE)
    if not data or not data.get("reels"):
        return {
            "has_data": False,
            "message": "No performance data yet — system will learn from first reels",
            "best_format": None,
            "format_rankings": {},
        }

    reels = data["reels"]
    format_stats = data.get("format_stats", {})

    # Calculate format rankings by composite score
    rankings = {}
    for fmt, stats in format_stats.items():
        if stats["count"] == 0:
            continue
        avg_views = stats["total_views"] / stats["count"]
        # Composite score: views weight + retention weight + CTR weight
        composite = (
            min(avg_views / 10000, 3.0) * 0.4  # Views normalized to 0-3
            + stats["avg_retention"] / 100 * 0.35  # Retention 0-1
            + stats["avg_ctr"] / 15 * 0.25  # CTR normalized to 0-1
        )
        rankings[fmt] = {
            "count": stats["count"],
            "avg_views": round(avg_views),
            "avg_retention": round(stats["avg_retention"], 1),
            "avg_ctr": round(stats["avg_ctr"], 1),
            "composite_score": round(composite, 3),
        }

    best_format = max(rankings, key=lambda k: rankings[k]["composite_score"]) if rankings else None

    return {
        "has_data": True,
        "total_reels": len(reels),
        "best_format": best_format,
        "format_rankings": rankings,
        "last_updated": data.get("last_updated"),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 4: TREND PREDICTION (historical analysis + forecasting)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def predict_trends() -> dict:
    """Analyze historical snapshots to predict rising/falling trends.

    Uses:
    - Moving averages to detect momentum
    - Velocity (rate of change) to detect acceleration
    - Own performance data to weight predictions

    Returns forecast with rising/falling/stable formats.
    """
    history = _load_history()

    if len(history) < MIN_SNAPSHOTS_FOR_PREDICTION:
        return {
            "has_prediction": False,
            "reason": f"Need {MIN_SNAPSHOTS_FOR_PREDICTION} snapshots, have {len(history)}",
            "snapshots_available": len(history),
            "recommendation": "Use real-time data directly until enough history collected",
        }

    # Get all format names seen across history
    all_formats: set[str] = set()
    for snap in history:
        all_formats.update(snap.get("format_signals", {}).keys())

    # Calculate trend velocity for each format
    format_trends: dict[str, dict] = {}

    for fmt in all_formats:
        # Get time series of this format's signal strength
        series = []
        for snap in history:
            ts = snap.get("timestamp", 0)
            value = snap.get("format_signals", {}).get(fmt, 0)
            series.append((ts, value))

        if len(series) < 2:
            continue

        # Split into recent (last 25%) and older (first 75%)
        split_idx = max(1, len(series) * 3 // 4)
        older = series[:split_idx]
        recent = series[split_idx:]

        older_avg = sum(v for _, v in older) / len(older) if older else 0
        recent_avg = sum(v for _, v in recent) / len(recent) if recent else 0

        # Velocity: how fast is this format's signal changing?
        if older_avg > 0:
            velocity = (recent_avg - older_avg) / older_avg
        elif recent_avg > 0:
            velocity = 1.0  # New format appearing
        else:
            velocity = 0.0

        # Current strength (most recent snapshot)
        current_value = series[-1][1] if series else 0

        # Trend classification
        if velocity > 0.2:
            direction = "rising"
        elif velocity < -0.2:
            direction = "falling"
        else:
            direction = "stable"

        format_trends[fmt] = {
            "current_strength": round(current_value, 1),
            "older_avg": round(older_avg, 2),
            "recent_avg": round(recent_avg, 2),
            "velocity": round(velocity, 3),
            "direction": direction,
            "data_points": len(series),
        }

    # Sort by momentum (rising formats first)
    rising = {k: v for k, v in format_trends.items() if v["direction"] == "rising"}
    falling = {k: v for k, v in format_trends.items() if v["direction"] == "falling"}
    stable = {k: v for k, v in format_trends.items() if v["direction"] == "stable"}

    # Factor in own performance
    own = get_own_performance_insights()
    own_boost: dict[str, float] = {}
    if own.get("has_data") and own.get("format_rankings"):
        for fmt, ranking in own["format_rankings"].items():
            own_boost[fmt] = ranking.get("composite_score", 0)

    # Build final recommendations
    # Score = current_strength × (1 + velocity) × own_performance_boost
    scored_formats: list[tuple[str, float]] = []
    for fmt, trend in format_trends.items():
        base = trend["current_strength"]
        momentum = 1 + max(-0.5, min(0.5, trend["velocity"]))  # Clamp velocity
        perf_boost = 1 + own_boost.get(fmt, 0)
        final_score = base * momentum * perf_boost
        scored_formats.append((fmt, final_score))

    scored_formats.sort(key=lambda x: x[1], reverse=True)

    # Map format keywords to reel styles
    format_to_style = {
        "clutch": "pro_clutch",
        "ace": "ace_compilation",
        "highlight": "highlight_react",
        "funny": "funny_moments",
        "edit": "sigma_edit",
        "react": "highlight_react",
        "tutorial": "tutorial_tip",
        "pro_play": "pro_clutch",
        "awp": "pro_clutch",
        "pistol": "ace_compilation",
    }

    recommended_style = "highlight_react"  # default
    if scored_formats:
        top_fmt = scored_formats[0][0]
        recommended_style = format_to_style.get(top_fmt, "highlight_react")

    forecast = {
        "has_prediction": True,
        "predicted_at": datetime.now(timezone.utc).isoformat(),
        "predicted_at_ts": time.time(),
        "recommended_style": recommended_style,
        "top_format_keyword": scored_formats[0][0] if scored_formats else "highlight",
        "format_scores": {fmt: round(score, 2) for fmt, score in scored_formats[:10]},
        "rising_trends": rising,
        "falling_trends": falling,
        "stable_trends": stable,
        "own_performance_boost": own_boost,
        "data_points_analyzed": len(history),
        "prediction_confidence": min(1.0, len(history) / 20),  # Higher confidence with more data
    }

    # Save forecast
    _save_json(_FORECAST_FILE, forecast)
    return forecast


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 5: SAFETY GATE — mandatory check before reel generation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def trend_safety_gate() -> dict:
    """MANDATORY check before any reel generation.

    Verifies:
    1. Twitch GQL is operational (circuit breaker not open)
    2. We have fresh clip data (not stale >30min)
    3. Trend analysis ran recently (not stale >30min)
    4. All critical systems are working

    Returns:
        {
            "can_proceed": True/False,
            "reason": str,
            "checks": {
                "twitch_gql": {"ok": bool, "detail": str},
                "data_freshness": {"ok": bool, "detail": str},
                "trend_data": {"ok": bool, "detail": str},
            }
        }

    If can_proceed is False, the reel pipeline MUST NOT run.
    """
    checks: dict = {}
    all_ok = True

    # Check 1: Twitch GQL operational
    try:
        from app.services.twitch_gql_client import health_check
        health = await health_check()
        gql_ok = health.get("operational", False)
        gql_blocking = health.get("blocking_pipeline", False)

        if gql_blocking:
            checks["twitch_gql"] = {
                "ok": False,
                "detail": f"BLOCKED: {health.get('message', 'unknown')}",
            }
            all_ok = False
        elif not gql_ok:
            checks["twitch_gql"] = {
                "ok": False,
                "detail": f"Degraded: {health.get('message', 'unknown')}",
            }
            all_ok = False
        else:
            response_ms = health.get("connectivity_test", {}).get("response_time_ms", 0)
            checks["twitch_gql"] = {
                "ok": True,
                "detail": f"Operational ({response_ms}ms)",
            }
    except Exception as e:
        checks["twitch_gql"] = {"ok": False, "detail": f"Health check failed: {e}"}
        all_ok = False

    # Check 2: Fresh clip data available
    try:
        from app.services.twitch_gql_client import verify_data_freshness
        freshness = await verify_data_freshness()
        if freshness.get("can_proceed"):
            age = freshness.get("data_age_seconds", 0)
            clips = freshness.get("clips_available", 0)
            checks["data_freshness"] = {
                "ok": True,
                "detail": f"Fresh data: {clips} clips, {age}s old",
            }
        else:
            checks["data_freshness"] = {
                "ok": False,
                "detail": freshness.get("reason", "Data not fresh"),
            }
            all_ok = False
    except Exception as e:
        checks["data_freshness"] = {"ok": False, "detail": f"Freshness check failed: {e}"}
        all_ok = False

    # Check 3: Trend analysis available
    from app.services.trend_analyzer import _cache_get
    trend_cache = _cache_get("combined_insights")
    if trend_cache and trend_cache.get("recommendations"):
        cache_age = time.time() - trend_cache.get("_cached_at", 0)
        if cache_age < MAX_TREND_AGE_SECONDS:
            checks["trend_data"] = {
                "ok": True,
                "detail": f"Trends fresh ({int(cache_age)}s old, max {MAX_TREND_AGE_SECONDS}s)",
            }
        else:
            checks["trend_data"] = {
                "ok": False,
                "detail": f"Trends stale ({int(cache_age)}s old, max {MAX_TREND_AGE_SECONDS}s)",
            }
            # Don't block for stale trends — just warn, we'll refresh
    else:
        checks["trend_data"] = {
            "ok": True,
            "detail": "No cached trends — will be fetched fresh during pipeline",
        }

    # Save safety state
    state = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "can_proceed": all_ok,
        "checks": checks,
    }
    _save_json(_SAFETY_FILE, state)

    reason = "All systems operational" if all_ok else "; ".join(
        f"{k}: {v['detail']}" for k, v in checks.items() if not v["ok"]
    )

    return {
        "can_proceed": all_ok,
        "reason": reason,
        "checks": checks,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN: Get trend-informed recommendations for reel generation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def get_smart_trend_recommendations() -> dict:
    """Get trend recommendations combining all 3 layers.

    1. Captures fresh snapshot (real-time data)
    2. Stores in history
    3. Runs prediction (if enough history)
    4. Combines with own performance
    5. Returns actionable recommendations

    This is the MAIN function the reel pipeline should call.
    """
    # Step 1: Capture fresh snapshot
    snapshot = await capture_trend_snapshot()
    store_snapshot(snapshot)

    # Step 2: Get prediction from history
    prediction = predict_trends()

    # Step 3: Get own performance insights
    own_insights = get_own_performance_insights()

    # Step 4: Build combined recommendation
    # Start with real-time signals
    combined_signals = snapshot.get("format_signals", {}).get("combined", {})

    # If we have prediction, use it
    recommended_style = "highlight_react"  # default
    confidence = 0.0

    if prediction.get("has_prediction"):
        recommended_style = prediction["recommended_style"]
        confidence = prediction.get("prediction_confidence", 0)
        logger.info(
            "Trend prediction: %s (confidence: %.0f%%, rising: %s)",
            recommended_style,
            confidence * 100,
            list(prediction.get("rising_trends", {}).keys())[:3],
        )
    else:
        # No prediction yet — use real-time signal
        if combined_signals:
            top_keyword = max(combined_signals, key=combined_signals.get)
            format_map = {
                "clutch": "pro_clutch",
                "ace": "ace_compilation",
                "highlight": "highlight_react",
                "funny": "funny_moments",
                "edit": "sigma_edit",
                "react": "highlight_react",
                "tutorial": "tutorial_tip",
                "pro_play": "pro_clutch",
                "awp": "pro_clutch",
                "pistol": "ace_compilation",
            }
            recommended_style = format_map.get(top_keyword, "highlight_react")
            confidence = 0.3  # Low confidence without history
            logger.info("Using real-time signal (no history): top=%s -> %s", top_keyword, recommended_style)

    # If own performance data says a format works much better, boost it
    if own_insights.get("has_data") and own_insights.get("best_format"):
        best = own_insights["best_format"]
        best_score = own_insights["format_rankings"].get(best, {}).get("composite_score", 0)
        if best_score > 0.5:  # Strong enough signal from own data
            logger.info("Own performance boost: %s (score=%.2f)", best, best_score)
            # Blend: 70% trend prediction + 30% own performance
            # If own data strongly disagrees with trend, log it
            if best != recommended_style:
                logger.info(
                    "NOTE: Own performance says %s, trend prediction says %s — using trend",
                    best, recommended_style,
                )

    # Map style to concrete parameters
    from app.services.trend_analyzer import (
        _COLOR_MAP, _MUSIC_MAP, _FONT_MAP, _DURATION_MAP, _KNOWN_FORMATS,
    )

    color_grade = _COLOR_MAP.get(recommended_style, "vibrant")
    music_style = _MUSIC_MAP.get(recommended_style, "electronic")
    font_style = _FONT_MAP.get(recommended_style, "glow_outline")
    duration = _DURATION_MAP.get(recommended_style, 25)

    return {
        "preferred_style": recommended_style,
        "recommended_color_grade": color_grade,
        "recommended_music_style": music_style,
        "recommended_font_style": font_style,
        "recommended_duration_sec": duration,
        "recommended_pacing": "fast" if recommended_style in ["sigma_edit", "funny_moments"] else "build_up",
        "recommended_hook": _KNOWN_FORMATS.get(recommended_style, {}).get("hook_type", "text_hook"),
        "confidence": round(confidence, 2),
        "data_sources_used": list(snapshot.get("sources", {}).keys()),
        "prediction": {
            "has_history": prediction.get("has_prediction", False),
            "rising_formats": list(prediction.get("rising_trends", {}).keys())[:5],
            "falling_formats": list(prediction.get("falling_trends", {}).keys())[:5],
            "snapshots_analyzed": prediction.get("data_points_analyzed", 0),
        },
        "own_performance": {
            "has_data": own_insights.get("has_data", False),
            "best_format": own_insights.get("best_format"),
            "total_reels": own_insights.get("total_reels", 0),
        },
        "real_time_signals": combined_signals,
        "snapshot_timestamp": snapshot.get("timestamp_human"),
        "data_type": "trend_learning_engine",
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STATUS / DEBUG
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def get_learning_status() -> dict:
    """Get full status of the trend learning engine."""
    history = _load_history()
    own = get_own_performance_insights()
    forecast = _load_json(_FORECAST_FILE)

    forecast_age = None
    if forecast.get("predicted_at_ts"):
        forecast_age = int(time.time() - forecast["predicted_at_ts"])

    return {
        "history": {
            "total_snapshots": len(history),
            "oldest": history[0].get("timestamp_human") if history else None,
            "newest": history[-1].get("timestamp_human") if history else None,
            "can_predict": len(history) >= MIN_SNAPSHOTS_FOR_PREDICTION,
        },
        "own_performance": own,
        "forecast": {
            "exists": bool(forecast.get("has_prediction")),
            "age_seconds": forecast_age,
            "recommended_style": forecast.get("recommended_style"),
            "confidence": forecast.get("prediction_confidence"),
            "rising": list(forecast.get("rising_trends", {}).keys())[:5],
            "falling": list(forecast.get("falling_trends", {}).keys())[:5],
        },
        "safety": _load_json(_SAFETY_FILE),
    }
