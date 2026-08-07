"""대시보드 리포트를 일반 텍스트와 Markdown으로 렌더링한다."""

from __future__ import annotations

import logging
from pathlib import Path

from review_analytics.dto import DashboardData, GeneratedFile
from review_analytics.errors import OutputWriteError
from review_analytics.models import ReportFormat, Sentiment


_SENTIMENT_LABELS = {
    Sentiment.POSITIVE: "긍정",
    Sentiment.NEUTRAL: "중립",
    Sentiment.NEGATIVE: "부정",
}
logger = logging.getLogger(__name__)


# 대시보드 스냅샷을 TXT 또는 Markdown 리포트 본문으로 렌더링한다.
def render_report_text(data: DashboardData, report_format: ReportFormat) -> str:
    """Render every report fact exclusively from the supplied snapshot."""
    markdown = report_format is ReportFormat.MD
    heading = (lambda level, value: f"{'#' * level} {value}") if markdown else _text_heading
    stats = data.stats
    lines = [
        heading(1, "고객 리뷰 감정 분석 종합 리포트"),
        "",
        f"생성 시각: {data.generated_at or 'N/A'}",
        f"적용 필터: {_filter_text(data)}",
        "",
        heading(2, "핵심 통계"),
        f"- 총 리뷰 수: {stats.total_clean}",
        f"- 분석 완료 수: {stats.analyzed_count}",
        f"- 분석 완료율: {_percentage(stats.metrics.completion_rate)}",
        f"- 평균 별점: {_decimal(stats.average_rating)}",
        f"- 평균 신뢰도: {_percentage(stats.metrics.average_confidence)}",
        f"- 별점·감정 일치율: {_percentage(stats.metrics.rating_sentiment_agreement)}",
        "",
        heading(2, "감정 분포"),
    ]
    lines.extend(
        f"- {_SENTIMENT_LABELS[sentiment]}: "
        f"{_count_ratio(count, stats.analyzed_count)}"
        for sentiment, count in stats.sentiment_counts
    )
    lines.extend(("", heading(2, "긍정 키워드")))
    lines.extend(_keyword_lines(data.positive_keywords))
    lines.extend(("", heading(2, "부정 키워드")))
    lines.extend(_keyword_lines(data.negative_keywords))
    lines.extend(("", heading(2, "AI 요약"), data.summary))
    lines.extend(("", heading(2, "개선 제안")))
    lines.extend(f"- {recommendation}" for recommendation in data.recommendations)
    lines.extend(("", heading(2, "생성된 차트 경로")))
    lines.extend(f"- {path}" for path in data.chart_paths)
    return "\n".join(lines).rstrip() + "\n"


# 렌더링한 리포트를 UTF-8 파일로 기록하고 파일 정보를 반환한다.
def write_report(
    data: DashboardData,
    report_format: ReportFormat,
    output_path: Path,
) -> GeneratedFile:
    """Write one UTF-8 report file and translate filesystem failures safely."""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        text = render_report_text(data, report_format)
        output_path.write_text(text, encoding="utf-8")
        return GeneratedFile("report", output_path, size_bytes=output_path.stat().st_size)
    except OSError as exc:
        logger.error(
            "event=output.failed output_type=report file_name=%s error_code=REPORT_WRITE_FAILED",
            output_path.name,
        )
        raise OutputWriteError("리포트 파일을 저장하지 못했습니다.", "REPORT_WRITE_FAILED") from exc


# 일반 텍스트 리포트의 단계별 제목 표현을 만든다.
def _text_heading(level: int, value: str) -> str:
    if level == 1:
        return value
    return f"[{value}]"


# 적용된 조회 필터를 사람이 읽을 수 있는 한 줄로 만든다.
def _filter_text(data: DashboardData) -> str:
    values = (
        ("sentiment", data.filter.sentiment.value if data.filter.sentiment is not None else None),
        ("rating", data.filter.rating),
        ("rating_min", data.filter.rating_min),
        ("date_from", data.filter.date_from),
        ("date_to", data.filter.date_to),
        ("product", data.filter.product),
    )
    selected = [f"{name}={value}" for name, value in values if value is not None]
    return ", ".join(selected) if selected else "없음"


# 선택 비율을 백분율 문자열 또는 N/A로 표시한다.
def _percentage(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.1f}%"


# 선택적 실수값을 소수점 둘째 자리 문자열 또는 N/A로 표시한다.
def _decimal(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


# 건수와 전체 대비 비율을 함께 표시한다.
def _count_ratio(count: int, total: int) -> str:
    ratio = "N/A" if total == 0 else f"{count / total * 100:.1f}%"
    return f"{count}건 ({ratio})"


# 키워드와 고유 근거 리뷰 건수를 리포트 항목으로 만든다.
def _keyword_lines(keywords) -> tuple[str, ...]:
    if not keywords:
        return ("- 없음",)
    return tuple(
        f"- {item.keyword} (근거 리뷰 {len(set(item.review_ids))}건)"
        for item in keywords
    )
