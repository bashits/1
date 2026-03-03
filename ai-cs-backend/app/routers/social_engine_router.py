"""
Smart Social Engine (SSE) Router — API endpoints for the intelligent social media autopilot.

All endpoints are under /api/social-engine/{profile_id}/...
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import aiosqlite

from app.database import get_db
from app.services.smart_social_engine import (
    TrendIntelligenceEngine,
    ContentStrategyEngine,
    PostingOrchestrator,
    EngagementEngine,
    LearningEngine,
    ChainGuard,
    get_engine_dashboard,
    initialize_engine,
)

router = APIRouter(prefix="/api/social-engine", tags=["Social Engine"])


# ─── Request Models ──────────────────────────────────────────────────

class AnalyzeTrendsRequest(BaseModel):
    platform: str = "instagram"
    content_format: str = "reels"
    niche: str = "gaming"
    region: str = "US"


class GeneratePlanRequest(BaseModel):
    days: int = 7
    niche: str = "gaming"


class GenerateCommentsRequest(BaseModel):
    niche: str = "gaming"
    count: int = 10
    comment_style: Optional[str] = None


class RecordPerformanceRequest(BaseModel):
    queue_id: int
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    reach: int = 0
    impressions: int = 0


class InitializeRequest(BaseModel):
    niche: str = "gaming"
    region: str = "US"


class QueuePostRequest(BaseModel):
    platform: str = "instagram"
    content_format: str = "reels"
    caption: Optional[str] = None
    hashtags: list = []
    scheduled_at: Optional[str] = None


# ─── Endpoints ────────────────────────────────────────────────────────

@router.post("/{profile_id}/initialize")
async def api_initialize_engine(
    profile_id: int,
    body: InitializeRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Initialize the SSE for a profile — runs initial trend analysis + plan generation."""
    result = await initialize_engine(db, profile_id, body.niche, body.region)
    return result


@router.get("/{profile_id}/dashboard")
async def api_get_dashboard(
    profile_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get complete SSE dashboard with all engine statuses."""
    return await get_engine_dashboard(db, profile_id)


# ─── Trend Intelligence ──────────────────────────────────────────────

@router.post("/{profile_id}/analyze-trends")
async def api_analyze_trends(
    profile_id: int,
    body: AnalyzeTrendsRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Run trend analysis for a specific platform + format combo."""
    result = await TrendIntelligenceEngine.analyze_trends(
        db, profile_id, body.platform, body.content_format, body.niche, body.region,
    )
    return result


@router.get("/{profile_id}/trends")
async def api_get_trends(
    profile_id: int,
    platform: Optional[str] = None,
    content_format: Optional[str] = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get latest trend data, optionally filtered."""
    return await TrendIntelligenceEngine.get_latest_trends(
        db, profile_id, platform, content_format,
    )


# ─── Content Strategy ────────────────────────────────────────────────

@router.post("/{profile_id}/generate-plan")
async def api_generate_plan(
    profile_id: int,
    body: GeneratePlanRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Generate a multi-day content plan across all platforms."""
    return await ContentStrategyEngine.generate_plan(
        db, profile_id, body.days, body.niche,
    )


@router.get("/{profile_id}/plan")
async def api_get_plan(
    profile_id: int,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get current content plan / posting queue."""
    return await ContentStrategyEngine.get_current_plan(
        db, profile_id, platform, status,
    )


# ─── Posting Queue ───────────────────────────────────────────────────

@router.post("/{profile_id}/queue-post")
async def api_queue_post(
    profile_id: int,
    body: QueuePostRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Add a post to the posting queue."""
    import json
    from datetime import datetime, timezone

    await db.execute(
        """INSERT INTO posting_queue
           (profile_id, platform, content_format, caption, hashtags, scheduled_at, status)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            profile_id, body.platform, body.content_format,
            body.caption, json.dumps(body.hashtags),
            body.scheduled_at or datetime.now(timezone.utc).isoformat(),
            "queued",
        ),
    )
    await db.commit()
    return {"status": "queued", "platform": body.platform, "format": body.content_format}


@router.get("/{profile_id}/queue")
async def api_get_queue(
    profile_id: int,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get posting queue with filters."""
    return await PostingOrchestrator.get_queue(db, profile_id, platform, status)


@router.post("/{profile_id}/pre-post-analysis/{queue_id}")
async def api_pre_post_analysis(
    profile_id: int,
    queue_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Run mandatory pre-post analysis for a queued post."""
    return await PostingOrchestrator.pre_post_analysis(db, profile_id, queue_id)


@router.post("/{profile_id}/execute-post/{queue_id}")
async def api_execute_post(
    profile_id: int,
    queue_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Execute a queued post (after pre-post analysis passes)."""
    return await PostingOrchestrator.execute_post(db, profile_id, queue_id)


# ─── Engagement Engine ───────────────────────────────────────────────

@router.post("/{profile_id}/engage")
async def api_generate_comments(
    profile_id: int,
    body: GenerateCommentsRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Generate smart comments for engagement in target region."""
    return await EngagementEngine.generate_comments(
        db, profile_id, body.niche, body.count, body.comment_style,
    )


@router.get("/{profile_id}/engagement-log")
async def api_get_engagement_log(
    profile_id: int,
    limit: int = 50,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get engagement actions log."""
    return await EngagementEngine.get_engagement_log(db, profile_id, limit)


# ─── Learning Engine ─────────────────────────────────────────────────

@router.post("/{profile_id}/record-performance")
async def api_record_performance(
    profile_id: int,
    body: RecordPerformanceRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Record post performance metrics for learning."""
    return await LearningEngine.record_performance(
        db, profile_id, body.queue_id,
        {
            "views": body.views, "likes": body.likes,
            "comments": body.comments, "shares": body.shares,
            "saves": body.saves, "reach": body.reach,
            "impressions": body.impressions,
        },
    )


@router.get("/{profile_id}/learning")
async def api_get_learning(
    profile_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get all learned patterns."""
    return await LearningEngine.get_all_learning(db, profile_id)


# ─── Chain Guard ──────────────────────────────────────────────────────

@router.get("/{profile_id}/chain-health")
async def api_chain_health(
    profile_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Get chain health status for all components."""
    return await ChainGuard.get_chain_status(db, profile_id)


@router.post("/{profile_id}/heal")
async def api_heal_chain(
    profile_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    """Trigger self-healing for unhealthy components."""
    return await ChainGuard.heal(db, profile_id)
