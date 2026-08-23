from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from seoul_weather.config import AnalysisConfig
from seoul_weather.errors import (
    AnalysisValidationError,
    DataDownloadError,
    DataValidationError,
)
from seoul_weather.workflows import run as run_module


IMAGE_NAMES = [
    "01_annual_temperature_trend.png",
    "02_monthly_temperature_heatmap.png",
    "03_temperature_anomalies.png",
]


def test_run_pipeline_stops_before_analysis_when_download_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        run_module,
        "run_download",
        Mock(side_effect=DataDownloadError("1999년 수집 실패")),
    )
    analyze = Mock()
    monkeypatch.setattr(run_module, "run_analysis", analyze)

    with pytest.raises(DataDownloadError, match="download 단계 실패.*1999년"):
        run_module.run_pipeline(
            raw_root=tmp_path / "raw",
            processed_path=tmp_path / "processed.csv",
            output_dir=tmp_path / "images",
            summary_path=tmp_path / "summary.json",
            analysis_config=AnalysisConfig(),
            start_year=1994,
            end_year=2024,
            station_id=108,
        )

    analyze.assert_not_called()


def test_run_pipeline_calls_analysis_with_downloaded_processed_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    processed_path = tmp_path / "processed.csv"
    download_result: dict[str, object] = {
        "mode": "rebuild",
        "year_count": 31,
        "row_count": 11323,
        "processed_path": processed_path,
    }

    def create_staged_download(**kwargs: object) -> dict[str, object]:
        target = kwargs["processed_path"]
        assert isinstance(target, Path)
        target.write_text("processed", encoding="utf-8")
        return {**download_result, "processed_path": target}

    monkeypatch.setattr(run_module, "run_download", create_staged_download)
    summary = {"data_quality": {"row_count": 11323}}

    def create_staged_analysis(**kwargs: object) -> dict[str, object]:
        target_dir = kwargs["output_dir"]
        target_summary = kwargs["summary_path"]
        assert isinstance(target_dir, Path)
        assert isinstance(target_summary, Path)
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in IMAGE_NAMES:
            (target_dir / name).write_bytes(b"image")
        target_summary.parent.mkdir(parents=True, exist_ok=True)
        target_summary.write_text("summary", encoding="utf-8")
        return summary

    analyze = Mock(side_effect=create_staged_analysis)
    monkeypatch.setattr(run_module, "run_analysis", analyze)
    config = AnalysisConfig()

    result = run_module.run_pipeline(
        raw_root=tmp_path / "raw",
        processed_path=processed_path,
        output_dir=tmp_path / "images",
        summary_path=tmp_path / "summary.json",
        analysis_config=config,
        start_year=1994,
        end_year=2024,
        station_id=108,
        rebuild_from_raw=True,
    )

    staged_path = analyze.call_args.kwargs["input_path"]
    staged_output_dir = analyze.call_args.kwargs["output_dir"]
    staged_summary_path = analyze.call_args.kwargs["summary_path"]
    assert staged_path != processed_path
    assert staged_output_dir != tmp_path / "images"
    assert staged_summary_path != tmp_path / "summary.json"
    analyze.assert_called_once_with(
        input_path=staged_path,
        output_dir=staged_output_dir,
        summary_path=staged_summary_path,
        config=config,
    )
    assert processed_path.read_text(encoding="utf-8") == "processed"
    assert len(list((tmp_path / "images").glob("*.png"))) == 3
    assert (tmp_path / "summary.json").read_text(encoding="utf-8") == "summary"
    assert result == {"download": download_result, "analysis": summary}


def test_run_pipeline_marks_analysis_stage_in_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        run_module,
        "run_download",
        Mock(
            return_value={
                "mode": "rebuild",
                "year_count": 31,
                "row_count": 11323,
                "processed_path": tmp_path / "processed.csv",
            }
        ),
    )
    monkeypatch.setattr(
        run_module,
        "run_analysis",
        Mock(side_effect=AnalysisValidationError("날짜 누락")),
    )

    with pytest.raises(
        AnalysisValidationError, match="analyze 단계 실패.*날짜 누락"
    ):
        run_module.run_pipeline(
            raw_root=tmp_path / "raw",
            processed_path=tmp_path / "processed.csv",
            output_dir=tmp_path / "images",
            summary_path=tmp_path / "summary.json",
            analysis_config=AnalysisConfig(),
            start_year=1994,
            end_year=2024,
            station_id=108,
        )


def test_run_pipeline_keeps_existing_processed_file_when_analysis_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    processed_path = tmp_path / "processed.csv"
    processed_path.write_text("existing processed", encoding="utf-8")

    def write_downloaded_data(**kwargs: object) -> dict[str, object]:
        target = kwargs["processed_path"]
        assert isinstance(target, Path)
        target.write_text("new processed", encoding="utf-8")
        return {
            "mode": "rebuild",
            "year_count": 31,
            "row_count": 11323,
            "processed_path": target,
        }

    monkeypatch.setattr(run_module, "run_download", write_downloaded_data)
    monkeypatch.setattr(
        run_module,
        "run_analysis",
        Mock(side_effect=AnalysisValidationError("요약 저장 실패")),
    )

    with pytest.raises(AnalysisValidationError, match="analyze 단계 실패"):
        run_module.run_pipeline(
            raw_root=tmp_path / "raw",
            processed_path=processed_path,
            output_dir=tmp_path / "images",
            summary_path=tmp_path / "summary.json",
            analysis_config=AnalysisConfig(),
            start_year=1994,
            end_year=2024,
            station_id=108,
        )

    assert processed_path.read_text(encoding="utf-8") == "existing processed"


def test_run_pipeline_restores_every_output_when_processed_promotion_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    processed_path = tmp_path / "processed.csv"
    processed_path.write_text("old processed", encoding="utf-8")
    output_dir = tmp_path / "images"
    output_dir.mkdir()
    image_paths = [output_dir / name for name in IMAGE_NAMES]
    for index, path in enumerate(image_paths, start=1):
        path.write_bytes(f"old image {index}".encode())
    summary_path = tmp_path / "summary.json"
    summary_path.write_text("old summary", encoding="utf-8")

    def create_staged_download(**kwargs: object) -> dict[str, object]:
        target = kwargs["processed_path"]
        assert isinstance(target, Path)
        target.write_text("new processed", encoding="utf-8")
        return {
            "mode": "rebuild",
            "year_count": 31,
            "row_count": 11323,
            "processed_path": target,
        }

    def create_analysis_outputs(**kwargs: object) -> dict[str, object]:
        target_dir = kwargs["output_dir"]
        target_summary = kwargs["summary_path"]
        assert isinstance(target_dir, Path)
        assert isinstance(target_summary, Path)
        target_dir.mkdir(parents=True, exist_ok=True)
        for index, name in enumerate(IMAGE_NAMES, start=1):
            (target_dir / name).write_bytes(f"new image {index}".encode())
        target_summary.parent.mkdir(parents=True, exist_ok=True)
        target_summary.write_text("new summary", encoding="utf-8")
        return {"data_quality": {"row_count": 11323}}

    monkeypatch.setattr(run_module, "run_download", create_staged_download)
    monkeypatch.setattr(run_module, "run_analysis", create_analysis_outputs)
    original_replace = Path.replace

    def fail_processed_promotion(self: Path, target: Path) -> Path:
        if (
            Path(target) == processed_path
            and self.name.startswith(f".{processed_path.name}.")
            and self.name.endswith(".staging")
        ):
            raise OSError("processed promotion failed")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_processed_promotion)

    with pytest.raises(DataValidationError, match="최종 경로"):
        run_module.run_pipeline(
            raw_root=tmp_path / "raw",
            processed_path=processed_path,
            output_dir=output_dir,
            summary_path=summary_path,
            analysis_config=AnalysisConfig(),
            start_year=1994,
            end_year=2024,
            station_id=108,
        )

    assert processed_path.read_text(encoding="utf-8") == "old processed"
    assert [path.read_bytes() for path in image_paths] == [
        b"old image 1",
        b"old image 2",
        b"old image 3",
    ]
    assert summary_path.read_text(encoding="utf-8") == "old summary"
