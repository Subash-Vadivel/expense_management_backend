from __future__ import annotations

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.category import CategoryType
from app.repositories.common import user_ownership_filter


async def find_category_by_normalized_name(
    db: AsyncIOMotorDatabase,
    user_id: ObjectId,
    category_type: CategoryType,
    normalized_name: str,
) -> dict | None:
    return await db.categories.find_one(
        {
            "createdBy": user_ownership_filter(user_id),
            "type": category_type,
            "normalizedName": normalized_name,
        }
    )


async def create_category(db: AsyncIOMotorDatabase, category: dict) -> ObjectId:
    result = await db.categories.insert_one(category)
    return result.inserted_id


async def find_category_by_id(db: AsyncIOMotorDatabase, category_id: ObjectId) -> dict | None:
    return await db.categories.find_one({"_id": category_id})


async def find_category_for_user(
    db: AsyncIOMotorDatabase,
    category_id: ObjectId,
    category_type: CategoryType,
    user_id: ObjectId,
) -> dict | None:
    return await db.categories.find_one(
        {
            "_id": category_id,
            "createdBy": user_ownership_filter(user_id),
            "type": category_type,
        }
    )


async def list_categories(
    db: AsyncIOMotorDatabase,
    category_type: CategoryType,
    user_id: ObjectId,
) -> list[dict]:
    cursor = db.categories.find(
        {"createdBy": user_ownership_filter(user_id), "type": category_type}
    ).sort("name", 1)
    return [category async for category in cursor]
