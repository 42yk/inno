"""비밀정보가 없는 불변 애플리케이션 설정을 읽는다."""

import json
from dataclasses import dataclass
from pathlib import Path

from review_analytics.errors import ConfigurationError
from review_analytics.models import DuplicatePolicy


DEFAULT_GEMINI_MODEL = "gemini-3.1-flash-lite"
DEFAULT_FONT_CANDIDATES = ("AppleGothic", "Malgun Gothic", "NanumGothic")
_DEFAULTS: dict[str, object] = {
    "database_path": "data/reviews.db",
    "gemini_model": DEFAULT_GEMINI_MODEL,
    "duplicate_policy": DuplicatePolicy.SKIP.value,
    "minimum_review_length": 5,
    "analysis_batch_size": 20,
    "extraction_chunk_characters": 50000,
    "ai_retry_count": 2,
    "default_page_size": 20,
    "maximum_page_size": 100,
    "chart_font_candidates": list(DEFAULT_FONT_CANDIDATES),
    "log_level": "INFO",
    "log_file": "logs/app.log",
    "output_directory": "output",
}
_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass(frozen=True)
class AppConfig:
    database_path: Path
    gemini_model: str = DEFAULT_GEMINI_MODEL
    duplicate_policy: DuplicatePolicy = DuplicatePolicy.SKIP
    minimum_review_length: int = 5
    analysis_batch_size: int = 20
    extraction_chunk_characters: int = 50000
    ai_retry_count: int = 2
    default_page_size: int = 20
    maximum_page_size: int = 100
    chart_font_candidates: tuple[str, ...] = DEFAULT_FONT_CANDIDATES
    log_level: str = "INFO"
    log_file: Path = Path("logs/app.log")
    output_directory: Path = Path("output")


# JSON 설정을 읽고 검증하여 불변 애플리케이션 설정으로 변환한다.
def load_config(path: Path) -> AppConfig:
    """Load and validate the documented JSON configuration object at *path*."""
    config_path = Path(path)
    try:
        raw_text = config_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigurationError("configuration file was not found", "CONFIG_FILE_NOT_FOUND") from exc
    except OSError as exc:
        raise ConfigurationError("configuration file could not be read", "CONFIG_FILE_READ_ERROR") from exc

    try:
        values = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ConfigurationError("configuration is not valid JSON", "INVALID_CONFIG_JSON") from exc
    if not isinstance(values, dict):
        raise ConfigurationError("configuration must be a JSON object", "INVALID_CONFIG_JSON")

    unknown = set(values) - set(_DEFAULTS)
    if unknown:
        raise ConfigurationError("configuration contains an unknown key", "UNKNOWN_CONFIG_KEY")
    merged = {**_DEFAULTS, **values}
    _validate_config_values(merged)

    base_dir = config_path.parent
    return AppConfig(
        database_path=_resolve_path(base_dir, merged["database_path"]),
        gemini_model=merged["gemini_model"],
        duplicate_policy=DuplicatePolicy(merged["duplicate_policy"]),
        minimum_review_length=merged["minimum_review_length"],
        analysis_batch_size=merged["analysis_batch_size"],
        extraction_chunk_characters=merged["extraction_chunk_characters"],
        ai_retry_count=merged["ai_retry_count"],
        default_page_size=merged["default_page_size"],
        maximum_page_size=merged["maximum_page_size"],
        chart_font_candidates=tuple(merged["chart_font_candidates"]),
        log_level=merged["log_level"],
        log_file=_resolve_path(base_dir, merged["log_file"]),
        output_directory=_resolve_path(base_dir, merged["output_directory"]),
    )


# 병합된 설정값 전체가 타입과 범위 계약을 만족하는지 확인한다.
def _validate_config_values(values: dict[str, object]) -> None:
    _require_non_empty_string(values, "database_path")
    _require_non_empty_string(values, "gemini_model")
    _require_non_empty_string(values, "log_file")
    _require_non_empty_string(values, "output_directory")

    duplicate_policy = values["duplicate_policy"]
    if not isinstance(duplicate_policy, str):
        _invalid_type("duplicate_policy")
    if duplicate_policy not in {policy.value for policy in DuplicatePolicy}:
        _invalid_value("duplicate_policy")

    for key in (
        "minimum_review_length",
        "analysis_batch_size",
        "extraction_chunk_characters",
        "default_page_size",
        "maximum_page_size",
    ):
        _require_integer(values, key, minimum=1)
    _require_integer(values, "ai_retry_count", minimum=0)
    if values["default_page_size"] > values["maximum_page_size"]:
        _invalid_value("default_page_size")

    fonts = values["chart_font_candidates"]
    if not isinstance(fonts, list):
        _invalid_type("chart_font_candidates")
    if not fonts or any(not isinstance(font, str) for font in fonts):
        _invalid_type("chart_font_candidates")
    if any(not font.strip() for font in fonts):
        _invalid_value("chart_font_candidates")

    log_level = values["log_level"]
    if not isinstance(log_level, str):
        _invalid_type("log_level")
    if log_level not in _LOG_LEVELS:
        _invalid_value("log_level")


# 지정한 설정값이 비어 있지 않은 문자열인지 검사한다.
def _require_non_empty_string(values: dict[str, object], key: str) -> None:
    value = values[key]
    if not isinstance(value, str):
        _invalid_type(key)
    if not value.strip():
        _invalid_value(key)


# 지정한 설정값이 최솟값 이상의 정수인지 검사한다.
def _require_integer(values: dict[str, object], key: str, minimum: int) -> None:
    value = values[key]
    if isinstance(value, bool) or not isinstance(value, int):
        _invalid_type(key)
    if value < minimum:
        _invalid_value(key)


# 설정 파일 기준의 상대 경로를 실제 경로로 해석한다.
def _resolve_path(base_dir: Path, raw_path: object) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else base_dir / path


# 설정 타입 오류를 안정적인 프로젝트 오류로 발생시킨다.
def _invalid_type(key: str) -> None:
    raise ConfigurationError(f"invalid type for {key}", "INVALID_CONFIG_TYPE")


# 설정 값 범위 오류를 안정적인 프로젝트 오류로 발생시킨다.
def _invalid_value(key: str) -> None:
    raise ConfigurationError(f"invalid value for {key}", "INVALID_CONFIG_VALUE")
