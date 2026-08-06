"""대시보드 스냅샷 조립과 부분 출력 생성을 조정한다."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from review_analytics.dto import (
    DashboardData,
    DashboardRequest,
    GeneratedFile,
    GeneratedFilesResult,
    OperationSummary,
    StatsRow,
)
from review_analytics.errors import OutputWriteError, StaleInsightError, ValidationError
from review_analytics.models import KeywordEvidence, ReportFormat
from review_analytics.output.charts import CHART_FILENAMES, render_charts
from review_analytics.output.reports import render_report_text, write_report
from review_analytics.repositories import AnalysisRepository, ReviewRepository
from review_analytics.services.extraction import extraction_scope
from review_analytics.services.query import calculate_stats


ChartRenderer = Callable[[DashboardData, Path, tuple[str, ...]], tuple[GeneratedFile, ...]]
ReportWriter = Callable[[DashboardData, ReportFormat, Path], GeneratedFile]


# 최신 인사이트를 검증하고 동일 스냅샷에서 차트와 리포트를 생성한다.
def build_dashboard(
    request: DashboardRequest,
    review_repository: ReviewRepository,
    analysis_repository: AnalysisRepository,
    font_candidates: tuple[str, ...] = (),
    chart_renderer: ChartRenderer = render_charts,
    report_writer: ReportWriter = write_report,
    now: Callable[[], str] = lambda: datetime.now(timezone.utc).isoformat(),
) -> GeneratedFilesResult:
    """Validate insight freshness, then render all outputs from one frozen DTO."""
    if request.output_dir is None:
        raise ValidationError("대시보드 출력 디렉터리가 필요합니다.", "DASHBOARD_OUTPUT_REQUIRED")
    if request.top_n < 1:
        raise ValidationError("TOP N은 1 이상이어야 합니다.", "DASHBOARD_TOP_INVALID")

    scope_json, scope_hash = extraction_scope(request.filter, None)
    insight = analysis_repository.latest_valid_insight(scope_hash)
    if (
        insight is None
        or insight.is_stale
        or insight.scope_hash != scope_hash
        or insight.scope_json != scope_json
    ):
        _raise_current_insight_required()

    rows = review_repository.export_rows(request.filter)
    if insight.review_count != len(rows):
        _raise_current_insight_required()

    chart_paths = tuple(request.output_dir / name for name in CHART_FILENAMES)
    data = DashboardData(
        stats=calculate_stats(
            tuple(
                StatsRow(row.review_id, row.rating, row.sentiment, row.confidence)
                for row in rows
            )
        ),
        positive_keywords=_top_keywords(insight.result.positive_keywords, request.top_n),
        negative_keywords=_top_keywords(insight.result.negative_keywords, request.top_n),
        summary=insight.result.summary,
        recommendations=insight.result.recommendations,
        filter=request.filter,
        generated_at=now(),
        rows=rows,
        chart_paths=chart_paths,
    )
    files: list[GeneratedFile] = []
    failure_codes: list[str] = []
    failed = 0
    try:
        chart_files = chart_renderer(data, request.output_dir, font_candidates)
        files.extend(chart_files)
        if len(chart_files) < len(CHART_FILENAMES):
            failed += len(CHART_FILENAMES) - len(chart_files)
            failure_codes.append("CHART_OUTPUT_INCOMPLETE")
    except OutputWriteError as exc:
        failed += len(CHART_FILENAMES)
        failure_codes.append(exc.code)

    actual_chart_paths = tuple(file.path for file in files if file.role == "chart")
    report_data = (
        data
        if actual_chart_paths == data.chart_paths
        else replace(data, chart_paths=actual_chart_paths)
    )
    console_report = render_report_text(report_data, request.report_format)
    report_path = request.output_dir / f"review_sentiment_report.{request.report_format.value}"
    try:
        files.append(report_writer(report_data, request.report_format, report_path))
    except OutputWriteError as exc:
        failed += 1
        failure_codes.append(exc.code)

    if not files:
        raise OutputWriteError(
            "대시보드 출력 파일을 하나도 생성하지 못했습니다.",
            "DASHBOARD_OUTPUT_FAILED",
        )
    return GeneratedFilesResult(
        files=tuple(files),
        summary=OperationSummary(
            processed=len(CHART_FILENAMES) + 1,
            succeeded=len(files),
            skipped=0,
            failed=failed,
            messages=(console_report, *failure_codes),
        ),
    )


# 고유 근거 수와 이름 순으로 상위 키워드를 안정적으로 선택한다.
def _top_keywords(
    keywords: tuple[KeywordEvidence, ...],
    top_n: int,
) -> tuple[KeywordEvidence, ...]:
    return tuple(
        sorted(
            keywords,
            key=lambda item: (
                -len(set(item.review_ids)),
                item.keyword.casefold(),
                item.keyword,
            ),
        )[:top_n]
    )


# 현재 범위에 맞는 인사이트가 필요하다는 안전 오류를 발생시킨다.
def _raise_current_insight_required() -> None:
    raise StaleInsightError(
        "현재 필터와 일치하는 유효한 인사이트가 없습니다. 같은 필터로 extract를 먼저 실행하세요.",
        "CURRENT_INSIGHT_REQUIRED",
    )
