from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_session
from app.dependencies.auth import get_current_user_id
from app.models.category import CategoryType
from app.schemas.category import CategoryCreate, CategoryResponse
from app.services.category_service import create_category, list_categories

router = APIRouter()


@router.post("", response_model=CategoryResponse, status_code=201)
async def create(
    payload: CategoryCreate,
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
) -> CategoryResponse:
    return await create_category(db, payload, user_id)


@router.get("", response_model=list[CategoryResponse])
async def list_by_type(
    type: CategoryType = Query(...),
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
) -> list[CategoryResponse]:
    return await list_categories(db, type, user_id)
