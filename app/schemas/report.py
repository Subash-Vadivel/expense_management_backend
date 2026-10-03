from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

ChartType = Literal["line", "area", "bar", "pie", "donut"]
WidgetWidth = Literal["half", "full"]
Interval = Literal["day", "week", "month"]
# percent: share of the category's entries where a STRING/BOOLEAN field is filled (true).
Aggregation = Literal["sum", "avg", "min", "max", "count", "percent"]
MAX_SERIES = 8


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AmountMetric(StrictModel):
    kind: Literal["amount"] = "amount"


class FieldMetric(StrictModel):
    kind: Literal["field"]
    fieldId: str = Field(min_length=1, max_length=64)


Metric = Annotated[Union[AmountMetric, FieldMetric], Field(discriminator="kind")]


class SeriesConfig(StrictModel):
    id: str = Field(min_length=1, max_length=64)
    label: str | None = Field(default=None, max_length=80)
    categoryId: str
    metric: Metric = Field(default_factory=AmountMetric)
    aggregation: Aggregation = "sum"


class ReportRangeMode(StrictModel):
    mode: Literal["report"] = "report"


class CustomRangeMode(StrictModel):
    mode: Literal["custom"]
    startDate: date
    endDate: date

    @model_validator(mode="after")
    def check_order(self) -> "CustomRangeMode":
        if self.startDate > self.endDate:
            raise ValueError("startDate cannot be after endDate")
        return self


WidgetDateRange = Annotated[Union[ReportRangeMode, CustomRangeMode], Field(discriminator="mode")]


class WidgetConfig(StrictModel):
    interval: Interval = "month"
    dateRange: WidgetDateRange = Field(default_factory=ReportRangeMode)
    series: list[SeriesConfig] = Field(min_length=1, max_length=MAX_SERIES)


class ReportCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class ReportUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class WidgetCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    chartType: ChartType
    config: WidgetConfig
    width: WidgetWidth = "half"


class WidgetUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    chartType: ChartType | None = None
    config: WidgetConfig | None = None
    width: WidgetWidth | None = None


class WidgetReorder(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=200)


class WidgetResponse(BaseModel):
    id: str
    reportId: str
    title: str
    chartType: ChartType
    config: WidgetConfig
    position: int
    width: WidgetWidth
    createdAt: datetime
    updatedAt: datetime


class ReportResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    widgetCount: int = 0
    createdBy: str
    createdAt: datetime
    updatedAt: datetime


class ReportDetailResponse(ReportResponse):
    widgets: list[WidgetResponse] = Field(default_factory=list)


class ReportQueryRequest(BaseModel):
    chartType: ChartType
    config: WidgetConfig
    # The effective range: the report's filter, or the widget's own range when it overrides.
    startDate: date | None = None
    endDate: date | None = None


class QueryBucket(BaseModel):
    key: date
    label: str


class QuerySeries(BaseModel):
    id: str
    label: str
    unit: Literal["currency", "number", "percent"]
    aggregation: Aggregation
    values: list[float | None]
    total: float | None


class ReportQueryResponse(BaseModel):
    buckets: list[QueryBucket]
    series: list[QuerySeries]
