from __future__ import annotations

from datetime import date, datetime, time, timezone

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.category import CategoryType
from app.schemas.dashboard import CategoryTotals, MonthlyTotals, SummaryTotals
from app.services.category_service import user_ownership_filter


def build_dashboard_match(user_id: ObjectId, start_date: date | None, end_date: date | None) -> dict:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="startDate cannot be after endDate",
        )

    match_filter = {"createdBy": user_ownership_filter(user_id)}
    date_filter = {}
    if start_date:
        date_filter["$gte"] = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    if end_date:
        date_filter["$lte"] = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
    if date_filter:
        match_filter["date"] = date_filter
    return match_filter


async def get_summary(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    start_date: date | None = None,
    end_date: date | None = None,
) -> SummaryTotals:
    pipeline = [
        {"$match": build_dashboard_match(user_id, start_date, end_date)},
        {"$group": {"_id": "$type", "total": {"$sum": "$amount"}}},
    ]
    totals = {item["_id"]: float(item["total"]) async for item in db.transactions.aggregate(pipeline)}
    income = totals.get("income", 0.0)
    expense = totals.get("expense", 0.0)
    return SummaryTotals(totalIncome=income, totalExpense=expense, netBalance=income - expense)


async def get_monthly_totals(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[MonthlyTotals]:
    pipeline = [
        {"$match": build_dashboard_match(user_id, start_date, end_date)},
        {
            "$group": {
                "_id": {
                    "month": {"$dateToString": {"format": "%Y-%m", "date": {"$toDate": "$date"}}},
                    "type": "$type",
                },
                "total": {"$sum": "$amount"},
            }
        },
        {"$sort": {"_id.month": 1}},
    ]
    by_month: dict[str, dict[str, float]] = {}
    async for item in db.transactions.aggregate(pipeline):
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
    match_filter = build_dashboard_match(user_id, start_date, end_date)
    match_filter["type"] = category_type
    pipeline = [
        {"$match": match_filter},
        {
            "$group": {
                "_id": {"categoryId": "$categoryId", "categoryName": "$categoryName"},
                "total": {"$sum": "$amount"},
            }
        },
        {"$sort": {"total": -1}},
    ]
    return [
        CategoryTotals(
            categoryId=str(item["_id"]["categoryId"]),
            categoryName=item["_id"]["categoryName"],
            total=float(item["total"]),
        )
        async for item in db.transactions.aggregate(pipeline)
    ]
