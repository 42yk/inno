from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest

from seoul_weather.collection.archives import extract_nested_archives, validate_zip_bytes
from seoul_weather.collection.manifest import (
    sha256_file,
    validate_manifest_scope,
    write_manifest_atomic,
)
from seoul_weather.collection.pipeline import collect_dataset, download_year
from seoul_weather.collection.portal import (
    build_download_payload,
    build_listing_payload,
    parse_fileset_info,
)
from seoul_weather.errors import DataDownloadError, DataValidationError
from seoul_weather.processing.dataset import (
    combine_year_frames,
    rebuild_processed_from_raw,
)
from seoul_weather.processing.normalize import normalize_year_csv


FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "asos_listing_1994.html"


def make_zip_bytes(filename: str = "sample.txt", content: bytes = b"weather") -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(filename, content)
    return buffer.getvalue()


def test_build_listing_payload_targets_daily_asos_station_and_year() -> None:
    payload = build_listing_payload(year=1994, station_id=108)

    assert payload == {
        "lrgClssCd": "SFC",
        "mddlClssCd": "SFC01",
        "serviceSe": "F00101",
        "menuNo": "32",
        "pgmNo": "34",
        "dataFormCd": "F00501",
        "startDt": "1994",
        "endDt": "1994",
        "stnIds": "108",
        "pageIndex": "1",
    }


def test_parse_fileset_info_returns_exact_portal_identifiers() -> None:
    info = parse_fileset_info(
        FIXTURE_PATH.read_text(encoding="utf-8"), year=1994, station_id=108
    )

    assert info.size_kb == pytest.approx(24.81)
    assert info.fileset_id == "513"
    assert info.detail_id == "180718"
    assert info.relative_path.endswith("SURFACE_ASOS_108_DAY_1994_1994_2018.zip")
    assert info.filename == "SURFACE_ASOS_108_DAY_1994_1994_2018.zip"


def test_parse_fileset_info_rejects_missing_result() -> None:
    with pytest.raises(DataDownloadError, match="찾지 못했습니다"):
        parse_fileset_info("<html><body></body></html>", year=1994, station_id=108)


def test_parse_fileset_info_rejects_multiple_matching_results() -> None:
    html = FIXTURE_PATH.read_text(encoding="utf-8")
    duplicated_input = html.replace("</form>", html.split("<form", 1)[1].split("</form>", 1)[0] + "</form>")

    with pytest.raises(DataDownloadError, match="여러 개"):
        parse_fileset_info(duplicated_input, year=1994, station_id=108)


def test_validate_zip_bytes_accepts_readable_zip() -> None:
    validate_zip_bytes(make_zip_bytes(), "정상 fixture")


def test_validate_zip_bytes_rejects_html_response() -> None:
    with pytest.raises(DataDownloadError, match="ZIP"):
        validate_zip_bytes(b"<html>login required</html>", "1994 바깥 압축 파일")


def test_validate_zip_bytes_rejects_corrupt_zip() -> None:
    with pytest.raises(DataDownloadError, match="손상"):
        validate_zip_bytes(b"PK\x03\x04not-a-real-zip", "1994 바깥 압축 파일")


def make_nested_archive(
    inner_filename: str,
    csv_filename: str,
    csv_content: bytes,
) -> bytes:
    inner_buffer = BytesIO()
    with ZipFile(inner_buffer, "w") as inner_archive:
        inner_archive.writestr(csv_filename, csv_content)

    outer_buffer = BytesIO()
    with ZipFile(outer_buffer, "w") as outer_archive:
        outer_archive.writestr(inner_filename, inner_buffer.getvalue())
    return outer_buffer.getvalue()


def write_cp949_sample(tmp_path: Path) -> Path:
    destination = tmp_path / "sample.csv"
    destination.write_bytes(
        FIXTURE_PATH.with_name("asos_1994_sample.csv").read_text(
            encoding="utf-8"
        ).encode("cp949")
    )
    return destination


def test_extract_nested_archives_preserves_inner_zip_and_csv_bytes(
    tmp_path: Path,
) -> None:
    inner_filename = "SURFACE_ASOS_108_DAY_1994_1994_2018.zip"
    csv_filename = inner_filename.removesuffix(".zip") + ".csv"
    csv_bytes = FIXTURE_PATH.with_name("asos_1994_sample.csv").read_text(
        encoding="utf-8"
    ).encode("cp949")
    outer_path = tmp_path / "downloaded.zip"
    outer_path.write_bytes(make_nested_archive(inner_filename, csv_filename, csv_bytes))

    inner_path, csv_path = extract_nested_archives(
        outer_path, tmp_path, inner_filename
    )

    assert inner_path.read_bytes().startswith(b"PK")
    assert csv_path.read_bytes() == csv_bytes


def test_extract_nested_archives_rejects_missing_expected_inner_zip(
    tmp_path: Path,
) -> None:
    outer_path = tmp_path / "downloaded.zip"
    outer_path.write_bytes(make_zip_bytes("unexpected.zip", make_zip_bytes()))

    with pytest.raises(DataDownloadError, match="안쪽 ZIP"):
        extract_nested_archives(
            outer_path,
            tmp_path,
            "SURFACE_ASOS_108_DAY_1994_1994_2018.zip",
        )


def test_extract_nested_archives_rejects_inner_zip_without_csv(
    tmp_path: Path,
) -> None:
    inner_filename = "SURFACE_ASOS_108_DAY_1994_1994_2018.zip"
    outer_path = tmp_path / "downloaded.zip"
    outer_path.write_bytes(
        make_nested_archive(inner_filename, "readme.txt", b"no csv here")
    )

    with pytest.raises(DataDownloadError, match="CSV"):
        extract_nested_archives(outer_path, tmp_path, inner_filename)


def test_normalize_year_csv_maps_columns_and_preserves_missing_values(
    tmp_path: Path,
) -> None:
    csv_path = write_cp949_sample(tmp_path)

    normalized = normalize_year_csv(csv_path, expected_year=1994)

    assert normalized.columns.tolist() == [
        "station_id",
        "station_name",
        "date",
        "avg_temp_c",
        "min_temp_c",
        "max_temp_c",
        "precipitation_mm",
        "avg_humidity_pct",
    ]
    assert normalized["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "1994-01-01",
        "1994-01-02",
    ]
    assert normalized.loc[0, "station_id"] == 108
    assert normalized.loc[0, "station_name"] == "서울"
    assert normalized.loc[0, "avg_temp_c"] == pytest.approx(-1.8)
    assert normalized.loc[0, "avg_humidity_pct"] == pytest.approx(62.3)
    assert normalized.loc[0, "precipitation_mm"] != normalized.loc[0, "precipitation_mm"]
    assert normalized.loc[1, "avg_temp_c"] != normalized.loc[1, "avg_temp_c"]


def test_normalize_year_csv_rejects_missing_required_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "지점,지점명,일시\n108,서울,1994-01-01\n",
        encoding="cp949",
    )

    with pytest.raises(DataValidationError, match="필수 원본 컬럼"):
        normalize_year_csv(csv_path, expected_year=1994)


def test_normalize_year_csv_rejects_wrong_station(tmp_path: Path) -> None:
    source = FIXTURE_PATH.with_name("asos_1994_sample.csv").read_text(
        encoding="utf-8"
    )
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(source.replace("108,1994", "109,1994", 1), encoding="cp949")

    with pytest.raises(DataValidationError, match="지점"):
        normalize_year_csv(csv_path, expected_year=1994)


def test_normalize_year_csv_wraps_invalid_cp949_as_domain_error(
    tmp_path: Path,
) -> None:
    csv_path = tmp_path / "invalid.csv"
    csv_path.write_bytes(b"\x81")

    with pytest.raises(DataValidationError, match="CP949 CSV로 읽을 수 없습니다"):
        normalize_year_csv(csv_path, expected_year=1994)


def test_normalize_year_csv_wraps_empty_file_as_domain_error(tmp_path: Path) -> None:
    csv_path = tmp_path / "empty.csv"
    csv_path.write_bytes(b"")

    with pytest.raises(DataValidationError, match="CP949 CSV로 읽을 수 없습니다"):
        normalize_year_csv(csv_path, expected_year=1994)


def test_normalize_year_csv_rejects_fractional_station_id(tmp_path: Path) -> None:
    source = FIXTURE_PATH.with_name("asos_1994_sample.csv").read_text(
        encoding="utf-8"
    )
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(source.replace("108,1994", "108.5,1994", 1), encoding="cp949")

    with pytest.raises(DataValidationError, match="station_id.*정수"):
        normalize_year_csv(csv_path, expected_year=1994)


def test_combine_year_frames_removes_exact_duplicate_rows(tmp_path: Path) -> None:
    frame = normalize_year_csv(write_cp949_sample(tmp_path), expected_year=1994)

    combined = combine_year_frames(
        [frame.iloc[[0]], frame.iloc[[0]].copy()],
        sources=["first.csv", "second.csv"],
    )

    assert len(combined) == 1
    assert combined.attrs["duplicate_rows_removed"] == 1
    assert combined.attrs["duplicate_groups"] == [
        {
            "date": "1994-01-01",
            "occurrences": [
                {"source": "first.csv", "csv_row": 2},
                {"source": "second.csv", "csv_row": 2},
            ],
        }
    ]


def test_combine_year_frames_rejects_conflicting_duplicate_dates(
    tmp_path: Path,
) -> None:
    frame = normalize_year_csv(write_cp949_sample(tmp_path), expected_year=1994)
    conflicting = frame.iloc[[0]].copy()
    conflicting.loc[conflicting.index[0], "avg_temp_c"] = 3.0

    with pytest.raises(DataValidationError, match="충돌"):
        combine_year_frames([frame.iloc[[0]], conflicting])


def test_build_download_payload_includes_selected_file_identifiers() -> None:
    info = parse_fileset_info(
        FIXTURE_PATH.read_text(encoding="utf-8"), year=1994, station_id=108
    )

    payload = build_download_payload(info, year=1994, station_id=108)

    assert payload["filesetSnList"] == "513"
    assert payload["filesetDtlSnList"] == "180718"
    assert payload["fileSizeMgList"] == (
        "24.81^513^/GWSS/fileset/upload/SFC/1994/"
        "SURFACE_ASOS_108_DAY_1994_1994_2018.zip^180718"
    )
    assert payload["startDt"] == "1994"
    assert payload["stnIds"] == "108"


class FakeResponse:
    def __init__(self, *, text: str = "", content: bytes = b"") -> None:
        self.text = text
        self.content = content
        self.status_code = 200
        self.headers = {"Content-Type": "application/zip"}

    def raise_for_status(self) -> None:
        return None


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = responses

    def post(
        self, url: str, *, data: dict[str, str], timeout: tuple[int, int]
    ) -> FakeResponse:
        del url, data, timeout
        return self.responses.pop(0)


def test_download_year_writes_and_hashes_all_original_files(tmp_path: Path) -> None:
    inner_filename = "SURFACE_ASOS_108_DAY_1994_1994_2018.zip"
    csv_filename = inner_filename.removesuffix(".zip") + ".csv"
    csv_bytes = FIXTURE_PATH.with_name("asos_1994_sample.csv").read_text(
        encoding="utf-8"
    ).encode("cp949")
    outer_bytes = make_nested_archive(inner_filename, csv_filename, csv_bytes)
    session = FakeSession(
        [
            FakeResponse(text=FIXTURE_PATH.read_text(encoding="utf-8")),
            FakeResponse(content=outer_bytes),
        ]
    )

    entry = download_year(
        session,
        year=1994,
        station_id=108,
        raw_root=tmp_path,
        accessed_at="2026-08-21T00:00:00+00:00",
    )

    year_dir = tmp_path / "1994"
    assert (year_dir / "downloaded.zip").read_bytes() == outer_bytes
    assert (year_dir / inner_filename).is_file()
    assert (year_dir / csv_filename).read_bytes() == csv_bytes
    assert entry["accessed_at"] == "2026-08-21T00:00:00+00:00"
    assert entry["files"]["outer_zip"]["sha256"] == sha256_file(
        year_dir / "downloaded.zip"
    )


def test_rebuild_processed_from_raw_combines_cp949_csvs(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    year_dir = raw_root / "1994"
    year_dir.mkdir(parents=True)
    csv_name = "SURFACE_ASOS_108_DAY_1994_1994_2018.csv"
    (year_dir / csv_name).write_bytes(
        FIXTURE_PATH.with_name("asos_1994_sample.csv").read_text(
            encoding="utf-8"
        ).encode("cp949")
    )
    processed_path = tmp_path / "processed" / "seoul_weather_daily.csv"

    rebuilt = rebuild_processed_from_raw(
        start_year=1994,
        end_year=1994,
        station_id=108,
        raw_root=raw_root,
        processed_path=processed_path,
    )

    assert len(rebuilt) == 2
    saved = processed_path.read_text(encoding="utf-8")
    assert "station_id,station_name,date,avg_temp_c" in saved
    assert "1994-01-01" in saved


def test_rebuild_processed_from_raw_wraps_output_path_error(tmp_path: Path) -> None:
    raw_root = tmp_path / "raw"
    year_dir = raw_root / "1994"
    year_dir.mkdir(parents=True)
    csv_path = year_dir / "SURFACE_ASOS_108_DAY_1994_1994_2018.csv"
    csv_path.write_bytes(
        FIXTURE_PATH.with_name("asos_1994_sample.csv")
        .read_text(encoding="utf-8")
        .encode("cp949")
    )
    output_directory = tmp_path / "processed.csv"
    output_directory.mkdir()

    with pytest.raises(DataValidationError, match="가공 CSV.*저장"):
        rebuild_processed_from_raw(
            start_year=1994,
            end_year=1994,
            station_id=108,
            raw_root=raw_root,
            processed_path=output_directory,
        )


def test_write_manifest_atomic_wraps_directory_target_error(tmp_path: Path) -> None:
    manifest_directory = tmp_path / "manifest.json"
    manifest_directory.mkdir()

    with pytest.raises(DataValidationError, match="manifest.*저장"):
        write_manifest_atomic(manifest_directory, {"entries": []})


def test_collect_dataset_writes_manifest_and_reuses_verified_raw_files(
    tmp_path: Path,
) -> None:
    inner_filename = "SURFACE_ASOS_108_DAY_1994_1994_2018.zip"
    csv_filename = inner_filename.removesuffix(".zip") + ".csv"
    csv_bytes = FIXTURE_PATH.with_name("asos_1994_sample.csv").read_text(
        encoding="utf-8"
    ).encode("cp949")
    outer_bytes = make_nested_archive(inner_filename, csv_filename, csv_bytes)
    session = FakeSession(
        [
            FakeResponse(text=FIXTURE_PATH.read_text(encoding="utf-8")),
            FakeResponse(content=outer_bytes),
        ]
    )
    raw_root = tmp_path / "raw"
    processed_path = tmp_path / "processed" / "seoul_weather_daily.csv"

    manifest = collect_dataset(
        start_year=1994,
        end_year=1994,
        station_id=108,
        raw_root=raw_root,
        processed_path=processed_path,
        session=session,
    )
    reused = collect_dataset(
        start_year=1994,
        end_year=1994,
        station_id=108,
        raw_root=raw_root,
        processed_path=processed_path,
        session=session,
    )

    assert manifest["entry_count"] == 1
    assert manifest["entries"][0]["year"] == 1994
    assert manifest["processing"] == {
        "duplicate_rows_removed": 0,
        "duplicate_groups": [],
    }
    assert reused["entries"] == manifest["entries"]
    assert (raw_root / "manifest.json").is_file()
    assert processed_path.is_file()


def test_collect_dataset_rejects_manifest_hash_mismatch(tmp_path: Path) -> None:
    inner_filename = "SURFACE_ASOS_108_DAY_1994_1994_2018.zip"
    csv_filename = inner_filename.removesuffix(".zip") + ".csv"
    csv_bytes = FIXTURE_PATH.with_name("asos_1994_sample.csv").read_text(
        encoding="utf-8"
    ).encode("cp949")
    session = FakeSession(
        [
            FakeResponse(text=FIXTURE_PATH.read_text(encoding="utf-8")),
            FakeResponse(
                content=make_nested_archive(inner_filename, csv_filename, csv_bytes)
            ),
        ]
    )
    raw_root = tmp_path / "raw"
    processed_path = tmp_path / "processed.csv"
    collect_dataset(
        start_year=1994,
        end_year=1994,
        station_id=108,
        raw_root=raw_root,
        processed_path=processed_path,
        session=session,
    )
    csv_path = raw_root / "1994" / csv_filename
    original = csv_path.read_bytes()
    csv_path.write_bytes(b"X" + original[1:])

    with pytest.raises(DataValidationError, match="SHA-256"):
        collect_dataset(
            start_year=1994,
            end_year=1994,
            station_id=108,
            raw_root=raw_root,
            processed_path=processed_path,
            session=session,
        )


def test_validate_manifest_scope_rejects_missing_year_entry() -> None:
    manifest = {
        "station_id": 108,
        "start_year": 1994,
        "end_year": 1995,
        "entry_count": 1,
        "entries": [{"year": 1994, "station_id": 108}],
    }

    with pytest.raises(DataValidationError, match="연도.*누락"):
        validate_manifest_scope(manifest, 1994, 1995, 108)


def test_validate_manifest_scope_rejects_entry_count_mismatch() -> None:
    manifest = {
        "station_id": 108,
        "start_year": 1994,
        "end_year": 1994,
        "entry_count": 2,
        "entries": [{"year": 1994, "station_id": 108}],
    }

    with pytest.raises(DataValidationError, match="entry_count"):
        validate_manifest_scope(manifest, 1994, 1994, 108)


def test_validate_manifest_scope_rejects_entry_station_mismatch() -> None:
    manifest = {
        "station_id": 108,
        "start_year": 1994,
        "end_year": 1994,
        "entry_count": 1,
        "entries": [{"year": 1994, "station_id": 109}],
    }

    with pytest.raises(DataValidationError, match="지점"):
        validate_manifest_scope(manifest, 1994, 1994, 108)
