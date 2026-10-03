from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import delete, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.transaction import Transaction, TransactionType
from app.repositories.common import transaction_date_filters
from app.schemas.pagination import LIKE_ESCAPE, SortOrder, like_pattern

SORT_COLUMNS = {
    "date": Transaction.date,
    "amount": Transaction.amount,
    "category": Transaction.category_name,
}


async def create_transaction(db: AsyncSession, transaction: Transaction) -> UUID:
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)
    return transaction.id


async def find_transaction_by_id(db: AsyncSession, transaction_id: UUID) -> Transaction | None:
    return await db.get(Transaction, transaction_id)


async def find_transaction_for_business(
    db: AsyncSession,
    transaction_id: UUID,
    transaction_type: TransactionType,
    business_id: UUID,
) -> Transaction | None:
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.business_id == business_id,
            Transaction.type == transaction_type,
        )
    )
    return result.scalar_one_or_none()


def list_filters(
    transaction_type: TransactionType,
    business_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    search: str | None = None,
) -> list:
    filters = [
        Transaction.business_id == business_id,
        Transaction.type == transaction_type,
        *transaction_date_filters(start_date, end_date),
    ]
    if search:
        pattern = like_pattern(search)
        filters.append(
            or_(
                Transaction.description.ilike(pattern, escape=LIKE_ESCAPE),
                Transaction.category_name.ilike(pattern, escape=LIKE_ESCAPE),
            )
        )
    return filters


async def list_transactions(
    db: AsyncSession,
    filters: list,
    sort: str = "date",
    order: SortOrder = "desc",
    limit: int = 50,
    offset: int = 0,
) -> list[Transaction]:
    sort_column = SORT_COLUMNS[sort]
    primary = sort_column.asc() if order == "asc" else sort_column.desc()
    result = await db.execute(
        select(Transaction)
        .where(*filters)
        # Tie-breakers keep page boundaries stable when many rows share the sort value.
        .order_by(primary, Transaction.date.desc(), Transaction.created_at.desc(), Transaction.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def summarize_transactions(db: AsyncSession, filters: list) -> tuple[int, float, int]:
    result = await db.execute(
        select(
            func.count(Transaction.id),
            func.coalesce(func.sum(Transaction.amount), 0),
            func.count(func.distinct(Transaction.category_id)),
        ).where(*filters)
    )
    count, total_amount, categories_used = result.one()
    return int(count), float(total_amount or 0), int(categories_used)


async def update_transaction(db: AsyncSession, transaction: Transaction) -> None:
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction)


async def delete_transaction(
    db: AsyncSession,
    transaction_id: UUID,
    transaction_type: TransactionType,
    business_id: UUID,
) -> int:
    result = await db.execute(
        delete(Transaction).where(
            Transaction.id == transaction_id,
            Transaction.business_id == business_id,
            Transaction.type == transaction_type,
        )
    )
    await db.commit()
    return result.rowcount or 0
