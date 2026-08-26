from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings
from app.errors import DuplicateDateError, InvalidPeriodError, RecordNotFoundError
from app.routers.data import router as data_router
from app.services.data_service import DataService
from app.services.summary_service import SummaryService


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


def create_app(
    settings: Settings | None = None,
    *,
    data_service: DataService | None = None,
    summary_service: SummaryService | None = None,
) -> FastAPI:
    active_settings = settings or Settings.from_env()
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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(active_settings.allowed_origins),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _error(
            422,
            "validation_error",
            "입력 값을 확인해 주세요.",
            exc.errors(),
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

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    if data_service is not None:
        app.include_router(data_router)

    return app
