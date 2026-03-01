import json
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.database import get_db
from app.models.schemas import MomentCreate, MomentDetectRequest, MomentResponse
from app.services.moment_detector import detect_moments

router = APIRouter(prefix="/api/moments", tags=["moments"])


@router.get("", response_model=list[MomentResponse])
async def list_moments(
    stream_id: int | None = None,
    moment_type: str | None = None,
    min_score: float = 0.0,
    limit: int = 50,
    offset: int = 0,
    db: aiosqlite.Connection = Depends(get_db),
):
    query = "SELECT * FROM moments WHERE score >= ?"
    params: list = [min_score]

    if stream_id:
        query += " AND stream_id = ?"
        params.append(stream_id)
    if moment_type:
        query += " AND moment_type = ?"
        params.append(moment_type)

    query += " ORDER BY score DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    results = []
    for row in rows:
        d = dict(row)
        d["metadata"] = json.loads(d["metadata"]) if isinstance(d["metadata"], str) else d["metadata"]
        results.append(d)
    return results


@router.post("/detect")
async def trigger_detection(
    request: MomentDetectRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    detected = await detect_moments(
        db, request.stream_id, request.sensitivity, request.moment_types
    )
    if not detected:
        raise HTTPException(status_code=404, detail="Stream not found or no moments detected")
    return {"stream_id": request.stream_id, "moments_detected": len(detected), "moments": detected}


@router.get("/{moment_id}", response_model=MomentResponse)
async def get_moment(
    moment_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute("SELECT * FROM moments WHERE id = ?", (moment_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Moment not found")
    d = dict(row)
    d["metadata"] = json.loads(d["metadata"]) if isinstance(d["metadata"], str) else d["metadata"]
    return d
