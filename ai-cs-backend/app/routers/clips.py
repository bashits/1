from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.database import get_db
from app.models.schemas import ClipCreate, ClipUpdate, ClipResponse
from app.services.content_generator import generate_clip_pipeline

router = APIRouter(prefix="/api/clips", tags=["clips"])


@router.get("", response_model=list[ClipResponse])
async def list_clips(
    format_type: str | None = None,
    status: str | None = None,
    ab_test_id: int | None = None,
    sort_by: str = "created_at",
    limit: int = 50,
    offset: int = 0,
    db: aiosqlite.Connection = Depends(get_db),
):
    query = "SELECT * FROM clips WHERE 1=1"
    params: list = []

    if format_type:
        query += " AND format_type = ?"
        params.append(format_type)
    if status:
        query += " AND status = ?"
        params.append(status)
    if ab_test_id is not None:
        query += " AND ab_test_id = ?"
        params.append(ab_test_id)

    allowed_sorts = {"created_at", "views", "retention_rate", "ctr", "watch_through_rate"}
    if sort_by not in allowed_sorts:
        sort_by = "created_at"
    query += f" ORDER BY {sort_by} DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    results = []
    for row in rows:
        d = dict(row)
        d["has_ai_girl"] = bool(d["has_ai_girl"])
        d["has_subtitles"] = bool(d["has_subtitles"])
        d["has_face_cam"] = bool(d["has_face_cam"])
        results.append(d)
    return results


@router.post("", response_model=ClipResponse)
async def create_clip(
    clip: ClipCreate,
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute(
        """INSERT INTO clips (moment_id, template_id, ab_test_id, title, description, format_type,
           duration, status, hook_text, cta_text, has_ai_girl, has_subtitles, has_face_cam, platform)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?, ?)""",
        (
            clip.moment_id, clip.template_id, clip.ab_test_id, clip.title, clip.description,
            clip.format_type, clip.duration, clip.hook_text, clip.cta_text,
            1 if clip.has_ai_girl else 0, 1 if clip.has_subtitles else 0,
            1 if clip.has_face_cam else 0, clip.platform,
        ),
    )
    await db.commit()
    clip_id = cursor.lastrowid
    cursor = await db.execute("SELECT * FROM clips WHERE id = ?", (clip_id,))
    row = await cursor.fetchone()
    d = dict(row)
    d["has_ai_girl"] = bool(d["has_ai_girl"])
    d["has_subtitles"] = bool(d["has_subtitles"])
    d["has_face_cam"] = bool(d["has_face_cam"])
    return d


@router.get("/{clip_id}", response_model=ClipResponse)
async def get_clip(
    clip_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute("SELECT * FROM clips WHERE id = ?", (clip_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Clip not found")
    d = dict(row)
    d["has_ai_girl"] = bool(d["has_ai_girl"])
    d["has_subtitles"] = bool(d["has_subtitles"])
    d["has_face_cam"] = bool(d["has_face_cam"])
    return d


@router.put("/{clip_id}", response_model=ClipResponse)
async def update_clip(
    clip_id: int,
    update: ClipUpdate,
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute("SELECT * FROM clips WHERE id = ?", (clip_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Clip not found")

    updates = []
    params = []
    for field, value in update.model_dump(exclude_unset=True).items():
        updates.append(f"{field} = ?")
        params.append(value)

    if updates:
        updates.append("updated_at = datetime('now')")
        params.append(clip_id)
        await db.execute(
            f"UPDATE clips SET {', '.join(updates)} WHERE id = ?", params
        )
        await db.commit()

    cursor = await db.execute("SELECT * FROM clips WHERE id = ?", (clip_id,))
    row = await cursor.fetchone()
    d = dict(row)
    d["has_ai_girl"] = bool(d["has_ai_girl"])
    d["has_subtitles"] = bool(d["has_subtitles"])
    d["has_face_cam"] = bool(d["has_face_cam"])
    return d


@router.delete("/{clip_id}")
async def delete_clip(
    clip_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute("SELECT * FROM clips WHERE id = ?", (clip_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Clip not found")
    await db.execute("DELETE FROM clips WHERE id = ?", (clip_id,))
    await db.commit()
    return {"deleted": True, "id": clip_id}


@router.post("/{clip_id}/generate-pipeline")
async def generate_pipeline(
    clip_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    pipeline = await generate_clip_pipeline(db, clip_id)
    if "error" in pipeline:
        raise HTTPException(status_code=404, detail=pipeline["error"])
    return pipeline
