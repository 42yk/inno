from __future__ import annotations

from pathlib import Path

from seoul_weather.config import AnalysisConfig, ProjectPaths


def test_project_paths_are_resolved_from_explicit_root(tmp_path: Path) -> None:
    paths = ProjectPaths.from_root(tmp_path)

    assert paths.root == tmp_path.resolve()
    assert paths.raw_root == tmp_path.resolve() / "data" / "raw" / "asos"
    assert paths.processed_path == (
        tmp_path.resolve() / "data" / "processed" / "seoul_weather_daily.csv"
    )
    assert paths.summary_path == (
        tmp_path.resolve() / "data" / "processed" / "analysis_summary.json"
    )
    assert paths.images_dir == tmp_path.resolve() / "images"


def test_analysis_config_preserves_approved_defaults() -> None:
    config = AnalysisConfig()

    assert config.station_id == 108
    assert config.start_date == "1994-01-01"
    assert config.end_date == "2024-12-31"
    assert config.monthly_coverage_threshold == 0.80
    assert config.annual_coverage_threshold == 0.95
    assert config.anomaly_z_threshold == 2.5
    assert config.annual_rolling_window == 5
    assert config.plausible_temperature_min_c == -50.0
    assert config.plausible_temperature_max_c == 50.0
