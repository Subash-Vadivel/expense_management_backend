from __future__ import annotations

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo.results import DeleteResult

from app.repositories.common import user_ownership_filter


async def create_api_key(db: AsyncIOMotorDatabase, api_key: dict) -> ObjectId:
    result = await db.mcp_api_keys.insert_one(api_key)
    return result.inserted_id


async def find_api_key_by_id(db: AsyncIOMotorDatabase, api_key_id: ObjectId) -> dict | None:
    return await db.mcp_api_keys.find_one({"_id": api_key_id})


async def find_api_key_for_user(
    db: AsyncIOMotorDatabase,
    api_key_id: ObjectId,
    user_id: ObjectId,
) -> dict | None:
    return await db.mcp_api_keys.find_one(
        {"_id": api_key_id, "createdBy": user_ownership_filter(user_id)}
    )


async def find_api_key_by_hash(db: AsyncIOMotorDatabase, key_hash: str) -> dict | None:
    return await db.mcp_api_keys.find_one({"keyHash": key_hash})


async def list_api_keys_for_user(db: AsyncIOMotorDatabase, user_id: ObjectId) -> list[dict]:
    cursor = db.mcp_api_keys.find({"createdBy": user_ownership_filter(user_id)}).sort("createdAt", -1)
    return [api_key async for api_key in cursor]


async def update_api_key(db: AsyncIOMotorDatabase, api_key_id: ObjectId, update_data: dict) -> None:
    await db.mcp_api_keys.update_one({"_id": api_key_id}, {"$set": update_data})


async def delete_api_key(
    db: AsyncIOMotorDatabase,
    api_key_id: ObjectId,
    user_id: ObjectId,
) -> DeleteResult:
    return await db.mcp_api_keys.delete_one(
        {"_id": api_key_id, "createdBy": user_ownership_filter(user_id)}
    )
