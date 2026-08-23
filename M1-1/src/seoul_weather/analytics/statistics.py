"""연·월·계절 집계와 장기 선형 추세."""

from __future__ import annotations

import numpy as np
import pandas as pd

from seoul_weather.analytics.features import add_time_features
from seoul_weather.config import AnalysisConfig
from seoul_weather.errors import AnalysisValidationError


# 관측률 기준을 적용해 연도별 기온 통계와 변화량을 계산한다.
def compute_annual_statistics(
    df: pd.DataFrame, config: AnalysisConfig
) -> pd.DataFrame:
    featured = add_time_features(df)
    grouped = featured.groupby("year", sort=True)
    annual = grouped.agg(
        valid_avg_temp_days=("avg_temp_c", "count"),
        raw_avg_temp_c=("avg_temp_c", "mean"),
        valid_min_temp_days=("min_temp_c", "count"),
        raw_mean_min_temp_c=("min_temp_c", "mean"),
        valid_max_temp_days=("max_temp_c", "count"),
        raw_mean_max_temp_c=("max_temp_c", "mean"),
    ).reset_index()
    annual["expected_days"] = annual["year"].map(_days_in_year)
    annual["avg_temp_coverage"] = (
        annual["valid_avg_temp_days"] / annual["expected_days"]
    )
    annual["min_temp_coverage"] = (
        annual["valid_min_temp_days"] / annual["expected_days"]
    )
    annual["max_temp_coverage"] = (
        annual["valid_max_temp_days"] / annual["expected_days"]
    )
    annual["avg_temp_c"] = annual["raw_avg_temp_c"].where(
        annual["avg_temp_coverage"] >= config.annual_coverage_threshold
    )
    annual["mean_min_temp_c"] = annual["raw_mean_min_temp_c"].where(
        annual["min_temp_coverage"] >= config.annual_coverage_threshold
    )
    annual["mean_max_temp_c"] = annual["raw_mean_max_temp_c"].where(
        annual["max_temp_coverage"] >= config.annual_coverage_threshold
    )
    annual["annual_change_c"] = annual["avg_temp_c"].diff()
    annual["rolling_5y_avg_c"] = annual["avg_temp_c"].rolling(
        window=config.annual_rolling_window,
        min_periods=config.annual_rolling_window,
    ).mean()
    return annual.drop(
        columns=["raw_avg_temp_c", "raw_mean_min_temp_c", "raw_mean_max_temp_c"]
    )


# 유효 연평균 기온에 선형회귀를 적합해 기울기와 결정계수를 계산한다.
def fit_annual_linear_trend(annual: pd.DataFrame) -> dict[str, float]:
    valid = annual.dropna(subset=["year", "avg_temp_c"])
    if len(valid) < 2:
        raise AnalysisValidationError(
            "선형 추세를 계산하려면 유효 연평균이 2개 이상 필요합니다."
        )
    years = valid["year"].to_numpy(dtype=float)
    temperatures = valid["avg_temp_c"].to_numpy(dtype=float)
    slope, intercept = np.polyfit(years, temperatures, 1)
    predictions = slope * years + intercept
    residual_sum = float(np.square(temperatures - predictions).sum())
    total_sum = float(np.square(temperatures - temperatures.mean()).sum())
    r_squared = (
        1.0
        if total_sum == 0 and residual_sum == 0
        else (0.0 if total_sum == 0 else 1.0 - residual_sum / total_sum)
    )
    return {
        "slope_c_per_year": float(slope),
        "slope_c_per_decade": float(slope * 10),
        "intercept_c": float(intercept),
        "r_squared": float(r_squared),
        "valid_year_count": int(len(valid)),
    }


# 관측률 기준을 적용해 연도별 월평균과 월 장기평균 대비 편차를 계산한다.
def compute_monthly_statistics(
    df: pd.DataFrame, config: AnalysisConfig
) -> pd.DataFrame:
    featured = add_time_features(df)
    grouped = featured.groupby(["year", "month"], sort=True)
    monthly = grouped.agg(
        expected_days=("date", lambda values: int(values.dt.days_in_month.iloc[0])),
        valid_avg_temp_days=("avg_temp_c", "count"),
        raw_avg_temp_c=("avg_temp_c", "mean"),
    ).reset_index()
    monthly["avg_temp_coverage"] = (
        monthly["valid_avg_temp_days"] / monthly["expected_days"]
    )
    monthly["avg_temp_c"] = monthly["raw_avg_temp_c"].where(
        monthly["avg_temp_coverage"] >= config.monthly_coverage_threshold
    )
    monthly["monthly_climatology_c"] = monthly.groupby("month")[
        "avg_temp_c"
    ].transform("mean")
    monthly["monthly_anomaly_c"] = (
        monthly["avg_temp_c"] - monthly["monthly_climatology_c"]
    )
    return monthly.drop(columns=["raw_avg_temp_c"])


# 일별 기온을 연도와 계절별로 집계한다.
def compute_seasonal_statistics(df: pd.DataFrame) -> pd.DataFrame:
    featured = add_time_features(df)
    seasonal = (
        featured.groupby(["year", "season"], observed=True)
        .agg(
            valid_avg_temp_days=("avg_temp_c", "count"),
            avg_temp_c=("avg_temp_c", "mean"),
        )
        .reset_index()
    )
    order = {"봄": 1, "여름": 2, "가을": 3, "겨울": 4}
    seasonal["season_order"] = seasonal["season"].map(order)
    return (
        seasonal.sort_values(["year", "season_order"])
        .drop(columns=["season_order"])
        .reset_index(drop=True)
    )


# 지정한 연도의 윤년을 반영한 총 일수를 반환한다.
def _days_in_year(year: int) -> int:
    return int(pd.Timestamp(year=year, month=12, day=31).dayofyear)
