from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


MessageRole = Literal["user", "assistant"]


class MessageInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    role: MessageRole
    content: str = Field(min_length=1, max_length=4000)


class Message(MessageInput):
    created_at: datetime


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=200)
    messages: list[MessageInput] = Field(min_length=1, max_length=100)

    @field_validator("messages")
    @classmethod
    def require_user_message(
        cls,
        value: list[MessageInput],
    ) -> list[MessageInput]:
        if not any(message.role == "user" for message in value):
            raise ValueError("at least one user message is required")
        return value


class Conversation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    messages: list[Message]
    created_at: datetime
    updated_at: datetime


class ConversationSummary(BaseModel):
    id: str
    title: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationSummary]
    count: int
