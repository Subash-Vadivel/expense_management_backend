from __future__ import annotations

from datetime import date

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.category import CategoryType
from app.repositories import dashboard_repository
from app.schemas.dashboard import CategoryTotals, MonthlyTotals, SummaryTotals


def validate_date_range(start_date: date | None, end_date: date | None) -> None:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="startDate cannot be after endDate",
        )


async def get_summary(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    start_date: date | None = None,
    end_date: date | None = None,
) -> SummaryTotals:
    validate_date_range(start_date, end_date)
    totals = await dashboard_repository.aggregate_summary_totals(db, user_id, start_date, end_date)
    income = totals.get("income", 0.0)
    expense = totals.get("expense", 0.0)
    return SummaryTotals(totalIncome=income, totalExpense=expense, netBalance=income - expense)


async def get_monthly_totals(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[MonthlyTotals]:
    validate_date_range(start_date, end_date)
    by_month: dict[str, dict[str, float]] = {}
    for item in await dashboard_repository.aggregate_monthly_totals(db, user_id, start_date, end_date):
        month = item["_id"]["month"]
        tx_type = item["_id"]["type"]
        by_month.setdefault(month, {"income": 0.0, "expense": 0.0})[tx_type] = float(item["total"])
    return [MonthlyTotals(month=month, **totals) for month, totals in by_month.items()]


async def get_category_totals(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    category_type: CategoryType,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[CategoryTotals]:
    validate_date_range(start_date, end_date)
    return [
        CategoryTotals(
            categoryId=str(item["_id"]["categoryId"]),
            categoryName=item["_id"]["categoryName"],
            total=float(item["total"]),
        )
        for item in await dashboard_repository.aggregate_category_totals(
            db, user_id, category_type, start_date, end_date
        )
    ]
