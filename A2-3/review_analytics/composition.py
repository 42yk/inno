"""명령줄 파싱과 출력에서 분리된 인프라 의존성 조립을 담당한다."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass

from dotenv import load_dotenv

from review_analytics.config import AppConfig
from review_analytics.errors import ConfigurationError


@dataclass(frozen=True)
class AppDependencies:
    config: AppConfig
    review_repository: object
    analysis_repository: object
    client_factory: Callable[[], object] | None = None


# 설정에 맞는 데이터베이스와 Repository 의존성을 조립한다.
def build_default_dependencies(config: AppConfig) -> AppDependencies:
    """Initialize persistent infrastructure only after command help has been parsed."""
    from review_analytics.repositories import AnalysisRepository, ReviewRepository, initialize_database

    try:
        config.database_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ConfigurationError(
            "데이터베이스 디렉터리를 만들 수 없습니다.",
            "DATABASE_DIRECTORY_FAILED",
        ) from exc
    initialize_database(config.database_path)
    return AppDependencies(
        config=config,
        review_repository=ReviewRepository(config.database_path),
        analysis_repository=AnalysisRepository(config.database_path),
    )


# 환경 변수의 API 키로 실제 Gemini Client를 지연 생성한다.
def create_live_client(config: AppConfig) -> object:
    """Load the secret and construct the official client at the first actual AI call."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key is None or not api_key.strip():
        raise ConfigurationError(
            "GEMINI_API_KEY가 필요합니다. .env 파일을 확인하세요.",
            "GEMINI_API_KEY_REQUIRED",
        )
    from review_analytics.clients.gemini import GeminiClient

    return GeminiClient.from_api_key(api_key, config.gemini_model)
