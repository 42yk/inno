from __future__ import annotations

import re

from app.errors import RecordNotFoundError
from app.repositories.conversation_repository import ConversationRepository
from app.schemas.conversations import (
    Conversation,
    ConversationCreate,
    ConversationSummary,
    MessageInput,
)


TITLE_LIMIT = 60


def normalize_title(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()[:TITLE_LIMIT]


class ConversationService:
    def __init__(self, repository: ConversationRepository) -> None:
        self._repository = repository

    def create(self, payload: ConversationCreate) -> Conversation:
        first_user = next(
            message.content for message in payload.messages if message.role == "user"
        )
        title = normalize_title(payload.title or first_user)
        return self._repository.create(title, payload.messages)

    def list(self) -> list[ConversationSummary]:
        conversations = sorted(
            self._repository.list(),
            key=lambda conversation: conversation.updated_at,
            reverse=True,
        )
        return [
            ConversationSummary(
                id=conversation.id,
                title=conversation.title,
                message_count=len(conversation.messages),
                created_at=conversation.created_at,
                updated_at=conversation.updated_at,
            )
            for conversation in conversations
        ]

    def get(self, conversation_id: str) -> Conversation:
        conversation = self._repository.get(conversation_id)
        if conversation is None:
            raise RecordNotFoundError(conversation_id)
        return conversation

    def delete(self, conversation_id: str) -> None:
        if not self._repository.delete(conversation_id):
            raise RecordNotFoundError(conversation_id)

    def append_exchange(
        self,
        conversation_id: str | None,
        user_content: str,
        assistant_content: str,
    ) -> Conversation:
        user_message = MessageInput(role="user", content=user_content)
        assistant_message = MessageInput(role="assistant", content=assistant_content)
        if conversation_id is None:
            return self._repository.create(
                normalize_title(user_message.content),
                [user_message, assistant_message],
            )
        if self._repository.get(conversation_id) is None:
            raise RecordNotFoundError(conversation_id)
        return self._repository.append_exchange(
            conversation_id,
            user_message.content,
            assistant_message.content,
        )
