from __future__ import annotations

from pathlib import Path

import pytest

from review_analytics.dto import DashboardRequest, ExportRow, GeneratedFile, ReviewFilter, StatsRow
from review_analytics.errors import OutputWriteError, StaleInsightError
from review_analytics.models import InsightResult, KeywordEvidence, Sentiment, StoredInsight
from review_analytics.services.extraction import extraction_scope


class DashboardReviewRepository:
    def __init__(self, rows: tuple[ExportRow, ...]) -> None:
        self.rows = rows
        self.filters: list[ReviewFilter] = []

    def export_rows(self, review_filter: ReviewFilter) -> tuple[ExportRow, ...]:
        self.filters.append(review_filter)
        return self.rows

    def stats_rows(self, review_filter: ReviewFilter) -> tuple[StatsRow, ...]:
        self.filters.append(review_filter)
        return tuple(
            StatsRow(row.review_id, row.rating, row.sentiment, row.confidence)
            for row in self.rows
        )


class DashboardAnalysisRepository:
    def __init__(self, insight: StoredInsight | None) -> None:
        self.insight = insight
        self.scope_hashes: list[str] = []

    def latest_valid_insight(self, scope_hash: str) -> StoredInsight | None:
        self.scope_hashes.append(scope_hash)
        return self.insight


def _rows() -> tuple[ExportRow, ...]:
    return (
        ExportRow(1, "좋아요", 5, "2026-08-01", "텀블러", Sentiment.POSITIVE, 0.9, "now"),
        ExportRow(2, "배송이 느려요", 2, "2026-08-02", "텀블러", Sentiment.NEGATIVE, 0.8, "now"),
    )


def _stored_insight(
    review_filter: ReviewFilter,
    *,
    review_count: int = 2,
    scope_json: str | None = None,
) -> StoredInsight:
    expected_json, scope_hash = extraction_scope(review_filter, None)
    return StoredInsight(
        id=7,
        scope_json=scope_json or expected_json,
        scope_hash=scope_hash,
        review_count=review_count,
        result=InsightResult(
            positive_keywords=(
                KeywordEvidence("가벼움", (1,)),
                KeywordEvidence("품질", (1, 2)),
            ),
            negative_keywords=(
                KeywordEvidence("포장", (2,)),
                KeywordEvidence("배송", (1, 2)),
            ),
            summary="고객은 품질을 좋아하지만 배송을 개선해야 합니다.",
            recommendations=("배송 과정을 점검하세요.",),
            model_name="fake-model",
            prompt_version="v1",
        ),
        is_stale=False,
        created_at="2026-08-06T01:00:00+00:00",
    )


def test_dashboard_without_current_insight_writes_nothing(tmp_path):
    """A dashboard must never emit stale-looking artifacts without exact-scope AI insight."""
    from review_analytics.services.reporting import build_dashboard

    output_dir = tmp_path / "output"

    def unused_renderer(*args, **kwargs):
        raise AssertionError("output must not be called")

    with pytest.raises(StaleInsightError) as raised:
        build_dashboard(
            DashboardRequest(output_dir=output_dir),
            DashboardReviewRepository(_rows()),
            DashboardAnalysisRepository(None),
            chart_renderer=unused_renderer,
            report_writer=unused_renderer,
        )

    assert raised.value.code == "CURRENT_INSIGHT_REQUIRED"
    assert not output_dir.exists()


@pytest.mark.parametrize(
    ("insight"),
    (
        _stored_insight(ReviewFilter(product="텀블러"), review_count=1),
        _stored_insight(ReviewFilter(product="텀블러"), scope_json='{"product":"다른 제품"}'),
    ),
)
def test_dashboard_rejects_mismatched_scope_or_review_count_before_output(tmp_path, insight):
    """Hash lookup alone and a once-current aggregate are insufficient freshness evidence."""
    from review_analytics.services.reporting import build_dashboard

    review_filter = ReviewFilter(product="텀블러")

    def unused_renderer(*args, **kwargs):
        raise AssertionError("output must not be called")

    with pytest.raises(StaleInsightError):
        build_dashboard(
            DashboardRequest(filter=review_filter, output_dir=tmp_path / "output"),
            DashboardReviewRepository(_rows()),
            DashboardAnalysisRepository(insight),
            chart_renderer=unused_renderer,
            report_writer=unused_renderer,
        )

    assert not (tmp_path / "output").exists()


def test_dashboard_builds_one_snapshot_and_ranks_keywords_by_unique_evidence(tmp_path):
    """Charts, console text, and file report must share identical statistics and TOP-N data."""
    from review_analytics.services.reporting import build_dashboard

    review_filter = ReviewFilter(product="텀블러")
    review_repository = DashboardReviewRepository(_rows())
    analysis_repository = DashboardAnalysisRepository(_stored_insight(review_filter))
    seen: dict[str, object] = {}

    def render_charts(data, output_dir: Path, fonts: tuple[str, ...]):
        seen["chart_data"] = data
        seen["fonts"] = fonts
        return tuple(
            GeneratedFile("chart", path, size_bytes=10)
            for path in data.chart_paths
        )

    def write_report(data, report_format, output_path: Path):
        seen["report_data"] = data
        seen["report_format"] = report_format
        return GeneratedFile("report", output_path, size_bytes=20)

    result = build_dashboard(
        DashboardRequest(
            filter=review_filter,
            top_n=1,
            output_dir=tmp_path / "output",
        ),
        review_repository,
        analysis_repository,
        font_candidates=("NanumGothic",),
        chart_renderer=render_charts,
        report_writer=write_report,
        now=lambda: "2026-08-06T02:00:00+00:00",
    )

    data = seen["chart_data"]
    assert data is seen["report_data"]
    assert data.rows == _rows()
    assert data.positive_keywords == (KeywordEvidence("품질", (1, 2)),)
    assert data.negative_keywords == (KeywordEvidence("배송", (1, 2)),)
    assert data.generated_at == "2026-08-06T02:00:00+00:00"
    assert tuple(path.name for path in data.chart_paths) == (
        "sentiment_distribution.png",
        "sentiment_trend.png",
        "rating_sentiment_matrix.png",
    )
    assert analysis_repository.scope_hashes == [extraction_scope(review_filter, None)[1]]
    assert review_repository.filters == [review_filter]
    assert result.summary.processed == 4
    assert result.summary.succeeded == 4
    assert result.summary.failed == 0
    assert "고객은 품질을 좋아하지만" in result.summary.messages[0]


def test_dashboard_keeps_report_when_chart_bundle_fails(tmp_path):
    """A report file remains useful even when the three chart outputs fail."""
    from review_analytics.services.reporting import build_dashboard

    review_filter = ReviewFilter(product="텀블러")
    reported_chart_paths: list[Path] = []

    def fail_charts(*args, **kwargs):
        raise OutputWriteError("차트를 저장하지 못했습니다.", "CHART_WRITE_FAILED")

    def write_report(data, report_format, output_path):
        reported_chart_paths.extend(data.chart_paths)
        return GeneratedFile("report", output_path, size_bytes=20)

    result = build_dashboard(
        DashboardRequest(filter=review_filter, output_dir=tmp_path),
        DashboardReviewRepository(_rows()),
        DashboardAnalysisRepository(_stored_insight(review_filter)),
        chart_renderer=fail_charts,
        report_writer=write_report,
    )

    assert tuple(file.role for file in result.files) == ("report",)
    assert result.summary.succeeded == 1
    assert result.summary.failed == 3
    assert "CHART_WRITE_FAILED" in result.summary.messages
    assert reported_chart_paths == []


def test_dashboard_keeps_charts_when_report_file_fails(tmp_path):
    """All successful PNGs remain represented when only the report file cannot be written."""
    from review_analytics.services.reporting import build_dashboard

    review_filter = ReviewFilter(product="텀블러")

    def render_charts(data, output_dir, fonts):
        return tuple(
            GeneratedFile("chart", path, size_bytes=10)
            for path in data.chart_paths
        )

    def fail_report(*args, **kwargs):
        raise OutputWriteError("리포트를 저장하지 못했습니다.", "REPORT_WRITE_FAILED")

    result = build_dashboard(
        DashboardRequest(filter=review_filter, output_dir=tmp_path),
        DashboardReviewRepository(_rows()),
        DashboardAnalysisRepository(_stored_insight(review_filter)),
        chart_renderer=render_charts,
        report_writer=fail_report,
    )

    assert len(result.files) == 3
    assert result.summary.succeeded == 3
    assert result.summary.failed == 1
    assert "REPORT_WRITE_FAILED" in result.summary.messages


def test_dashboard_raises_when_every_file_output_fails(tmp_path):
    """Console text alone does not turn four failed file outputs into a partial success."""
    from review_analytics.services.reporting import build_dashboard

    review_filter = ReviewFilter(product="텀블러")

    def fail_charts(*args, **kwargs):
        raise OutputWriteError("차트를 저장하지 못했습니다.", "CHART_WRITE_FAILED")

    def fail_report(*args, **kwargs):
        raise OutputWriteError("리포트를 저장하지 못했습니다.", "REPORT_WRITE_FAILED")

    with pytest.raises(OutputWriteError) as raised:
        build_dashboard(
            DashboardRequest(filter=review_filter, output_dir=tmp_path),
            DashboardReviewRepository(_rows()),
            DashboardAnalysisRepository(_stored_insight(review_filter)),
            chart_renderer=fail_charts,
            report_writer=fail_report,
        )

    assert raised.value.code == "DASHBOARD_OUTPUT_FAILED"
