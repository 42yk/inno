from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.api_core.exceptions import GoogleAPIError

from app.bootstrap import build_services
from app.config import Settings
from app.errors import (
    AIProviderError,
    DataStoreError,
    DuplicateDateError,
    InvalidPeriodError,
    RecordNotFoundError,
    ToolCallLimitError,
)
from app.routers.chat import router as chat_router
from app.routers.conversations import router as conversations_router
from app.routers.data import router as data_router
from app.services.conversation_service import ConversationService
from app.services.chat_service import ChatService
from app.services.data_service import DataService
from app.services.summary_service import SummaryService
from app.logging_config import configure_logging
from app.middleware import RequestContextMiddleware


def _error(
    status_code: int,
    code: str,
    message: str,
    details: Any = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            {
                "error": {
                    "code": code,
                    "message": message,
                    "details": details,
                }
            }
        ),
    )


def _safe_validation_errors(
    exc: RequestValidationError,
) -> list[dict[str, Any]]:
    return [
        {
            "type": error["type"],
            "loc": error["loc"],
            "msg": error["msg"],
        }
        for error in exc.errors()
    ]


def create_app(
    settings: Settings | None = None,
    *,
    data_service: DataService | None = None,
    summary_service: SummaryService | None = None,
    conversation_service: ConversationService | None = None,
    chat_service: ChatService | None = None,
) -> FastAPI:
    production_mode = settings is None
    active_settings = settings or Settings.from_env()
    if production_mode:
        services = build_services(active_settings)
        data_service = services.data
        summary_service = services.summary
        conversation_service = services.conversations
        chat_service = services.chat
    configure_logging()
    app = FastAPI(
        title="Weight AI API",
        version="0.1.0",
        description="개인 체중 변화 기록 분석 AI 백엔드",
    )
    app.state.settings = active_settings
    if data_service is not None:
        app.state.data_service = data_service
        app.state.summary_service = summary_service or SummaryService(data_service)
    elif summary_service is not None:
        raise ValueError("summary_service requires data_service")
    if conversation_service is not None:
        app.state.conversation_service = conversation_service
    if chat_service is not None:
        app.state.chat_service = chat_service
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _error(
            422,
            "validation_error",
            "입력 값을 확인해 주세요.",
            _safe_validation_errors(exc),
        )

    @app.exception_handler(InvalidPeriodError)
    async def invalid_period_handler(
        _request: Request,
        _exc: InvalidPeriodError,
    ) -> JSONResponse:
        return _error(400, "invalid_period", "조회 기간이 올바르지 않습니다.")

    @app.exception_handler(DuplicateDateError)
    async def duplicate_date_handler(
        _request: Request,
        _exc: DuplicateDateError,
    ) -> JSONResponse:
        return _error(409, "duplicate_date", "해당 날짜의 기록이 이미 존재합니다.")

    @app.exception_handler(RecordNotFoundError)
    async def record_not_found_handler(
        _request: Request,
        _exc: RecordNotFoundError,
    ) -> JSONResponse:
        return _error(404, "record_not_found", "요청한 기록을 찾을 수 없습니다.")

    @app.exception_handler(AIProviderError)
    @app.exception_handler(ToolCallLimitError)
    async def ai_provider_error_handler(
        _request: Request,
        _exc: AIProviderError | ToolCallLimitError,
    ) -> JSONResponse:
        return _error(
            502,
            "ai_provider_error",
            "AI 답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        )

    @app.exception_handler(DataStoreError)
    @app.exception_handler(GoogleAPIError)
    async def data_store_error_handler(
        _request: Request,
        _exc: DataStoreError | GoogleAPIError,
    ) -> JSONResponse:
        return _error(
            503,
            "data_store_error",
            "데이터를 처리하지 못했습니다. 잠시 후 다시 시도해 주세요.",
        )

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    if data_service is not None:
        app.include_router(data_router)
    if conversation_service is not None:
        app.include_router(conversations_router)
    if chat_service is not None:
        app.include_router(chat_router)

    return app
