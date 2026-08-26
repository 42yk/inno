from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from app.schemas.data import DataRecord
from app.services.summary_service import (
    calculate_period_statistics,
    calculate_summary,
)


def make_records(values: list[str]) -> list[DataRecord]:
    created_at = datetime(2025, 1, 1, tzinfo=UTC)
    return [
        DataRecord(
            id=(date(2025, 1, 1) + timedelta(days=index)).isoformat(),
            date=date(2025, 1, 1) + timedelta(days=index),
            value=Decimal(value),
            memo="",
            created_at=created_at,
            updated_at=created_at,
        )
        for index, value in enumerate(values)
    ]


def test_empty_summary_has_explicit_no_data_state() -> None:
    summary = calculate_summary([])

    assert summary.count == 0
    assert summary.period is None
    assert summary.metrics is None
    assert summary.trend.status == "no_data"


def test_summary_calculates_metrics_and_all_tied_dates() -> None:
    records = make_records(["72.0", "75.0", "70.0", "75.0", "70.0"])

    summary = calculate_summary(records)

    assert summary.period.start == date(2025, 1, 1)
    assert summary.period.end == date(2025, 1, 5)
    assert summary.count == 5
    assert summary.metrics.average == Decimal("72.4")
    assert summary.metrics.max.value == Decimal("75.0")
    assert summary.metrics.max.dates == [date(2025, 1, 2), date(2025, 1, 4)]
    assert summary.metrics.min.value == Decimal("70.0")
    assert summary.metrics.min.dates == [date(2025, 1, 3), date(2025, 1, 5)]
    assert summary.metrics.first.value == Decimal("72.0")
    assert summary.metrics.latest.value == Decimal("70.0")
    assert summary.metrics.change == Decimal("-2.0")
    assert summary.trend.status == "insufficient_data"


@pytest.mark.parametrize(
    ("recent_value", "expected_status"),
    [
        ("69.7", "decrease"),
        ("69.8", "maintain"),
        ("70.0", "maintain"),
        ("70.2", "maintain"),
        ("70.3", "increase"),
    ],
)
def test_trend_uses_inclusive_point_two_maintain_band(
    recent_value: str,
    expected_status: str,
) -> None:
    records = make_records((["70.0"] * 10) + ([recent_value] * 10))

    summary = calculate_summary(records)

    assert summary.trend.status == expected_status


def test_period_statistics_sorts_input_and_rounds_half_up() -> None:
    records = list(reversed(make_records(["70.0", "70.1", "70.1"])))

    result = calculate_period_statistics(records)

    assert result.metrics.average == Decimal("70.1")
    assert result.metrics.first.date == date(2025, 1, 1)
    assert result.metrics.latest.date == date(2025, 1, 3)


def test_summary_json_serializes_decimal_metrics_as_numbers() -> None:
    summary = calculate_summary(make_records(["72.4"]))

    payload = summary.model_dump(mode="json")

    assert payload["metrics"]["average"] == pytest.approx(72.4)
