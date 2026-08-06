from __future__ import annotations

import io
import logging
import re
from dataclasses import replace
from logging.handlers import RotatingFileHandler

import pytest

from review_analytics.config import AppConfig
from review_analytics.errors import ConfigurationError


@pytest.fixture(autouse=True)
def restore_application_logger():
    yield
    logger = logging.getLogger("review_analytics")
    for handler in tuple(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    logger.setLevel(logging.NOTSET)
    logger.propagate = True


def _config(tmp_path, *, level="INFO") -> AppConfig:
    return AppConfig(
        database_path=tmp_path / "reviews.db",
        log_level=level,
        log_file=tmp_path / "logs" / "app.log",
        output_directory=tmp_path / "output",
    )


def _flush(logger: logging.Logger) -> None:
    for handler in logger.handlers:
        handler.flush()


def test_configure_logging_is_idempotent_with_one_console_and_rotating_file_handler(tmp_path):
    from review_analytics.logging_config import configure_logging

    stream = io.StringIO()
    logger = configure_logging(_config(tmp_path), stream=stream)
    logger = configure_logging(_config(tmp_path), stream=stream)

    console_handlers = [handler for handler in logger.handlers if type(handler) is logging.StreamHandler]
    file_handlers = [handler for handler in logger.handlers if isinstance(handler, RotatingFileHandler)]
    assert len(console_handlers) == 1
    assert len(file_handlers) == 1
    assert file_handlers[0].maxBytes == 5 * 1024 * 1024
    assert file_handlers[0].backupCount == 3
    assert file_handlers[0].encoding.lower().replace("-", "") == "utf8"
    assert logger.propagate is False


def test_logging_respects_level_and_uses_timezone_aware_iso_timestamp(tmp_path):
    from review_analytics.logging_config import configure_logging

    stream = io.StringIO()
    logger = configure_logging(_config(tmp_path, level="WARNING"), stream=stream)
    child = logging.getLogger("review_analytics.services.example")

    child.info("event=hidden")
    child.warning("event=visible review_id=7")
    _flush(logger)

    output = stream.getvalue()
    assert "event=hidden" not in output
    assert "WARNING review_analytics.services.example event=visible review_id=7" in output
    assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}", output)


def test_logging_setup_translates_filesystem_failure_without_exposing_path_contents(tmp_path):
    from review_analytics.logging_config import configure_logging

    blocker = tmp_path / "not-a-directory"
    blocker.write_text("PRIVATE", encoding="utf-8")
    config = replace(_config(tmp_path), log_file=blocker / "app.log")

    with pytest.raises(ConfigurationError) as raised:
        configure_logging(config)

    assert raised.value.code == "LOG_SETUP_FAILED"
    assert "PRIVATE" not in str(raised.value)
