"""수집과 분석을 순차 실행하는 통합 workflow."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from seoul_weather.config import AnalysisConfig
from seoul_weather.errors import (
    AnalysisValidationError,
    DataDownloadError,
    DataValidationError,
)
from seoul_weather.visualization.plots import VISUALIZATION_FILENAMES
from seoul_weather.workflows.analyze import run_analysis
from seoul_weather.workflows.download import run_download
from seoul_weather.workflows.outputs import promote_files_with_rollback


# 데이터 준비와 분석을 staging에서 실행하고 모든 산출물을 함께 승격한다.
def run_pipeline(
    *,
    raw_root: Path,
    processed_path: Path,
    output_dir: Path,
    summary_path: Path,
    analysis_config: AnalysisConfig,
    start_year: int,
    end_year: int,
    station_id: int,
    rebuild_from_raw: bool = False,
    session: Any | None = None,
) -> dict[str, object]:
    staging_token = uuid.uuid4().hex
    try:
        staging_processed_path = processed_path.with_name(
            f".{processed_path.name}.{staging_token}.staging"
        )
        staging_output_dir = output_dir.with_name(
            f".{output_dir.name}.{staging_token}.staging"
        )
        staging_summary_path = summary_path.with_name(
            f".{summary_path.name}.{staging_token}.staging"
        )
    except ValueError as exc:
        raise DataValidationError(
            "run 출력 경로에는 파일 또는 디렉터리 이름이 있어야 합니다."
        ) from exc
    try:
        try:
            processed_path.parent.mkdir(parents=True, exist_ok=True)
            if processed_path.exists() and not processed_path.is_file():
                raise DataValidationError(
                    f"가공 데이터 출력 경로가 파일이 아닙니다: {processed_path}"
                )
            download_result = run_download(
                raw_root=raw_root,
                processed_path=staging_processed_path,
                start_year=start_year,
                end_year=end_year,
                station_id=station_id,
                rebuild_from_raw=rebuild_from_raw,
                session=session,
            )
        except (
            DataDownloadError,
            DataValidationError,
            AnalysisValidationError,
        ) as exc:
            raise type(exc)(f"download 단계 실패: {exc}") from exc
        except OSError as exc:
            raise DataValidationError(
                "download 단계 실패: 가공 데이터 경로를 준비할 수 없습니다: "
                f"{exc}"
            ) from exc

        try:
            analysis_summary = run_analysis(
                input_path=staging_processed_path,
                output_dir=staging_output_dir,
                summary_path=staging_summary_path,
                config=analysis_config,
            )
        except (
            DataDownloadError,
            DataValidationError,
            AnalysisValidationError,
        ) as exc:
            raise type(exc)(f"analyze 단계 실패: {exc}") from exc

        promote_files_with_rollback(
            [
                *(
                    (staging_output_dir / filename, output_dir / filename)
                    for filename in VISUALIZATION_FILENAMES
                ),
                (staging_summary_path, summary_path),
                (staging_processed_path, processed_path),
            ],
            error_type=DataValidationError,
            error_message="run 산출물을 최종 경로로 옮길 수 없습니다.",
        )

        download_result = {**download_result, "processed_path": processed_path}
        return {"download": download_result, "analysis": analysis_summary}
    finally:
        _remove_staging_file(staging_processed_path)
        _remove_staging_file(staging_summary_path)
        try:
            shutil.rmtree(staging_output_dir)
        except FileNotFoundError:
            pass
        except OSError:
            pass


# 남은 staging 파일을 오류 없이 정리한다.
def _remove_staging_file(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
