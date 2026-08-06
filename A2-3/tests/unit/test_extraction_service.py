from __future__ import annotations

import json
import logging

import pytest

from review_analytics.dto import ExportRow, ExtractRequest, ReviewFilter
from review_analytics.errors import AIServiceError, NotFoundError
from review_analytics.models import InsightResult, KeywordEvidence, Sentiment


def _row(review_id: int, text: str, sentiment: Sentiment | None = None) -> ExportRow:
    return ExportRow(review_id, text, 5, "2026-08-01", "Bottle", sentiment, 0.9 if sentiment else None, None)


class ReviewRepositoryFake:
    def __init__(self, rows):
        self.rows = tuple(rows)
        self.filter = None

    def export_rows(self, review_filter):
        self.filter = review_filter
        return self.rows


class InsightRepositoryFake:
    def __init__(self):
        self.saved = None

    def save_insight(self, scope_json, scope_hash, review_count, result, created_at=None):
        self.saved = (scope_json, scope_hash, review_count, result)
        return 7


class InsightClientFake:
    def __init__(self):
        self.extract_calls = []
        self.merge_calls = []

    def extract(self, insight_input):
        self.extract_calls.append(insight_input)
        ids = tuple(item.review_id for item in insight_input.reviews)
        return InsightResult(
            (KeywordEvidence("Quality", ids + (999, ids[0])),),
            (KeywordEvidence("delay", ids),),
            f"chunk {len(self.extract_calls)}",
            ("improve",),
            "fake",
            "insight-v1",
        )

    def merge_insights(self, parts):
        self.merge_calls.append(tuple(parts))
        return InsightResult(
            (KeywordEvidence("quality", (1, 2, 999, 2)), KeywordEvidence("QUALITY", (3,))),
            (KeywordEvidence("delay", (2, 2)),),
            "merged",
            ("improve",),
            "fake",
            "insight-merge-v1",
        )


def test_extract_with_no_targets_skips_client_and_persistence():
    """No matching reviews is a user-correctable failure, not an empty AI request."""
    from review_analytics.services.extraction import extract_insights

    with pytest.raises(NotFoundError) as raised:
        extract_insights(
            ExtractRequest(),
            ReviewRepositoryFake(()),
            InsightRepositoryFake(),
            InsightClientFake(),
            chunk_characters=100,
            retry_count=0,
        )

    assert raised.value.code == "NO_REVIEWS_FOR_EXTRACTION"


def test_extract_chunks_by_character_count_merges_and_sanitizes_evidence():
    """Oversized requests and unverified duplicate evidence IDs would corrupt TOP-N counts."""
    from review_analytics.services.extraction import extract_insights

    reviews = ReviewRepositoryFake((_row(1, "aaaa"), _row(2, "bbbb"), _row(3, "cccc")))
    insights = InsightRepositoryFake()
    client = InsightClientFake()

    summary = extract_insights(
        ExtractRequest(filter=ReviewFilter(product="Bottle")),
        reviews,
        insights,
        client,
        chunk_characters=5,
        retry_count=0,
    )

    assert [len(call.reviews) for call in client.extract_calls] == [1, 1, 1]
    assert len(client.merge_calls) == 1
    scope_json, scope_hash, review_count, result = insights.saved
    assert json.loads(scope_json)["product"] == "Bottle"
    assert len(scope_hash) == 64 and review_count == 3
    assert result.positive_keywords == (KeywordEvidence("quality", (1, 2, 3)),)
    assert result.negative_keywords == (KeywordEvidence("delay", (2,)),)
    assert (summary.processed, summary.succeeded, summary.failed) == (3, 3, 0)


def test_extraction_scope_is_canonical_and_limit_changes_identity():
    """Equivalent filters need one stable scope while limited extracts must not satisfy full dashboards."""
    from review_analytics.services.extraction import extraction_scope

    review_filter = ReviewFilter(sentiment=Sentiment.NEGATIVE, product="Bottle", date_from="2026-08-01")
    first_json, first_hash = extraction_scope(review_filter, None)
    second_json, second_hash = extraction_scope(review_filter, None)
    limited_json, limited_hash = extraction_scope(review_filter, 10)

    assert (first_json, first_hash) == (second_json, second_hash)
    assert json.loads(first_json)["limit"] is None
    assert json.loads(limited_json)["limit"] == 10
    assert first_hash != limited_hash


def test_extract_retries_temporary_client_failure_before_saving(caplog):
    """A transient extraction failure must retry without persisting an incomplete insight."""
    from review_analytics.services.extraction import extract_insights

    class RetryClient(InsightClientFake):
        def __init__(self):
            super().__init__()
            self.attempts = 0

        def extract(self, insight_input):
            self.attempts += 1
            if self.attempts == 1:
                raise AIServiceError("temporary", "AI_REQUEST_FAILED")
            return super().extract(insight_input)

    client = RetryClient()
    insights = InsightRepositoryFake()
    delays = []

    with caplog.at_level(logging.WARNING):
        extract_insights(
            ExtractRequest(),
            ReviewRepositoryFake((_row(1, "private review body"),)),
            insights,
            client,
            100,
            1,
            sleep=delays.append,
        )

    assert client.attempts == 2
    assert delays == [1.0]
    assert insights.saved is not None
    assert "event=ai.retry operation=extract attempt=1 error_code=AI_REQUEST_FAILED" in caplog.text
    assert "private review body" not in caplog.text
