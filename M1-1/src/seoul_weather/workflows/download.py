"""원자료 수집 또는 보존 원자료 재통합 workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from seoul_weather.errors import (
    AnalysisValidationError,
    DataDownloadError,
    DataValidationError,
)
from seoul_weather.collection.manifest import (
    load_manifest,
    validate_manifest_files,
    validate_manifest_scope,
    write_manifest_atomic,
)
from seoul_weather.collection.pipeline import collect_dataset
from seoul_weather.processing.dataset import (
    load_processed_data,
    processing_diagnostics,
    rebuild_processed_from_raw,
)


# 표준 CSV 준비 흐름을 호출하고 파일 작업 오류를 도메인 오류로 변환한다.
def run_download(
    *,
    raw_root: Path,
    processed_path: Path,
    start_year: int = 1994,
    end_year: int = 2024,
    station_id: int = 108,
    rebuild_from_raw: bool = False,
    session: Any | None = None,
) -> dict[str, object]:
    """표준 CSV를 만들고 실행 결과를 반환한다."""

    try:
        return _run_download(
            raw_root=raw_root,
            processed_path=processed_path,
            start_year=start_year,
            end_year=end_year,
            station_id=station_id,
            rebuild_from_raw=rebuild_from_raw,
            session=session,
        )
    except (DataDownloadError, DataValidationError, AnalysisValidationError):
        raise
    except OSError as exc:
        raise DataValidationError(f"데이터 파일 작업에 실패했습니다: {exc}") from exc


# 보존 원자료 재통합 또는 누락 원자료 수집 흐름을 실제로 수행한다.
def _run_download(
    *,
    raw_root: Path,
    processed_path: Path,
    start_year: int,
    end_year: int,
    station_id: int,
    rebuild_from_raw: bool,
    session: Any | None,
) -> dict[str, object]:

    if rebuild_from_raw:
        manifest = load_manifest(raw_root / "manifest.json")
        validate_manifest_scope(
            manifest,
            start_year=start_year,
            end_year=end_year,
            station_id=station_id,
        )
        validated_entries = validate_manifest_files(manifest, raw_root)
        frame = rebuild_processed_from_raw(
            start_year=start_year,
            end_year=end_year,
            station_id=station_id,
            raw_root=raw_root,
            processed_path=processed_path,
            csv_paths_by_year={
                year: raw_root / entry["files"]["csv"]["path"]
                for year, entry in validated_entries.items()
            },
        )
        diagnostics = processing_diagnostics(frame)
        manifest["processing"] = diagnostics
        write_manifest_atomic(raw_root / "manifest.json", manifest)
        mode = "rebuild"
        year_count = end_year - start_year + 1
    else:
        manifest = collect_dataset(
            start_year=start_year,
            end_year=end_year,
            station_id=station_id,
            raw_root=raw_root,
            processed_path=processed_path,
            reuse_existing=True,
            session=session,
        )
        frame = load_processed_data(processed_path)
        diagnostics = manifest.get(
            "processing",
            {"duplicate_rows_removed": 0, "duplicate_groups": []},
        )
        mode = "download"
        year_count = int(manifest["entry_count"])

    return {
        "mode": mode,
        "year_count": year_count,
        "row_count": int(len(frame)),
        "processed_path": processed_path,
        "duplicate_rows_removed": diagnostics["duplicate_rows_removed"],
        "duplicate_groups": diagnostics["duplicate_groups"],
    }
