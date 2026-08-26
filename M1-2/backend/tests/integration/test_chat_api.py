from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.clients.openai_client import ModelTurn
from app.config import Settings
from app.main import create_app
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


def make_client(turns: list[ModelTurn | Exception]) -> TestClient:
    data_service = DataService(InMemoryDataRepository())
    data_service.create_record(
        DataCreate(date=date(2025, 1, 1), value=Decimal("72.4"), memo="")
    )
    summary_service = SummaryService(data_service)
    conversation_service = ConversationService(InMemoryConversationRepository())
    chat_service = ChatService(
        ai_client=ScriptedOpenAIClient(turns),
        summary_service=summary_service,
        tool_service=ToolService(data_service, summary_service),
        conversation_service=conversation_service,
        max_tool_calls=4,
    )
    return TestClient(
        create_app(
            Settings.for_test(),
            conversation_service=conversation_service,
            chat_service=chat_service,
        )
    )


def test_chat_returns_answer_and_automatic_conversation_id() -> None:
    client = make_client(
        [
            ModelTurn(
                response_id="response-1",
                final_text="최근 체중은 72.4kg입니다.",
                function_calls=[],
            )
        ]
    )

    response = client.post("/api/chat", json={"message": "최근 체중은?"})

    assert response.status_code == 200
    assert response.json()["answer"] == "최근 체중은 72.4kg입니다."
    assert response.json()["conversation_id"].startswith("conversation-")
    assert response.json()["tools_used"] == []
    assert client.get("/api/conversations").json()["count"] == 1


def test_chat_validation_uses_public_error_envelope() -> None:
    client = make_client([])

    blank = client.post("/api/chat", json={"message": "   "})
    too_long = client.post("/api/chat", json={"message": "가" * 1001})

    assert blank.status_code == 422
    assert too_long.status_code == 422
    assert blank.json()["error"]["code"] == "validation_error"


def test_validation_error_does_not_echo_private_prompt() -> None:
    client = make_client([])
    private_prompt = "PRIVATE-PROMPT-" * 80

    response = client.post("/api/chat", json={"message": private_prompt})

    assert response.status_code == 422
    assert "PRIVATE-PROMPT" not in response.text
    assert set(response.json()["error"]["details"][0]) == {
        "type",
        "loc",
        "msg",
    }


def test_openai_failure_returns_502_without_internal_detail() -> None:
    client = make_client([RuntimeError("secret provider detail")])

    response = client.post("/api/chat", json={"message": "최근 체중은?"})

    assert response.status_code == 502
    assert response.json() == {
        "error": {
            "code": "ai_provider_error",
            "message": "AI 답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.",
            "details": None,
        }
    }
    assert "secret" not in response.text
