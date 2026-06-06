from __future__ import annotations

from datetime import date

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.results import DeleteResult

from app.models.transaction import TransactionType
from app.repositories.common import date_range_filter, user_ownership_filter


def transaction_match_filter(
    user_id: ObjectId,
    transaction_type: TransactionType,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict:
    match_filter = {"createdBy": user_ownership_filter(user_id), "type": transaction_type}
    date_filter = date_range_filter(start_date, end_date)
    if date_filter:
        match_filter["date"] = date_filter
    return match_filter


async def create_transaction(db: AsyncIOMotorDatabase, transaction: dict) -> ObjectId:
    result = await db.transactions.insert_one(transaction)
    return result.inserted_id


async def find_transaction_by_id(db: AsyncIOMotorDatabase, transaction_id: ObjectId) -> dict | None:
    return await db.transactions.find_one({"_id": transaction_id})


async def find_transaction_for_user(
    db: AsyncIOMotorDatabase,
    transaction_id: ObjectId,
    transaction_type: TransactionType,
    user_id: ObjectId,
) -> dict | None:
    return await db.transactions.find_one(
        {
            "_id": transaction_id,
            "createdBy": user_ownership_filter(user_id),
            "type": transaction_type,
        }
    )


async def list_transactions(
    db: AsyncIOMotorDatabase,
    transaction_type: TransactionType,
    user_id: ObjectId,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    cursor = db.transactions.find(
        transaction_match_filter(user_id, transaction_type, start_date, end_date)
    ).sort("date", -1)
    return [transaction async for transaction in cursor]


async def update_transaction(
    db: AsyncIOMotorDatabase,
    transaction_id: ObjectId,
    update_data: dict,
) -> None:
    await db.transactions.update_one({"_id": transaction_id}, {"$set": update_data})


async def delete_transaction(
    db: AsyncIOMotorDatabase,
    transaction_id: ObjectId,
    transaction_type: TransactionType,
    user_id: ObjectId,
) -> DeleteResult:
    return await db.transactions.delete_one(
        {
            "_id": transaction_id,
            "createdBy": user_ownership_filter(user_id),
            "type": transaction_type,
        }
    )
