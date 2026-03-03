import json
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.database import get_db
from app.models.schemas import AIGirlConfigResponse, AIGirlConfigUpdate

router = APIRouter(prefix="/api/ai-girl", tags=["ai-girl"])


@router.get("/config", response_model=AIGirlConfigResponse)
async def get_config(
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute("SELECT * FROM ai_girl_config LIMIT 1")
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="AI Girl config not found")
    d = dict(row)
    d["is_enabled"] = bool(d["is_enabled"])
    d["use_only_when_better"] = bool(d["use_only_when_better"])
    return d


@router.put("/config", response_model=AIGirlConfigResponse)
async def update_config(
    update: AIGirlConfigUpdate,
    db: aiosqlite.Connection = Depends(get_db),
):
    updates = []
    params = []
    if update.is_enabled is not None:
        updates.append("is_enabled = ?")
        params.append(1 if update.is_enabled else 0)
    if update.model_name is not None:
        updates.append("model_name = ?")
        params.append(update.model_name)
    if update.voice_style is not None:
        updates.append("voice_style = ?")
        params.append(update.voice_style)
    if update.appearance_style is not None:
        updates.append("appearance_style = ?")
        params.append(update.appearance_style)
    if update.overlay_position is not None:
        updates.append("overlay_position = ?")
        params.append(update.overlay_position)
    if update.overlay_size is not None:
        updates.append("overlay_size = ?")
        params.append(update.overlay_size)
    if update.use_only_when_better is not None:
        updates.append("use_only_when_better = ?")
        params.append(1 if update.use_only_when_better else 0)
    if update.min_improvement_pct is not None:
        updates.append("min_improvement_pct = ?")
        params.append(update.min_improvement_pct)

    if updates:
        updates.append("updated_at = datetime('now')")
        await db.execute(
            f"UPDATE ai_girl_config SET {', '.join(updates)} WHERE id = 1", params
        )
        await db.commit()

    cursor = await db.execute("SELECT * FROM ai_girl_config LIMIT 1")
    row = await cursor.fetchone()
    d = dict(row)
    d["is_enabled"] = bool(d["is_enabled"])
    d["use_only_when_better"] = bool(d["use_only_when_better"])
    return d
