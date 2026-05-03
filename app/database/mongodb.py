from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import settings

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    global _client, _db
    _client = AsyncIOMotorClient(settings.mongodb_uri)
    _db = _client[settings.mongodb_db]
    await create_indexes(_db)


async def close_mongo_connection() -> None:
    global _client, _db
    if _client:
        _client.close()
    _client = None
    _db = None


def get_database() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("MongoDB connection has not been initialized")
    return _db


async def create_indexes(db: AsyncIOMotorDatabase) -> None:
    await db.users.create_index("email", unique=True)
    await db.categories.create_index(
        [("createdBy", 1), ("type", 1), ("normalizedName", 1)], unique=True
    )
    await db.transactions.create_index([("createdBy", 1), ("type", 1), ("date", -1)])
    await db.transactions.create_index([("createdBy", 1), ("categoryId", 1)])
