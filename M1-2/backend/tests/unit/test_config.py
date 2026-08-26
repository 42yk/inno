import pytest

from app.config import Settings


def test_settings_parses_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://copa.example/v1")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv(
        "FIREBASE_SERVICE_ACCOUNT_FILE",
        "firebase-service-account.json",
    )
    monkeypatch.setenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173, https://app.example",
    )

    settings = Settings.from_env()

    assert settings.allowed_origins == (
        "http://localhost:5173",
        "https://app.example",
    )
    assert settings.openai_max_output_tokens == 500
    assert settings.openai_base_url == "https://copa.example/v1"
    assert settings.firebase_service_account_file == (
        "firebase-service-account.json"
    )
    assert settings.max_tool_calls == 4


def test_settings_rejects_missing_required_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://copa.example/v1")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv(
        "FIREBASE_SERVICE_ACCOUNT_FILE",
        "firebase-service-account.json",
    )
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173")

    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        Settings.from_env()
