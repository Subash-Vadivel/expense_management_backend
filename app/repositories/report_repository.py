from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import Date, Float, cast, column, func, or_, true
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.category import Category
from app.models.report import Report, ReportWidget
from app.models.transaction import Transaction
from app.repositories.common import transaction_date_filters

# --- reports & widgets -----------------------------------------------------------------------


async def list_reports_with_counts(db: AsyncSession, business_id: UUID) -> list[tuple[Report, int]]:
    widget_count = (
        select(func.count(ReportWidget.id)).where(ReportWidget.report_id == Report.id).scalar_subquery()
    )
    result = await db.execute(
        select(Report, widget_count).where(Report.business_id == business_id).order_by(Report.updated_at.desc())
    )
    return [(report, int(count or 0)) for report, count in result.all()]


async def get_report(db: AsyncSession, report_id: UUID, business_id: UUID) -> Report | None:
    result = await db.execute(select(Report).where(Report.id == report_id, Report.business_id == business_id))
    return result.scalar_one_or_none()


async def list_widgets(db: AsyncSession, report_id: UUID) -> list[ReportWidget]:
    result = await db.execute(
        select(ReportWidget)
        .where(ReportWidget.report_id == report_id)
        .order_by(ReportWidget.created_at.asc())
    )
    return list(result.scalars().all())


async def get_widget(db: AsyncSession, widget_id: UUID, report_id: UUID) -> ReportWidget | None:
    result = await db.execute(
        select(ReportWidget).where(ReportWidget.id == widget_id, ReportWidget.report_id == report_id)
    )
    return result.scalar_one_or_none()


async def find_categories(db: AsyncSession, business_id: UUID, category_ids: list[UUID]) -> list[Category]:
    result = await db.execute(
        select(Category).where(Category.business_id == business_id, Category.id.in_(category_ids))
    )
    return list(result.scalars().all())


# --- aggregation -----------------------------------------------------------------------------
# Each query returns every aggregate at once (sum, avg, min, max, count) so each series can pick
# the one it asked for, and totals can be derived from the buckets without another round trip.


def bucket_expr(interval: str | None):
    if interval is None:
        return None
    return cast(func.date_trunc(interval, Transaction.date), Date)


def aggregate_columns(value):
    return (
        func.sum(value).label("sum"),
        func.avg(value).label("avg"),
        func.min(value).label("min"),
        func.max(value).label("max"),
        func.count(value).label("count"),
    )


async def aggregate_amounts(
    db: AsyncSession,
    business_id: UUID,
    category_ids: list[UUID],
    interval: str | None,
    start_date: date | None,
    end_date: date | None,
) -> list[dict]:
    """Rows of {bucket, category_id, sum, avg, min, max, count} over transaction amounts."""
    bucket = bucket_expr(interval)
    keys = [bucket.label("bucket")] if bucket is not None else []
    statement = (
        select(*keys, Transaction.category_id, *aggregate_columns(Transaction.amount))
        .where(
            Transaction.business_id == business_id,
            Transaction.category_id.in_(category_ids),
            *transaction_date_filters(start_date, end_date),
        )
        .group_by(*([bucket] if bucket is not None else []), Transaction.category_id)
    )
    result = await db.execute(statement)
    return [dict(row._mapping) for row in result.all()]


async def aggregate_custom_fields(
    db: AsyncSession,
    business_id: UUID,
    category_ids: list[UUID],
    field_ids: list[str],
    interval: str | None,
    start_date: date | None,
    end_date: date | None,
) -> list[dict]:
    """Rows of {bucket, category_id, field_id, sum, avg, min, max, count} over custom field values.

    custom_field_values is a json array of {fieldId, valueNumber | valueString | valueBoolean};
    unnest it per transaction. count is the number of entries where the field is filled (for
    BOOLEAN: set to true); sum/avg/min/max are over valueNumber, so only meaningful for NUMBER fields.
    """
    element = (
        func.json_array_elements(Transaction.custom_field_values)
        .table_valued(column("value", JSON), joins_implicitly=True)
        .render_derived(name="field_value")
    )
    field_id = element.c.value["fieldId"].astext
    number = cast(element.c.value["valueNumber"].astext, Float)
    filled = or_(
        element.c.value["valueNumber"].astext.isnot(None),
        func.trim(element.c.value["valueString"].astext) != "",
        element.c.value["valueBoolean"].astext == "true",
    )
    bucket = bucket_expr(interval)
    keys = [bucket.label("bucket")] if bucket is not None else []
    statement = (
        select(
            *keys,
            Transaction.category_id,
            field_id.label("field_id"),
            *aggregate_columns(number)[:4],
            func.count().label("count"),
        )
        .select_from(Transaction)
        .join(element, true())
        .where(
            Transaction.business_id == business_id,
            Transaction.category_id.in_(category_ids),
            field_id.in_(field_ids),
            filled,
            *transaction_date_filters(start_date, end_date),
        )
        .group_by(*([bucket] if bucket is not None else []), Transaction.category_id, field_id)
    )
    result = await db.execute(statement)
    return [dict(row._mapping) for row in result.all()]


async def transaction_date_bounds(
    db: AsyncSession, business_id: UUID, category_ids: list[UUID]
) -> tuple[date | None, date | None]:
    result = await db.execute(
        select(func.min(Transaction.date), func.max(Transaction.date)).where(
            Transaction.business_id == business_id, Transaction.category_id.in_(category_ids)
        )
    )
    low, high = result.one()
    return low, high
