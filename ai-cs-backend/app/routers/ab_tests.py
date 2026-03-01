import json
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.database import get_db
from app.models.schemas import ABTestCreate, ABTestResultSubmit, ABTestResponse
from app.services.template_engine import generate_ab_variants

router = APIRouter(prefix="/api/ab-tests", tags=["ab-tests"])


@router.get("")
async def list_ab_tests(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: aiosqlite.Connection = Depends(get_db),
):
    if status:
        cursor = await db.execute(
            "SELECT * FROM ab_tests WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (status, limit, offset),
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM ab_tests ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
    rows = await cursor.fetchall()

    results = []
    for row in rows:
        test_data = dict(row)
        # Get associated clips
        clip_cursor = await db.execute(
            "SELECT * FROM clips WHERE ab_test_id = ? ORDER BY views DESC", (row["id"],)
        )
        clips = await clip_cursor.fetchall()
        test_data["clips"] = []
        for clip in clips:
            cd = dict(clip)
            cd["has_ai_girl"] = bool(cd["has_ai_girl"])
            cd["has_subtitles"] = bool(cd["has_subtitles"])
            cd["has_face_cam"] = bool(cd["has_face_cam"])
            test_data["clips"].append(cd)
        results.append(test_data)

    return results


@router.post("")
async def create_ab_test(
    test: ABTestCreate,
    db: aiosqlite.Connection = Depends(get_db),
):
    if test.moment_id:
        # Auto-generate variants using template engine
        result = await generate_ab_variants(db, test.moment_id, template_ids=None)
        if not result:
            raise HTTPException(status_code=400, detail="Could not generate variants")
        return result
    else:
        # Manual A/B test creation
        cursor = await db.execute(
            "INSERT INTO ab_tests (name, moment_id, status) VALUES (?, ?, 'running')",
            (test.name, test.moment_id),
        )
        await db.commit()
        test_id = cursor.lastrowid

        # Link existing clips if provided
        if test.clip_ids:
            for clip_id in test.clip_ids:
                await db.execute(
                    "UPDATE clips SET ab_test_id = ? WHERE id = ?", (test_id, clip_id)
                )
            await db.commit()

        cursor = await db.execute("SELECT * FROM ab_tests WHERE id = ?", (test_id,))
        row = await cursor.fetchone()
        return dict(row)


@router.get("/{test_id}")
async def get_ab_test(
    test_id: int,
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute("SELECT * FROM ab_tests WHERE id = ?", (test_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="A/B test not found")

    test_data = dict(row)
    clip_cursor = await db.execute(
        "SELECT * FROM clips WHERE ab_test_id = ? ORDER BY views DESC", (test_id,)
    )
    clips = await clip_cursor.fetchall()
    test_data["clips"] = []
    for clip in clips:
        cd = dict(clip)
        cd["has_ai_girl"] = bool(cd["has_ai_girl"])
        cd["has_subtitles"] = bool(cd["has_subtitles"])
        cd["has_face_cam"] = bool(cd["has_face_cam"])
        test_data["clips"].append(cd)

    return test_data


@router.post("/{test_id}/results")
async def submit_results(
    test_id: int,
    result: ABTestResultSubmit,
    db: aiosqlite.Connection = Depends(get_db),
):
    # Verify test exists
    cursor = await db.execute("SELECT * FROM ab_tests WHERE id = ?", (test_id,))
    test = await cursor.fetchone()
    if not test:
        raise HTTPException(status_code=404, detail="A/B test not found")

    # Update clip metrics
    await db.execute(
        """UPDATE clips SET views = ?, likes = ?, comments = ?, shares = ?,
           ctr = ?, retention_rate = ?, watch_through_rate = ?,
           status = 'published', updated_at = datetime('now')
           WHERE id = ? AND ab_test_id = ?""",
        (
            result.views, result.likes, result.comments, result.shares,
            result.ctr, result.retention_rate, result.watch_through_rate,
            result.clip_id, test_id,
        ),
    )
    await db.commit()

    # Check if all clips in test have results - auto-determine winner
    clip_cursor = await db.execute(
        "SELECT * FROM clips WHERE ab_test_id = ? AND status = 'published' ORDER BY views DESC",
        (test_id,),
    )
    published_clips = await clip_cursor.fetchall()

    all_clips_cursor = await db.execute(
        "SELECT COUNT(*) as cnt FROM clips WHERE ab_test_id = ?", (test_id,)
    )
    all_count = (await all_clips_cursor.fetchone())["cnt"]

    response = {"updated": True, "clip_id": result.clip_id}

    if len(published_clips) == all_count and all_count > 0:
        # Determine winner by composite score
        best_clip = None
        best_score = -1
        for clip in published_clips:
            score = clip["retention_rate"] * 0.35 + clip["ctr"] * 0.25 + clip["watch_through_rate"] * 0.25 + (clip["comments"] / max(clip["views"], 1)) * 100 * 0.15
            if score > best_score:
                best_score = score
                best_clip = clip

        if best_clip:
            await db.execute(
                "UPDATE ab_tests SET winner_clip_id = ?, status = 'completed', ended_at = datetime('now') WHERE id = ?",
                (best_clip["id"], test_id),
            )
            await db.commit()
            response["test_completed"] = True
            response["winner_clip_id"] = best_clip["id"]
            response["winner_format"] = best_clip["format_type"]

    return response
