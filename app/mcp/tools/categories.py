from __future__ import annotations

from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.category import CategoryCreate
from app.services.category_service import create_category, list_categories


async def handle_list_categories(db: AsyncIOMotorDatabase, user_id: ObjectId, arguments: dict) -> object:
    category_type = arguments["type"]
    return jsonable_encoder(await list_categories(db, category_type, user_id))


async def handle_create_category(db: AsyncIOMotorDatabase, user_id: ObjectId, arguments: dict) -> object:
    payload = CategoryCreate(**arguments)
    return jsonable_encoder(await create_category(db, payload, user_id))
