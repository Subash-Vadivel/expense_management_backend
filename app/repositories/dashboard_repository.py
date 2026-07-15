from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.category import CategoryType
from app.models.transaction import Transaction
from app.repositories.common import transaction_date_filters


async def aggregate_summary_totals(
    db: AsyncSession,
    business_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, float]:
    result = await db.execute(
        select(Transaction.type, func.coalesce(func.sum(Transaction.amount), 0.0))
        .where(Transaction.business_id == business_id, *transaction_date_filters(start_date, end_date))
        .group_by(Transaction.type)
    )
    return {row[0]: float(row[1] or 0.0) for row in result.all()}


async def aggregate_monthly_totals(
    db: AsyncSession,
    business_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    month_expr = func.to_char(Transaction.date, "YYYY-MM")
    result = await db.execute(
        select(month_expr.label("month"), Transaction.type, func.coalesce(func.sum(Transaction.amount), 0.0))
        .where(Transaction.business_id == business_id, *transaction_date_filters(start_date, end_date))
        .group_by(month_expr, Transaction.type)
        .order_by(month_expr.asc())
    )
    return [{"month": row[0], "type": row[1], "total": float(row[2] or 0.0)} for row in result.all()]


async def aggregate_category_totals(
    db: AsyncSession,
    business_id: UUID,
    category_type: CategoryType,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[dict]:
    result = await db.execute(
        select(
            Transaction.category_id,
            Transaction.category_name,
            func.coalesce(func.sum(Transaction.amount), 0.0).label("total"),
        )
        .where(
            Transaction.business_id == business_id,
            Transaction.type == category_type,
            *transaction_date_filters(start_date, end_date),
        )
        .group_by(Transaction.category_id, Transaction.category_name)
        .order_by(func.coalesce(func.sum(Transaction.amount), 0.0).desc())
    )
    return [
        {"category_id": row[0], "category_name": row[1], "total": float(row[2] or 0.0)}
        for row in result.all()
    ]
