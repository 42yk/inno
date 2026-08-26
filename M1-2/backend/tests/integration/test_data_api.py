from datetime import date

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services.data_service import DataService
from app.services.summary_service import SummaryService
from tests.fakes.repositories import InMemoryDataRepository


def make_client() -> TestClient:
    data_service = DataService(InMemoryDataRepository())
    return TestClient(
        create_app(
            Settings.for_test(),
            data_service=data_service,
            summary_service=SummaryService(data_service),
        )
    )


def add(client: TestClient, day: int, value: float = 72.4) -> dict:
    response = client.post(
        "/api/data",
        json={"date": f"2025-01-{day:02d}", "value": value, "memo": ""},
    )
    assert response.status_code == 201
    return response.json()


def test_create_and_list_records_in_descending_order() -> None:
    client = make_client()
    add(client, 1, 72.4)
    add(client, 3, 72.1)

    response = client.get("/api/data")

    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert [item["date"] for item in response.json()["items"]] == [
        "2025-01-03",
        "2025-01-01",
    ]


def test_create_rejects_duplicate_date_with_error_envelope() -> None:
    client = make_client()
    add(client, 1)

    response = client.post(
        "/api/data",
        json={"date": "2025-01-01", "value": 72.0, "memo": ""},
    )

    assert response.status_code == 409
    assert response.json() == {
        "error": {
            "code": "duplicate_date",
            "message": "해당 날짜의 기록이 이미 존재합니다.",
            "details": None,
        }
    }


def test_list_filters_inclusive_date_range() -> None:
    client = make_client()
    for day in (1, 2, 3, 4):
        add(client, day)

    response = client.get(
        "/api/data?start_date=2025-01-02&end_date=2025-01-03"
    )

    assert response.status_code == 200
    assert [item["date"] for item in response.json()["items"]] == [
        "2025-01-03",
        "2025-01-02",
    ]


def test_reversed_date_range_returns_400() -> None:
    client = make_client()

    response = client.get(
        "/api/data?start_date=2025-01-03&end_date=2025-01-02"
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_period"


def test_update_can_change_date_and_delete_record() -> None:
    client = make_client()
    add(client, 1)

    update = client.put(
        "/api/data/2025-01-01",
        json={"date": "2025-01-02", "value": 71.9, "memo": "아침"},
    )
    missing_delete = client.delete("/api/data/2025-01-01")
    deleted = client.delete("/api/data/2025-01-02")

    assert update.status_code == 200
    assert update.json()["id"] == "2025-01-02"
    assert update.json()["value"] == 71.9
    assert missing_delete.status_code == 404
    assert deleted.status_code == 204
    assert client.get("/api/data").json()["count"] == 0


def test_summary_returns_required_metrics() -> None:
    client = make_client()
    add(client, 1, 72.0)
    add(client, 2, 75.0)
    add(client, 3, 70.0)
    add(client, 4, 75.0)

    response = client.get("/api/data/summary")
    payload = response.json()

    assert response.status_code == 200
    assert payload["period"] == {"start": "2025-01-01", "end": "2025-01-04"}
    assert payload["count"] == 4
    assert payload["metrics"]["average"] == 73.0
    assert payload["metrics"]["max"] == {
        "value": 75.0,
        "dates": ["2025-01-02", "2025-01-04"],
    }
    assert payload["metrics"]["change"] == 3.0
    assert payload["trend"]["status"] == "insufficient_data"


def test_validation_errors_use_public_envelope() -> None:
    client = make_client()

    response = client.post(
        "/api/data",
        json={"date": date.today().isoformat(), "value": 10, "memo": ""},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["message"] == "입력 값을 확인해 주세요."
