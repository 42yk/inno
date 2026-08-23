from __future__ import annotations

from pathlib import Path

import pytest

from seoul_weather.errors import AnalysisValidationError
from seoul_weather.workflows.outputs import promote_files_with_rollback


def test_promote_files_restores_every_destination_when_later_promotion_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    first_source = tmp_path / "first.staging"
    second_source = tmp_path / "second.staging"
    first_destination = tmp_path / "first.txt"
    second_destination = tmp_path / "second.txt"
    first_source.write_text("new first", encoding="utf-8")
    second_source.write_text("new second", encoding="utf-8")
    first_destination.write_text("old first", encoding="utf-8")
    second_destination.write_text("old second", encoding="utf-8")

    original_replace = Path.replace

    def fail_second_promotion(self: Path, target: Path) -> Path:
        if self == second_source and Path(target) == second_destination:
            raise OSError("second promotion failed")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_second_promotion)

    with pytest.raises(AnalysisValidationError, match="최종 경로"):
        promote_files_with_rollback(
            [
                (first_source, first_destination),
                (second_source, second_destination),
            ],
            error_type=AnalysisValidationError,
            error_message="산출물을 최종 경로로 옮길 수 없습니다.",
        )

    assert first_destination.read_text(encoding="utf-8") == "old first"
    assert second_destination.read_text(encoding="utf-8") == "old second"
    assert not list(tmp_path.glob("*.backup"))
