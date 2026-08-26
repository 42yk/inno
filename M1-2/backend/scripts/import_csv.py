from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pydantic import ValidationError

from app.config import Settings
from app.errors import DuplicateDateError
from app.firebase import create_firestore_client
from app.repositories.data_repository import FirestoreDataRepository
from app.schemas.data import DataCreate
from app.services.data_service import DataService


EXPECTED_HEADERS = ["date", "value", "memo"]


@dataclass
class ImportBatch:
    records: list[DataCreate]
    skipped: int
    errors: list[str]


@dataclass
class ImportReport:
    valid: int
    created: int
    skipped: int
    failed: int


def parse_csv(path: Path) -> ImportBatch:
    records: list[DataCreate] = []
    errors: list[str] = []
    skipped = 0
    seen_dates: set[str] = set()

    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != EXPECTED_HEADERS:
            return ImportBatch(
                records=[],
                skipped=0,
                errors=["CSV headers must be exactly: date,value,memo"],
            )

        for row_number, row in enumerate(reader, start=2):
            raw_date = (row.get("date") or "").strip()
            raw_value = (row.get("value") or "").strip()
            if not raw_date or not raw_value:
                skipped += 1
                continue
            if raw_date in seen_dates:
                errors.append(f"row {row_number}: duplicate date {raw_date}")
                continue
            try:
                payload = DataCreate(
                    date=raw_date,
                    value=raw_value,
                    memo=(row.get("memo") or "").strip(),
                )
            except ValidationError as exc:
                errors.append(f"row {row_number}: {exc.errors()[0]['msg']}")
                continue
            seen_dates.add(raw_date)
            records.append(payload)

    return ImportBatch(records=records, skipped=skipped, errors=errors)


def import_records(
    service: DataService,
    batch: ImportBatch,
    *,
    dry_run: bool,
) -> ImportReport:
    if dry_run:
        return ImportReport(
            valid=len(batch.records),
            created=0,
            skipped=batch.skipped,
            failed=len(batch.errors),
        )

    created = 0
    skipped = batch.skipped
    failed = len(batch.errors)
    for record in batch.records:
        try:
            service.create_record(record)
        except DuplicateDateError:
            skipped += 1
        except Exception:
            failed += 1
        else:
            created += 1
    return ImportReport(
        valid=len(batch.records),
        created=created,
        skipped=skipped,
        failed=failed,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Import weight records from CSV")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    batch = parse_csv(args.csv_path)
    if args.dry_run:
        report = ImportReport(
            valid=len(batch.records),
            created=0,
            skipped=batch.skipped,
            failed=len(batch.errors),
        )
    else:
        settings = Settings.from_env()
        client = create_firestore_client(settings.firebase_service_account_json)
        service = DataService(FirestoreDataRepository(client))
        report = import_records(service, batch, dry_run=False)

    print(json.dumps(report.__dict__, ensure_ascii=False))
    for error in batch.errors:
        print(error, file=sys.stderr)
    return 1 if report.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
