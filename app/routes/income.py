from __future__ import annotations

from datetime import date

from bson import ObjectId
from fastapi import APIRouter, Depends, Query, Response, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database.mongodb import get_database
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
async def create_income(
    payload: TransactionCreate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    user_id: ObjectId = Depends(get_current_user_id),
) -> TransactionResponse:
    return await create_transaction(db, payload, "income", user_id)


@router.get("", response_model=list[TransactionResponse])
async def list_income(
    startDate: date | None = Query(default=None),
    endDate: date | None = Query(default=None),
    db: AsyncIOMotorDatabase = Depends(get_database),
    user_id: ObjectId = Depends(get_current_user_id),
) -> list[TransactionResponse]:
    return await list_transactions(db, "income", user_id, startDate, endDate)


@router.put("/{entry_id}", response_model=TransactionResponse)
async def update_income(
    entry_id: str,
    payload: TransactionUpdate,
    db: AsyncIOMotorDatabase = Depends(get_database),
    user_id: ObjectId = Depends(get_current_user_id),
) -> TransactionResponse:
    return await update_transaction(db, entry_id, payload, "income", user_id)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_income(
    entry_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database),
    user_id: ObjectId = Depends(get_current_user_id),
) -> Response:
    await delete_transaction(db, entry_id, "income", user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
