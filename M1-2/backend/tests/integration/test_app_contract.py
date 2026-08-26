from datetime import date
from decimal import Decimal

from fastapi.testclient import TestClient

from app.clients.openai_client import ModelTurn
from app.config import Settings
from app.errors import DataStoreError
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


def assembled_client() -> TestClient:
    data_service = DataService(InMemoryDataRepository())
    data_service.create_record(
        DataCreate(date=date(2025, 1, 1), value=Decimal("72.4"), memo="")
    )
    summary_service = SummaryService(data_service)
    conversations = ConversationService(InMemoryConversationRepository())
    chat_service = ChatService(
        ai_client=ScriptedOpenAIClient(
            [ModelTurn(response_id="response", final_text="답변", function_calls=[])]
        ),
        summary_service=summary_service,
        tool_service=ToolService(data_service, summary_service),
        conversation_service=conversations,
        max_tool_calls=4,
    )
    return TestClient(
        create_app(
            Settings.for_test(),
            data_service=data_service,
            summary_service=summary_service,
            conversation_service=conversations,
            chat_service=chat_service,
        )
    )


def test_openapi_exposes_every_required_assignment_endpoint() -> None:
    client = assembled_client()
    paths = client.get("/openapi.json").json()["paths"]
    required = {
        "/api/data": {"get", "post"},
        "/api/data/{record_id}": {"put", "delete"},
        "/api/data/summary": {"get"},
        "/api/conversations": {"get", "post"},
        "/api/conversations/{conversation_id}": {"get", "delete"},
        "/api/chat": {"post"},
    }

    for path, methods in required.items():
        assert path in paths
        assert methods <= set(paths[path])
    assert client.get("/health").status_code == 200
    assert client.get("/docs").status_code == 200


def test_request_id_is_returned_without_echoing_untrusted_value() -> None:
    client = assembled_client()

    response = client.get("/health", headers={"X-Request-ID": "secret-user-value"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] != "secret-user-value"
    assert len(response.headers["X-Request-ID"]) == 36


def test_data_store_error_uses_safe_503_envelope() -> None:
    class FailingRepository(InMemoryDataRepository):
        def list(self, *args: object, **kwargs: object) -> list:
            raise DataStoreError("service account secret")

    data_service = DataService(FailingRepository())
    client = TestClient(
        create_app(
            Settings.for_test(),
            data_service=data_service,
            summary_service=SummaryService(data_service),
        )
    )

    response = client.get("/api/data")

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "data_store_error",
        "message": "데이터를 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        "details": None,
    }
    assert "secret" not in response.text
