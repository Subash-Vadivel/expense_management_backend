from __future__ import annotations

from bson import ObjectId
from fastapi import APIRouter, Depends, Query
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import get_database
from app.dependencies.auth import get_current_user_id
from app.models.category import CategoryType
from app.schemas.category import CategoryCreate, CategoryResponse
from app.services.category_service import create_category, list_categories

router = APIRouter()


@router.post("", response_model=CategoryResponse, status_code=201)
async def create(
    payload: CategoryCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    user_id: ObjectId = Depends(get_current_user_id),
) -> CategoryResponse:
    return await create_category(db, payload, user_id)


@router.get("", response_model=list[CategoryResponse])
async def list_by_type(
    type: CategoryType = Query(...),
    db: AsyncIOMotorDatabase = Depends(get_database),
    user_id: ObjectId = Depends(get_current_user_id),
) -> list[CategoryResponse]:
    return await list_categories(db, type, user_id)
