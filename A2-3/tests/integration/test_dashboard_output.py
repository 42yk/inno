from __future__ import annotations

import logging

import pytest

from review_analytics.dto import DashboardData, ExportRow, ReviewFilter, StatsResult
from review_analytics.models import KeywordEvidence, QualityMetrics, ReportFormat, Sentiment
from review_analytics.errors import OutputWriteError


def _dashboard(tmp_path, *, rows=None) -> DashboardData:
    chart_paths = (
        tmp_path / "sentiment_distribution.png",
        tmp_path / "sentiment_trend.png",
        tmp_path / "rating_sentiment_matrix.png",
    )
    return DashboardData(
        stats=StatsResult(
            total_clean=3,
            analyzed_count=2,
            sentiment_counts=(
                (Sentiment.POSITIVE, 1),
                (Sentiment.NEUTRAL, 0),
                (Sentiment.NEGATIVE, 1),
            ),
            rating_counts=((1, 1), (2, 0), (3, 0), (4, 0), (5, 1)),
            average_rating=3.0,
            metrics=QualityMetrics(2 / 3, 0.85, 1.0),
        ),
        positive_keywords=(KeywordEvidence("품질", (1, 2)),),
        negative_keywords=(KeywordEvidence("배송", (2,)),),
        summary="품질 만족도가 높고 배송 개선이 필요합니다.",
        recommendations=("배송 과정을 점검하세요.", "포장을 보강하세요."),
        filter=ReviewFilter(product="텀블러", date_from="2026-08-01"),
        rows=rows
        if rows is not None
        else (
            ExportRow(1, "좋아요", 5, "2026-08-01", "텀블러", Sentiment.POSITIVE, 0.9, "now"),
            ExportRow(2, "느려요", 1, "2026-08-02", "텀블러", Sentiment.NEGATIVE, 0.8, "now"),
            ExportRow(3, "아직 분석 전", None, None, "텀블러", None, None, None),
        ),
        chart_paths=chart_paths,
        generated_at="2026-08-06T03:00:00+00:00",
    )


def test_render_charts_creates_three_nonempty_png_files_headlessly(tmp_path):
    from review_analytics.output.charts import render_charts

    generated = render_charts(_dashboard(tmp_path), tmp_path, ("DejaVu Sans",))

    assert tuple(file.path.name for file in generated) == (
        "sentiment_distribution.png",
        "sentiment_trend.png",
        "rating_sentiment_matrix.png",
    )
    assert all(file.path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for file in generated)
    assert all(file.size_bytes and file.size_bytes > 0 for file in generated)


def test_missing_date_and_rating_data_still_render_placeholder_pngs(tmp_path, monkeypatch):
    from matplotlib.axes import Axes

    from review_analytics.output.charts import render_charts

    labels: list[str] = []
    original_text = Axes.text

    def recording_text(self, x, y, text, *args, **kwargs):
        labels.append(text)
        return original_text(self, x, y, text, *args, **kwargs)

    monkeypatch.setattr(Axes, "text", recording_text)
    rows = (ExportRow(1, "본문", None, None, "텀블러", Sentiment.POSITIVE, 0.9, "now"),)

    generated = render_charts(_dashboard(tmp_path, rows=rows), tmp_path, ("DejaVu Sans",))

    assert labels.count("표시할 데이터 없음") >= 2
    assert len(generated) == 3
    assert all(file.path.exists() for file in generated)


def test_unavailable_korean_font_logs_warning_and_uses_default(tmp_path, caplog):
    from review_analytics.output.charts import render_charts

    with caplog.at_level(logging.WARNING):
        generated = render_charts(_dashboard(tmp_path), tmp_path, ("Definitely Missing Font",))

    assert len(generated) == 3
    assert "event=chart.font.fallback" in caplog.text


def test_markdown_and_text_reports_contain_the_same_dashboard_facts(tmp_path):
    from review_analytics.output.reports import render_report_text, write_report

    data = _dashboard(tmp_path)
    markdown = render_report_text(data, ReportFormat.MD)
    text = render_report_text(data, ReportFormat.TXT)

    for report in (markdown, text):
        assert "총 리뷰 수: 3" in report
        assert "분석 완료 수: 2" in report
        assert "분석 완료율: 66.7%" in report
        assert "긍정: 1건 (50.0%)" in report
        assert "중립: 0건 (0.0%)" in report
        assert "부정: 1건 (50.0%)" in report
        assert "평균 별점: 3.00" in report
        assert "평균 신뢰도: 85.0%" in report
        assert "별점·감정 일치율: 100.0%" in report
        assert "품질 (근거 리뷰 2건)" in report
        assert "배송 (근거 리뷰 1건)" in report
        assert data.summary in report
        assert data.recommendations[0] in report
        assert "product=텀블러" in report
        assert "date_from=2026-08-01" in report
        assert "2026-08-06T03:00:00+00:00" in report
        assert "sentiment_distribution.png" in report

    markdown_file = write_report(data, ReportFormat.MD, tmp_path / "report.md")
    text_file = write_report(data, ReportFormat.TXT, tmp_path / "nested" / "report.txt")
    assert markdown_file.path.read_text(encoding="utf-8") == markdown
    assert text_file.path.read_text(encoding="utf-8") == text
    assert markdown_file.size_bytes and text_file.size_bytes


def test_chart_and_report_write_failures_log_safe_output_events(tmp_path, monkeypatch, caplog):
    from review_analytics.output import charts
    from review_analytics.output.reports import write_report

    def fail_save(figure, path):
        raise OSError("PRIVATE output failure")

    monkeypatch.setattr(charts, "_save_figure", fail_save)
    with caplog.at_level(logging.ERROR), pytest.raises(OutputWriteError):
        charts.render_charts(_dashboard(tmp_path), tmp_path, ("DejaVu Sans",))

    blocker = tmp_path / "private-parent"
    blocker.write_text("PRIVATE FILE CONTENT", encoding="utf-8")
    with pytest.raises(OutputWriteError):
        write_report(_dashboard(tmp_path), ReportFormat.MD, blocker / "report.md")

    assert "event=output.failed output_type=chart file_name=chart_bundle error_code=CHART_WRITE_FAILED" in caplog.text
    assert "event=output.failed output_type=report file_name=report.md error_code=REPORT_WRITE_FAILED" in caplog.text
    assert "PRIVATE output failure" not in caplog.text
    assert "PRIVATE FILE CONTENT" not in caplog.text
    assert str(tmp_path) not in caplog.text
