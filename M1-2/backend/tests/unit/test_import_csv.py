from pathlib import Path

from app.services.data_service import DataService
from scripts.import_csv import import_records, parse_csv
from tests.fakes.repositories import InMemoryDataRepository


def write(path: Path, contents: str) -> Path:
    path.write_text(contents, encoding="utf-8")
    return path


def test_parse_csv_skips_blanks_and_reports_invalid_rows(tmp_path: Path) -> None:
    csv_path = write(
        tmp_path / "weights.csv",
        "date,value,memo\n"
        "2025-01-01,72.4,\n"
        ",72.3,missing date\n"
        "2025-01-03,,missing value\n"
        "invalid,72.2,bad date\n",
    )

    batch = parse_csv(csv_path)

    assert len(batch.records) == 1
    assert batch.skipped == 2
    assert len(batch.errors) == 1
    assert "row 5" in batch.errors[0]


def test_parse_csv_rejects_wrong_headers(tmp_path: Path) -> None:
    csv_path = write(tmp_path / "weights.csv", "day,weight\n2025-01-01,72.4\n")

    batch = parse_csv(csv_path)

    assert batch.records == []
    assert batch.errors == ["CSV headers must be exactly: date,value,memo"]


def test_parse_csv_rejects_duplicate_dates_inside_file(tmp_path: Path) -> None:
    csv_path = write(
        tmp_path / "weights.csv",
        "date,value,memo\n2025-01-01,72.4,\n2025-01-01,72.2,\n",
    )

    batch = parse_csv(csv_path)

    assert len(batch.records) == 1
    assert len(batch.errors) == 1
    assert "duplicate date" in batch.errors[0]


def test_dry_run_counts_valid_rows_without_writes(tmp_path: Path) -> None:
    csv_path = write(
        tmp_path / "weights.csv",
        "date,value,memo\n2025-01-01,72.4,\n2025-01-02,72.2,\n",
    )
    batch = parse_csv(csv_path)
    service = DataService(InMemoryDataRepository())

    report = import_records(service, batch, dry_run=True)

    assert report.valid == 2
    assert report.created == 0
    assert report.skipped == 0
    assert report.failed == 0
    assert service.list_records() == []


def test_import_preserves_existing_dates(tmp_path: Path) -> None:
    csv_path = write(
        tmp_path / "weights.csv",
        "date,value,memo\n2025-01-01,72.4,\n2025-01-02,72.2,\n",
    )
    batch = parse_csv(csv_path)
    service = DataService(InMemoryDataRepository())
    service.create_record(batch.records[0])

    report = import_records(service, batch, dry_run=False)

    assert report.created == 1
    assert report.skipped == 1
    assert report.failed == 0
    assert len(service.list_records()) == 2
