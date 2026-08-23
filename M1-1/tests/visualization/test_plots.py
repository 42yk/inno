from __future__ import annotations

import os
import subprocess
import sys
import warnings
from pathlib import Path

import pandas as pd
import pytest
from PIL import Image

from seoul_weather.errors import AnalysisValidationError
from seoul_weather.visualization.plots import create_visualizations


def test_create_visualizations_writes_three_valid_pngs(tmp_path: Path) -> None:
    annual = pd.DataFrame(
        {
            "year": list(range(1994, 2001)),
            "avg_temp_c": [12.0, 12.1, 11.9, 12.3, 12.4, 12.2, 12.6],
        }
    )
    annual["rolling_5y_avg_c"] = annual["avg_temp_c"].rolling(5).mean()
    monthly = pd.DataFrame(
        [
            {
                "year": year,
                "month": month,
                "monthly_anomaly_c": (year - 1994) * 0.1 + (month - 6) * 0.02,
            }
            for year in range(1994, 2001)
            for month in range(1, 13)
        ]
    )
    anomaly_dates = pd.date_range("1994-01-01", periods=40, freq="D")
    anomaly_z = pd.Series([0.0] * 40)
    anomaly_z.iloc[5] = 3.0
    anomaly_z.iloc[25] = -3.1
    anomalies = pd.DataFrame(
        {
            "date": anomaly_dates,
            "avg_temp_c": range(40),
            "monthly_anomaly_z": anomaly_z,
            "anomaly_category": [
                "hot" if value >= 2.5 else "cold" if value <= -2.5 else "normal"
                for value in anomaly_z
            ],
        }
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        paths = create_visualizations(annual, monthly, anomalies, tmp_path)

    assert caught == []
    assert [path.name for path in paths] == [
        "01_annual_temperature_trend.png",
        "02_monthly_temperature_heatmap.png",
        "03_temperature_anomalies.png",
    ]
    for path in paths:
        assert path.stat().st_size > 1_000
        with Image.open(path) as image:
            assert image.format == "PNG"
            image.verify()


def test_import_visualization_style_uses_writable_fallback_font_cache() -> None:
    environment = os.environ.copy()
    environment.pop("MPLCONFIGDIR", None)
    environment.pop("XDG_CACHE_HOME", None)
    environment["HOME"] = "/path-that-is-not-writable"
    project_root = Path(__file__).parents[2]
    environment["PYTHONPATH"] = str(project_root / "src")

    result = subprocess.run(
        [sys.executable, "-c", "import seoul_weather.visualization.style"],
        cwd=project_root,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "temporary cache directory" not in result.stderr
    assert "Fontconfig error" not in result.stderr


def test_create_visualizations_wraps_output_directory_file_error(
    tmp_path: Path,
) -> None:
    output_file = tmp_path / "images"
    output_file.write_text("not a directory", encoding="utf-8")

    with pytest.raises(AnalysisValidationError, match="시각화 출력"):
        create_visualizations(
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), output_file
        )
