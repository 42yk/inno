from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.schemas.conversations import Conversation, Message, MessageInput
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


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self.conversations: dict[str, Conversation] = {}
        self._counter = 0

    def _now(self) -> datetime:
        self._counter += 1
        return datetime.now(UTC) + timedelta(microseconds=self._counter)

    def create(
        self,
        title: str,
        messages: list[MessageInput],
    ) -> Conversation:
        now = self._now()
        conversation_id = f"conversation-{self._counter}"
        conversation = Conversation(
            id=conversation_id,
            title=title,
            messages=[
                Message(
                    role=message.role,
                    content=message.content,
                    created_at=now,
                )
                for message in messages
            ],
            created_at=now,
            updated_at=now,
        )
        self.conversations[conversation_id] = conversation
        return conversation

    def list(self) -> list[Conversation]:
        return list(self.conversations.values())

    def get(self, conversation_id: str) -> Conversation | None:
        return self.conversations.get(conversation_id)

    def delete(self, conversation_id: str) -> bool:
        return self.conversations.pop(conversation_id, None) is not None

    def append_exchange(
        self,
        conversation_id: str,
        user_content: str,
        assistant_content: str,
    ) -> Conversation:
        original = self.conversations[conversation_id]
        now = self._now()
        updated = original.model_copy(
            update={
                "messages": [
                    *original.messages,
                    Message(role="user", content=user_content, created_at=now),
                    Message(
                        role="assistant",
                        content=assistant_content,
                        created_at=now,
                    ),
                ],
                "updated_at": now,
            }
        )
        self.conversations[conversation_id] = updated
        return updated
