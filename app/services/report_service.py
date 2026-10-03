from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.common import parse_uuid
from app.models.report import Report, ReportWidget
from app.repositories import report_repository
from app.schemas.report import (
    WIDGET_SIZES,
    QueryBucket,
    QuerySeries,
    ReportCreate,
    ReportDetailResponse,
    ReportLayoutUpdate,
    ReportQueryRequest,
    ReportQueryResponse,
    ReportResponse,
    ReportUpdate,
    SeriesConfig,
    WidgetConfig,
    WidgetCreate,
    WidgetLayout,
    WidgetResponse,
    WidgetUpdate,
)
from app.services.dashboard_service import validate_date_range

MAX_BUCKETS = 366
PIE_TYPES = {"pie", "donut"}
# Chart types with no date axis: one total per series over the range.
TOTAL_ONLY_TYPES = PIE_TYPES | {"kpi"}
# Which aggregations make sense for each metric.
AMOUNT_AGGREGATIONS = {"sum", "avg", "min", "max", "count"}
NUMBER_FIELD_AGGREGATIONS = {"sum", "avg", "min", "max"}
OTHER_FIELD_AGGREGATIONS = {"count", "percent"}
AGGREGATION_NAMES = {"avg": "avg", "min": "min", "max": "max"}
INTERVAL_NAMES = {"day": "days", "week": "weeks", "month": "months"}


def bad_request(message: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)


def not_found(label: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None


# --- serialization ---------------------------------------------------------------------------


def report_to_response(report: Report, widget_count: int) -> ReportResponse:
    return ReportResponse(
        id=str(report.id),
        name=report.name,
        description=report.description,
        widgetCount=widget_count,
        createdBy=str(report.created_by),
        createdAt=report.created_at,
        updatedAt=report.updated_at,
    )


def widget_to_response(widget: ReportWidget) -> WidgetResponse:
    return WidgetResponse(
        id=str(widget.id),
        reportId=str(widget.report_id),
        title=widget.title,
        chartType=widget.chart_type,
        config=WidgetConfig.model_validate(widget.config),
        layout=WidgetLayout.model_validate(widget.layout),
        createdAt=widget.created_at,
        updatedAt=widget.updated_at,
    )


# --- reports ---------------------------------------------------------------------------------


async def list_reports(db: AsyncSession, business_id: UUID) -> list[ReportResponse]:
    rows = await report_repository.list_reports_with_counts(db, business_id)
    return [report_to_response(report, count) for report, count in rows]


async def load_report(db: AsyncSession, report_id: str, business_id: UUID) -> Report:
    report = await report_repository.get_report(db, parse_uuid(report_id, "report id"), business_id)
    if not report:
        raise not_found("Report")
    return report


async def get_report_detail(db: AsyncSession, report_id: str, business_id: UUID) -> ReportDetailResponse:
    report = await load_report(db, report_id, business_id)
    widgets = await report_repository.list_widgets(db, report.id)
    return ReportDetailResponse(
        **report_to_response(report, len(widgets)).model_dump(),
        widgets=[widget_to_response(widget) for widget in widgets],
    )


async def create_report(db: AsyncSession, payload: ReportCreate, business_id: UUID, user_id: UUID) -> ReportResponse:
    name = clean_text(payload.name)
    if not name:
        raise bad_request("Name is required")
    report = Report(business_id=business_id, name=name, description=clean_text(payload.description), created_by=user_id)
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report_to_response(report, 0)


async def update_report(db: AsyncSession, report_id: str, payload: ReportUpdate, business_id: UUID) -> ReportResponse:
    report = await load_report(db, report_id, business_id)
    fields = payload.model_fields_set
    if "name" in fields:
        name = clean_text(payload.name)
        if not name:
            raise bad_request("Name is required")
        report.name = name
    if "description" in fields:
        report.description = clean_text(payload.description)
    report.updated_at = datetime.utcnow()
    db.add(report)
    await db.commit()
    await db.refresh(report)
    widgets = await report_repository.list_widgets(db, report.id)
    return report_to_response(report, len(widgets))


async def delete_report(db: AsyncSession, report_id: str, business_id: UUID) -> None:
    report = await load_report(db, report_id, business_id)
    await db.delete(report)
    await db.commit()


# --- widgets ---------------------------------------------------------------------------------

def fit_layout(chart_type: str, layout: WidgetLayout) -> WidgetLayout:
    """Clamp a layout into the chart type's min..max size (and the grid)."""
    sizes = WIDGET_SIZES[chart_type]
    (min_w, min_h), (max_w, max_h) = sizes["min"], sizes["max"]
    w = min(max(layout.w, min_w), max_w)
    h = min(max(layout.h, min_h), max_h)
    return WidgetLayout(x=min(layout.x, 12 - w), y=layout.y, w=w, h=h)


def check_layout(chart_type: str, layout: WidgetLayout) -> None:
    sizes = WIDGET_SIZES[chart_type]
    (min_w, min_h), (max_w, max_h) = sizes["min"], sizes["max"]
    if not (min_w <= layout.w <= max_w and min_h <= layout.h <= max_h):
        raise bad_request(
            f"A {chart_type} widget must be {min_w}-{max_w} columns wide and {min_h}-{max_h} rows tall"
        )


def default_layout(chart_type: str, widgets: list[ReportWidget]) -> WidgetLayout:
    """The chart type's default size, below the existing widgets."""
    w, h = WIDGET_SIZES[chart_type]["default"]
    return WidgetLayout(x=0, y=bottom_of(widgets), w=w, h=h)


def bottom_of(widgets: list[ReportWidget]) -> int:
    return max((w.layout.get("y", 0) + w.layout.get("h", 0) for w in widgets), default=0)



async def touch(db: AsyncSession, report: Report) -> None:
    report.updated_at = datetime.utcnow()
    db.add(report)


async def create_widget(
    db: AsyncSession, report_id: str, payload: WidgetCreate, business_id: UUID
) -> WidgetResponse:
    report = await load_report(db, report_id, business_id)
    check_series_count(payload.chartType, payload.config)
    await resolve_series(db, business_id, payload.config.series)
    if payload.layout:
        check_layout(payload.chartType, payload.layout)
    layout = payload.layout or default_layout(payload.chartType, await report_repository.list_widgets(db, report.id))
    widget = ReportWidget(
        report_id=report.id,
        title=clean_text(payload.title) or "Untitled widget",
        chart_type=payload.chartType,
        config=payload.config.model_dump(mode="json"),
        layout=layout.model_dump(),
    )
    db.add(widget)
    await touch(db, report)
    await db.commit()
    await db.refresh(widget)
    return widget_to_response(widget)


async def load_widget(db: AsyncSession, report: Report, widget_id: str) -> ReportWidget:
    widget = await report_repository.get_widget(db, parse_uuid(widget_id, "widget id"), report.id)
    if not widget:
        raise not_found("Widget")
    return widget


async def update_widget(
    db: AsyncSession, report_id: str, widget_id: str, payload: WidgetUpdate, business_id: UUID
) -> WidgetResponse:
    report = await load_report(db, report_id, business_id)
    widget = await load_widget(db, report, widget_id)
    if payload.title is not None:
        widget.title = clean_text(payload.title) or widget.title
    if payload.chartType is not None:
        widget.chart_type = payload.chartType
    if payload.config is not None:
        await resolve_series(db, business_id, payload.config.series)
        widget.config = payload.config.model_dump(mode="json")
    check_series_count(widget.chart_type, WidgetConfig.model_validate(widget.config))
    # Changing the chart type (e.g. line -> KPI) brings the size within the new type's limits.
    widget.layout = fit_layout(widget.chart_type, WidgetLayout.model_validate(widget.layout)).model_dump()
    widget.updated_at = datetime.utcnow()
    db.add(widget)
    await touch(db, report)
    await db.commit()
    await db.refresh(widget)
    return widget_to_response(widget)


async def delete_widget(db: AsyncSession, report_id: str, widget_id: str, business_id: UUID) -> None:
    report = await load_report(db, report_id, business_id)
    widget = await load_widget(db, report, widget_id)
    await db.delete(widget)
    await touch(db, report)
    await db.commit()


async def save_layout(
    db: AsyncSession, report_id: str, payload: ReportLayoutUpdate, business_id: UUID
) -> list[WidgetResponse]:
    report = await load_report(db, report_id, business_id)
    widgets = await report_repository.list_widgets(db, report.id)
    by_id = {str(widget.id): widget for widget in widgets}
    unknown = [item.id for item in payload.items if item.id not in by_id]
    if unknown:
        raise bad_request("Layout includes widgets that are not in this report")
    for item in payload.items:
        widget = by_id[item.id]
        layout = WidgetLayout.model_validate(item.model_dump(exclude={"id"}))
        check_layout(widget.chart_type, layout)
        widget.layout = layout.model_dump()
        db.add(widget)
    await touch(db, report)
    await db.commit()
    return [widget_to_response(widget) for widget in widgets]


# --- query -----------------------------------------------------------------------------------


async def resolve_series(
    db: AsyncSession, business_id: UUID, series: list[SeriesConfig]
) -> dict[str, tuple[Category, dict | None]]:
    """Check every series points at a category in this business (and one of its custom fields),
    with an aggregation that suits the metric.

    Returns {series id: (category, field definition or None for amount)}.
    """
    ids = {s.id for s in series}
    if len(ids) != len(series):
        raise bad_request("Series ids must be unique")
    category_ids = {parse_uuid(s.categoryId, "category id") for s in series}
    categories = {c.id: c for c in await report_repository.find_categories(db, business_id, list(category_ids))}
    resolved: dict[str, tuple[Category, dict | None]] = {}
    for s in series:
        category = categories.get(parse_uuid(s.categoryId, "category id"))
        if not category:
            raise bad_request("A selected category was not found in this business")
        field = None
        allowed = AMOUNT_AGGREGATIONS
        if s.metric.kind == "field":
            field = next((f for f in category.custom_fields or [] if f.get("id") == s.metric.fieldId), None)
            if not field:
                raise bad_request(f"{category.name} has no custom field with that id")
            allowed = NUMBER_FIELD_AGGREGATIONS if field.get("type") == "NUMBER" else OTHER_FIELD_AGGREGATIONS
        if s.aggregation not in allowed:
            metric = field["name"] if field else "Amount"
            raise bad_request(f"{metric} supports {', '.join(sorted(allowed))}, not {s.aggregation}")
        resolved[s.id] = (category, field)
    return resolved


def bucket_start(value: date, interval: str) -> date:
    if interval == "week":
        return value - timedelta(days=value.weekday())  # Monday, like Postgres date_trunc('week')
    if interval == "month":
        return value.replace(day=1)
    return value


def next_bucket(value: date, interval: str) -> date:
    if interval == "day":
        return value + timedelta(days=1)
    if interval == "week":
        return value + timedelta(weeks=1)
    return date(value.year + (value.month == 12), value.month % 12 + 1, 1)


def bucket_label(value: date, interval: str) -> str:
    if interval == "month":
        return value.strftime("%b %Y")
    if interval == "week":
        return f"Wk of {value.strftime('%d %b')}"
    return value.strftime("%d %b")


def build_buckets(start: date, end: date, interval: str) -> list[date]:
    keys: list[date] = []
    current = bucket_start(start, interval)
    while current <= end:
        keys.append(current)
        if len(keys) > MAX_BUCKETS:
            raise bad_request(
                f"This range has more than {MAX_BUCKETS} {INTERVAL_NAMES[interval]}. "
                "Pick a shorter range or a larger interval."
            )
        current = next_bucket(current, interval)
    return keys


def pick(row: dict | None, aggregation: str) -> float | None:
    if row is None:
        return 0.0 if aggregation == "count" else None
    value = row[aggregation]
    return float(value) if value is not None else None


def combine(rows: list[dict], aggregation: str) -> float | None:
    """Combine per-bucket aggregates into one total for the whole range."""
    rows = [row for row in rows if row and row["count"]]
    if aggregation == "count":
        return float(sum(row["count"] for row in rows))
    if not rows:
        return None
    if aggregation == "sum":
        return float(sum(row["sum"] for row in rows))
    if aggregation == "min":
        return float(min(row["min"] for row in rows))
    if aggregation == "max":
        return float(max(row["max"] for row in rows))
    # Weighted average across buckets: total sum / total count.
    return float(sum(row["sum"] for row in rows) / sum(row["count"] for row in rows))


def percent(filled: float | None, entries: float | None) -> float | None:
    if not entries:
        return None
    return float(filled or 0) / float(entries) * 100


def series_label(series: SeriesConfig, category: Category, field: dict | None) -> str:
    if series.label and series.label.strip():
        return series.label.strip()
    if series.aggregation == "percent":
        return f"{category.name} · {field['name']} %"
    if series.aggregation == "count":
        return f"{category.name} · {field['name'] + ' entries' if field else 'Entries'}"
    metric = field["name"] if field else "Amount"
    suffix = "" if series.aggregation == "sum" else f" ({AGGREGATION_NAMES[series.aggregation]})"
    return f"{category.name} · {metric}{suffix}"


def check_series_count(chart_type: str, config: WidgetConfig) -> None:
    if chart_type == "kpi" and len(config.series) != 1:
        raise bad_request("A KPI widget shows exactly one series")


def previous_period(start: date, end: date) -> tuple[date, date]:
    """The equally long period ending the day before start (e.g. 30 days -> the 30 days before)."""
    length = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    return previous_end - timedelta(days=length - 1), previous_end


async def run_query(db: AsyncSession, payload: ReportQueryRequest, business_id: UUID) -> ReportQueryResponse:
    validate_date_range(payload.startDate, payload.endDate)
    config = payload.config
    resolved = await resolve_series(db, business_id, config.series)
    category_ids = sorted({category.id for category, _ in resolved.values()}, key=str)
    check_series_count(payload.chartType, config)
    interval = None if payload.chartType in TOTAL_ONLY_TYPES else config.interval

    # Percent series divide by the category's entry count, which the amount query provides.
    amount_categories = {
        resolved[s.id][0].id for s in config.series if s.metric.kind == "amount" or s.aggregation == "percent"
    }
    field_series = [s for s in config.series if s.metric.kind == "field"]

    amount_rows = (
        await report_repository.aggregate_amounts(
            db, business_id, sorted(amount_categories, key=str), interval, payload.startDate, payload.endDate
        )
        if amount_categories
        else []
    )
    field_rows = (
        await report_repository.aggregate_custom_fields(
            db,
            business_id,
            sorted({parse_uuid(s.categoryId) for s in field_series}, key=str),
            sorted({s.metric.fieldId for s in field_series}),
            interval,
            payload.startDate,
            payload.endDate,
        )
        if field_series
        else []
    )

    # rows keyed by (bucket or None, category_id, field_id or None)
    indexed: dict[tuple, dict] = {}
    for row in amount_rows:
        indexed[(row.get("bucket"), row["category_id"], None)] = row
    for row in field_rows:
        indexed[(row.get("bucket"), row["category_id"], row["field_id"])] = row

    buckets: list[date] = []
    if interval:
        start, end = payload.startDate, payload.endDate
        if not start or not end:
            low, high = await report_repository.transaction_date_bounds(db, business_id, category_ids)
            start, end = start or low, end or high
        if start and end and start <= end:
            buckets = build_buckets(start, end, interval)

    series_out: list[QuerySeries] = []
    for s in config.series:
        category, field = resolved[s.id]
        field_id = field["id"] if field else None
        keys = buckets if interval else [None]
        rows = [indexed.get((bucket, category.id, field_id)) for bucket in keys]
        if s.aggregation == "percent":
            entries = [indexed.get((bucket, category.id, None)) for bucket in keys]
            values = [percent(row and row["count"], entry and entry["count"]) for row, entry in zip(rows, entries)]
            total = percent(
                sum(row["count"] for row in rows if row), sum(entry["count"] for entry in entries if entry)
            )
        else:
            values = [pick(row, s.aggregation) for row in rows]
            total = combine([row for row in rows if row], s.aggregation)
        if not interval:
            values = []
        unit = "currency" if not field and s.aggregation != "count" else "number"
        series_out.append(
            QuerySeries(
                id=s.id,
                label=series_label(s, category, field),
                unit="percent" if s.aggregation == "percent" else unit,
                aggregation=s.aggregation,
                values=values,
                total=total,
            )
        )
    if payload.chartType == "kpi" and payload.startDate and payload.endDate:
        previous = previous_period(payload.startDate, payload.endDate)
        prior = await run_query(
            db,
            payload.model_copy(update={"chartType": "pie", "startDate": previous[0], "endDate": previous[1]}),
            business_id,
        )
        for current, before in zip(series_out, prior.series):
            current.previousTotal = before.total
    return ReportQueryResponse(
        buckets=[QueryBucket(key=bucket, label=bucket_label(bucket, interval)) for bucket in buckets],
        series=series_out,
    )


async def get_widget_data(
    db: AsyncSession,
    report_id: str,
    widget_id: str,
    business_id: UUID,
    start_date: date | None,
    end_date: date | None,
) -> dict:
    """A saved widget's computed data. Widgets pinned to their own range ignore start/end."""
    report = await load_report(db, report_id, business_id)
    widget = await load_widget(db, report, widget_id)
    config = WidgetConfig.model_validate(widget.config)
    if config.dateRange.mode == "custom":
        start_date, end_date = config.dateRange.startDate, config.dateRange.endDate
    data = await run_query(
        db,
        ReportQueryRequest(chartType=widget.chart_type, config=config, startDate=start_date, endDate=end_date),
        business_id,
    )
    return {
        "widgetId": str(widget.id),
        "title": widget.title,
        "chartType": widget.chart_type,
        "range": {"startDate": start_date, "endDate": end_date, "pinnedByWidget": config.dateRange.mode == "custom"},
        **data.model_dump(),
    }
