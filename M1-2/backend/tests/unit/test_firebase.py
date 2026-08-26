import json

import pytest

from app.firebase import load_service_account


def test_load_service_account_reads_json_object(tmp_path) -> None:
    path = tmp_path / "service-account.json"
    path.write_text(
        json.dumps({"type": "service_account", "project_id": "test-project"}),
        encoding="utf-8",
    )

    payload = load_service_account(str(path))

    assert payload["type"] == "service_account"
    assert payload["project_id"] == "test-project"


def test_load_service_account_rejects_non_object_json(tmp_path) -> None:
    path = tmp_path / "service-account.json"
    path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="JSON object"):
        load_service_account(str(path))


def test_load_service_account_resolves_relative_path_from_backend_root(
    tmp_path,
    monkeypatch,
) -> None:
    path = tmp_path / "service-account.json"
    path.write_text('{"project_id":"relative-project"}', encoding="utf-8")
    monkeypatch.setattr("app.firebase.BACKEND_ROOT", tmp_path)

    payload = load_service_account("service-account.json")

    assert payload["project_id"] == "relative-project"
