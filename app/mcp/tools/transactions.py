from __future__ import annotations

from datetime import date

from uuid import UUID
from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.transaction import TransactionCreate, TransactionUpdate
from app.services.transaction_service import create_transaction, delete_transaction, list_transactions, update_transaction


def parse_optional_date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


async def handle_list_transactions(
    db: AsyncSession,
    user_id: UUID,
    transaction_type: str,
    arguments: dict,
) -> object:
    start_date = parse_optional_date(arguments.get("startDate"))
    end_date = parse_optional_date(arguments.get("endDate"))
    return jsonable_encoder(await list_transactions(db, transaction_type, user_id, start_date, end_date))


async def handle_create_transaction(
    db: AsyncSession,
    user_id: UUID,
    transaction_type: str,
    arguments: dict,
) -> object:
    payload = TransactionCreate(**arguments)
    return jsonable_encoder(await create_transaction(db, payload, transaction_type, user_id))


async def handle_update_transaction(
    db: AsyncSession,
    user_id: UUID,
    transaction_type: str,
    arguments: dict,
) -> object:
    entry_id = arguments["id"]
    payload = TransactionUpdate(**{key: value for key, value in arguments.items() if key != "id"})
    return jsonable_encoder(await update_transaction(db, entry_id, payload, transaction_type, user_id))


async def handle_delete_transaction(
    db: AsyncSession,
    user_id: UUID,
    transaction_type: str,
    arguments: dict,
) -> object:
    await delete_transaction(db, arguments["id"], transaction_type, user_id)
    return {"deleted": True, "id": arguments["id"], "type": transaction_type}
