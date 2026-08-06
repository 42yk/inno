import json
from pathlib import Path

import pytest

from review_analytics.config import load_config
from review_analytics.errors import ConfigurationError


def test_load_config_applies_documented_defaults_and_resolves_relative_paths(tmp_path: Path):
    """Removing optional configuration keys must preserve documented behavior."""
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps({"database_path": "state/reviews.db"}), encoding="utf-8")

    config = load_config(config_path)

    assert config.database_path == tmp_path / "state/reviews.db"
    assert config.gemini_model == "gemini-3.1-flash-lite"
    assert config.minimum_review_length == 5
    assert config.analysis_batch_size == 20
    assert config.chart_font_candidates == ("AppleGothic", "Malgun Gothic", "NanumGothic")


def test_load_config_rejects_missing_file_with_safe_configuration_error(tmp_path: Path):
    """A missing configuration file must fail before a command uses its paths."""
    with pytest.raises(ConfigurationError, match="CONFIG_FILE_NOT_FOUND"):
        load_config(tmp_path / "missing.json")


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({"database_path": 4}, "INVALID_CONFIG_TYPE"),
        ({"database_path": "reviews.db", "analysis_batch_size": 0}, "INVALID_CONFIG_VALUE"),
        ({"database_path": "reviews.db", "duplicate_policy": "replace"}, "INVALID_CONFIG_VALUE"),
    ],
)
def test_load_config_rejects_invalid_value_types_and_ranges(tmp_path: Path, payload: dict[str, object], code: str):
    """Removing type/range validation would let invalid runtime configuration through."""
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ConfigurationError, match=code):
        load_config(config_path)
