"""표준 CSV 검증부터 통계·시각화 저장까지의 분석 workflow."""

from __future__ import annotations

import json
import tempfile
import uuid
from pathlib import Path

import pandas as pd

from seoul_weather.analytics.anomalies import compute_daily_anomalies
from seoul_weather.analytics.statistics import (
    compute_annual_statistics,
    compute_monthly_statistics,
    compute_seasonal_statistics,
    fit_annual_linear_trend,
)
from seoul_weather.analytics.summary import build_analysis_summary, json_safe
from seoul_weather.analytics.validation import validate_daily_data
from seoul_weather.config import AnalysisConfig
from seoul_weather.errors import AnalysisValidationError
from seoul_weather.processing.dataset import load_processed_data
from seoul_weather.visualization.plots import create_visualizations
from seoul_weather.workflows.outputs import promote_files_with_rollback


# 표준 CSV를 검증·분석하고 요약 JSON과 시각화를 생성한다.
def run_analysis(
    input_path: Path,
    output_dir: Path,
    summary_path: Path,
    config: AnalysisConfig,
) -> dict[str, object]:
    frame = load_processed_data(input_path)
    quality = validate_daily_data(frame, config)
    annual = compute_annual_statistics(frame, config)
    trend = fit_annual_linear_trend(annual)
    monthly = compute_monthly_statistics(frame, config)
    seasonal = compute_seasonal_statistics(frame)
    anomalies = compute_daily_anomalies(
        frame, threshold=config.anomaly_z_threshold
    )
    summary = build_analysis_summary(
        quality=quality,
        annual=annual,
        trend=trend,
        monthly=monthly,
        seasonal=seasonal,
        anomalies=anomalies,
        config=config,
    )
    _write_analysis_outputs_atomic(
        annual=annual,
        monthly=monthly,
        anomalies=anomalies,
        output_dir=output_dir,
        summary_path=summary_path,
        summary=summary,
    )
    return summary


# 분석 요약을 JSON으로 변환해 임시 파일을 거쳐 저장한다.
def write_summary_json(path: Path, summary: dict[str, object]) -> None:
    temporary_path = path.with_name(f".{path.name}.part")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path.write_text(
            json.dumps(json_safe(summary), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)
    except OSError as exc:
        raise AnalysisValidationError(
            f"분석 요약 JSON을 저장할 수 없습니다: {path}"
        ) from exc
    finally:
        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass


# 요약과 세 PNG를 staging에서 만든 뒤 한 번에 승격한다.
def _write_analysis_outputs_atomic(
    *,
    annual: pd.DataFrame,
    monthly: pd.DataFrame,
    anomalies: pd.DataFrame,
    output_dir: Path,
    summary_path: Path,
    summary: dict[str, object],
) -> None:
    try:
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        summary_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise AnalysisValidationError(
            "분석 산출물의 상위 디렉터리를 준비할 수 없습니다."
        ) from exc
    if output_dir.exists() and not output_dir.is_dir():
        raise AnalysisValidationError(
            f"시각화 출력 경로가 디렉터리가 아닙니다: {output_dir}"
        )
    if summary_path.exists() and not summary_path.is_file():
        raise AnalysisValidationError(
            f"분석 요약 경로가 파일이 아닙니다: {summary_path}"
        )

    staging_summary = summary_path.with_name(
        f".{summary_path.name}.{uuid.uuid4().hex}.staging"
    )
    try:
        with tempfile.TemporaryDirectory(
            prefix=f".{output_dir.name}-staging-", dir=output_dir.parent
        ) as staging_root_text:
            staging_image_dir = Path(staging_root_text) / "images"
            staging_images = create_visualizations(
                annual, monthly, anomalies, staging_image_dir
            )
            write_summary_json(staging_summary, summary)
            promote_files_with_rollback(
                [
                    *(
                        (staging_image, output_dir / staging_image.name)
                        for staging_image in staging_images
                    ),
                    (staging_summary, summary_path),
                ],
                error_type=AnalysisValidationError,
                error_message=(
                    "분석 산출물을 최종 경로에 저장할 수 없습니다."
                ),
            )
    except AnalysisValidationError:
        raise
    except OSError as exc:
        raise AnalysisValidationError(
            "분석 산출물을 최종 경로에 저장할 수 없습니다."
        ) from exc
    finally:
        try:
            staging_summary.unlink(missing_ok=True)
        except OSError:
            pass
