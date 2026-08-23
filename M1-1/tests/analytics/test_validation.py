from __future__ import annotations

import pandas as pd
import pytest

from seoul_weather.analytics.validation import validate_daily_data
from seoul_weather.config import AnalysisConfig
from seoul_weather.errors import AnalysisValidationError


def make_daily_frame(start: str, end: str, avg_temp_c: float = 10.0) -> pd.DataFrame:
    dates = pd.date_range(start, end, freq="D")
    return pd.DataFrame(
        {
            "station_id": 108,
            "station_name": "서울",
            "date": dates,
            "avg_temp_c": avg_temp_c,
            "min_temp_c": avg_temp_c - 3.0,
            "max_temp_c": avg_temp_c + 3.0,
            "precipitation_mm": 0.0,
            "avg_humidity_pct": 60.0,
        }
    )


def test_validate_daily_data_reports_complete_calendar_and_missing_counts() -> None:
    frame = make_daily_frame("2024-02-01", "2024-02-29")
    frame.loc[0, "avg_temp_c"] = float("nan")
    config = AnalysisConfig(start_date="2024-02-01", end_date="2024-02-29")

    quality = validate_daily_data(frame, config)

    assert quality["row_count"] == 29
    assert quality["unique_date_count"] == 29
    assert quality["missing_calendar_date_count"] == 0
    assert quality["missing_counts"]["avg_temp_c"] == 1
    assert quality["missing_rates_pct"]["avg_temp_c"] == pytest.approx(100 / 29)


def test_validate_daily_data_rejects_missing_calendar_date() -> None:
    frame = make_daily_frame("2024-01-01", "2024-01-03").drop(index=1)
    config = AnalysisConfig(start_date="2024-01-01", end_date="2024-01-03")

    with pytest.raises(AnalysisValidationError, match="누락 날짜"):
        validate_daily_data(frame, config)


def test_validate_daily_data_rejects_duplicate_date() -> None:
    frame = make_daily_frame("2024-01-01", "2024-01-02")
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    config = AnalysisConfig(start_date="2024-01-01", end_date="2024-01-02")

    with pytest.raises(AnalysisValidationError, match="중복 날짜"):
        validate_daily_data(frame, config)


def test_validate_daily_data_rejects_non_seoul_station() -> None:
    frame = make_daily_frame("2024-01-01", "2024-01-02")
    frame.loc[1, "station_id"] = 109
    config = AnalysisConfig(start_date="2024-01-01", end_date="2024-01-02")

    with pytest.raises(AnalysisValidationError, match="지점"):
        validate_daily_data(frame, config)


def test_validate_daily_data_rejects_non_seoul_station_name() -> None:
    frame = make_daily_frame("2024-01-01", "2024-01-02")
    frame.loc[1, "station_name"] = "부산"
    config = AnalysisConfig(start_date="2024-01-01", end_date="2024-01-02")

    with pytest.raises(AnalysisValidationError, match="지점명"):
        validate_daily_data(frame, config)


def test_validate_daily_data_flags_temperature_order_without_deleting_row() -> None:
    frame = make_daily_frame("2024-01-01", "2024-01-02")
    frame.loc[0, "min_temp_c"] = 12.0
    config = AnalysisConfig(start_date="2024-01-01", end_date="2024-01-02")

    quality = validate_daily_data(frame, config)

    assert quality["temperature_order_violation_count"] == 1
    assert quality["temperature_order_violation_dates"] == ["2024-01-01"]


def test_validate_daily_data_flags_humidity_and_precipitation_ranges() -> None:
    frame = make_daily_frame("2024-01-01", "2024-01-02")
    frame.loc[0, "avg_humidity_pct"] = 101.0
    frame.loc[1, "precipitation_mm"] = -0.1
    config = AnalysisConfig(start_date="2024-01-01", end_date="2024-01-02")

    quality = validate_daily_data(frame, config)

    assert quality["humidity_range_violation_count"] == 1
    assert quality["negative_precipitation_count"] == 1


def test_validate_daily_data_flags_implausible_temperature_without_deleting() -> None:
    frame = make_daily_frame("2024-01-01", "2024-01-02")
    frame.loc[0, ["avg_temp_c", "min_temp_c", "max_temp_c"]] = [
        999.0,
        998.0,
        1000.0,
    ]
    config = AnalysisConfig(start_date="2024-01-01", end_date="2024-01-02")

    quality = validate_daily_data(frame, config)

    assert len(frame) == 2
    assert quality["temperature_range_violation_count"] == 1
    assert quality["temperature_range_violation_dates"] == ["2024-01-01"]
