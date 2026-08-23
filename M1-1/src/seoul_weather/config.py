"""분석 설정과 프로젝트 기본 경로."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AnalysisConfig:
    """서울 기온 분석에 사용하는 고정 기준."""

    station_id: int = 108
    start_date: str = "1994-01-01"
    end_date: str = "2024-12-31"
    monthly_coverage_threshold: float = 0.80
    annual_coverage_threshold: float = 0.95
    anomaly_z_threshold: float = 2.5
    annual_rolling_window: int = 5
    plausible_temperature_min_c: float = -50.0
    plausible_temperature_max_c: float = 50.0


@dataclass(frozen=True)
class ProjectPaths:
    """프로젝트 루트를 기준으로 해석한 기본 입출력 경로."""

    root: Path
    raw_root: Path
    processed_path: Path
    summary_path: Path
    images_dir: Path

    # 프로젝트 루트를 절대 경로로 바꾸고 기본 입출력 경로를 구성한다.
    @classmethod
    def from_root(cls, root: Path) -> "ProjectPaths":
        resolved = root.resolve()
        return cls(
            root=resolved,
            raw_root=resolved / "data" / "raw" / "asos",
            processed_path=(
                resolved / "data" / "processed" / "seoul_weather_daily.csv"
            ),
            summary_path=(
                resolved / "data" / "processed" / "analysis_summary.json"
            ),
            images_dir=resolved / "images",
        )
