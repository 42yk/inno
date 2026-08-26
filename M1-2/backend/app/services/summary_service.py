from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.data import (
    DataRecord,
    DataSummary,
    DatePeriod,
    DateValue,
    ExtremeMetric,
    PeriodStatistics,
    SummaryMetrics,
    TrendResult,
)


ONE_DECIMAL = Decimal("0.1")


def _round(value: Decimal) -> Decimal:
    return value.quantize(ONE_DECIMAL, rounding=ROUND_HALF_UP)


def _average(records: Sequence[DataRecord]) -> Decimal:
    return sum((record.value for record in records), Decimal("0")) / Decimal(
        len(records)
    )


def _trend(records: Sequence[DataRecord]) -> TrendResult:
    if not records:
        return TrendResult(status="no_data", label="데이터 없음")
    if len(records) < 20:
        return TrendResult(status="insufficient_data", label="데이터 부족")

    previous_average = _average(records[-20:-10])
    recent_average = _average(records[-10:])
    difference = recent_average - previous_average
    if difference < Decimal("-0.2"):
        status = "decrease"
        label = "감소"
    elif difference > Decimal("0.2"):
        status = "increase"
        label = "증가"
    else:
        status = "maintain"
        label = "유지"
    return TrendResult(
        status=status,
        label=label,
        previous_average=_round(previous_average),
        recent_average=_round(recent_average),
        difference=_round(difference),
    )


def calculate_period_statistics(
    records: Sequence[DataRecord],
) -> PeriodStatistics:
    ordered = sorted(records, key=lambda record: record.date)
    if not ordered:
        return PeriodStatistics(
            period=None,
            count=0,
            metrics=None,
            trend=_trend(ordered),
        )

    maximum = max(record.value for record in ordered)
    minimum = min(record.value for record in ordered)
    first = ordered[0]
    latest = ordered[-1]
    metrics = SummaryMetrics(
        average=_round(_average(ordered)),
        max=ExtremeMetric(
            value=maximum,
            dates=[record.date for record in ordered if record.value == maximum],
        ),
        min=ExtremeMetric(
            value=minimum,
            dates=[record.date for record in ordered if record.value == minimum],
        ),
        first=DateValue(date=first.date, value=first.value),
        latest=DateValue(date=latest.date, value=latest.value),
        change=_round(latest.value - first.value),
    )
    return PeriodStatistics(
        period=DatePeriod(start=first.date, end=latest.date),
        count=len(ordered),
        metrics=metrics,
        trend=_trend(ordered),
    )


def calculate_summary(records: Sequence[DataRecord]) -> DataSummary:
    statistics = calculate_period_statistics(records)
    return DataSummary.model_validate(statistics.model_dump())
