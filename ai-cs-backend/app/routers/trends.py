import json
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.database import get_db
from app.models.schemas import TrendAnalyzeRequest, TrendResponse
from app.services.trend_analyzer import analyze_trends, get_viral_patterns

router = APIRouter(prefix="/api/trends", tags=["trends"])


@router.get("", response_model=list[TrendResponse])
async def list_trends(
    platform: str | None = None,
    active_only: bool = True,
    limit: int = 50,
    offset: int = 0,
    db: aiosqlite.Connection = Depends(get_db),
):
    query = "SELECT * FROM trends WHERE 1=1"
    params: list = []

    if active_only:
        query += " AND is_active = 1"
    if platform:
        query += " AND platform = ?"
        params.append(platform)

    query += " ORDER BY score DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    results = []
    for row in rows:
        d = dict(row)
        d["metadata"] = json.loads(d["metadata"]) if isinstance(d["metadata"], str) else d["metadata"]
        d["is_active"] = bool(d["is_active"])
        results.append(d)
    return results


@router.post("/analyze")
async def trigger_analysis(
    request: TrendAnalyzeRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    new_trends = await analyze_trends(db, request.platforms, request.categories)
    return {
        "analyzed": True,
        "platforms": request.platforms,
        "new_trends_count": len(new_trends),
        "trends": new_trends,
        "viral_patterns": get_viral_patterns(),
    }


@router.get("/platforms/{platform}", response_model=list[TrendResponse])
async def get_platform_trends(
    platform: str,
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute(
        "SELECT * FROM trends WHERE platform = ? AND is_active = 1 ORDER BY score DESC",
        (platform,),
    )
    rows = await cursor.fetchall()
    results = []
    for row in rows:
        d = dict(row)
        d["metadata"] = json.loads(d["metadata"]) if isinstance(d["metadata"], str) else d["metadata"]
        d["is_active"] = bool(d["is_active"])
        results.append(d)
    return results
