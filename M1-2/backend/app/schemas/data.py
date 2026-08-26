from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    field_validator,
)


WeightValue = Annotated[
    Decimal,
    Field(ge=Decimal("20.0"), le=Decimal("300.0"), decimal_places=1),
    PlainSerializer(lambda value: float(value), return_type=float, when_used="json"),
]
MetricValue = Annotated[
    Decimal,
    PlainSerializer(lambda value: float(value), return_type=float, when_used="json"),
]


class DataCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    date: date
    value: WeightValue
    memo: str = Field(default="", max_length=200)

    @field_validator("date")
    @classmethod
    def reject_future_date(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("future dates are not allowed")
        return value


class DataUpdate(DataCreate):
    pass


class DataRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    date: date
    value: WeightValue
    memo: str
    created_at: datetime
    updated_at: datetime


class DataListResponse(BaseModel):
    items: list[DataRecord]
    count: int


class DatePeriod(BaseModel):
    start: date
    end: date


class DateValue(BaseModel):
    date: date
    value: MetricValue


class ExtremeMetric(BaseModel):
    value: MetricValue
    dates: list[date]


class SummaryMetrics(BaseModel):
    average: MetricValue
    max: ExtremeMetric
    min: ExtremeMetric
    first: DateValue
    latest: DateValue
    change: MetricValue


TrendStatus = Literal[
    "no_data",
    "insufficient_data",
    "decrease",
    "maintain",
    "increase",
]


class TrendResult(BaseModel):
    status: TrendStatus
    label: str
    previous_average: MetricValue | None = None
    recent_average: MetricValue | None = None
    difference: MetricValue | None = None


class PeriodStatistics(BaseModel):
    period: DatePeriod | None
    count: int
    metrics: SummaryMetrics | None
    trend: TrendResult


class DataSummary(PeriodStatistics):
    pass
