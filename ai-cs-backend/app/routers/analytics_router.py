from fastapi import APIRouter, Depends
import aiosqlite
from app.database import get_db
from app.services.analytics import (
    get_overview,
    get_format_performance,
    auto_adapt_weights,
    get_strategy_recommendations,
    get_growth_phase,
    update_growth_phase,
)
from app.models.schemas import StrategyPhaseUpdate

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview")
async def analytics_overview(
    db: aiosqlite.Connection = Depends(get_db),
):
    return await get_overview(db)


@router.get("/formats")
async def format_performance(
    db: aiosqlite.Connection = Depends(get_db),
):
    return await get_format_performance(db)


@router.post("/adapt-weights")
async def adapt_weights(
    db: aiosqlite.Connection = Depends(get_db),
):
    return await auto_adapt_weights(db)


@router.get("/growth-phase")
async def growth_phase(
    db: aiosqlite.Connection = Depends(get_db),
):
    return await get_growth_phase(db)


@router.put("/growth-phase")
async def set_growth_phase(
    update: StrategyPhaseUpdate,
    db: aiosqlite.Connection = Depends(get_db),
):
    return await update_growth_phase(db, update.phase)


@router.get("/recommendations")
async def recommendations(
    db: aiosqlite.Connection = Depends(get_db),
):
    recs = await get_strategy_recommendations(db)
    return {"recommendations": recs}
