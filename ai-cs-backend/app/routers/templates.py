import json
from fastapi import APIRouter, Depends, HTTPException
import aiosqlite
from app.database import get_db
from app.models.schemas import TemplateCreate, TemplateUpdate, TemplateResponse

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[TemplateResponse])
async def list_templates(
    active_only: bool = False,
    db: aiosqlite.Connection = Depends(get_db),
):
    if active_only:
        cursor = await db.execute(
            "SELECT * FROM templates WHERE is_active = 1 ORDER BY weight DESC"
        )
    else:
        cursor = await db.execute("SELECT * FROM templates ORDER BY weight DESC")
    rows = await cursor.fetchall()
    results = []
    for row in rows:
        d = dict(row)
        d["config"] = json.loads(d["config"]) if isinstance(d["config"], str) else d["config"]
        d["is_active"] = bool(d["is_active"])
        results.append(d)
    return results


@router.post("", response_model=TemplateResponse)
async def create_template(
    template: TemplateCreate,
    db: aiosqlite.Connection = Depends(get_db),
):
    config_json = json.dumps(template.config or {})
    cursor = await db.execute(
        "INSERT INTO templates (name, format_type, description, config) VALUES (?, ?, ?, ?)",
        (template.name, template.format_type, template.description, config_json),
    )
    await db.commit()
    tmpl_id = cursor.lastrowid
    cursor = await db.execute("SELECT * FROM templates WHERE id = ?", (tmpl_id,))
    row = await cursor.fetchone()
    d = dict(row)
    d["config"] = json.loads(d["config"]) if isinstance(d["config"], str) else d["config"]
    d["is_active"] = bool(d["is_active"])
    return d


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: int,
    update: TemplateUpdate,
    db: aiosqlite.Connection = Depends(get_db),
):
    cursor = await db.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Template not found")

    updates = []
    params = []
    if update.name is not None:
        updates.append("name = ?")
        params.append(update.name)
    if update.format_type is not None:
        updates.append("format_type = ?")
        params.append(update.format_type)
    if update.description is not None:
        updates.append("description = ?")
        params.append(update.description)
    if update.config is not None:
        updates.append("config = ?")
        params.append(json.dumps(update.config))
    if update.is_active is not None:
        updates.append("is_active = ?")
        params.append(1 if update.is_active else 0)
    if update.weight is not None:
        updates.append("weight = ?")
        params.append(update.weight)

    if updates:
        updates.append("updated_at = datetime('now')")
        params.append(template_id)
        await db.execute(
            f"UPDATE templates SET {', '.join(updates)} WHERE id = ?", params
        )
        await db.commit()

    cursor = await db.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
    row = await cursor.fetchone()
    d = dict(row)
    d["config"] = json.loads(d["config"]) if isinstance(d["config"], str) else d["config"]
    d["is_active"] = bool(d["is_active"])
    return d
