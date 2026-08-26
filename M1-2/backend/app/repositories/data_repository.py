from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.errors import DuplicateDateError, RecordNotFoundError
from app.schemas.data import DataCreate, DataRecord, DataUpdate


class DataRepository(Protocol):
    def list(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        *,
        descending: bool = False,
    ) -> list[DataRecord]: ...

    def get(self, record_id: str) -> DataRecord | None: ...

    def create(self, payload: DataCreate) -> DataRecord: ...

    def replace(self, record_id: str, payload: DataUpdate) -> DataRecord: ...

    def delete(self, record_id: str) -> bool: ...


class FirestoreDataRepository:
    def __init__(self, client: Any) -> None:
        self._client = client
        self._collection = client.collection("data")

    @staticmethod
    def _payload(payload: DataCreate | DataUpdate) -> dict[str, Any]:
        return {
            "date": payload.date.isoformat(),
            "value": float(payload.value),
            "memo": payload.memo,
        }

    @staticmethod
    def _record(snapshot: Any) -> DataRecord:
        payload = snapshot.to_dict()
        return DataRecord(
            id=snapshot.id,
            date=payload["date"],
            value=payload["value"],
            memo=payload.get("memo", ""),
            created_at=payload["created_at"],
            updated_at=payload["updated_at"],
        )

    def list(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        *,
        descending: bool = False,
    ) -> list[DataRecord]:
        query = self._collection
        if start_date is not None:
            query = query.where(
                filter=FieldFilter("date", ">=", start_date.isoformat())
            )
        if end_date is not None:
            query = query.where(
                filter=FieldFilter("date", "<=", end_date.isoformat())
            )
        direction = (
            firestore.Query.DESCENDING
            if descending
            else firestore.Query.ASCENDING
        )
        query = query.order_by("date", direction=direction)
        return [self._record(snapshot) for snapshot in query.stream()]

    def get(self, record_id: str) -> DataRecord | None:
        snapshot = self._collection.document(record_id).get()
        return self._record(snapshot) if snapshot.exists else None

    def create(self, payload: DataCreate) -> DataRecord:
        reference = self._collection.document(payload.date.isoformat())
        transaction = self._client.transaction()

        @firestore.transactional
        def create_in_transaction(active_transaction: Any) -> None:
            if reference.get(transaction=active_transaction).exists:
                raise DuplicateDateError(payload.date.isoformat())
            document = self._payload(payload)
            document["created_at"] = firestore.SERVER_TIMESTAMP
            document["updated_at"] = firestore.SERVER_TIMESTAMP
            active_transaction.set(reference, document)

        create_in_transaction(transaction)
        return self._record(reference.get())

    def replace(self, record_id: str, payload: DataUpdate) -> DataRecord:
        old_reference = self._collection.document(record_id)
        new_id = payload.date.isoformat()
        new_reference = self._collection.document(new_id)
        transaction = self._client.transaction()

        @firestore.transactional
        def replace_in_transaction(active_transaction: Any) -> None:
            old_snapshot = old_reference.get(transaction=active_transaction)
            if not old_snapshot.exists:
                raise RecordNotFoundError(record_id)
            if new_id != record_id and new_reference.get(
                transaction=active_transaction
            ).exists:
                raise DuplicateDateError(new_id)
            document = self._payload(payload)
            document["created_at"] = old_snapshot.to_dict()["created_at"]
            document["updated_at"] = firestore.SERVER_TIMESTAMP
            active_transaction.set(new_reference, document)
            if new_id != record_id:
                active_transaction.delete(old_reference)

        replace_in_transaction(transaction)
        return self._record(new_reference.get())

    def delete(self, record_id: str) -> bool:
        reference = self._collection.document(record_id)
        transaction = self._client.transaction()

        @firestore.transactional
        def delete_in_transaction(active_transaction: Any) -> bool:
            snapshot = reference.get(transaction=active_transaction)
            if not snapshot.exists:
                return False
            active_transaction.delete(reference)
            return True

        return delete_in_transaction(transaction)
