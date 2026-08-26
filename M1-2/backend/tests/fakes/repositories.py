from __future__ import annotations

from datetime import UTC, date, datetime

from app.schemas.data import DataCreate, DataRecord, DataUpdate


class InMemoryDataRepository:
    def __init__(self) -> None:
        self.records: dict[str, DataRecord] = {}

    def list(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        *,
        descending: bool = False,
    ) -> list[DataRecord]:
        records = [
            record
            for record in self.records.values()
            if (start_date is None or record.date >= start_date)
            and (end_date is None or record.date <= end_date)
        ]
        return sorted(
            records,
            key=lambda record: record.date,
            reverse=descending,
        )

    def get(self, record_id: str) -> DataRecord | None:
        return self.records.get(record_id)

    def create(self, payload: DataCreate) -> DataRecord:
        now = datetime.now(UTC)
        record = DataRecord(
            id=payload.date.isoformat(),
            date=payload.date,
            value=payload.value,
            memo=payload.memo,
            created_at=now,
            updated_at=now,
        )
        self.records[record.id] = record
        return record

    def replace(self, record_id: str, payload: DataUpdate) -> DataRecord:
        original = self.records[record_id]
        updated = DataRecord(
            id=payload.date.isoformat(),
            date=payload.date,
            value=payload.value,
            memo=payload.memo,
            created_at=original.created_at,
            updated_at=datetime.now(UTC),
        )
        del self.records[record_id]
        self.records[updated.id] = updated
        return updated

    def delete(self, record_id: str) -> bool:
        return self.records.pop(record_id, None) is not None
