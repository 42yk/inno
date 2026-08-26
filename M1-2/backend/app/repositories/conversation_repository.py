from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

from google.cloud import firestore

from app.errors import RecordNotFoundError
from app.schemas.conversations import Conversation, Message, MessageInput


class ConversationRepository(Protocol):
    def create(
        self,
        title: str,
        messages: list[MessageInput],
    ) -> Conversation: ...

    def list(self) -> list[Conversation]: ...

    def get(self, conversation_id: str) -> Conversation | None: ...

    def delete(self, conversation_id: str) -> bool: ...

    def append_exchange(
        self,
        conversation_id: str,
        user_content: str,
        assistant_content: str,
    ) -> Conversation: ...


class FirestoreConversationRepository:
    def __init__(self, client: Any) -> None:
        self._client = client
        self._collection = client.collection("conversations")

    @staticmethod
    def _message_dict(message: MessageInput, created_at: datetime) -> dict[str, Any]:
        return {
            "role": message.role,
            "content": message.content,
            "created_at": created_at,
        }

    @staticmethod
    def _conversation(snapshot: Any) -> Conversation:
        payload = snapshot.to_dict()
        return Conversation(
            id=snapshot.id,
            title=payload["title"],
            messages=[Message.model_validate(message) for message in payload["messages"]],
            created_at=payload["created_at"],
            updated_at=payload["updated_at"],
        )

    def create(
        self,
        title: str,
        messages: list[MessageInput],
    ) -> Conversation:
        reference = self._collection.document()
        created_at = datetime.now(UTC)
        reference.set(
            {
                "title": title,
                "messages": [
                    self._message_dict(message, created_at) for message in messages
                ],
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP,
            }
        )
        return self._conversation(reference.get())

    def list(self) -> list[Conversation]:
        query = self._collection.order_by(
            "updated_at",
            direction=firestore.Query.DESCENDING,
        )
        return [self._conversation(snapshot) for snapshot in query.stream()]

    def get(self, conversation_id: str) -> Conversation | None:
        snapshot = self._collection.document(conversation_id).get()
        return self._conversation(snapshot) if snapshot.exists else None

    def delete(self, conversation_id: str) -> bool:
        reference = self._collection.document(conversation_id)
        transaction = self._client.transaction()

        @firestore.transactional
        def delete_in_transaction(active_transaction: Any) -> bool:
            snapshot = reference.get(transaction=active_transaction)
            if not snapshot.exists:
                return False
            active_transaction.delete(reference)
            return True

        return delete_in_transaction(transaction)

    def append_exchange(
        self,
        conversation_id: str,
        user_content: str,
        assistant_content: str,
    ) -> Conversation:
        reference = self._collection.document(conversation_id)
        transaction = self._client.transaction()

        @firestore.transactional
        def append_in_transaction(active_transaction: Any) -> None:
            snapshot = reference.get(transaction=active_transaction)
            if not snapshot.exists:
                raise RecordNotFoundError(conversation_id)
            now = datetime.now(UTC)
            messages = list(snapshot.to_dict()["messages"])
            messages.extend(
                [
                    self._message_dict(
                        MessageInput(role="user", content=user_content),
                        now,
                    ),
                    self._message_dict(
                        MessageInput(role="assistant", content=assistant_content),
                        now,
                    ),
                ]
            )
            active_transaction.update(
                reference,
                {
                    "messages": messages,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                },
            )

        append_in_transaction(transaction)
        return self._conversation(reference.get())
