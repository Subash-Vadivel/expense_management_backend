from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.sql.elements import ColumnElement

from app.models.transaction import Transaction


def transaction_date_filters(
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = []
    if start_date:
        filters.append(Transaction.date >= start_date)
    if end_date:
        filters.append(Transaction.date <= end_date)
    return filters


def owner_filter(column, user_id: UUID):
    return column == user_id
