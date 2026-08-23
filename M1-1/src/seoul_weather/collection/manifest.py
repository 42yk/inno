"""원자료 파일 기록과 manifest 무결성 검증."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from seoul_weather.errors import DataValidationError


# 파일 내용을 읽어 SHA-256 해시를 계산한다.
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# 파일의 상대 경로·크기·SHA-256을 manifest 기록으로 만든다.
def file_record(path: Path, root: Path) -> dict[str, object]:
    return {
        "path": path.relative_to(root).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


# manifest JSON을 읽고 최상위 자료형을 검증한다.
def load_manifest(path: Path) -> dict[str, object]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataValidationError(f"manifest를 읽을 수 없습니다: {path}") from exc
    if not isinstance(manifest, dict):
        raise DataValidationError("manifest 최상위 값은 객체여야 합니다.")
    return manifest


# manifest의 지점·기간·연도 항목이 실행 범위와 일치하는지 검증한다.
def validate_manifest_scope(
    manifest: dict[str, object],
    start_year: int,
    end_year: int,
    station_id: int,
) -> None:
    expected = {
        "station_id": station_id,
        "start_year": start_year,
        "end_year": end_year,
    }
    mismatches = {
        key: (manifest.get(key), value)
        for key, value in expected.items()
        if manifest.get(key) != value
    }
    if mismatches:
        raise DataValidationError(f"manifest 범위가 실행 조건과 다릅니다: {mismatches}")

    raw_entries = manifest.get("entries")
    if not isinstance(raw_entries, list):
        raise DataValidationError("manifest의 entries는 배열이어야 합니다.")
    if manifest.get("entry_count") != len(raw_entries):
        raise DataValidationError(
            "manifest의 entry_count가 실제 연도 항목 수와 일치하지 않습니다."
        )

    years: list[int] = []
    for entry in raw_entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("year"), int):
            raise DataValidationError("manifest 연도 항목의 형식이 올바르지 않습니다.")
        if entry.get("station_id") != station_id:
            raise DataValidationError(
                f"manifest {entry['year']}년 지점이 {station_id}와 다릅니다."
            )
        years.append(entry["year"])

    duplicate_years = sorted({year for year in years if years.count(year) > 1})
    expected_years = set(range(start_year, end_year + 1))
    actual_years = set(years)
    missing_years = sorted(expected_years - actual_years)
    unexpected_years = sorted(actual_years - expected_years)
    if duplicate_years:
        raise DataValidationError(
            f"manifest 연도 항목이 중복되었습니다: {duplicate_years}"
        )
    if missing_years:
        raise DataValidationError(
            f"manifest 연도 항목이 누락되었습니다: {missing_years}"
        )
    if unexpected_years:
        raise DataValidationError(
            f"manifest 범위 밖 연도 항목이 있습니다: {unexpected_years}"
        )


# manifest가 가리키는 원본 파일의 경로·크기·해시를 검증한다.
def validate_manifest_files(
    manifest: dict[str, object], raw_root: Path
) -> dict[int, dict[str, object]]:
    raw_entries = manifest.get("entries")
    if not isinstance(raw_entries, list):
        raise DataValidationError("manifest의 entries는 배열이어야 합니다.")
    validated: dict[int, dict[str, object]] = {}
    resolved_root = raw_root.resolve()
    for raw_entry in raw_entries:
        if not isinstance(raw_entry, dict) or not isinstance(raw_entry.get("year"), int):
            raise DataValidationError("manifest 연도 항목의 형식이 올바르지 않습니다.")
        year = raw_entry["year"]
        files = raw_entry.get("files")
        if not isinstance(files, dict):
            raise DataValidationError(f"manifest {year}년 파일 목록이 없습니다.")
        for label in ("outer_zip", "inner_zip", "csv"):
            record = files.get(label)
            if not isinstance(record, dict):
                raise DataValidationError(f"manifest {year}년 {label} 기록이 없습니다.")
            relative_text = record.get("path")
            if not isinstance(relative_text, str):
                raise DataValidationError(
                    f"manifest {year}년 {label} 경로가 올바르지 않습니다."
                )
            path = (raw_root / relative_text).resolve()
            if not path.is_relative_to(resolved_root):
                raise DataValidationError(
                    f"manifest {year}년 {label} 경로가 원자료 폴더 밖을 가리킵니다."
                )
            if not path.is_file():
                raise DataValidationError(
                    f"manifest {year}년 {label} 파일이 없습니다: {path}"
                )
            if record.get("size_bytes") != path.stat().st_size:
                raise DataValidationError(
                    f"manifest {year}년 {label} 파일 크기가 일치하지 않습니다."
                )
            if record.get("sha256") != sha256_file(path):
                raise DataValidationError(
                    f"manifest {year}년 {label} SHA-256이 일치하지 않습니다."
                )
        if year in validated:
            raise DataValidationError(f"manifest에 {year}년 항목이 중복되었습니다.")
        validated[year] = raw_entry
    return validated


# manifest를 임시 파일에 쓴 뒤 최종 경로로 원자적으로 교체한다.
def write_manifest_atomic(path: Path, content: dict[str, object]) -> None:
    temporary_path = path.with_name(f".{path.name}.part")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path.write_text(
            json.dumps(content, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)
    except OSError as exc:
        raise DataValidationError(f"manifest를 저장할 수 없습니다: {path}") from exc
    finally:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass
