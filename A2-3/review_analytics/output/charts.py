"""불변 대시보드 스냅샷을 헤드리스 matplotlib 차트로 렌더링한다."""

from __future__ import annotations

import logging
import os
import tempfile
import warnings
from collections import defaultdict
from datetime import date
from pathlib import Path

if "MPLCONFIGDIR" not in os.environ:
    os.environ["MPLCONFIGDIR"] = str(Path(tempfile.gettempdir()) / "review-analytics-matplotlib")

import matplotlib

matplotlib.use("Agg", force=True)

from matplotlib import font_manager, pyplot as plt

from review_analytics.dto import DashboardData, GeneratedFile
from review_analytics.errors import OutputWriteError
from review_analytics.models import Sentiment


logger = logging.getLogger(__name__)

CHART_FILENAMES = (
    "sentiment_distribution.png",
    "sentiment_trend.png",
    "rating_sentiment_matrix.png",
)
_SENTIMENTS = (Sentiment.POSITIVE, Sentiment.NEUTRAL, Sentiment.NEGATIVE)
_LABELS = {
    Sentiment.POSITIVE: "긍정",
    Sentiment.NEUTRAL: "중립",
    Sentiment.NEGATIVE: "부정",
}
_COLORS = {
    Sentiment.POSITIVE: "#2E8B57",
    Sentiment.NEUTRAL: "#808080",
    Sentiment.NEGATIVE: "#C94C4C",
}


# 대시보드 스냅샷으로 고정된 세 종류의 PNG 차트를 생성한다.
def render_charts(
    data: DashboardData,
    output_dir: Path,
    font_candidates: tuple[str, ...],
) -> tuple[GeneratedFile, ...]:
    """Create the three fixed PNG artifacts without exposing matplotlib objects."""
    selected_font = _select_font(font_candidates)
    context = {"axes.unicode_minus": False}
    if selected_font is not None:
        context["font.family"] = selected_font

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".charts-", dir=output_dir) as staging_dir:
            staging_path = Path(staging_dir)
            with plt.rc_context(context):
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", message=r"Glyph .* missing from font.*")
                    figures = (
                        _sentiment_distribution(data),
                        _sentiment_trend(data),
                        _rating_sentiment_matrix(data),
                    )
                    try:
                        for filename, figure in zip(CHART_FILENAMES, figures, strict=True):
                            _save_figure(figure, staging_path / filename)
                    finally:
                        for figure in figures:
                            plt.close(figure)
            generated: list[GeneratedFile] = []
            for filename in CHART_FILENAMES:
                path = output_dir / filename
                (staging_path / filename).replace(path)
                generated.append(GeneratedFile("chart", path, size_bytes=path.stat().st_size))
        return tuple(generated)
    except OSError as exc:
        logger.error(
            "event=output.failed output_type=chart file_name=chart_bundle error_code=CHART_WRITE_FAILED"
        )
        raise OutputWriteError("차트 파일을 저장하지 못했습니다.", "CHART_WRITE_FAILED") from exc


# 설치된 폰트 중 첫 번째 후보를 선택하고 없으면 폴백을 기록한다.
def _select_font(candidates: tuple[str, ...]) -> str | None:
    available = {font.name for font in font_manager.fontManager.ttflist}
    for candidate in candidates:
        if candidate in available:
            return candidate
    logger.warning("event=chart.font.fallback candidates=%d", len(candidates))
    return None


# 감정별 건수를 원형 분포 차트로 그린다.
def _sentiment_distribution(data: DashboardData):
    figure, axis = plt.subplots(figsize=(7, 5))
    counts = dict(data.stats.sentiment_counts)
    values = [counts.get(sentiment, 0) for sentiment in _SENTIMENTS]
    if not any(values):
        _no_data(axis, "감정 분포")
        return figure
    axis.pie(
        values,
        labels=[_LABELS[sentiment] for sentiment in _SENTIMENTS],
        colors=[_COLORS[sentiment] for sentiment in _SENTIMENTS],
        autopct="%1.1f%%",
        startangle=90,
    )
    axis.set_title("감정 분포")
    axis.axis("equal")
    figure.tight_layout()
    return figure


# 날짜별 감정 비율을 시간 추이 선 차트로 그린다.
def _sentiment_trend(data: DashboardData):
    figure, axis = plt.subplots(figsize=(9, 5))
    daily: dict[date, dict[Sentiment, int]] = defaultdict(lambda: defaultdict(int))
    for row in data.rows:
        if row.review_date is None or row.sentiment is None:
            continue
        try:
            review_date = date.fromisoformat(row.review_date)
        except ValueError:
            continue
        daily[review_date][row.sentiment] += 1
    if not daily:
        _no_data(axis, "일별 감정 비율 추이")
        return figure
    days = sorted(daily)
    for sentiment in _SENTIMENTS:
        ratios = [
            daily[day].get(sentiment, 0) / sum(daily[day].values())
            for day in days
        ]
        axis.plot(
            days,
            ratios,
            marker="o",
            label=_LABELS[sentiment],
            color=_COLORS[sentiment],
        )
    axis.set_title("일별 감정 비율 추이")
    axis.set_ylabel("비율")
    axis.set_ylim(0, 1)
    axis.legend()
    figure.autofmt_xdate()
    figure.tight_layout()
    return figure


# 별점별 감정 건수를 누적 막대 차트로 그린다.
def _rating_sentiment_matrix(data: DashboardData):
    figure, axis = plt.subplots(figsize=(8, 5))
    matrix = {rating: {sentiment: 0 for sentiment in _SENTIMENTS} for rating in range(1, 6)}
    has_data = False
    for row in data.rows:
        if row.rating is None or row.sentiment is None:
            continue
        matrix[row.rating][row.sentiment] += 1
        has_data = True
    if not has_data:
        _no_data(axis, "별점별 감정 건수")
        return figure
    ratings = tuple(range(1, 6))
    bottom = [0] * len(ratings)
    for sentiment in _SENTIMENTS:
        values = [matrix[rating][sentiment] for rating in ratings]
        axis.bar(
            ratings,
            values,
            bottom=bottom,
            label=_LABELS[sentiment],
            color=_COLORS[sentiment],
        )
        bottom = [current + value for current, value in zip(bottom, values, strict=True)]
    axis.set_title("별점별 감정 건수")
    axis.set_xlabel("별점")
    axis.set_ylabel("리뷰 수")
    axis.set_xticks(ratings)
    axis.legend()
    figure.tight_layout()
    return figure


# 차트 데이터가 없을 때 공통 빈 상태를 표시한다.
def _no_data(axis, title: str) -> None:
    axis.set_title(title)
    axis.text(
        0.5,
        0.5,
        "표시할 데이터 없음",
        ha="center",
        va="center",
        transform=axis.transAxes,
    )
    axis.set_axis_off()


# Figure를 경고 없이 지정된 PNG 경로에 저장한다.
def _save_figure(figure, path: Path) -> None:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=r"Glyph .* missing from font.*")
        figure.savefig(path, format="png", dpi=150, bbox_inches="tight")
