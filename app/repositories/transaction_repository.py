from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.transaction import Transaction, TransactionType
from app.repositories.common import transaction_date_filters


async def create_transaction(db: AsyncSession, transaction: Transaction) -> UUID:
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    return transaction.id


async def find_transaction_by_id(db: AsyncSession, transaction_id: UUID) -> Transaction | None:
    return await db.get(Transaction, transaction_id)


async def find_transaction_for_user(
    db: AsyncSession,
    transaction_id: UUID,
    transaction_type: TransactionType,
    user_id: UUID,
) -> Transaction | None:
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.created_by == user_id,
            Transaction.type == transaction_type,
        )
    )
    return result.scalar_one_or_none()


async def list_transactions(
    db: AsyncSession,
    transaction_type: TransactionType,
    user_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Transaction]:
    result = await db.execute(
        select(Transaction)
        .where(
            Transaction.created_by == user_id,
            Transaction.type == transaction_type,
            *transaction_date_filters(start_date, end_date),
        )
        .order_by(Transaction.date.desc(), Transaction.created_at.desc())
    )
    return list(result.scalars().all())


async def update_transaction(db: AsyncSession, transaction: Transaction) -> None:
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)


async def delete_transaction(
    db: AsyncSession,
    transaction_id: UUID,
    transaction_type: TransactionType,
    user_id: UUID,
) -> int:
    result = await db.execute(
        delete(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.created_by == user_id,
            Transaction.type == transaction_type,
        )
    )
    await db.commit()
    return result.rowcount or 0
