from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import get_database
from app.dependencies.auth import get_current_user_id
from app.models.category import CategoryType
from app.schemas.dashboard import CategoryTotals, MonthlyTotals, SummaryTotals
from app.services.dashboard_service import get_category_totals, get_monthly_totals, get_summary

router = APIRouter()


@router.get("/summary", response_model=SummaryTotals)
async def summary(
    db: AsyncIOMotorDatabase = Depends(get_database),
    user_id: ObjectId = Depends(get_current_user_id),
) -> SummaryTotals:
    return await get_summary(db, user_id)


@router.get("/monthly-totals", response_model=list[MonthlyTotals])
async def monthly_totals(
    db: AsyncIOMotorDatabase = Depends(get_database),
    user_id: ObjectId = Depends(get_current_user_id),
) -> list[MonthlyTotals]:
    return await get_monthly_totals(db, user_id)


@router.get("/category-totals", response_model=list[CategoryTotals])
async def category_totals(
    type: CategoryType = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_database),
    user_id: ObjectId = Depends(get_current_user_id),
) -> list[CategoryTotals]:
    return await get_category_totals(db, user_id, type)
