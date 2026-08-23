"""연도별 기상청 원자료 수집과 전체 데이터셋 생성."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from seoul_weather.collection.archives import (
    extract_nested_archives,
    validate_zip_bytes,
    write_preserving_existing,
)
from seoul_weather.collection.manifest import (
    file_record,
    load_manifest,
    validate_manifest_files,
    validate_manifest_scope,
    write_manifest_atomic,
)
from seoul_weather.collection.portal import (
    DOWNLOAD_URL,
    LISTING_URL,
    REQUEST_TIMEOUT,
    build_download_payload,
    build_listing_payload,
    create_http_session,
    parse_fileset_info,
)
from seoul_weather.errors import DataDownloadError, DataValidationError
from seoul_weather.processing.dataset import (
    processing_diagnostics,
    rebuild_processed_from_raw,
)
from seoul_weather.processing.normalize import normalize_year_csv


# 한 연도의 파일을 검색·다운로드·압축 해제하고 수집 기록을 만든다.
def download_year(
    session: Any,
    year: int,
    station_id: int,
    raw_root: Path,
    accessed_at: str | None = None,
) -> dict[str, object]:
    try:
        listing_response = session.post(
            LISTING_URL,
            data=build_listing_payload(year=year, station_id=station_id),
            timeout=REQUEST_TIMEOUT,
        )
        listing_response.raise_for_status()
    except requests.RequestException as exc:
        raise DataDownloadError(f"{year}년 파일 검색 요청에 실패했습니다: {exc}") from exc

    info = parse_fileset_info(listing_response.text, year, station_id)
    try:
        download_response = session.post(
            DOWNLOAD_URL,
            data=build_download_payload(info, year=year, station_id=station_id),
            timeout=REQUEST_TIMEOUT,
        )
        download_response.raise_for_status()
    except requests.RequestException as exc:
        raise DataDownloadError(f"{year}년 파일 다운로드에 실패했습니다: {exc}") from exc

    validate_zip_bytes(download_response.content, f"{year}년 다운로드 응답")
    year_dir = raw_root / str(year)
    year_dir.mkdir(parents=True, exist_ok=True)
    outer_path = year_dir / "downloaded.zip"
    write_preserving_existing(outer_path, download_response.content)
    inner_path, csv_path = extract_nested_archives(
        outer_path, year_dir, info.filename
    )
    normalize_year_csv(csv_path, expected_year=year, station_id=station_id)

    timestamp = accessed_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {
        "year": year,
        "station_id": station_id,
        "source_url": LISTING_URL,
        "accessed_at": timestamp,
        "portal_filename": info.filename,
        "fileset_id": info.fileset_id,
        "fileset_detail_id": info.detail_id,
        "portal_reported_size_kb": info.size_kb,
        "files": {
            "outer_zip": file_record(outer_path, raw_root),
            "inner_zip": file_record(inner_path, raw_root),
            "csv": file_record(csv_path, raw_root),
        },
    }


# 검증된 기존 원본을 재사용하고 누락 연도를 수집해 데이터셋을 완성한다.
def collect_dataset(
    start_year: int,
    end_year: int,
    station_id: int,
    raw_root: Path,
    processed_path: Path,
    reuse_existing: bool = True,
    session: Any | None = None,
) -> dict[str, object]:
    if start_year > end_year:
        raise DataValidationError("시작 연도는 종료 연도보다 클 수 없습니다.")

    raw_root.mkdir(parents=True, exist_ok=True)
    manifest_path = raw_root / "manifest.json"
    reusable_entries: dict[int, dict[str, object]] = {}
    if reuse_existing and manifest_path.exists():
        existing_manifest = load_manifest(manifest_path)
        validate_manifest_scope(
            existing_manifest,
            start_year=start_year,
            end_year=end_year,
            station_id=station_id,
        )
        reusable_entries = validate_manifest_files(existing_manifest, raw_root)

    entries: list[dict[str, object]] = []
    active_session = session
    for year in range(start_year, end_year + 1):
        if year in reusable_entries:
            entries.append(reusable_entries[year])
            continue
        if active_session is None:
            active_session = create_http_session()
        entries.append(
            download_year(
                active_session,
                year=year,
                station_id=station_id,
                raw_root=raw_root,
            )
        )

    processed = rebuild_processed_from_raw(
        start_year=start_year,
        end_year=end_year,
        station_id=station_id,
        raw_root=raw_root,
        processed_path=processed_path,
        csv_paths_by_year={
            int(entry["year"]): raw_root / entry["files"]["csv"]["path"]
            for entry in entries
        },
    )
    manifest: dict[str, object] = {
        "manifest_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "기상청 기상자료개방포털 ASOS 연도별 파일셋",
        "source_url": LISTING_URL,
        "license": "공공저작물 출처표시 제1유형",
        "station_id": station_id,
        "start_year": start_year,
        "end_year": end_year,
        "entry_count": len(entries),
        "entries": entries,
        "processing": processing_diagnostics(processed),
    }
    write_manifest_atomic(manifest_path, manifest)
    return manifest
