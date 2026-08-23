"""같은 달 분포를 기준으로 한 일별 이상 기온 후보."""

from __future__ import annotations

import numpy as np
import pandas as pd

from seoul_weather.analytics.features import add_time_features


# 같은 달의 장기 분포를 기준으로 일별 편차와 이상 기온 범주를 계산한다.
def compute_daily_anomalies(
    df: pd.DataFrame, threshold: float = 2.5
) -> pd.DataFrame:
    anomalies = add_time_features(df)
    anomalies["monthly_climatology_c"] = anomalies.groupby("month")[
        "avg_temp_c"
    ].transform("mean")
    anomalies["monthly_std_c"] = anomalies.groupby("month")[
        "avg_temp_c"
    ].transform(lambda values: values.std(ddof=0))
    anomalies["monthly_anomaly_c"] = (
        anomalies["avg_temp_c"] - anomalies["monthly_climatology_c"]
    )
    nonzero_std = anomalies["monthly_std_c"].replace(0, np.nan)
    anomalies["monthly_anomaly_z"] = anomalies["monthly_anomaly_c"] / nonzero_std
    categories = np.select(
        [
            anomalies["monthly_anomaly_z"] >= threshold,
            anomalies["monthly_anomaly_z"] <= -threshold,
        ],
        ["hot", "cold"],
        default="normal",
    )
    anomalies["anomaly_category"] = pd.Series(categories, index=anomalies.index)
    anomalies.loc[anomalies["monthly_anomaly_z"].isna(), "anomaly_category"] = (
        "missing"
    )
    return anomalies


# 고온·저온 후보 중 그래프에 표시할 대표 관측을 선택한다.
def select_anomaly_annotations(
    anomalies: pd.DataFrame, per_category: int = 3
) -> pd.DataFrame:
    if per_category < 1:
        raise ValueError("per_category는 1 이상이어야 합니다.")
    hot = anomalies.loc[anomalies["anomaly_category"] == "hot"].nlargest(
        per_category, "monthly_anomaly_z"
    )
    cold = anomalies.loc[anomalies["anomaly_category"] == "cold"].nsmallest(
        per_category, "monthly_anomaly_z"
    )
    selected = pd.concat([hot, cold])
    if "date" in selected:
        return selected.sort_values("date")
    return selected.sort_index()
