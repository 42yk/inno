from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest

from seoul_weather.analytics.anomalies import (
    compute_daily_anomalies,
    select_anomaly_annotations,
)
from seoul_weather.analytics.features import add_time_features
from seoul_weather.analytics.statistics import (
    compute_annual_statistics,
    compute_monthly_statistics,
    compute_seasonal_statistics,
    fit_annual_linear_trend,
)
from seoul_weather.analytics.summary import build_analysis_summary
from seoul_weather.config import AnalysisConfig
from seoul_weather.errors import AnalysisValidationError
from seoul_weather.processing.dataset import load_processed_data


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


def test_add_time_features_uses_trailing_30_day_window_with_24_observations() -> None:
    frame = make_daily_frame("2024-01-01", "2024-01-30")
    frame["avg_temp_c"] = range(1, 31)

    featured = add_time_features(frame)

    assert pd.isna(featured.loc[22, "rolling_30d_avg_c"])
    assert featured.loc[23, "rolling_30d_avg_c"] == pytest.approx(12.5)
    assert featured.loc[29, "rolling_30d_avg_c"] == pytest.approx(15.5)
    assert featured.loc[0, "daily_range_c"] == pytest.approx(6.0)
    assert featured.loc[0, "season"] == "겨울"


def test_annual_statistics_enforces_95_percent_coverage_boundary() -> None:
    below = make_daily_frame("2023-01-01", "2023-12-31")
    below.loc[:18, "avg_temp_c"] = float("nan")
    enough = below.copy()
    enough.loc[18, "avg_temp_c"] = 10.0

    below_result = compute_annual_statistics(below, AnalysisConfig())
    enough_result = compute_annual_statistics(enough, AnalysisConfig())

    assert below_result.loc[0, "valid_avg_temp_days"] == 346
    assert pd.isna(below_result.loc[0, "avg_temp_c"])
    assert enough_result.loc[0, "valid_avg_temp_days"] == 347
    assert enough_result.loc[0, "avg_temp_c"] == pytest.approx(10.0)


def test_annual_statistics_calculates_change_and_five_year_trailing_mean() -> None:
    frames = []
    for year, temperature in zip(range(2000, 2005), range(10, 15), strict=True):
        frames.append(make_daily_frame(f"{year}-01-01", f"{year}-12-31", temperature))
    frame = pd.concat(frames, ignore_index=True)

    annual = compute_annual_statistics(frame, AnalysisConfig())

    assert annual.loc[4, "annual_change_c"] == pytest.approx(1.0)
    assert annual.loc[:3, "rolling_5y_avg_c"].isna().all()
    assert annual.loc[4, "rolling_5y_avg_c"] == pytest.approx(12.0)


def test_fit_annual_linear_trend_reports_degrees_per_decade_and_r_squared() -> None:
    annual = pd.DataFrame(
        {"year": [2000, 2001, 2002], "avg_temp_c": [10.0, 10.2, 10.4]}
    )

    result = fit_annual_linear_trend(annual)

    assert result["slope_c_per_decade"] == pytest.approx(2.0)
    assert result["r_squared"] == pytest.approx(1.0)
    assert result["valid_year_count"] == 3


def test_monthly_statistics_uses_valid_year_months_for_climatology() -> None:
    first = make_daily_frame("2000-01-01", "2000-01-31", 0.0)
    second = make_daily_frame("2001-01-01", "2001-01-31", 2.0)

    monthly = compute_monthly_statistics(
        pd.concat([first, second], ignore_index=True), AnalysisConfig()
    )

    assert monthly["monthly_climatology_c"].tolist() == pytest.approx([1.0, 1.0])
    assert monthly["monthly_anomaly_c"].tolist() == pytest.approx([-1.0, 1.0])


def test_monthly_statistics_marks_month_below_80_percent_as_missing() -> None:
    february = make_daily_frame("2023-02-01", "2023-02-28")
    february.loc[:5, "avg_temp_c"] = float("nan")

    monthly = compute_monthly_statistics(february, AnalysisConfig())

    assert monthly.loc[0, "valid_avg_temp_days"] == 22
    assert pd.isna(monthly.loc[0, "avg_temp_c"])


def test_compute_seasonal_statistics_uses_calendar_year_season_definition() -> None:
    frame = pd.concat(
        [
            make_daily_frame("2024-01-01", "2024-01-01", 0.0),
            make_daily_frame("2024-04-01", "2024-04-01", 10.0),
            make_daily_frame("2024-07-01", "2024-07-01", 20.0),
            make_daily_frame("2024-10-01", "2024-10-01", 12.0),
            make_daily_frame("2024-12-01", "2024-12-01", 2.0),
        ],
        ignore_index=True,
    )

    seasonal = compute_seasonal_statistics(frame)

    winter = seasonal.loc[seasonal["season"] == "겨울", "avg_temp_c"].iloc[0]
    assert winter == pytest.approx(1.0)


def test_daily_anomalies_use_month_population_standard_deviation() -> None:
    frame = make_daily_frame("2024-01-01", "2024-01-05")
    frame["avg_temp_c"] = [-2.0, -1.0, 0.0, 1.0, 2.0]

    anomalies = compute_daily_anomalies(frame, threshold=1.4)

    assert anomalies.loc[4, "monthly_std_c"] == pytest.approx(math.sqrt(2.0))
    assert anomalies.loc[4, "monthly_anomaly_z"] == pytest.approx(math.sqrt(2.0))
    assert anomalies.loc[0, "anomaly_category"] == "cold"
    assert anomalies.loc[2, "anomaly_category"] == "normal"
    assert anomalies.loc[4, "anomaly_category"] == "hot"


def test_select_anomaly_annotations_balances_hot_and_cold_candidates() -> None:
    anomalies = pd.DataFrame(
        {
            "monthly_anomaly_z": [2.6, 2.7, 2.8, 2.9, -3.9, -3.8, -3.7, -3.6],
            "anomaly_category": ["hot"] * 4 + ["cold"] * 4,
        }
    )

    selected = select_anomaly_annotations(anomalies, per_category=3)

    assert selected["anomaly_category"].value_counts().to_dict() == {
        "hot": 3,
        "cold": 3,
    }
    assert selected.loc[selected["anomaly_category"] == "hot", "monthly_anomaly_z"].min() == pytest.approx(2.7)
    assert selected.loc[selected["anomaly_category"] == "cold", "monthly_anomaly_z"].max() == pytest.approx(-3.7)


def test_load_processed_data_restores_dates_and_nullable_values(tmp_path: Path) -> None:
    csv_path = tmp_path / "processed.csv"
    csv_path.write_text(
        "station_id,station_name,date,avg_temp_c,min_temp_c,max_temp_c,"
        "precipitation_mm,avg_humidity_pct\n"
        "108,서울,2024-01-01,1.0,-2.0,4.0,,60.0\n",
        encoding="utf-8",
    )

    loaded = load_processed_data(csv_path)

    assert loaded.loc[0, "date"] == pd.Timestamp("2024-01-01")
    assert loaded.loc[0, "station_id"] == 108
    assert pd.isna(loaded.loc[0, "precipitation_mm"])


def test_load_processed_data_wraps_invalid_utf8_as_domain_error(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "invalid.csv"
    csv_path.write_bytes(b"\xff\xfe\x00\x00")

    with pytest.raises(AnalysisValidationError, match="CSV로 읽을 수 없습니다"):
        load_processed_data(csv_path)


def test_load_processed_data_wraps_empty_csv_as_domain_error(tmp_path: Path) -> None:
    csv_path = tmp_path / "empty.csv"
    csv_path.write_bytes(b"")

    with pytest.raises(AnalysisValidationError, match="CSV로 읽을 수 없습니다"):
        load_processed_data(csv_path)


def test_load_processed_data_rejects_fractional_station_id(tmp_path: Path) -> None:
    csv_path = tmp_path / "processed.csv"
    csv_path.write_text(
        "station_id,station_name,date,avg_temp_c,min_temp_c,max_temp_c,"
        "precipitation_mm,avg_humidity_pct\n"
        "108.5,서울,2024-01-01,1.0,-2.0,4.0,,60.0\n",
        encoding="utf-8",
    )

    with pytest.raises(AnalysisValidationError, match="station_id.*정수"):
        load_processed_data(csv_path)


def test_build_analysis_summary_compares_decades_and_ranks_extremes() -> None:
    years = list(range(1994, 2025))
    annual = pd.DataFrame(
        {
            "year": years,
            "avg_temp_c": [10.0 + (year - 1994) * 0.1 for year in years],
        }
    )
    annual["annual_change_c"] = annual["avg_temp_c"].diff()
    annual["rolling_5y_avg_c"] = annual["avg_temp_c"].rolling(5).mean()
    trend = fit_annual_linear_trend(annual)
    monthly_rows = []
    seasonal_rows = []
    for year in years:
        period_offset = 0.0 if year <= 2003 else (2.0 if year >= 2015 else 1.0)
        for month in range(1, 13):
            monthly_rows.append(
                {"year": year, "month": month, "avg_temp_c": month + period_offset}
            )
        for season in ["봄", "여름", "가을", "겨울"]:
            seasonal_rows.append(
                {"year": year, "season": season, "avg_temp_c": 10 + period_offset}
            )
    anomalies = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["1994-01-01", "2000-07-01", "2010-01-01", "2024-08-01"]
            ),
            "avg_temp_c": [-12.0, 30.0, -10.0, 32.0],
            "monthly_anomaly_c": [-8.0, 7.0, -6.0, 9.0],
            "monthly_anomaly_z": [-3.2, 2.7, -2.6, 3.5],
            "anomaly_category": ["cold", "hot", "cold", "hot"],
        }
    )
    quality = {
        "row_count": 11323,
        "unique_date_count": 11323,
        "missing_calendar_date_count": 0,
        "duplicate_date_count": 0,
        "temperature_order_violation_count": 0,
        "missing_counts": {"avg_temp_c": 0},
    }

    summary = build_analysis_summary(
        quality=quality,
        annual=annual,
        trend=trend,
        monthly=pd.DataFrame(monthly_rows),
        seasonal=pd.DataFrame(seasonal_rows),
        anomalies=anomalies,
        config=AnalysisConfig(),
    )

    assert summary["trend"]["early_decade_mean_c"] == pytest.approx(10.45)
    assert summary["trend"]["recent_decade_mean_c"] == pytest.approx(12.55)
    assert summary["trend"]["difference_c"] == pytest.approx(2.10)
    assert summary["extremes"]["warmest_year"] == 2024
    assert summary["extremes"]["coldest_year"] == 1994
    assert summary["extremes"]["hot_candidate_count"] == 2
    assert summary["extremes"]["top_hot_candidates"][0]["date"] == "2024-08-01"
    assert summary["monthly_period_comparison"][0]["difference_c"] == pytest.approx(
        2.0
    )
