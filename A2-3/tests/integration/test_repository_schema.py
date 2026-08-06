from __future__ import annotations

import sqlite3

import pytest

from review_analytics.errors import PersistenceError
from review_analytics.models import DuplicatePolicy, Sentiment, SentimentResult
from review_analytics.repositories import AnalysisRepository, ReviewRepository, initialize_database

from .conftest import seed_clean, scalar


def test_initialize_database_is_idempotent_and_creates_documented_tables_and_indexes(database_path):
    """Dropping IF NOT EXISTS or a documented index would break repeated startup or query support."""
    initialize_database(database_path)
    initialize_database(database_path)

    with sqlite3.connect(database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        indexes = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
        }

    assert {"raw_reviews", "clean_reviews", "sentiment_analyses", "insight_extractions"} <= tables
    assert {
        "idx_raw_reviews_clean_status_id",
        "idx_raw_reviews_source_ref",
        "idx_clean_reviews_review_date",
        "idx_clean_reviews_rating",
        "idx_clean_reviews_product_name",
        "idx_sentiment_analyses_sentiment",
        "idx_sentiment_analyses_confidence",
        "idx_insight_extractions_scope_current",
    } <= indexes


def test_schema_enforces_unique_foreign_key_and_check_constraints(database_path, raw_input):
    """Missing DDL constraints would allow contradictory persisted domain state."""
    initialize_database(database_path)
    reviews = ReviewRepository(database_path)
    analyses = AnalysisRepository(database_path)
    saved, clean = seed_clean(reviews, raw_input)

    with sqlite3.connect(database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO raw_reviews (fingerprint, review_text_raw, source_type, source_ref, clean_status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("fingerprint", "duplicate", "csv", "other.csv", "pending", "now", "now"),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE clean_reviews SET rating = 6 WHERE id = ?", (clean.id,))

    with pytest.raises(PersistenceError):
        analyses.save_sentiment_batch(
            (
                SentimentResult(
                    clean_review_id=999_999,
                    sentiment=Sentiment.POSITIVE,
                    confidence=0.8,
                    model_name="fake",
                    prompt_version="v1",
                ),
            )
        )

    assert scalar(database_path, "SELECT id FROM raw_reviews") == saved.review_id


def test_repository_connections_enable_foreign_keys_for_cascade_deletes(database_path, raw_input):
    """Forgetting PRAGMA foreign_keys on a repository connection would leave orphan analyses."""
    initialize_database(database_path)
    reviews = ReviewRepository(database_path)
    analyses = AnalysisRepository(database_path)
    _, clean = seed_clean(reviews, raw_input)
    analyses.save_sentiment_batch(
        (
            SentimentResult(
                clean_review_id=clean.id,
                sentiment=Sentiment.POSITIVE,
                confidence=0.8,
                model_name="fake",
                prompt_version="v1",
            ),
        )
    )

    reviews.save_raw(raw_input, "fingerprint", DuplicatePolicy.UPSERT)

    assert scalar(database_path, "SELECT COUNT(*) FROM clean_reviews") == 0
    assert scalar(database_path, "SELECT COUNT(*) FROM sentiment_analyses") == 0
