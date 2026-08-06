from __future__ import annotations

from pathlib import Path

import pytest

from review_analytics.dto import (
    ExportRequest,
    ReviewDetailRequest,
    ReviewFilter,
    StatsRequest,
    StatsRow,
)
from review_analytics.errors import NotFoundError
from review_analytics.models import ExportFormat, Sentiment


class StatsRepository:
    def __init__(self, rows: tuple[StatsRow, ...]) -> None:
        self.rows = rows

    def stats_rows(self, review_filter: ReviewFilter) -> tuple[StatsRow, ...]:
        return self.rows


def test_get_stats_before_analysis_keeps_clean_reviews_in_denominator():
    """Dropping unanalyzed rows would falsely report a complete analysis."""
    from review_analytics.services.query import get_stats

    repository = StatsRepository((StatsRow(1, 5, None, None), StatsRow(2, 2, None, None)))

    result = get_stats(StatsRequest(), repository)

    assert result.total_clean == 2
    assert result.analyzed_count == 0
    assert result.sentiment_counts == (
        (Sentiment.POSITIVE, 0),
        (Sentiment.NEUTRAL, 0),
        (Sentiment.NEGATIVE, 0),
    )
    assert result.average_rating == 3.5
    assert result.metrics.completion_rate == 0.0
    assert result.metrics.average_confidence is None
    assert result.metrics.rating_sentiment_agreement is None


def test_get_stats_uses_only_eligible_rows_for_analysis_metrics():
    """Using clean rows for confidence or agreement would corrupt metric denominators."""
    from review_analytics.services.query import get_stats

    rows = (
        StatsRow(1, 5, Sentiment.POSITIVE, 0.9),
        StatsRow(2, 1, Sentiment.NEGATIVE, 0.7),
        StatsRow(3, None, None, None),
    )

    result = get_stats(StatsRequest(), StatsRepository(rows))

    assert result.total_clean == 3
    assert result.analyzed_count == 2
    assert result.sentiment_counts == (
        (Sentiment.POSITIVE, 1),
        (Sentiment.NEUTRAL, 0),
        (Sentiment.NEGATIVE, 1),
    )
    assert result.rating_counts == ((1, 1), (2, 0), (3, 0), (4, 0), (5, 1))
    assert result.average_rating == 3.0
    assert result.metrics.completion_rate == pytest.approx(2 / 3)
    assert result.metrics.average_confidence == pytest.approx(0.8)
    assert result.metrics.rating_sentiment_agreement == 1.0


def test_show_review_raises_safe_not_found_error_for_missing_raw_id():
    """Returning None would force CLI code to know repository absence semantics."""
    from review_analytics.services.query import show_review

    class MissingRepository:
        def get_review_detail(self, review_id: int):
            return None

    with pytest.raises(NotFoundError) as raised:
        show_review(ReviewDetailRequest(42), MissingRepository())

    assert raised.value.code == "RAW_REVIEW_NOT_FOUND"


def test_export_reviews_writes_headers_when_filter_has_no_rows(tmp_path):
    """An empty result is a successful usable export, not a missing-file error."""
    from review_analytics.services.exporting import export_reviews

    class EmptyRepository:
        def export_rows(self, review_filter: ReviewFilter):
            return ()

    output = tmp_path / "nested" / "empty.csv"
    generated = export_reviews(
        ExportRequest(format=ExportFormat.CSV, output_path=output),
        EmptyRepository(),
    )

    assert generated.path == output
    assert generated.record_count == 0
    assert output.read_text(encoding="utf-8-sig").splitlines() == [
        "review_id,review_text,rating,review_date,product_name,sentiment,confidence,analyzed_at"
    ]


def test_export_reviews_rejects_missing_output_path():
    """A missing CLI-required output path must fail before repository or writer calls."""
    from review_analytics.services.exporting import export_reviews
    from review_analytics.errors import ValidationError

    class UnusedRepository:
        def export_rows(self, review_filter: ReviewFilter):
            raise AssertionError("repository must not be called")

    with pytest.raises(ValidationError) as raised:
        export_reviews(ExportRequest(output_path=None), UnusedRepository())

    assert raised.value.code == "EXPORT_OUTPUT_REQUIRED"

