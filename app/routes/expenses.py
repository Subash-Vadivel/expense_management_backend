from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_session
from app.dependencies.auth import get_current_user_id
from app.schemas.transaction import TransactionCreate, TransactionResponse, TransactionUpdate
from app.services.transaction_service import (
    create_transaction,
    delete_transaction,
    list_transactions,
    update_transaction,
)

router = APIRouter()


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_expense(
    payload: TransactionCreate,
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
) -> TransactionResponse:
    return await create_transaction(db, payload, "expense", user_id)


@router.get("", response_model=list[TransactionResponse])
async def list_expenses(
    startDate: date | None = Query(default=None),
    endDate: date | None = Query(default=None),
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
) -> list[TransactionResponse]:
    return await list_transactions(db, "expense", user_id, startDate, endDate)


@router.put("/{entry_id}", response_model=TransactionResponse)
async def update_expense(
    entry_id: str,
    payload: TransactionUpdate,
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
) -> TransactionResponse:
    return await update_transaction(db, entry_id, payload, "expense", user_id)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_expense(
    entry_id: str,
    db: AsyncSession = Depends(get_session),
    user_id: UUID = Depends(get_current_user_id),
) -> Response:
    await delete_transaction(db, entry_id, "expense", user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
