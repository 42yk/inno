from __future__ import annotations

import csv
import math
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path


FIELDNAMES = ("date", "value", "memo")


def build_rows(count: int = 120) -> list[dict[str, str]]:
    if count < 1:
        raise ValueError("count must be positive")
    start = date(2025, 1, 1)
    rows: list[dict[str, str]] = []
    for index in range(count):
        measured_on = start + timedelta(days=index + index // 3)
        weight = 78.0 - (0.035 * index) + (0.4 * math.sin(index / 6))
        rows.append(
            {
                "date": measured_on.isoformat(),
                "value": f"{weight:.1f}",
                "memo": "",
            }
        )
    return rows


def write_csv(path: Path, rows: Sequence[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    write_csv(project_root / "data" / "weights.csv", build_rows())


if __name__ == "__main__":
    main()
