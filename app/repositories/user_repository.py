from __future__ import annotations

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


async def create_user(db: AsyncIOMotorDatabase, user: dict) -> ObjectId:
    result = await db.users.insert_one(user)
    return result.inserted_id


async def find_user_by_id(db: AsyncIOMotorDatabase, user_id: ObjectId) -> dict | None:
    return await db.users.find_one({"_id": user_id})


async def find_user_by_email(db: AsyncIOMotorDatabase, email: str) -> dict | None:
    return await db.users.find_one({"email": email})
