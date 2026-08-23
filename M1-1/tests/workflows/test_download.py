from __future__ import annotations

import json
from pathlib import Path

import pytest

from seoul_weather.collection.manifest import file_record
from seoul_weather.errors import DataValidationError
from seoul_weather.workflows.download import run_download


FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "asos_1994_sample.csv"


def test_rebuild_records_duplicate_diagnostics_in_manifest(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    year_dir = raw_root / "1994"
    year_dir.mkdir(parents=True)
    csv_path = year_dir / "SURFACE_ASOS_108_DAY_1994_1994_2018.csv"
    csv_path.write_bytes(FIXTURE_PATH.read_text(encoding="utf-8").encode("cp949"))
    outer_path = year_dir / "downloaded.zip"
    inner_path = year_dir / "SURFACE_ASOS_108_DAY_1994_1994_2018.zip"
    outer_path.write_bytes(b"outer fixture")
    inner_path.write_bytes(b"inner fixture")
    manifest_path = raw_root / "manifest.json"
    manifest = {
        "station_id": 108,
        "start_year": 1994,
        "end_year": 1994,
        "entry_count": 1,
        "entries": [
            {
                "year": 1994,
                "station_id": 108,
                "files": {
                    "outer_zip": file_record(outer_path, raw_root),
                    "inner_zip": file_record(inner_path, raw_root),
                    "csv": file_record(csv_path, raw_root),
                },
            }
        ],
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )

    result = run_download(
        raw_root=raw_root,
        processed_path=tmp_path / "processed.csv",
        start_year=1994,
        end_year=1994,
        station_id=108,
        rebuild_from_raw=True,
    )

    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert saved["processing"] == {
        "duplicate_rows_removed": 0,
        "duplicate_groups": [],
    }
    assert result["duplicate_rows_removed"] == 0


def test_rebuild_uses_manifest_csv_path_instead_of_unrecorded_match(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    year_dir = raw_root / "1994"
    year_dir.mkdir(parents=True)
    source = FIXTURE_PATH.read_text(encoding="utf-8")
    recorded_csv = year_dir / "recorded-source.csv"
    recorded_csv.write_bytes(source.encode("cp949"))
    unrecorded_csv = year_dir / "SURFACE_ASOS_108_DAY_1994_1994_2099.csv"
    unrecorded_csv.write_bytes(source.replace("-1.8", "99.0", 1).encode("cp949"))
    outer_path = year_dir / "downloaded.zip"
    inner_path = year_dir / "recorded-source.zip"
    outer_path.write_bytes(b"outer fixture")
    inner_path.write_bytes(b"inner fixture")
    manifest_path = raw_root / "manifest.json"
    manifest = {
        "station_id": 108,
        "start_year": 1994,
        "end_year": 1994,
        "entry_count": 1,
        "entries": [
            {
                "year": 1994,
                "station_id": 108,
                "files": {
                    "outer_zip": file_record(outer_path, raw_root),
                    "inner_zip": file_record(inner_path, raw_root),
                    "csv": file_record(recorded_csv, raw_root),
                },
            }
        ],
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    processed_path = tmp_path / "processed.csv"

    run_download(
        raw_root=raw_root,
        processed_path=processed_path,
        start_year=1994,
        end_year=1994,
        station_id=108,
        rebuild_from_raw=True,
    )

    assert "-1.8" in processed_path.read_text(encoding="utf-8")
    assert "99.0" not in processed_path.read_text(encoding="utf-8")


def test_download_wraps_raw_root_file_error(tmp_path: Path) -> None:
    raw_root_file = tmp_path / "raw"
    raw_root_file.write_text("not a directory", encoding="utf-8")

    with pytest.raises(DataValidationError, match="데이터 파일 작업"):
        run_download(
            raw_root=raw_root_file,
            processed_path=tmp_path / "processed.csv",
            start_year=1994,
            end_year=1994,
            station_id=108,
        )
