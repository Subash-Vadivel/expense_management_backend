from __future__ import annotations

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.category import CategoryType
from app.schemas.dashboard import CategoryTotals, MonthlyTotals, SummaryTotals
from app.services.category_service import user_ownership_filter


async def get_summary(db: AsyncIOMotorDatabase, user_id: ObjectId) -> SummaryTotals:
    pipeline = [
        {"$match": {"createdBy": user_ownership_filter(user_id)}},
        {"$group": {"_id": "$type", "total": {"$sum": "$amount"}}},
    ]
    totals = {item["_id"]: float(item["total"]) async for item in db.transactions.aggregate(pipeline)}
    income = totals.get("income", 0.0)
    expense = totals.get("expense", 0.0)
    return SummaryTotals(totalIncome=income, totalExpense=expense, netBalance=income - expense)


async def get_monthly_totals(db: AsyncIOMotorDatabase, user_id: ObjectId) -> list[MonthlyTotals]:
    pipeline = [
        {"$match": {"createdBy": user_ownership_filter(user_id)}},
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
    db: AsyncIOMotorDatabase, user_id: ObjectId, category_type: CategoryType
) -> list[CategoryTotals]:
    pipeline = [
        {"$match": {"createdBy": user_ownership_filter(user_id), "type": category_type}},
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
