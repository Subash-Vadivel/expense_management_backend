from __future__ import annotations

from datetime import date

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.category import CategoryType
from app.repositories.common import date_range_filter, user_ownership_filter


def dashboard_match_filter(
    user_id: ObjectId,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    match_filter = {"createdBy": user_ownership_filter(user_id)}
    date_filter = date_range_filter(start_date, end_date)
    if date_filter:
        match_filter["date"] = date_filter
    return match_filter


async def aggregate_summary_totals(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, float]:
    pipeline = [
        {"$match": dashboard_match_filter(user_id, start_date, end_date)},
        {"$group": {"_id": "$type", "total": {"$sum": "$amount"}}},
    ]
    return {item["_id"]: float(item["total"]) async for item in db.transactions.aggregate(pipeline)}


async def aggregate_monthly_totals(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    pipeline = [
        {"$match": dashboard_match_filter(user_id, start_date, end_date)},
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
    return [item async for item in db.transactions.aggregate(pipeline)]


async def aggregate_category_totals(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    category_type: CategoryType,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    match_filter = dashboard_match_filter(user_id, start_date, end_date)
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
    return [item async for item in db.transactions.aggregate(pipeline)]
