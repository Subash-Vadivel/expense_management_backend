from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

ChartType = Literal["line", "area", "bar", "pie", "donut", "kpi"]


def utc_now() -> datetime:
    return datetime.utcnow()


class Report(SQLModel, table=True):
    __tablename__ = "reports"
    __table_args__ = (Index("ix_reports_business_created", "business_id", "created_at"),)

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    business_id: UUID = Field(sa_column=Column(ForeignKey("business_entities.id", ondelete="CASCADE"), nullable=False, index=True))
    name: str
    description: str | None = None
    created_by: UUID = Field(sa_column=Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ReportWidget(SQLModel, table=True):
    __tablename__ = "report_widgets"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    report_id: UUID = Field(sa_column=Column(ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True))
    title: str
    chart_type: str
    # Validated WidgetConfig (app.schemas.report): interval, dateRange, series.
    config: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    # Grid placement on the report's 12-column layout: {x, y, w, h}.
    layout: dict = Field(default_factory=dict, sa_column=Column(JSONB, nullable=False))
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
