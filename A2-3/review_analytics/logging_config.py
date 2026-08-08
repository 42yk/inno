"""시간대가 포함된 한 줄 로그를 중복 없이 구성한다."""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import TextIO

from review_analytics.config import AppConfig
from review_analytics.errors import ConfigurationError


_LOGGER_NAME = "review_analytics"
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 3
_OWNED_HANDLER = "_review_analytics_owned_handler"


class _IsoTimezoneFormatter(logging.Formatter):
    # 로그 시각을 현재 시간대가 포함된 ISO 문자열로 표현한다.
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        return datetime.fromtimestamp(record.created).astimezone().isoformat(timespec="seconds")


# 중복 없이 콘솔과 로그 파일 순환 핸들러를 구성한다.
def configure_logging(config: AppConfig, stream: TextIO | None = None) -> logging.Logger:
    """Configure one console and one rotating file handler without duplicates."""
    logger = logging.getLogger(_LOGGER_NAME)
    for handler in tuple(logger.handlers):
        if getattr(handler, _OWNED_HANDLER, False):
            logger.removeHandler(handler)
            handler.close()

    level = getattr(logging, config.log_level)
    formatter = _IsoTimezoneFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    console = logging.StreamHandler(stream or sys.stderr)
    try:
        file_handler = _file_handler(config)
    except OSError as exc:
        raise ConfigurationError("로그 파일을 설정할 수 없습니다.", "LOG_SETUP_FAILED") from exc
    for handler in (console, file_handler):
        setattr(handler, _OWNED_HANDLER, True)
        handler.setLevel(level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


# 설정된 경로에 용량 기반 로그 파일 순환 핸들러를 만든다.
def _file_handler(config: AppConfig) -> RotatingFileHandler:
    config.log_file.parent.mkdir(parents=True, exist_ok=True)
    return RotatingFileHandler(
        config.log_file,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
