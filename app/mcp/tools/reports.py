"""Report MCP tools. Validation (categories, fields, aggregations, sizes) lives in report_service."""
from __future__ import annotations

from datetime import date

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.workspace import WorkspaceContext
from app.schemas.report import ChartType, ReportCreate, ReportUpdate, WidgetConfig, WidgetCreate, WidgetUpdate
from app.services import report_service


class StrictArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReportIdArgs(StrictArgs):
    reportId: str


class WidgetIdArgs(StrictArgs):
    reportId: str
    widgetId: str


class CreateWidgetArgs(StrictArgs):
    reportId: str
    title: str = Field(min_length=1, max_length=120)
    chartType: ChartType
    config: WidgetConfig


class UpdateWidgetArgs(StrictArgs):
    reportId: str
    widgetId: str
    title: str | None = Field(default=None, min_length=1, max_length=120)
    chartType: ChartType | None = None
    config: WidgetConfig | None = None


class UpdateReportArgs(StrictArgs):
    reportId: str
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class WidgetDataArgs(StrictArgs):
    reportId: str
    widgetId: str
    startDate: date | None = None
    endDate: date | None = None


async def handle_list_reports(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    StrictArgs(**arguments)
    reports = await report_service.list_reports(db, ctx.business_id)
    return {
        "reports": [
            {"id": r.id, "name": r.name, "description": r.description, "widgetCount": r.widgetCount}
            for r in reports
        ]
    }


async def handle_get_report(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    args = ReportIdArgs(**arguments)
    return jsonable_encoder(await report_service.get_report_detail(db, args.reportId, ctx.business_id))


async def handle_create_report(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    report = await report_service.create_report(db, ReportCreate(**arguments), ctx.business_id, ctx.user_id)
    return jsonable_encoder(report)


async def handle_delete_report(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    args = ReportIdArgs(**arguments)
    await report_service.delete_report(db, args.reportId, ctx.business_id)
    return {"deleted": True, "reportId": args.reportId}


async def handle_create_widget(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    args = CreateWidgetArgs(**arguments)
    widget = await report_service.create_widget(
        db,
        args.reportId,
        WidgetCreate(title=args.title, chartType=args.chartType, config=args.config),
        ctx.business_id,
    )
    return jsonable_encoder(widget)


async def handle_delete_widget(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    args = WidgetIdArgs(**arguments)
    await report_service.delete_widget(db, args.reportId, args.widgetId, ctx.business_id)
    return {"deleted": True, "reportId": args.reportId, "widgetId": args.widgetId}


async def handle_update_widget(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    args = UpdateWidgetArgs(**arguments)
    widget = await report_service.update_widget(
        db,
        args.reportId,
        args.widgetId,
        WidgetUpdate(title=args.title, chartType=args.chartType, config=args.config),
        ctx.business_id,
    )
    return jsonable_encoder(widget)


async def handle_update_report(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    args = UpdateReportArgs(**arguments)
    # Only fields the caller sent change (description: null clears it).
    changes = {key: value for key, value in arguments.items() if key in ("name", "description")}
    report = await report_service.update_report(db, args.reportId, ReportUpdate(**changes), ctx.business_id)
    return jsonable_encoder(report)


async def handle_get_widget_data(db: AsyncSession, ctx: WorkspaceContext, arguments: dict) -> object:
    args = WidgetDataArgs(**arguments)
    data = await report_service.get_widget_data(
        db, args.reportId, args.widgetId, ctx.business_id, args.startDate, args.endDate
    )
    return jsonable_encoder(data)
