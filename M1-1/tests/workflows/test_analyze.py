from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from seoul_weather.config import AnalysisConfig
from seoul_weather.errors import AnalysisValidationError
from seoul_weather.workflows import analyze as analyze_module
from seoul_weather.workflows.analyze import run_analysis


def test_run_analysis_writes_summary_and_all_visualizations(tmp_path: Path) -> None:
    dates = pd.date_range("1994-01-01", "2024-12-31", freq="D")
    year_offsets = (dates.year - 1994) * 0.1
    seasonal_cycle = pd.Series(dates.month, dtype="float64").to_numpy() * 0.2
    average = 8.0 + year_offsets + seasonal_cycle
    frame = pd.DataFrame(
        {
            "station_id": 108,
            "station_name": "서울",
            "date": dates,
            "avg_temp_c": average,
            "min_temp_c": average - 3.0,
            "max_temp_c": average + 3.0,
            "precipitation_mm": 0.0,
            "avg_humidity_pct": 60.0,
        }
    )
    input_path = tmp_path / "seoul_weather_daily.csv"
    frame.to_csv(input_path, index=False, date_format="%Y-%m-%d")
    image_dir = tmp_path / "images"
    summary_path = tmp_path / "analysis_summary.json"

    summary = run_analysis(
        input_path=input_path,
        output_dir=image_dir,
        summary_path=summary_path,
        config=AnalysisConfig(),
    )

    saved = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["data_quality"]["row_count"] == 11323
    assert saved["trend"]["difference_c"] == pytest.approx(2.1)
    assert len(list(image_dir.glob("*.png"))) == 3


def test_run_analysis_keeps_existing_images_when_summary_staging_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dates = pd.date_range("1994-01-01", "2024-12-31", freq="D")
    average = 10.0 + (dates.year - 1994) * 0.1
    frame = pd.DataFrame(
        {
            "station_id": 108,
            "station_name": "서울",
            "date": dates,
            "avg_temp_c": average,
            "min_temp_c": average - 3.0,
            "max_temp_c": average + 3.0,
            "precipitation_mm": 0.0,
            "avg_humidity_pct": 60.0,
        }
    )
    input_path = tmp_path / "input.csv"
    frame.to_csv(input_path, index=False, date_format="%Y-%m-%d")
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    existing_images = [
        image_dir / "01_annual_temperature_trend.png",
        image_dir / "02_monthly_temperature_heatmap.png",
        image_dir / "03_temperature_anomalies.png",
    ]
    for path in existing_images:
        path.write_bytes(b"existing image")
    summary_path = tmp_path / "summary.json"
    summary_path.write_text("existing summary", encoding="utf-8")

    monkeypatch.setattr(
        analyze_module,
        "write_summary_json",
        lambda path, summary: (_ for _ in ()).throw(
            AnalysisValidationError("요약 staging 실패")
        ),
    )

    with pytest.raises(AnalysisValidationError, match="staging 실패"):
        run_analysis(
            input_path=input_path,
            output_dir=image_dir,
            summary_path=summary_path,
            config=AnalysisConfig(),
        )

    assert [path.read_bytes() for path in existing_images] == [
        b"existing image",
        b"existing image",
        b"existing image",
    ]
    assert summary_path.read_text(encoding="utf-8") == "existing summary"


def test_write_summary_json_wraps_directory_target_error(tmp_path: Path) -> None:
    summary_directory = tmp_path / "summary.json"
    summary_directory.mkdir()

    with pytest.raises(AnalysisValidationError, match="요약 JSON.*저장"):
        analyze_module.write_summary_json(summary_directory, {"value": 1})


def test_analysis_output_promotion_restores_all_existing_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    image_names = [
        "01_annual_temperature_trend.png",
        "02_monthly_temperature_heatmap.png",
        "03_temperature_anomalies.png",
    ]
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    existing_images = [image_dir / name for name in image_names]
    for index, path in enumerate(existing_images, start=1):
        path.write_bytes(f"old image {index}".encode())
    summary_path = tmp_path / "summary.json"
    summary_path.write_text("old summary", encoding="utf-8")

    def create_staged_images(
        annual: pd.DataFrame,
        monthly: pd.DataFrame,
        anomalies: pd.DataFrame,
        output_dir: Path,
    ) -> list[Path]:
        del annual, monthly, anomalies
        output_dir.mkdir(parents=True)
        paths = [output_dir / name for name in image_names]
        for index, path in enumerate(paths, start=1):
            path.write_bytes(f"new image {index}".encode())
        return paths

    def create_staged_summary(path: Path, summary: dict[str, object]) -> None:
        del summary
        path.write_text("new summary", encoding="utf-8")

    monkeypatch.setattr(analyze_module, "create_visualizations", create_staged_images)
    monkeypatch.setattr(analyze_module, "write_summary_json", create_staged_summary)
    original_replace = Path.replace

    def fail_second_image_promotion(self: Path, target: Path) -> Path:
        if (
            Path(target) == existing_images[1]
            and self.name == existing_images[1].name
        ):
            raise OSError("second image promotion failed")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_second_image_promotion)

    with pytest.raises(AnalysisValidationError, match="최종 경로"):
        analyze_module._write_analysis_outputs_atomic(
            annual=pd.DataFrame(),
            monthly=pd.DataFrame(),
            anomalies=pd.DataFrame(),
            output_dir=image_dir,
            summary_path=summary_path,
            summary={"value": 1},
        )

    assert [path.read_bytes() for path in existing_images] == [
        b"old image 1",
        b"old image 2",
        b"old image 3",
    ]
    assert summary_path.read_text(encoding="utf-8") == "old summary"
