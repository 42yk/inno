"""패키지·콘솔 실행을 공유하는 명령행 인터페이스."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from seoul_weather import __version__
from seoul_weather.config import AnalysisConfig, ProjectPaths
from seoul_weather.errors import (
    AnalysisValidationError,
    DataDownloadError,
    DataValidationError,
)
from seoul_weather.workflows.analyze import run_analysis
from seoul_weather.workflows.download import run_download
from seoul_weather.workflows.run import run_pipeline


# download·analyze·run 하위 명령과 공통 옵션을 정의한다.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="seoul-weather",
        description="서울 ASOS 일자료를 수집하고 장기 기온을 분석합니다.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="데이터·이미지 기본 경로의 기준 디렉터리(기본: 현재 디렉터리)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    download_parser = subparsers.add_parser(
        "download", help="원자료를 수집하거나 보존 원자료를 다시 통합합니다."
    )
    _add_collection_arguments(download_parser)
    download_parser.add_argument(
        "--output", type=Path, help="생성할 표준 CSV 경로"
    )

    analyze_parser = subparsers.add_parser(
        "analyze", help="표준 CSV를 분석하고 요약과 PNG를 생성합니다."
    )
    analyze_parser.add_argument("--input", type=Path, help="분석할 표준 CSV 경로")
    analyze_parser.add_argument(
        "--output-dir", type=Path, help="PNG를 저장할 디렉터리"
    )
    analyze_parser.add_argument("--summary", type=Path, help="요약 JSON 경로")

    run_parser = subparsers.add_parser(
        "run", help="수집 또는 재통합 후 분석까지 순서대로 실행합니다."
    )
    _add_collection_arguments(run_parser)
    run_parser.add_argument(
        "--processed", type=Path, help="생성하고 분석할 표준 CSV 경로"
    )
    run_parser.add_argument(
        "--output-dir", type=Path, help="PNG를 저장할 디렉터리"
    )
    run_parser.add_argument("--summary", type=Path, help="요약 JSON 경로")
    return parser


# 명령행 인자를 workflow로 전달하고 도메인 오류를 종료 코드로 변환한다.
def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = ProjectPaths.from_root(args.project_root)
    try:
        if args.command == "download":
            result = run_download(
                raw_root=_resolve_path(paths.root, args.raw_root, paths.raw_root),
                processed_path=_resolve_path(
                    paths.root, args.output, paths.processed_path
                ),
                start_year=args.start_year,
                end_year=args.end_year,
                station_id=args.station_id,
                rebuild_from_raw=args.rebuild_from_raw,
            )
            _print_download_result(result)
        elif args.command == "analyze":
            summary = run_analysis(
                input_path=_resolve_path(paths.root, args.input, paths.processed_path),
                output_dir=_resolve_path(
                    paths.root, args.output_dir, paths.images_dir
                ),
                summary_path=_resolve_path(
                    paths.root, args.summary, paths.summary_path
                ),
                config=AnalysisConfig(),
            )
            _print_analysis_result(summary)
        else:
            result = run_pipeline(
                raw_root=_resolve_path(paths.root, args.raw_root, paths.raw_root),
                processed_path=_resolve_path(
                    paths.root, args.processed, paths.processed_path
                ),
                output_dir=_resolve_path(
                    paths.root, args.output_dir, paths.images_dir
                ),
                summary_path=_resolve_path(
                    paths.root, args.summary, paths.summary_path
                ),
                analysis_config=AnalysisConfig(),
                start_year=args.start_year,
                end_year=args.end_year,
                station_id=args.station_id,
                rebuild_from_raw=args.rebuild_from_raw,
            )
            _print_download_result(result["download"])
            _print_analysis_result(result["analysis"])
    except (DataDownloadError, DataValidationError, AnalysisValidationError) as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1
    return 0


# 수집과 통합 실행에 공통으로 쓰는 명령행 옵션을 추가한다.
def _add_collection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--rebuild-from-raw",
        action="store_true",
        help="네트워크 요청 없이 보존된 CSV에서 가공 CSV를 다시 만듭니다.",
    )
    parser.add_argument("--raw-root", type=Path, help="원자료 디렉터리")
    parser.set_defaults(start_year=1994, end_year=2024, station_id=108)


# 선택 경로를 프로젝트 루트 기준의 절대 경로로 해석한다.
def _resolve_path(root: Path, value: Path | None, default: Path) -> Path:
    if value is None:
        return default
    return value if value.is_absolute() else (root / value).resolve()


# 수집 또는 원자료 재통합 결과를 사람이 읽을 수 있게 출력한다.
def _print_download_result(result: object) -> None:
    if not isinstance(result, dict):
        return
    label = "원자료 재통합" if result.get("mode") == "rebuild" else "수집·통합"
    print(
        f"{label} 완료: {result['year_count']}개 연도, "
        f"{result['row_count']:,}행 -> {result['processed_path']}"
    )


# 분석 요약에서 기간·추세·이상 기온 후보 수를 출력한다.
def _print_analysis_result(summary: object) -> None:
    if not isinstance(summary, dict):
        return
    quality = summary["data_quality"]
    trend = summary["trend"]
    extremes = summary["extremes"]
    print(
        f"분석 완료: {quality['row_count']:,}행, "
        f"{quality['actual_start_date']}~{quality['actual_end_date']}"
    )
    print(
        f"선형 추세: {trend['slope_c_per_decade']:+.3f} °C/10년 "
        f"(R²={trend['r_squared']:.3f})"
    )
    print(
        f"통계적 이상 기온 후보: 고온 {extremes['hot_candidate_count']:,}일, "
        f"저온 {extremes['cold_candidate_count']:,}일"
    )
