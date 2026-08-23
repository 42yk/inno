"""분석 결과를 문서와 테스트가 공유하는 JSON 구조로 요약."""

from __future__ import annotations

from dataclasses import asdict

import numpy as np
import pandas as pd

from seoul_weather.config import AnalysisConfig
from seoul_weather.errors import AnalysisValidationError


# 품질·통계·이상 기온 결과를 문서용 요약 구조로 조합한다.
def build_analysis_summary(
    quality: dict[str, object],
    annual: pd.DataFrame,
    trend: dict[str, float],
    monthly: pd.DataFrame,
    seasonal: pd.DataFrame,
    anomalies: pd.DataFrame,
    config: AnalysisConfig,
) -> dict[str, object]:
    start_year = pd.Timestamp(config.start_date).year
    end_year = pd.Timestamp(config.end_date).year
    early_end_year = start_year + 9
    recent_start_year = end_year - 9
    valid_annual = annual.dropna(subset=["avg_temp_c"]).copy()
    if valid_annual.empty:
        raise AnalysisValidationError("요약을 만들 유효 연평균이 없습니다.")

    early_mean = valid_annual.loc[
        valid_annual["year"].between(start_year, early_end_year), "avg_temp_c"
    ].mean()
    recent_mean = valid_annual.loc[
        valid_annual["year"].between(recent_start_year, end_year), "avg_temp_c"
    ].mean()
    if pd.isna(early_mean) or pd.isna(recent_mean):
        raise AnalysisValidationError("초기·최근 10년 평균을 계산할 수 없습니다.")

    warmest = valid_annual.loc[valid_annual["avg_temp_c"].idxmax()]
    coldest = valid_annual.loc[valid_annual["avg_temp_c"].idxmin()]
    hot = anomalies.loc[anomalies["anomaly_category"] == "hot"].sort_values(
        "monthly_anomaly_z", ascending=False
    )
    cold = anomalies.loc[anomalies["anomaly_category"] == "cold"].sort_values(
        "monthly_anomaly_z", ascending=True
    )

    trend_summary = {
        "slope_c_per_decade": rounded(trend["slope_c_per_decade"], 3),
        "r_squared": rounded(trend["r_squared"], 3),
        "valid_year_count": int(trend["valid_year_count"]),
        "early_period": f"{start_year}-{early_end_year}",
        "early_decade_mean_c": rounded(early_mean, 2),
        "recent_period": f"{recent_start_year}-{end_year}",
        "recent_decade_mean_c": rounded(recent_mean, 2),
        "difference_c": rounded(recent_mean - early_mean, 2),
    }
    annual_records = [
        {
            "year": int(row.year),
            "avg_temp_c": rounded(row.avg_temp_c, 2),
            "annual_change_c": rounded(
                getattr(row, "annual_change_c", np.nan), 2
            ),
            "rolling_5y_avg_c": rounded(
                getattr(row, "rolling_5y_avg_c", np.nan), 2
            ),
        }
        for row in annual.itertuples(index=False)
    ]

    return {
        "config": asdict(config),
        "data_quality": json_safe(quality),
        "trend": trend_summary,
        "annual_statistics": annual_records,
        "monthly_period_comparison": _period_comparison(
            monthly,
            group_column="month",
            groups=list(range(1, 13)),
            start_year=start_year,
            early_end_year=early_end_year,
            recent_start_year=recent_start_year,
            end_year=end_year,
        ),
        "seasonal_period_comparison": _period_comparison(
            seasonal,
            group_column="season",
            groups=["봄", "여름", "가을", "겨울"],
            start_year=start_year,
            early_end_year=early_end_year,
            recent_start_year=recent_start_year,
            end_year=end_year,
        ),
        "extremes": {
            "warmest_year": int(warmest["year"]),
            "warmest_year_mean_c": rounded(warmest["avg_temp_c"], 2),
            "coldest_year": int(coldest["year"]),
            "coldest_year_mean_c": rounded(coldest["avg_temp_c"], 2),
            "hot_candidate_count": int(len(hot)),
            "cold_candidate_count": int(len(cold)),
            "top_hot_candidates": _anomaly_records(hot.head(10)),
            "top_cold_candidates": _anomaly_records(cold.head(10)),
        },
    }


# 결측을 보존하면서 숫자를 지정 자릿수로 반올림한다.
def rounded(value: object, digits: int) -> float | None:
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


# NumPy·pandas 값을 JSON으로 직렬화 가능한 값으로 변환한다.
def json_safe(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return None if np.isnan(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m-%d")
    return value


# 초기 10년과 최근 10년의 그룹별 평균 차이를 계산한다.
def _period_comparison(
    frame: pd.DataFrame,
    group_column: str,
    groups: list[object],
    start_year: int,
    early_end_year: int,
    recent_start_year: int,
    end_year: int,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for group in groups:
        selected = frame.loc[frame[group_column] == group]
        early_mean = selected.loc[
            selected["year"].between(start_year, early_end_year), "avg_temp_c"
        ].mean()
        recent_mean = selected.loc[
            selected["year"].between(recent_start_year, end_year), "avg_temp_c"
        ].mean()
        records.append(
            {
                group_column: json_safe(group),
                "early_mean_c": rounded(early_mean, 2),
                "recent_mean_c": rounded(recent_mean, 2),
                "difference_c": rounded(recent_mean - early_mean, 2),
            }
        )
    return records


# 이상 기온 행을 JSON 요약용 레코드로 변환한다.
def _anomaly_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    return [
        {
            "date": pd.Timestamp(row.date).strftime("%Y-%m-%d"),
            "avg_temp_c": rounded(row.avg_temp_c, 2),
            "monthly_anomaly_c": rounded(row.monthly_anomaly_c, 2),
            "monthly_anomaly_z": rounded(row.monthly_anomaly_z, 3),
        }
        for row in frame.itertuples(index=False)
    ]
