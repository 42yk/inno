from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_base_url: str
    openai_model: str
    openai_max_output_tokens: int
    firebase_service_account_file: str
    allowed_origins: tuple[str, ...]
    max_tool_calls: int = 4

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        origins = tuple(
            origin.strip()
            for origin in _required("ALLOWED_ORIGINS").split(",")
            if origin.strip()
        )
        if not origins:
            raise ValueError("ALLOWED_ORIGINS must contain at least one origin")
        try:
            max_output_tokens = int(
                os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "500")
            )
        except ValueError as exc:
            raise ValueError(
                "OPENAI_MAX_OUTPUT_TOKENS must be an integer"
            ) from exc
        if max_output_tokens <= 0:
            raise ValueError("OPENAI_MAX_OUTPUT_TOKENS must be positive")
        return cls(
            openai_api_key=_required("OPENAI_API_KEY"),
            openai_base_url=_required("OPENAI_BASE_URL"),
            openai_model=_required("OPENAI_MODEL"),
            openai_max_output_tokens=max_output_tokens,
            firebase_service_account_file=_required(
                "FIREBASE_SERVICE_ACCOUNT_FILE"
            ),
            allowed_origins=origins,
        )

    @classmethod
    def for_test(cls) -> "Settings":
        return cls(
            openai_api_key="test-key",
            openai_base_url="https://example.test/v1",
            openai_model="test-model",
            openai_max_output_tokens=500,
            firebase_service_account_file="firebase-service-account.example.json",
            allowed_origins=("http://localhost:5173",),
        )
