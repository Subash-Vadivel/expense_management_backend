from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_session
from app.dependencies.auth import BusinessAccess, get_business_access
from app.models.category import CategoryType
from app.schemas.dashboard import CategoryTotals, MonthlyTotals, SummaryTotals
from app.services.dashboard_service import get_category_totals, get_monthly_totals, get_summary

router = APIRouter()


@router.get("/summary", response_model=SummaryTotals)
async def summary(
    startDate: date | None = Query(default=None),
    endDate: date | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(get_business_access),
) -> SummaryTotals:
    return await get_summary(db, access.business.id, startDate, endDate)


@router.get("/monthly-totals", response_model=list[MonthlyTotals])
async def monthly_totals(
    startDate: date | None = Query(default=None),
    endDate: date | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(get_business_access),
) -> list[MonthlyTotals]:
    return await get_monthly_totals(db, access.business.id, startDate, endDate)


@router.get("/category-totals", response_model=list[CategoryTotals])
async def category_totals(
    type: CategoryType = Query(...),
    startDate: date | None = Query(default=None),
    endDate: date | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(get_business_access),
) -> list[CategoryTotals]:
    return await get_category_totals(db, access.business.id, type, startDate, endDate)
