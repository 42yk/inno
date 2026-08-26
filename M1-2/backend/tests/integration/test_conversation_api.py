from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.conversation_service import ConversationService
from tests.fakes.repositories import InMemoryConversationRepository


def make_client() -> TestClient:
    service = ConversationService(InMemoryConversationRepository())
    return TestClient(
        create_app(Settings.for_test(), conversation_service=service)
    )


def create_conversation(client: TestClient, title: str = "체중 질문") -> dict:
    response = client.post(
        "/api/conversations",
        json={
            "title": title,
            "messages": [
                {"role": "user", "content": "최근 체중은?"},
                {"role": "assistant", "content": "72.1kg입니다."},
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_list_and_load_conversation() -> None:
    client = make_client()
    created = create_conversation(client)

    listing = client.get("/api/conversations")
    detail = client.get(f"/api/conversations/{created['id']}")

    assert listing.status_code == 200
    assert listing.json()["count"] == 1
    assert listing.json()["items"][0]["message_count"] == 2
    assert "messages" not in listing.json()["items"][0]
    assert detail.status_code == 200
    assert [message["role"] for message in detail.json()["messages"]] == [
        "user",
        "assistant",
    ]


def test_conversation_list_is_updated_time_descending() -> None:
    client = make_client()
    first = create_conversation(client, "첫 대화")
    second = create_conversation(client, "둘째 대화")

    response = client.get("/api/conversations")

    assert [item["id"] for item in response.json()["items"]] == [
        second["id"],
        first["id"],
    ]


def test_delete_and_missing_conversation_use_public_contract() -> None:
    client = make_client()
    created = create_conversation(client)

    deleted = client.delete(f"/api/conversations/{created['id']}")
    missing_detail = client.get(f"/api/conversations/{created['id']}")
    missing_delete = client.delete("/api/conversations/missing")

    assert deleted.status_code == 204
    assert missing_detail.status_code == 404
    assert missing_detail.json()["error"]["code"] == "record_not_found"
    assert missing_delete.status_code == 404


def test_create_validates_roles_content_and_title() -> None:
    client = make_client()

    invalid_role = client.post(
        "/api/conversations",
        json={
            "title": "테스트",
            "messages": [{"role": "system", "content": "비공개 프롬프트"}],
        },
    )
    blank_content = client.post(
        "/api/conversations",
        json={
            "title": "테스트",
            "messages": [{"role": "user", "content": "   "}],
        },
    )

    assert invalid_role.status_code == 422
    assert blank_content.status_code == 422
    assert invalid_role.json()["error"]["code"] == "validation_error"
