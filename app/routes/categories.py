from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_session
from app.dependencies.auth import BusinessAccess, get_business_access, require_business_role
from app.models.category import CategoryType
from app.schemas.category import CategoryCreate, CategoryPage, CategoryResponse
from app.schemas.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, MAX_SEARCH_LENGTH
from app.services.category_service import create_category, delete_category, list_categories

router = APIRouter()


@router.post("", response_model=CategoryResponse, status_code=201)
async def create(
    payload: CategoryCreate,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(require_business_role("owner", "admin", "manager")),
) -> CategoryResponse:
    return await create_category(db, payload, access.business.id, access.user.id)


@router.get("", response_model=CategoryPage)
async def list_by_type(
    type: CategoryType = Query(...),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=MAX_SEARCH_LENGTH),
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(get_business_access),
) -> CategoryPage:
    return await list_categories(db, type, access.business.id, limit, offset, search)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    category_id: str,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(require_business_role("owner", "admin", "manager")),
) -> Response:
    await delete_category(db, category_id, access.business.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
