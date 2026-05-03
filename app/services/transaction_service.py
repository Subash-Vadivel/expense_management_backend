from __future__ import annotations

from datetime import date, datetime, time, timezone

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.transaction import TransactionModel, TransactionType
from app.schemas.transaction import TransactionCreate, TransactionResponse, TransactionUpdate
from app.services.category_service import get_category_for_user, user_ownership_filter


def transaction_to_response(transaction: dict) -> TransactionResponse:
    stored_date = transaction["date"]
    entry_date = stored_date.date() if isinstance(stored_date, datetime) else stored_date
    return TransactionResponse(
        id=str(transaction["_id"]),
        date=entry_date,
        categoryId=str(transaction["categoryId"]),
        categoryName=transaction["categoryName"],
        description=transaction.get("description"),
        amount=float(transaction["amount"]),
        type=transaction["type"],
        createdAt=transaction["createdAt"],
        updatedAt=transaction["updatedAt"],
    )


async def create_transaction(
    db: AsyncIOMotorDatabase,
    payload: TransactionCreate,
    transaction_type: TransactionType,
    user_id: ObjectId,
) -> TransactionResponse:
    category = await get_category_for_user(db, payload.categoryId, transaction_type, user_id)
    transaction = TransactionModel(
        date=payload.date,
        categoryId=category["_id"],
        categoryName=category["name"],
        description=payload.description,
        amount=payload.amount,
        type=transaction_type,
        createdBy=user_id,
    )
    result = await db.transactions.insert_one(transaction.to_mongo())
    created = await db.transactions.find_one({"_id": result.inserted_id})
    return transaction_to_response(created)


async def list_transactions(
    db: AsyncIOMotorDatabase, transaction_type: TransactionType, user_id: ObjectId
) -> list[TransactionResponse]:
    cursor = db.transactions.find(
        {"createdBy": user_ownership_filter(user_id), "type": transaction_type}
    ).sort("date", -1)
    return [transaction_to_response(transaction) async for transaction in cursor]


async def update_transaction(
    db: AsyncIOMotorDatabase,
    entry_id: str,
    payload: TransactionUpdate,
    transaction_type: TransactionType,
    user_id: ObjectId,
) -> TransactionResponse:
    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entry id")

    existing = await db.transactions.find_one(
        {
            "_id": ObjectId(entry_id),
            "createdBy": user_ownership_filter(user_id),
            "type": transaction_type,
        }
    )
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")

    update_data = payload.model_dump(exclude_unset=True, by_alias=True)
    if "date" in update_data and isinstance(update_data["date"], date):
        update_data["date"] = datetime.combine(update_data["date"], time.min, tzinfo=timezone.utc)

    if "categoryId" in update_data and update_data["categoryId"]:
        category = await get_category_for_user(db, update_data["categoryId"], transaction_type, user_id)
        update_data["categoryId"] = category["_id"]
        update_data["categoryName"] = category["name"]
    update_data["updatedAt"] = datetime.now(timezone.utc)

    await db.transactions.update_one({"_id": existing["_id"]}, {"$set": update_data})
    updated = await db.transactions.find_one({"_id": existing["_id"]})
    return transaction_to_response(updated)


async def delete_transaction(
    db: AsyncIOMotorDatabase, entry_id: str, transaction_type: TransactionType, user_id: ObjectId
) -> None:
    if not ObjectId.is_valid(entry_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid entry id")
    result = await db.transactions.delete_one(
        {
            "_id": ObjectId(entry_id),
            "createdBy": user_ownership_filter(user_id),
            "type": transaction_type,
        }
    )
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
