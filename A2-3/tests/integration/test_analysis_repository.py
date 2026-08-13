from __future__ import annotations

import sqlite3
from dataclasses import replace

import pytest

from review_analytics.errors import PersistenceError
from review_analytics.models import (
    DuplicatePolicy,
    InsightResult,
    KeywordEvidence,
    Sentiment,
    SentimentResult,
    TargetMode,
)

from .conftest import scalar, seed_clean, seed_sentiment


def _insight(summary="summary"):
    return InsightResult(
        positive_keywords=(KeywordEvidence("quality", (1, 2)),),
        negative_keywords=(KeywordEvidence("delay", (2,)),),
        summary=summary,
        recommendations=("improve shipping",),
        model_name="fake-model",
        prompt_version="v1",
    )


def test_analysis_targets_honor_mode_force_id_limit_and_return_named_inputs(initialized_repositories, raw_input):
    """Wrong target predicates could resend analyzed reviews or analyze the wrong clean ID."""
    reviews, analyses = initialized_repositories
    _, clean_one = seed_clean(reviews, raw_input, "one")
    _, clean_two = seed_clean(reviews, replace(raw_input, review_text_raw="second"), "two")
    seed_sentiment(analyses, clean_one.id)

    assert [item.review_id for item in analyses.analysis_targets(TargetMode.UNANALYZED)] == [clean_two.id]
    assert [item.review_id for item in analyses.analysis_targets(TargetMode.ALL)] == [clean_two.id]
    assert [item.review_id for item in analyses.analysis_targets(TargetMode.ALL, force=True)] == [clean_one.id, clean_two.id]
    assert [item.review_id for item in analyses.analysis_targets(TargetMode.ID, clean_one.id, force=True)] == [clean_one.id]
    assert analyses.analysis_targets(TargetMode.ID, clean_one.id, force=False) == ()
    assert len(analyses.analysis_targets(TargetMode.ALL, force=True, limit=1)) == 1
    assert not isinstance(analyses.analysis_targets(TargetMode.ALL, force=True)[0], sqlite3.Row)


def test_sentiment_batch_is_atomic_on_constraint_failure(initialized_repositories, database_path, raw_input):
    """Committing each row separately would leave a partial successful batch after one invalid result."""
    reviews, analyses = initialized_repositories
    _, clean_one = seed_clean(reviews, raw_input, "one")
    _, clean_two = seed_clean(reviews, replace(raw_input, review_text_raw="second"), "two")
    batch = (
        SentimentResult(clean_one.id, Sentiment.POSITIVE, 0.9, "fake", "v1"),
        SentimentResult(clean_two.id, Sentiment.NEGATIVE, 1.5, "fake", "v1"),
    )

    with pytest.raises(PersistenceError):
        analyses.save_sentiment_batch(batch)

    assert scalar(database_path, "SELECT COUNT(*) FROM sentiment_analyses") == 0


def test_sentiment_batch_replaces_existing_analysis_without_changing_identity(
    initialized_repositories, database_path, raw_input
):
    """Force analysis must replace the one current result instead of violating UNIQUE or duplicating it."""
    reviews, analyses = initialized_repositories
    _, clean = seed_clean(reviews, raw_input)
    first = SentimentResult(clean.id, Sentiment.POSITIVE, 0.9, "fake", "v1")
    second = SentimentResult(clean.id, Sentiment.NEGATIVE, 0.7, "fake", "v2")

    assert analyses.save_sentiment_batch((first,)) == 1
    analysis_id = scalar(database_path, "SELECT id FROM sentiment_analyses")
    assert analyses.save_sentiment_batch((second,)) == 1

    assert scalar(database_path, "SELECT COUNT(*) FROM sentiment_analyses") == 1
    assert scalar(database_path, "SELECT id FROM sentiment_analyses") == analysis_id
    assert scalar(database_path, "SELECT sentiment FROM sentiment_analyses") == "negative"


def test_replacing_sentiment_marks_current_insights_stale(
    initialized_repositories, database_path, raw_input
):
    """A report must not reuse insights derived from sentiment results that force analysis replaced."""
    reviews, analyses = initialized_repositories
    _, clean = seed_clean(reviews, raw_input)
    analyses.save_sentiment_batch(
        (SentimentResult(clean.id, Sentiment.POSITIVE, 0.9, "fake", "v1"),)
    )
    insight_id = analyses.save_insight("{}", "scope", 1, _insight())

    analyses.save_sentiment_batch(
        (SentimentResult(clean.id, Sentiment.NEGATIVE, 0.8, "fake", "v2"),)
    )

    assert scalar(
        database_path,
        "SELECT is_stale FROM insight_extractions WHERE id = ?",
        (insight_id,),
    ) == 1


def test_latest_valid_insight_round_trips_json_as_immutable_models(initialized_repositories):
    """Returning stale/old JSON blobs or mutable dicts would violate exact-scope and safe mapping contracts."""
    _, analyses = initialized_repositories
    old_id = analyses.save_insight("{\"product\":\"A\"}", "scope", 2, _insight("old"), "2026-08-06T01:00:00+00:00")
    new_id = analyses.save_insight("{\"product\":\"A\"}", "scope", 2, _insight("new"), "2026-08-06T02:00:00+00:00")
    analyses.save_insight("{}", "other", 1, _insight("other"), "2026-08-06T03:00:00+00:00")

    current = analyses.latest_valid_insight("scope")

    assert current.id == new_id
    assert current.id != old_id
    assert current.scope_json == "{\"product\":\"A\"}"
    assert current.review_count == 2
    assert current.result.summary == "new"
    assert current.result.positive_keywords == (KeywordEvidence("quality", (1, 2)),)
    assert analyses.latest_valid_insight("missing") is None
    assert not isinstance(current, (sqlite3.Row, sqlite3.Connection, sqlite3.Cursor))


@pytest.mark.parametrize(
    ("column", "malformed_json"),
    (
        ("recommendations_json", '"12"'),
        ("recommendations_json", "[1]"),
        ("positive_keywords_json", '[{"keyword":7,"review_ids":[1]}]'),
        ("positive_keywords_json", '[{"keyword":"quality","review_ids":"12"}]'),
        ("positive_keywords_json", '[{"keyword":"quality","review_ids":[true]}]'),
    ),
)
def test_latest_valid_insight_rejects_malformed_json_shapes_and_exact_scalar_types(
    initialized_repositories, database_path, column, malformed_json
):
    """Coercing malformed persisted JSON would create a valid-looking but false domain model."""
    _, analyses = initialized_repositories
    insight_id = analyses.save_insight("{}", "scope", 2, _insight(), "2026-08-06T01:00:00+00:00")
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            f"UPDATE insight_extractions SET {column} = ? WHERE id = ?",
            (malformed_json, insight_id),
        )

    with pytest.raises(PersistenceError) as error:
        analyses.latest_valid_insight("scope")

    assert error.value.code == "INSIGHT_QUERY_FAILED"


def test_upsert_marks_all_scopes_stale_and_latest_valid_excludes_them(
    initialized_repositories, raw_input
):
    """A stale extraction must never satisfy a later dashboard lookup."""
    reviews, analyses = initialized_repositories
    reviews.save_raw(raw_input, "fingerprint", DuplicatePolicy.SKIP)
    analyses.save_insight("{}", "scope", 1, _insight(), "2026-08-06T01:00:00+00:00")

    reviews.save_raw(raw_input, "fingerprint", DuplicatePolicy.UPSERT)

    assert analyses.latest_valid_insight("scope") is None
