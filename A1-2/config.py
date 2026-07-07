from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"
ALLOWED_GEMINI_MODELS = {"gemini-3.1-flash-lite", "gemini-2.5-flash-lite"}


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    kakao_rest_api_key: str
    gemini_model: str


class ConfigError(Exception):
    pass


# 따옴표로 감싼 .env 값을 환경변수 값처럼 정리합니다.
def _clean_env_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


# A1-2/.env 파일이 있으면 현재 프로세스 환경변수에 반영합니다.
def load_env_file(env_path: Path | None = None) -> None:
    path = env_path or BASE_DIR / ".env"
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = _clean_env_value(value)


# 필수 API 키와 Gemini 모델 설정을 읽고 검증합니다.
def load_settings() -> Settings:
    load_env_file()

    gemini_api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    kakao_rest_api_key = os.environ.get("KAKAO_REST_API_KEY", "").strip()
    gemini_model = os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip()

    missing_keys = []
    if not gemini_api_key:
        missing_keys.append("GEMINI_API_KEY")
    if not kakao_rest_api_key:
        missing_keys.append("KAKAO_REST_API_KEY")

    if missing_keys:
        missing_text = ", ".join(missing_keys)
        raise ConfigError(
            f"필수 API 키가 설정되지 않았습니다: {missing_text}\n"
            "A1-2/.env 파일 또는 환경변수에 아래 형식으로 설정해주세요.\n"
            'GEMINI_API_KEY="YOUR_GEMINI_API_KEY"\n'
            'KAKAO_REST_API_KEY="YOUR_KAKAO_REST_API_KEY"'
        )

    if gemini_model not in ALLOWED_GEMINI_MODELS:
        allowed = ", ".join(sorted(ALLOWED_GEMINI_MODELS))
        raise ConfigError(f"GEMINI_MODEL은 다음 중 하나여야 합니다: {allowed}")

    return Settings(
        gemini_api_key=gemini_api_key,
        kakao_rest_api_key=kakao_rest_api_key,
        gemini_model=gemini_model,
    )
