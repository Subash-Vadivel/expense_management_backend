from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_session
from app.dependencies.auth import BusinessAccess, get_business_access, require_business_role
from app.schemas.pagination import DEFAULT_PAGE_LIMIT, MAX_PAGE_LIMIT, MAX_SEARCH_LENGTH, SortOrder
from app.schemas.transaction import (
    TransactionCreate,
    TransactionPage,
    TransactionResponse,
    TransactionSortField,
    TransactionUpdate,
)
from app.services.transaction_service import (
    create_transaction,
    delete_transaction,
    get_transaction,
    list_transactions,
    update_transaction,
)

router = APIRouter()


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_income(
    payload: TransactionCreate,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(require_business_role("owner", "admin", "manager")),
) -> TransactionResponse:
    return await create_transaction(db, payload, "income", access.business.id, access.user.id)


@router.get("", response_model=TransactionPage)
async def list_income(
    startDate: date | None = Query(default=None),
    endDate: date | None = Query(default=None),
    limit: int = Query(default=DEFAULT_PAGE_LIMIT, ge=1, le=MAX_PAGE_LIMIT),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, max_length=MAX_SEARCH_LENGTH),
    sort: TransactionSortField = Query(default="date"),
    order: SortOrder = Query(default="desc"),
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(get_business_access),
) -> TransactionPage:
    return await list_transactions(
        db, "income", access.business.id, startDate, endDate, limit, offset, search, sort, order
    )


@router.get("/{entry_id}", response_model=TransactionResponse)
async def get_income(
    entry_id: str,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(get_business_access),
) -> TransactionResponse:
    return await get_transaction(db, entry_id, "income", access.business.id)


@router.put("/{entry_id}", response_model=TransactionResponse)
async def update_income(
    entry_id: str,
    payload: TransactionUpdate,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(require_business_role("owner", "admin", "manager")),
) -> TransactionResponse:
    return await update_transaction(db, entry_id, payload, "income", access.business.id)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_income(
    entry_id: str,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(require_business_role("owner", "admin", "manager")),
) -> Response:
    await delete_transaction(db, entry_id, "income", access.business.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
