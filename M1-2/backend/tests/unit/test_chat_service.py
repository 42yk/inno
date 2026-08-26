import json
from datetime import date
from decimal import Decimal

import pytest

from app.clients.openai_client import FunctionCall, ModelTurn
from app.errors import AIProviderError, ToolCallLimitError
from app.schemas.chat import ChatRequest
from app.schemas.data import DataCreate
from app.services.chat_service import ChatService
from app.services.conversation_service import ConversationService
from app.services.data_service import DataService
from app.services.summary_service import SummaryService
from app.services.tool_service import ToolService
from tests.fakes.openai_client import ScriptedOpenAIClient
from tests.fakes.repositories import (
    InMemoryConversationRepository,
    InMemoryDataRepository,
)


def final_turn(answer: str, response_id: str = "response-final") -> ModelTurn:
    return ModelTurn(response_id=response_id, final_text=answer, function_calls=[])


def tool_turn(
    name: str,
    arguments: str,
    *,
    call_id: str = "call-1",
    response_id: str = "response-tool",
) -> ModelTurn:
    return ModelTurn(
        response_id=response_id,
        final_text=None,
        function_calls=[
            FunctionCall(call_id=call_id, name=name, arguments=arguments)
        ],
    )


def build_service(
    client: ScriptedOpenAIClient,
    *,
    max_tool_calls: int = 4,
) -> tuple[ChatService, ConversationService]:
    data_service = DataService(InMemoryDataRepository())
    data_service.create_record(
        DataCreate(
            date=date(2025, 3, 10),
            value=Decimal("72.4"),
            memo="",
        )
    )
    summary_service = SummaryService(data_service)
    conversations = ConversationService(InMemoryConversationRepository())
    return (
        ChatService(
            ai_client=client,
            summary_service=summary_service,
            tool_service=ToolService(data_service, summary_service),
            conversation_service=conversations,
            max_tool_calls=max_tool_calls,
        ),
        conversations,
    )


def test_summary_is_injected_before_direct_answer_and_exchange_is_saved() -> None:
    client = ScriptedOpenAIClient([final_turn("최근 체중은 72.4kg입니다.")])
    service, conversations = build_service(client)

    result = service.chat(ChatRequest(message="최근 체중은?"))

    assert '"count": 1' in client.start_calls[0]["instructions"]
    assert '"value": 72.4' in client.start_calls[0]["instructions"]
    assert client.start_calls[0]["messages"] == [
        {"role": "user", "content": "최근 체중은?"}
    ]
    assert result.answer == "최근 체중은 72.4kg입니다."
    saved = conversations.get(result.conversation_id)
    assert [message.content for message in saved.messages] == [
        "최근 체중은?",
        "최근 체중은 72.4kg입니다.",
    ]


def test_date_tool_is_dispatched_and_call_id_is_preserved() -> None:
    client = ScriptedOpenAIClient(
        [
            tool_turn(
                "get_weight_by_date",
                '{"date":"2025-03-10"}',
                call_id="date-call",
            ),
            final_turn("2025-03-10 체중은 72.4kg입니다."),
        ]
    )
    service, _conversations = build_service(client)

    result = service.chat(ChatRequest(message="3월 10일 체중은?"))

    output = client.continue_calls[0]["outputs"][0]
    assert output.call_id == "date-call"
    assert json.loads(output.output)["record"]["value"] == 72.4
    assert result.tools_used == ["get_weight_by_date"]


def test_range_statistics_tool_is_dispatched() -> None:
    client = ScriptedOpenAIClient(
        [
            tool_turn(
                "get_weight_statistics",
                '{"start_date":"2025-03-01","end_date":"2025-03-31"}',
            ),
            final_turn("3월 평균은 72.4kg입니다."),
        ]
    )
    service, _conversations = build_service(client)

    result = service.chat(ChatRequest(message="3월 평균은?"))

    output = json.loads(client.continue_calls[0]["outputs"][0].output)
    assert output["count"] == 1
    assert result.tools_used == ["get_weight_statistics"]


def test_invalid_tool_arguments_are_returned_as_safe_output() -> None:
    client = ScriptedOpenAIClient(
        [
            tool_turn("get_weight_by_date", '{"date":"not-a-date"}'),
            final_turn("날짜를 확인해 주세요."),
        ]
    )
    service, _conversations = build_service(client)

    service.chat(ChatRequest(message="그날 체중은?"))

    output = json.loads(client.continue_calls[0]["outputs"][0].output)
    assert output == {
        "ok": False,
        "error": {"code": "invalid_tool_arguments"},
    }


def test_more_than_tool_limit_stops_without_saving() -> None:
    calls = [
        FunctionCall(call_id=f"call-{index}", name="get_weight_summary", arguments="{}")
        for index in range(5)
    ]
    client = ScriptedOpenAIClient(
        [ModelTurn(response_id="too-many", final_text=None, function_calls=calls)]
    )
    service, conversations = build_service(client, max_tool_calls=4)

    with pytest.raises(ToolCallLimitError):
        service.chat(ChatRequest(message="요약해줘"))

    assert conversations.list() == []
    assert client.continue_calls == []


def test_openai_failure_stores_no_exchange() -> None:
    client = ScriptedOpenAIClient([RuntimeError("secret provider detail")])
    service, conversations = build_service(client)

    with pytest.raises(AIProviderError):
        service.chat(ChatRequest(message="최근 체중은?"))

    assert conversations.list() == []


def test_existing_conversation_history_is_supplied_and_extended() -> None:
    client = ScriptedOpenAIClient([final_turn("첫 답변"), final_turn("둘째 답변")])
    service, conversations = build_service(client)
    first = service.chat(ChatRequest(message="첫 질문"))

    second = service.chat(
        ChatRequest(message="둘째 질문", conversation_id=first.conversation_id)
    )

    assert client.start_calls[1]["messages"] == [
        {"role": "user", "content": "첫 질문"},
        {"role": "assistant", "content": "첫 답변"},
        {"role": "user", "content": "둘째 질문"},
    ]
    assert second.conversation_id == first.conversation_id
    assert [message.content for message in conversations.get(first.conversation_id).messages] == [
        "첫 질문",
        "첫 답변",
        "둘째 질문",
        "둘째 답변",
    ]
