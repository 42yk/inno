"""기상청 연도별 CP949 CSV를 표준 스키마로 변환."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from seoul_weather.errors import DataValidationError
from seoul_weather.processing.schema import (
    NUMERIC_COLUMNS,
    SOURCE_COLUMN_MAP,
    STANDARD_COLUMNS,
    STATION_NAMES,
)


# 한 연도의 CP949 원본 CSV를 검증해 표준 컬럼과 자료형으로 변환한다.
def normalize_year_csv(
    csv_path: Path, expected_year: int, station_id: int = 108
) -> pd.DataFrame:
    try:
        raw = pd.read_csv(csv_path, encoding="cp949")
    except (
        OSError,
        UnicodeError,
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
    ) as exc:
        raise DataValidationError(
            f"{csv_path.name}을 CP949 CSV로 읽을 수 없습니다."
        ) from exc

    raw.columns = [str(column).strip().lstrip("\ufeff") for column in raw.columns]
    missing_columns = [column for column in SOURCE_COLUMN_MAP if column not in raw]
    if missing_columns:
        raise DataValidationError(
            f"{csv_path.name}에 필수 원본 컬럼이 누락되었습니다: {missing_columns}"
        )

    normalized = raw[list(SOURCE_COLUMN_MAP)].rename(columns=SOURCE_COLUMN_MAP).copy()
    station_values = _parse_numeric_column(normalized["station_id"], "station_id")
    if station_values.isna().any():
        raise DataValidationError(f"{csv_path.name}의 지점 값에 결측이 있습니다.")
    if station_values.mod(1).ne(0).any():
        raise DataValidationError(
            f"{csv_path.name}의 station_id는 정수여야 합니다."
        )
    normalized["station_id"] = station_values.astype("Int64")

    unexpected_stations = sorted(
        int(value)
        for value in normalized.loc[
            normalized["station_id"] != station_id, "station_id"
        ].unique()
    )
    if unexpected_stations:
        raise DataValidationError(
            f"{csv_path.name}에 예상하지 않은 지점이 있습니다: {unexpected_stations}"
        )
    if station_id not in STATION_NAMES:
        raise DataValidationError(
            f"지점 {station_id}의 표준 지점명이 정의되지 않았습니다."
        )
    normalized.insert(1, "station_name", STATION_NAMES[station_id])

    date_text = normalized["date"].astype("string").str.strip()
    normalized["date"] = pd.to_datetime(date_text, errors="coerce")
    if normalized["date"].isna().any():
        bad_rows = (normalized.index[normalized["date"].isna()] + 2).tolist()[:5]
        raise DataValidationError(
            f"{csv_path.name}에 해석할 수 없는 날짜가 있습니다. CSV 행: {bad_rows}"
        )
    unexpected_years = sorted(
        int(value)
        for value in normalized.loc[
            normalized["date"].dt.year != expected_year, "date"
        ].dt.year.unique()
    )
    if unexpected_years:
        raise DataValidationError(
            f"{csv_path.name}에 대상 연도 {expected_year}와 다른 날짜가 있습니다: "
            f"{unexpected_years}"
        )

    for column in NUMERIC_COLUMNS:
        normalized[column] = _parse_numeric_column(normalized[column], column)
    normalized["station_name"] = normalized["station_name"].astype("string")
    normalized["_source_csv_row"] = normalized.index + 2
    normalized = normalized.sort_values("date").reset_index(drop=True)
    source_csv_rows = normalized.pop("_source_csv_row").astype(int).tolist()
    result = normalized[STANDARD_COLUMNS]
    result.attrs["source_path"] = str(csv_path)
    result.attrs["source_csv_rows"] = source_csv_rows
    return result


# 빈값은 유지하고 비어 있지 않은 숫자 오류는 거부해 실수형으로 변환한다.
def _parse_numeric_column(series: pd.Series, column_name: str) -> pd.Series:
    text = series.astype("string").str.strip()
    parsed = pd.to_numeric(text, errors="coerce")
    invalid_mask = text.notna() & text.ne("") & parsed.isna()
    if invalid_mask.any():
        rows = (series.index[invalid_mask] + 2).tolist()[:5]
        values = text.loc[invalid_mask].tolist()[:5]
        raise DataValidationError(
            f"{column_name}에 숫자로 해석할 수 없는 값이 있습니다. "
            f"CSV 행: {rows}, 값: {values}"
        )
    return parsed.astype("float64")
