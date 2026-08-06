from __future__ import annotations

import sqlite3
import threading
from dataclasses import replace

import pytest

from review_analytics.dto import ReviewFilter
from review_analytics.errors import PersistenceError
from review_analytics.models import (
    AnalysisStatus,
    CleanReview,
    CleanStatus,
    DuplicatePolicy,
    InsightResult,
    KeywordEvidence,
    Sentiment,
    SortField,
    SortOrder,
    TargetMode,
)

from .conftest import scalar, seed_clean, seed_sentiment


def _observe_read_while_write_locked(monkeypatch, database_path, statement_prefix, operation):
    """Return whether a repository SELECT ran before an existing writer released its lock."""
    from review_analytics.repositories import database

    real_connect = sqlite3.connect
    blocker = real_connect(database_path)
    blocker.execute("BEGIN IMMEDIATE")
    connection_opened = threading.Event()
    read_seen = threading.Event()
    failures = []

    def traced_connect(*args, **kwargs):
        connection = real_connect(*args, **kwargs)
        connection.set_trace_callback(
            lambda statement: read_seen.set()
            if statement.strip().upper().startswith(statement_prefix)
            else None
        )
        connection_opened.set()
        return connection

    monkeypatch.setattr(database.sqlite3, "connect", traced_connect)

    def run_operation():
        try:
            operation()
        except Exception as exc:  # pragma: no cover - asserted below with thread handoff
            failures.append(exc)

    worker = threading.Thread(target=run_operation)
    worker.start()
    assert connection_opened.wait(1.0)
    read_while_locked = read_seen.wait(0.2)
    blocker.rollback()
    blocker.close()
    worker.join(2.0)

    assert not worker.is_alive()
    assert failures == []
    return read_while_locked


def _insight():
    return InsightResult(
        positive_keywords=(KeywordEvidence("durable", (1,)),),
        negative_keywords=(),
        summary="summary",
        recommendations=("keep quality",),
        model_name="fake-model",
        prompt_version="v1",
    )


def test_skip_preserves_existing_raw_and_all_derivatives(initialized_repositories, database_path, raw_input):
    """Treating skip like update would silently destroy already-computed derivatives."""
    reviews, analyses = initialized_repositories
    first, clean = seed_clean(reviews, raw_input)
    seed_sentiment(analyses, clean.id)
    analyses.save_insight("{}", "scope", 1, _insight(), "2026-08-06T01:00:00+00:00")

    skipped = reviews.save_raw(replace(raw_input, rating_raw="1"), "fingerprint", DuplicatePolicy.SKIP)

    assert skipped.review_id == first.review_id
    assert skipped.action == "skipped"
    assert scalar(database_path, "SELECT rating_raw FROM raw_reviews WHERE id = ?", (first.review_id,)) == "5"
    assert scalar(database_path, "SELECT COUNT(*) FROM clean_reviews") == 1
    assert scalar(database_path, "SELECT COUNT(*) FROM sentiment_analyses") == 1
    assert scalar(database_path, "SELECT is_stale FROM insight_extractions") == 0


def test_upsert_keeps_raw_id_and_invalidates_all_derivatives(initialized_repositories, database_path, raw_input):
    """Allocating a new ID or retaining derived rows would violate duplicate-upsert semantics."""
    reviews, analyses = initialized_repositories
    first, clean = seed_clean(reviews, raw_input)
    seed_sentiment(analyses, clean.id)
    analyses.save_insight("{}", "scope", 1, _insight(), "2026-08-06T01:00:00+00:00")

    upserted = reviews.save_raw(replace(raw_input, rating_raw="1"), "fingerprint", DuplicatePolicy.UPSERT)

    assert upserted.review_id == first.review_id
    assert upserted.action == "upserted"
    assert scalar(database_path, "SELECT rating_raw FROM raw_reviews") == "1"
    assert scalar(database_path, "SELECT clean_status FROM raw_reviews") == "pending"
    assert scalar(database_path, "SELECT rejection_reason FROM raw_reviews") is None
    assert scalar(database_path, "SELECT COUNT(*) FROM clean_reviews") == 0
    assert scalar(database_path, "SELECT COUNT(*) FROM sentiment_analyses") == 0
    assert scalar(database_path, "SELECT is_stale FROM insight_extractions") == 1


def test_failed_upsert_rolls_back_raw_and_derivative_changes(initialized_repositories, database_path, raw_input):
    """A failure after raw update and clean deletion must roll the whole upsert graph back."""
    reviews, analyses = initialized_repositories
    first, clean = seed_clean(reviews, raw_input)
    seed_sentiment(analyses, clean.id)
    analyses.save_insight("{}", "scope", 1, _insight(), "2026-08-06T01:00:00+00:00")

    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            CREATE TRIGGER fail_insight_stale_update
            BEFORE UPDATE OF is_stale ON insight_extractions
            BEGIN
                SELECT RAISE(ABORT, 'controlled later-statement failure');
            END
            """
        )

    with pytest.raises(PersistenceError):
        reviews.save_raw(replace(raw_input, rating_raw="1"), "fingerprint", DuplicatePolicy.UPSERT)

    assert scalar(database_path, "SELECT rating_raw FROM raw_reviews WHERE id = ?", (first.review_id,)) == "5"
    assert scalar(database_path, "SELECT clean_status FROM raw_reviews") == "cleaned"
    assert scalar(database_path, "SELECT COUNT(*) FROM clean_reviews") == 1
    assert scalar(database_path, "SELECT COUNT(*) FROM sentiment_analyses") == 1
    assert scalar(database_path, "SELECT is_stale FROM insight_extractions") == 0


def test_save_raw_acquires_write_lock_before_duplicate_read(
    initialized_repositories, database_path, raw_input, monkeypatch
):
    """A duplicate read before write-lock acquisition permits two importers to observe stale absence."""
    reviews, _ = initialized_repositories

    read_while_locked = _observe_read_while_write_locked(
        monkeypatch,
        database_path,
        "SELECT ID FROM RAW_REVIEWS WHERE FINGERPRINT",
        lambda: reviews.save_raw(raw_input, "concurrent", DuplicatePolicy.SKIP),
    )

    assert read_while_locked is False


def test_save_clean_acquires_write_lock_before_change_detection_read(
    initialized_repositories, database_path, raw_input, monkeypatch
):
    """A clean-state read before write-lock acquisition can invalidate from a stale comparison."""
    reviews, _ = initialized_repositories
    saved, clean = seed_clean(reviews, raw_input)

    read_while_locked = _observe_read_while_write_locked(
        monkeypatch,
        database_path,
        "SELECT * FROM CLEAN_REVIEWS WHERE RAW_REVIEW_ID",
        lambda: reviews.save_clean(
            saved.review_id,
            replace(clean, id=None, raw_review_id=None, review_text="concurrent clean change"),
        ),
    )

    assert read_while_locked is False


def test_clean_change_and_rejection_invalidate_analysis_and_insights(initialized_repositories, database_path, raw_input):
    """Changing or rejecting clean data without invalidation would expose stale analysis."""
    reviews, analyses = initialized_repositories
    saved, clean = seed_clean(reviews, raw_input)
    seed_sentiment(analyses, clean.id)
    analyses.save_insight("{}", "scope", 1, _insight(), "2026-08-06T01:00:00+00:00")

    unchanged = reviews.save_clean(
        saved.review_id,
        replace(clean, id=None, raw_review_id=None),
    )
    assert unchanged.id == clean.id
    assert scalar(database_path, "SELECT COUNT(*) FROM sentiment_analyses") == 1
    assert scalar(database_path, "SELECT is_stale FROM insight_extractions") == 0

    changed = reviews.save_clean(
        saved.review_id,
        replace(clean, id=None, raw_review_id=None, review_text="changed clean text"),
    )
    assert changed.id == clean.id
    assert scalar(database_path, "SELECT COUNT(*) FROM sentiment_analyses") == 0
    assert scalar(database_path, "SELECT is_stale FROM insight_extractions") == 1

    seed_sentiment(analyses, changed.id)
    analyses.save_insight("{\"next\":true}", "scope-next", 1, _insight(), "2026-08-06T02:00:00+00:00")
    reviews.reject_clean(saved.review_id, "INVALID_RATING")

    assert scalar(database_path, "SELECT clean_status FROM raw_reviews") == "rejected"
    assert scalar(database_path, "SELECT rejection_reason FROM raw_reviews") == "INVALID_RATING"
    assert scalar(database_path, "SELECT COUNT(*) FROM clean_reviews") == 0
    assert scalar(database_path, "SELECT COUNT(*) FROM sentiment_analyses") == 0
    assert scalar(database_path, "SELECT COUNT(*) FROM insight_extractions WHERE is_stale = 0") == 0


def test_select_raw_targets_returns_models_not_sqlite_objects(initialized_repositories, raw_input):
    """Leaking sqlite rows from target selection would violate the repository boundary."""
    reviews, _ = initialized_repositories
    pending = reviews.save_raw(raw_input, "one", DuplicatePolicy.SKIP)
    cleaned, _ = seed_clean(reviews, replace(raw_input, review_text_raw="second"), "two")

    pending_targets = reviews.select_raw_targets(TargetMode.PENDING)
    all_targets = reviews.select_raw_targets(TargetMode.ALL)
    selected = reviews.select_raw_targets(TargetMode.ID, cleaned.review_id)

    assert [item.id for item in pending_targets] == [pending.review_id]
    assert [item.clean_status for item in all_targets] == [CleanStatus.PENDING, CleanStatus.CLEANED]
    assert [item.id for item in selected] == [cleaned.review_id]
    assert not any(isinstance(item, (sqlite3.Row, sqlite3.Connection, sqlite3.Cursor)) for item in all_targets)


def test_list_filters_are_parameterized_and_nullable_sorts_put_unanalyzed_last(
    initialized_repositories, raw_input
):
    """Interpolated filters or DB-default NULL ordering would expose injection and unstable CLI results."""
    reviews, analyses = initialized_repositories
    rows = []
    for index, (rating, product) in enumerate(((4, "A"), (5, "B"), (3, "C"), (2, "%' OR 1=1 --")), 1):
        saved, clean = seed_clean(
            reviews,
            replace(raw_input, review_text_raw=f"review {index}"),
            f"fp-{index}",
            rating_raw=str(rating),
            product_name_raw=product,
        )
        rows.append((saved, clean))
    seed_sentiment(analyses, rows[0][1].id, Sentiment.NEGATIVE, 0.5)
    seed_sentiment(analyses, rows[1][1].id, Sentiment.POSITIVE, 0.5)

    exact = reviews.list_reviews(ReviewFilter(product="%' OR 1=1 --"), 1, 20, SortField.ID, SortOrder.ASC)
    confidence_desc = reviews.list_reviews(ReviewFilter(), 1, 20, SortField.CONFIDENCE, SortOrder.DESC)
    sentiment_asc = reviews.list_reviews(ReviewFilter(), 1, 20, SortField.SENTIMENT, SortOrder.ASC)

    assert exact.total_items == 1
    assert [item.product_name for item in exact.items] == ["%' OR 1=1 --"]
    assert [item.review_id for item in confidence_desc.items] == [rows[0][0].review_id, rows[1][0].review_id, rows[2][0].review_id, rows[3][0].review_id]
    assert [item.analysis_status for item in confidence_desc.items] == [
        AnalysisStatus.ANALYZED,
        AnalysisStatus.ANALYZED,
        AnalysisStatus.UNANALYZED,
        AnalysisStatus.UNANALYZED,
    ]
    assert [item.review_id for item in sentiment_asc.items][-2:] == [rows[2][0].review_id, rows[3][0].review_id]


def test_detail_stats_and_export_rows_are_safe_named_types(initialized_repositories, raw_input):
    """Returning SQL rows from query APIs would couple services to SQLite column layout."""
    reviews, analyses = initialized_repositories
    saved, clean = seed_clean(reviews, raw_input)
    seed_sentiment(analyses, clean.id, Sentiment.POSITIVE, 0.95)

    detail = reviews.get_review_detail(saved.review_id)
    stats = reviews.stats_rows(ReviewFilter(rating_min=4))
    exported = reviews.export_rows(ReviewFilter(sentiment=Sentiment.POSITIVE))

    assert detail.review_id == saved.review_id
    assert detail.clean_status is CleanStatus.CLEANED
    assert detail.analysis_status is AnalysisStatus.ANALYZED
    assert stats[0].review_id == saved.review_id
    assert stats[0].confidence == 0.95
    assert exported[0].review_id == saved.review_id
    assert exported[0].sentiment is Sentiment.POSITIVE
    for value in (detail, *stats, *exported):
        assert not isinstance(value, (sqlite3.Row, sqlite3.Connection, sqlite3.Cursor))
