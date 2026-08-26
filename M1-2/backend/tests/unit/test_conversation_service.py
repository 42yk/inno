from datetime import UTC, datetime, timedelta

import pytest

from app.errors import RecordNotFoundError
from app.schemas.conversations import ConversationCreate, MessageInput
from app.services.conversation_service import ConversationService
from tests.fakes.repositories import InMemoryConversationRepository


@pytest.fixture
def service() -> ConversationService:
    return ConversationService(InMemoryConversationRepository())


def test_append_exchange_creates_title_from_first_question(
    service: ConversationService,
) -> None:
    conversation = service.append_exchange(
        None,
        "3월 평균 체중은?",
        "72.1kg입니다.",
    )

    assert conversation.title == "3월 평균 체중은?"
    assert [message.role for message in conversation.messages] == [
        "user",
        "assistant",
    ]


def test_append_exchange_preserves_order(service: ConversationService) -> None:
    first = service.append_exchange(None, "첫 질문", "첫 답변")
    second = service.append_exchange(first.id, "둘째 질문", "둘째 답변")

    assert [message.content for message in second.messages] == [
        "첫 질문",
        "첫 답변",
        "둘째 질문",
        "둘째 답변",
    ]


def test_generated_title_is_single_line_normalized_and_limited(
    service: ConversationService,
) -> None:
    conversation = service.append_exchange(
        None,
        "  여러   공백과\n줄바꿈이 있는 " + "긴 질문" * 30,
        "답변",
    )

    assert "\n" not in conversation.title
    assert "  " not in conversation.title
    assert len(conversation.title) == 60


def test_create_uses_explicit_title_and_messages(
    service: ConversationService,
) -> None:
    conversation = service.create(
        ConversationCreate(
            title=" 저장할   대화 ",
            messages=[
                MessageInput(role="user", content="질문"),
                MessageInput(role="assistant", content="답변"),
            ],
        )
    )

    assert conversation.title == "저장할 대화"
    assert [message.content for message in conversation.messages] == ["질문", "답변"]


def test_list_returns_updated_time_descending() -> None:
    repository = InMemoryConversationRepository()
    service = ConversationService(repository)
    first = service.append_exchange(None, "첫 질문", "첫 답변")
    second = service.append_exchange(None, "다른 질문", "다른 답변")
    repository.conversations[first.id] = repository.conversations[
        first.id
    ].model_copy(update={"updated_at": datetime.now(UTC) + timedelta(days=1)})

    items = service.list()

    assert [item.id for item in items] == [first.id, second.id]
    assert all(item.message_count == 2 for item in items)


def test_get_delete_and_append_raise_for_missing_conversation(
    service: ConversationService,
) -> None:
    with pytest.raises(RecordNotFoundError):
        service.get("missing")
    with pytest.raises(RecordNotFoundError):
        service.delete("missing")
    with pytest.raises(RecordNotFoundError):
        service.append_exchange("missing", "질문", "답변")
