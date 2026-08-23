"""분석 입력 데이터의 기간·지점·품질 계약 검사."""

from __future__ import annotations

import pandas as pd

from seoul_weather.config import AnalysisConfig
from seoul_weather.errors import AnalysisValidationError
from seoul_weather.processing.schema import STANDARD_COLUMNS, STATION_NAMES


# 일별 분석 데이터의 스키마·기간·지점·결측·값 범위를 검증한다.
def validate_daily_data(
    df: pd.DataFrame, config: AnalysisConfig
) -> dict[str, object]:
    missing_columns = [column for column in STANDARD_COLUMNS if column not in df]
    if missing_columns:
        raise AnalysisValidationError(f"필수 컬럼이 누락되었습니다: {missing_columns}")
    if df.empty:
        raise AnalysisValidationError("분석 입력 데이터가 비어 있습니다.")

    dates = pd.to_datetime(df["date"], errors="coerce")
    if dates.isna().any():
        bad_rows = (df.index[dates.isna()] + 2).tolist()[:10]
        raise AnalysisValidationError(
            f"날짜로 해석할 수 없는 값이 있습니다. CSV 행: {bad_rows}"
        )
    duplicate_mask = dates.duplicated(keep=False)
    if duplicate_mask.any():
        duplicate_dates = dates.loc[duplicate_mask].dt.strftime("%Y-%m-%d").unique()
        raise AnalysisValidationError(
            f"중복 날짜가 있습니다: {duplicate_dates[:10].tolist()}"
        )

    station_values = pd.to_numeric(df["station_id"], errors="coerce")
    unexpected_stations = sorted(
        int(value)
        for value in station_values.dropna().unique()
        if value != config.station_id
    )
    if station_values.isna().any() or unexpected_stations:
        raise AnalysisValidationError(
            f"지점 값은 모두 {config.station_id}여야 합니다. "
            f"다른 값: {unexpected_stations}"
        )
    expected_station_name = STATION_NAMES.get(config.station_id)
    station_names = df["station_name"].astype("string").str.strip()
    if expected_station_name is None or station_names.isna().any() or (
        station_names != expected_station_name
    ).any():
        unexpected_names = sorted(
            str(value)
            for value in station_names.dropna().unique()
            if value != expected_station_name
        )
        raise AnalysisValidationError(
            f"지점명은 모두 {expected_station_name!r}이어야 합니다. "
            f"다른 값: {unexpected_names}"
        )

    expected_dates = pd.date_range(config.start_date, config.end_date, freq="D")
    actual_index = pd.DatetimeIndex(dates)
    missing_dates = expected_dates.difference(actual_index)
    unexpected_dates = actual_index.difference(expected_dates)
    if len(missing_dates) > 0:
        examples = missing_dates.strftime("%Y-%m-%d").tolist()[:10]
        raise AnalysisValidationError(
            f"분석 기간에 누락 날짜가 {len(missing_dates)}개 있습니다: {examples}"
        )
    if len(unexpected_dates) > 0:
        examples = unexpected_dates.strftime("%Y-%m-%d").tolist()[:10]
        raise AnalysisValidationError(
            f"분석 기간 밖 날짜가 {len(unexpected_dates)}개 있습니다: {examples}"
        )

    temperature_order_mask = (
        (df["min_temp_c"] > df["avg_temp_c"])
        | (df["avg_temp_c"] > df["max_temp_c"])
        | (df["min_temp_c"] > df["max_temp_c"])
    )
    humidity_violation_mask = df["avg_humidity_pct"].notna() & (
        (df["avg_humidity_pct"] < 0) | (df["avg_humidity_pct"] > 100)
    )
    negative_precipitation_mask = df["precipitation_mm"].notna() & (
        df["precipitation_mm"] < 0
    )
    temperature_range_violation_mask = pd.Series(False, index=df.index)
    for column in ("avg_temp_c", "min_temp_c", "max_temp_c"):
        temperature_range_violation_mask |= df[column].notna() & (
            (df[column] < config.plausible_temperature_min_c)
            | (df[column] > config.plausible_temperature_max_c)
        )
    missing_counts = {
        column: int(df[column].isna().sum()) for column in STANDARD_COLUMNS
    }
    missing_rates_pct = {
        column: count / len(df) * 100 for column, count in missing_counts.items()
    }

    return {
        "row_count": int(len(df)),
        "unique_date_count": int(dates.nunique()),
        "expected_date_count": int(len(expected_dates)),
        "actual_start_date": dates.min().strftime("%Y-%m-%d"),
        "actual_end_date": dates.max().strftime("%Y-%m-%d"),
        "missing_calendar_date_count": 0,
        "duplicate_date_count": 0,
        "missing_counts": missing_counts,
        "missing_rates_pct": missing_rates_pct,
        "dtypes": {column: str(df[column].dtype) for column in STANDARD_COLUMNS},
        "temperature_order_violation_count": int(temperature_order_mask.sum()),
        "temperature_order_violation_dates": _masked_date_strings(
            dates, temperature_order_mask
        ),
        "humidity_range_violation_count": int(humidity_violation_mask.sum()),
        "humidity_range_violation_dates": _masked_date_strings(
            dates, humidity_violation_mask
        ),
        "negative_precipitation_count": int(negative_precipitation_mask.sum()),
        "negative_precipitation_dates": _masked_date_strings(
            dates, negative_precipitation_mask
        ),
        "temperature_range_violation_count": int(
            temperature_range_violation_mask.sum()
        ),
        "temperature_range_violation_dates": _masked_date_strings(
            dates, temperature_range_violation_mask
        ),
    }


# 조건에 해당하는 날짜를 문자열 목록으로 제한해 반환한다.
def _masked_date_strings(
    dates: pd.Series, mask: pd.Series, limit: int = 20
) -> list[str]:
    return dates.loc[mask].dt.strftime("%Y-%m-%d").tolist()[:limit]
