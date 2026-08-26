from __future__ import annotations

from datetime import date

from app.errors import DuplicateDateError, InvalidPeriodError, RecordNotFoundError
from app.repositories.data_repository import DataRepository
from app.schemas.data import DataCreate, DataRecord, DataUpdate


class DataService:
    def __init__(self, repository: DataRepository) -> None:
        self._repository = repository

    def list_records(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        *,
        descending: bool = True,
    ) -> list[DataRecord]:
        if start_date is not None and end_date is not None:
            if start_date > end_date:
                raise InvalidPeriodError("start_date must not exceed end_date")
        return self._repository.list(
            start_date=start_date,
            end_date=end_date,
            descending=descending,
        )

    def find_record(self, record_id: str) -> DataRecord | None:
        return self._repository.get(record_id)

    def create_record(self, payload: DataCreate) -> DataRecord:
        record_id = payload.date.isoformat()
        if self._repository.get(record_id) is not None:
            raise DuplicateDateError(record_id)
        return self._repository.create(payload)

    def update_record(
        self,
        record_id: str,
        payload: DataUpdate,
    ) -> DataRecord:
        if self._repository.get(record_id) is None:
            raise RecordNotFoundError(record_id)
        target_id = payload.date.isoformat()
        if target_id != record_id and self._repository.get(target_id) is not None:
            raise DuplicateDateError(target_id)
        return self._repository.replace(record_id, payload)

    def delete_record(self, record_id: str) -> None:
        if not self._repository.delete(record_id):
            raise RecordNotFoundError(record_id)
