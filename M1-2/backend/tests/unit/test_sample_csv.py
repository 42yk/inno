import csv
from datetime import date
from decimal import Decimal
from itertools import pairwise
from pathlib import Path

from scripts.generate_sample_csv import build_rows, write_csv


def test_build_rows_produces_valid_irregular_time_series() -> None:
    rows = build_rows(120)
    dates = [date.fromisoformat(row["date"]) for row in rows]
    values = [Decimal(row["value"]) for row in rows]

    assert len(rows) == 120
    assert dates == sorted(dates)
    assert len(set(dates)) == 120
    assert any((right - left).days > 1 for left, right in pairwise(dates))
    assert all(
        Decimal("20.0") <= value <= Decimal("300.0")
        for value in values
    )
    assert all(
        value == value.quantize(Decimal("0.1")) for value in values
    )
    assert all(row["memo"] == "" for row in rows)


def test_write_csv_uses_expected_header_and_utf8(tmp_path: Path) -> None:
    output = tmp_path / "weights.csv"

    write_csv(output, build_rows(3))

    with output.open(encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)
    assert reader.fieldnames == ["date", "value", "memo"]
    assert len(rows) == 3
    assert rows[0] == {"date": "2025-01-01", "value": "78.0", "memo": ""}
