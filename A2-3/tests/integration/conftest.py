from __future__ import annotations

import sqlite3
from dataclasses import replace

import pytest

from review_analytics.models import CleanReview, RawReviewInput, Sentiment, SentimentResult


@pytest.fixture
def database_path(tmp_path):
    return tmp_path / "reviews.sqlite3"


@pytest.fixture
def raw_input():
    return RawReviewInput(
        review_text_raw="  Excellent bottle  ",
        rating_raw="5",
        review_date_raw="2026-08-01",
        product_name_raw="Bottle",
        source_type="csv",
        source_ref="reviews.csv",
        source_row=2,
    )


@pytest.fixture
def initialized_repositories(database_path):
    from review_analytics.repositories import AnalysisRepository, ReviewRepository, initialize_database

    initialize_database(database_path)
    return ReviewRepository(database_path), AnalysisRepository(database_path)


def seed_clean(reviews, raw_input, fingerprint="fingerprint", **changes):
    from review_analytics.models import DuplicatePolicy

    saved = reviews.save_raw(replace(raw_input, **changes), fingerprint, DuplicatePolicy.SKIP)
    clean = reviews.save_clean(
        saved.review_id,
        CleanReview(
            review_text=f"clean {saved.review_id}",
            rating=int(changes.get("rating_raw", raw_input.rating_raw)),
            review_date=changes.get("review_date_raw", raw_input.review_date_raw),
            product_name=changes.get("product_name_raw", raw_input.product_name_raw),
            cleaning_version="v1",
            cleaned_at="2026-08-06T00:00:00+00:00",
        ),
    )
    return saved, clean


def seed_sentiment(analyses, clean_review_id, sentiment=Sentiment.POSITIVE, confidence=0.9):
    analyses.save_sentiment_batch(
        (
            SentimentResult(
                clean_review_id=clean_review_id,
                sentiment=sentiment,
                confidence=confidence,
                model_name="fake-model",
                prompt_version="v1",
                analyzed_at="2026-08-06T00:01:00+00:00",
            ),
        )
    )


def scalar(database_path, sql, parameters=()):
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(sql, parameters).fetchone()
    return None if row is None else row[0]
