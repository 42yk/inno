"""연도별 원자료 통합과 표준 CSV 입출력."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

import pandas as pd

from seoul_weather.errors import AnalysisValidationError, DataValidationError
from seoul_weather.processing.normalize import normalize_year_csv
from seoul_weather.processing.schema import STANDARD_COLUMNS


# 통합 데이터에 기록된 중복 제거 진단 정보를 반환한다.
def processing_diagnostics(frame: pd.DataFrame) -> dict[str, object]:
    return {
        "duplicate_rows_removed": int(
            frame.attrs.get("duplicate_rows_removed", 0)
        ),
        "duplicate_groups": list(frame.attrs.get("duplicate_groups", [])),
    }


# 연도별 데이터를 합치고 동일 중복은 제거·기록하며 충돌 중복은 거부한다.
def combine_year_frames(
    frames: Sequence[pd.DataFrame],
    sources: Sequence[str] | None = None,
) -> pd.DataFrame:
    if not frames:
        raise DataValidationError("통합할 연도별 데이터가 없습니다.")
    if sources is not None and len(sources) != len(frames):
        raise DataValidationError("원본 경로 수와 연도별 데이터 수가 다릅니다.")

    annotated_frames: list[pd.DataFrame] = []
    for frame_index, frame in enumerate(frames):
        annotated = frame.copy()
        source = (
            sources[frame_index]
            if sources is not None
            else str(frame.attrs.get("source_path", f"frame[{frame_index}]"))
        )
        source_rows = frame.attrs.get("source_csv_rows")
        if not isinstance(source_rows, list) or len(source_rows) != len(frame):
            source_rows = [int(index) + 2 for index in frame.index]
        annotated["_source"] = source
        annotated["_source_csv_row"] = source_rows
        annotated_frames.append(annotated)

    combined = pd.concat(annotated_frames, ignore_index=True)
    missing_columns = [column for column in STANDARD_COLUMNS if column not in combined]
    if missing_columns:
        raise DataValidationError(
            f"통합 데이터에 표준 컬럼이 누락되었습니다: {missing_columns}"
        )

    exact_duplicate_mask = combined.duplicated(
        subset=STANDARD_COLUMNS, keep=False
    )
    duplicate_groups = _duplicate_groups(combined.loc[exact_duplicate_mask])
    duplicate_rows_removed = sum(
        len(group["occurrences"]) - 1 for group in duplicate_groups
    )

    deduplicated = combined.drop_duplicates(subset=STANDARD_COLUMNS).copy()
    duplicate_mask = deduplicated.duplicated(subset=["date"], keep=False)
    if duplicate_mask.any():
        conflicts = []
        for date, group in deduplicated.loc[duplicate_mask].groupby("date"):
            conflicts.append(
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "occurrences": [
                        {
                            "source": row["_source"],
                            "csv_row": int(row["_source_csv_row"]),
                        }
                        for _, row in group.iterrows()
                    ],
                }
            )
        raise DataValidationError(
            f"같은 날짜의 값이 충돌합니다: {conflicts[:10]}"
        )

    result = (
        deduplicated[STANDARD_COLUMNS].sort_values("date").reset_index(drop=True)
    )
    result.attrs["duplicate_rows_removed"] = duplicate_rows_removed
    result.attrs["duplicate_groups"] = duplicate_groups
    return result


# 동일 중복 행을 원본 파일과 CSV 행 위치별 그룹으로 정리한다.
def _duplicate_groups(duplicates: pd.DataFrame) -> list[dict[str, object]]:
    groups: list[dict[str, object]] = []
    remaining = duplicates.copy()
    while not remaining.empty:
        first = remaining.iloc[0]
        same_row = pd.Series(True, index=remaining.index)
        for column in STANDARD_COLUMNS:
            same_row &= remaining[column].eq(first[column]) | (
                remaining[column].isna() & pd.isna(first[column])
            )
        matched = remaining.loc[same_row]
        groups.append(
            {
                "date": first["date"].strftime("%Y-%m-%d"),
                "occurrences": [
                    {
                        "source": row["_source"],
                        "csv_row": int(row["_source_csv_row"]),
                    }
                    for _, row in matched.iterrows()
                ],
            }
        )
        remaining = remaining.loc[~same_row]
    return groups


# 보존 원본을 연도별로 정규화·통합해 표준 CSV를 원자적으로 저장한다.
def rebuild_processed_from_raw(
    start_year: int,
    end_year: int,
    station_id: int,
    raw_root: Path,
    processed_path: Path,
    csv_paths_by_year: Mapping[int, Path] | None = None,
) -> pd.DataFrame:
    try:
        temporary_path = processed_path.with_name(f".{processed_path.name}.part")
    except ValueError as exc:
        raise DataValidationError(
            f"가공 CSV 출력 경로가 올바르지 않습니다: {processed_path}"
        ) from exc

    frames: list[pd.DataFrame] = []
    sources: list[str] = []
    for year in range(start_year, end_year + 1):
        if csv_paths_by_year is not None:
            csv_path = csv_paths_by_year.get(year)
            if csv_path is None or not csv_path.is_file():
                raise DataValidationError(
                    f"manifest에 기록된 {year}년 원본 CSV가 없습니다."
                )
        else:
            year_dir = raw_root / str(year)
            pattern = f"SURFACE_ASOS_{station_id}_DAY_{year}_{year}_*.csv"
            csv_paths = sorted(year_dir.glob(pattern))
            if len(csv_paths) != 1:
                raise DataValidationError(
                    f"{year}년 원본 CSV를 정확히 한 개 찾아야 하지만 "
                    f"{len(csv_paths)}개입니다: {year_dir}"
                )
            csv_path = csv_paths[0]
        frames.append(
            normalize_year_csv(
                csv_path, expected_year=year, station_id=station_id
            )
        )
        try:
            sources.append(csv_path.relative_to(raw_root).as_posix())
        except ValueError:
            sources.append(str(csv_path))

    combined = combine_year_frames(frames, sources=sources)
    try:
        processed_path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(
            temporary_path,
            index=False,
            encoding="utf-8",
            date_format="%Y-%m-%d",
        )
        temporary_path.replace(processed_path)
    except OSError as exc:
        raise DataValidationError(
            f"가공 CSV를 저장할 수 없습니다: {processed_path}"
        ) from exc
    finally:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
    return combined


# UTF-8 표준 CSV를 읽고 스키마·날짜·숫자 자료형을 검증한다.
def load_processed_data(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise AnalysisValidationError(f"가공 데이터 파일이 없습니다: {path}")
    try:
        frame = pd.read_csv(path, encoding="utf-8")
    except (
        OSError,
        UnicodeError,
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
    ) as exc:
        raise AnalysisValidationError(
            f"가공 데이터를 UTF-8 CSV로 읽을 수 없습니다: {path}"
        ) from exc
    missing_columns = [column for column in STANDARD_COLUMNS if column not in frame]
    if missing_columns:
        raise AnalysisValidationError(f"필수 컬럼이 누락되었습니다: {missing_columns}")

    date_text = frame["date"].astype("string").str.strip()
    frame["date"] = pd.to_datetime(date_text, errors="coerce")
    if frame["date"].isna().any():
        raise AnalysisValidationError("가공 데이터에 해석할 수 없는 날짜가 있습니다.")

    numeric_columns = [
        "station_id",
        "avg_temp_c",
        "min_temp_c",
        "max_temp_c",
        "precipitation_mm",
        "avg_humidity_pct",
    ]
    for column in numeric_columns:
        original = frame[column].astype("string").str.strip()
        parsed = pd.to_numeric(original, errors="coerce")
        invalid = original.notna() & original.ne("") & parsed.isna()
        if invalid.any():
            raise AnalysisValidationError(
                f"가공 데이터의 {column}에 숫자가 아닌 값이 있습니다."
            )
        frame[column] = parsed
    if frame["station_id"].isna().any():
        raise AnalysisValidationError("가공 데이터의 station_id에 결측이 있습니다.")
    fractional_station_mask = frame["station_id"].mod(1).ne(0)
    if fractional_station_mask.any():
        raise AnalysisValidationError(
            "가공 데이터의 station_id는 정수여야 합니다."
        )
    frame["station_id"] = frame["station_id"].astype("Int64")
    frame["station_name"] = frame["station_name"].astype("string").str.strip()
    return frame[STANDARD_COLUMNS].sort_values("date").reset_index(drop=True)
