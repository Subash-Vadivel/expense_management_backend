from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.postgres import get_session
from app.dependencies.auth import BusinessAccess, get_business_access, require_business_role
from app.schemas.report import (
    ReportCreate,
    ReportDetailResponse,
    ReportQueryRequest,
    ReportQueryResponse,
    ReportResponse,
    ReportUpdate,
    WidgetCreate,
    WidgetReorder,
    WidgetResponse,
    WidgetUpdate,
)
from app.services import report_service

router = APIRouter()
editor = require_business_role("owner", "admin", "manager")


@router.post("/query", response_model=ReportQueryResponse)
async def query(
    payload: ReportQueryRequest,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(get_business_access),
) -> ReportQueryResponse:
    return await report_service.run_query(db, payload, access.business.id)


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(get_business_access),
) -> list[ReportResponse]:
    return await report_service.list_reports(db, access.business.id)


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    payload: ReportCreate,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(editor),
) -> ReportResponse:
    return await report_service.create_report(db, payload, access.business.id, access.user.id)


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: str,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(get_business_access),
) -> ReportDetailResponse:
    return await report_service.get_report_detail(db, report_id, access.business.id)


@router.patch("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: str,
    payload: ReportUpdate,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(editor),
) -> ReportResponse:
    return await report_service.update_report(db, report_id, payload, access.business.id)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(
    report_id: str,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(editor),
) -> Response:
    await report_service.delete_report(db, report_id, access.business.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{report_id}/widgets", response_model=WidgetResponse, status_code=status.HTTP_201_CREATED)
async def create_widget(
    report_id: str,
    payload: WidgetCreate,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(editor),
) -> WidgetResponse:
    return await report_service.create_widget(db, report_id, payload, access.business.id)


@router.post("/{report_id}/widgets/reorder", response_model=list[WidgetResponse])
async def reorder_widgets(
    report_id: str,
    payload: WidgetReorder,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(editor),
) -> list[WidgetResponse]:
    return await report_service.reorder_widgets(db, report_id, payload, access.business.id)


@router.patch("/{report_id}/widgets/{widget_id}", response_model=WidgetResponse)
async def update_widget(
    report_id: str,
    widget_id: str,
    payload: WidgetUpdate,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(editor),
) -> WidgetResponse:
    return await report_service.update_widget(db, report_id, widget_id, payload, access.business.id)


@router.delete("/{report_id}/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_widget(
    report_id: str,
    widget_id: str,
    db: AsyncSession = Depends(get_session),
    access: BusinessAccess = Depends(editor),
) -> Response:
    await report_service.delete_widget(db, report_id, widget_id, access.business.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
