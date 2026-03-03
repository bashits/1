"""Tool Registry Router - Browse and select open-source AI tools.

Shows all researched GitHub tools with stars, quality scores,
VRAM requirements, and allows selecting which tools to use in pipeline.
"""

import json
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.database import get_db
from app.models.schemas import ToolRegistryResponse, ToolSelectUpdate
from app.services.ai_profile_generator import TOOL_REGISTRY, get_recommended_pipeline

router = APIRouter(prefix="/api/tools", tags=["tool-registry"])


@router.get("/", response_model=list[ToolRegistryResponse])
async def list_tools(
    category: str | None = None,
    db: aiosqlite.Connection = Depends(get_db),
):
    if category:
        cursor = await db.execute(
            "SELECT * FROM tool_registry WHERE category = ? ORDER BY quality_score DESC",
            (category,),
        )
    else:
        cursor = await db.execute("SELECT * FROM tool_registry ORDER BY category, quality_score DESC")
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["config"] = json.loads(d["config"]) if isinstance(d["config"], str) else d["config"]
        d["is_free"] = bool(d["is_free"])
        d["is_selected"] = bool(d["is_selected"])
        result.append(d)
    return result


@router.get("/categories")
async def list_categories(
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute(
        "SELECT category, COUNT(*) as count FROM tool_registry GROUP BY category ORDER BY category"
    )
    rows = await cursor.fetchall()
    return [{"category": row["category"], "count": row["count"]} for row in rows]


@router.put("/{tool_id}/select", response_model=ToolRegistryResponse)
async def toggle_tool_selection(
    tool_id: int,
    update: ToolSelectUpdate,
    db: aiosqlite.Connection = Depends(get_db),
):
    await db.execute(
        "UPDATE tool_registry SET is_selected = ? WHERE id = ?",
        (1 if update.is_selected else 0, tool_id),
    )
    await db.commit()

    cursor = await db.execute("SELECT * FROM tool_registry WHERE id = ?", (tool_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Tool not found")
    d = dict(row)
    d["config"] = json.loads(d["config"]) if isinstance(d["config"], str) else d["config"]
    d["is_free"] = bool(d["is_free"])
    d["is_selected"] = bool(d["is_selected"])
    return d


@router.get("/selected")
async def get_selected_tools(
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute(
        "SELECT * FROM tool_registry WHERE is_selected = 1 ORDER BY category"
    )
    rows = await cursor.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        d["config"] = json.loads(d["config"]) if isinstance(d["config"], str) else d["config"]
        d["is_free"] = bool(d["is_free"])
        d["is_selected"] = bool(d["is_selected"])
        result.append(d)
    return result


@router.get("/pipeline/{budget}")
async def get_pipeline_config(budget: str = "minimal"):
    """Get recommended pipeline for a budget level (minimal/moderate/full)."""
    if budget not in ("minimal", "moderate", "full"):
        raise HTTPException(status_code=400, detail="Budget must be: minimal, moderate, or full")
    pipeline = get_recommended_pipeline(budget)
    return {"budget": budget, **pipeline}


@router.get("/comparison")
async def compare_all_budgets():
    """Compare all budget tiers side by side."""
    return {
        "minimal": get_recommended_pipeline("minimal"),
        "moderate": get_recommended_pipeline("moderate"),
        "full": get_recommended_pipeline("full"),
    }
