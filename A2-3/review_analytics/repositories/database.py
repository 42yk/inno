"""데이터베이스 연결을 구성하고 SQLite 스키마를 멱등으로 초기화한다."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from review_analytics.errors import PersistenceError


_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_reviews (
    id INTEGER PRIMARY KEY,
    fingerprint TEXT NOT NULL UNIQUE,
    review_text_raw TEXT NOT NULL,
    rating_raw TEXT,
    review_date_raw TEXT,
    product_name_raw TEXT,
    source_type TEXT NOT NULL CHECK (source_type IN ('csv', 'xlsx')),
    source_ref TEXT NOT NULL,
    source_row INTEGER,
    clean_status TEXT NOT NULL CHECK (clean_status IN ('pending', 'cleaned', 'rejected')),
    rejection_reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_raw_reviews_clean_status_id
    ON raw_reviews(clean_status, id);
CREATE INDEX IF NOT EXISTS idx_raw_reviews_source_ref
    ON raw_reviews(source_ref);

CREATE TABLE IF NOT EXISTS clean_reviews (
    id INTEGER PRIMARY KEY,
    raw_review_id INTEGER NOT NULL UNIQUE REFERENCES raw_reviews(id) ON DELETE CASCADE,
    review_text TEXT NOT NULL,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    review_date TEXT,
    product_name TEXT,
    cleaning_version TEXT NOT NULL,
    cleaned_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_clean_reviews_review_date
    ON clean_reviews(review_date);
CREATE INDEX IF NOT EXISTS idx_clean_reviews_rating
    ON clean_reviews(rating);
CREATE INDEX IF NOT EXISTS idx_clean_reviews_product_name
    ON clean_reviews(product_name);

CREATE TABLE IF NOT EXISTS sentiment_analyses (
    id INTEGER PRIMARY KEY,
    clean_review_id INTEGER NOT NULL UNIQUE REFERENCES clean_reviews(id) ON DELETE CASCADE,
    sentiment TEXT NOT NULL CHECK (sentiment IN ('positive', 'negative', 'neutral')),
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    analyzed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sentiment_analyses_sentiment
    ON sentiment_analyses(sentiment);
CREATE INDEX IF NOT EXISTS idx_sentiment_analyses_confidence
    ON sentiment_analyses(confidence);

CREATE TABLE IF NOT EXISTS insight_extractions (
    id INTEGER PRIMARY KEY,
    scope_json TEXT NOT NULL,
    scope_hash TEXT NOT NULL,
    review_count INTEGER NOT NULL CHECK (review_count >= 0),
    positive_keywords_json TEXT NOT NULL,
    negative_keywords_json TEXT NOT NULL,
    summary TEXT NOT NULL,
    recommendations_json TEXT NOT NULL,
    model_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    is_stale INTEGER NOT NULL DEFAULT 0 CHECK (is_stale IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_insight_extractions_scope_current
    ON insight_extractions(scope_hash, is_stale, created_at DESC);
"""


# 외래 키가 활성화된 SQLite 연결을 열고 사용 후 닫는다.
@contextmanager
def _connection(database_path: str | Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(database_path)
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        yield connection
    finally:
        connection.close()


# 읽기-수정-쓰기 전에 SQLite 쓰기 예약을 획득한다.
def _begin_write(connection: sqlite3.Connection) -> None:
    """Acquire the SQLite write reservation before a read-modify-write sequence."""
    connection.execute("BEGIN IMMEDIATE")


# 문서화된 SQLite 스키마와 인덱스를 멱등으로 초기화한다.
def initialize_database(database_path: str | Path) -> None:
    """Create the documented schema without exposing the initializing connection."""
    try:
        with _connection(database_path) as connection:
            with connection:
                connection.executescript(_SCHEMA)
    except sqlite3.Error as exc:
        raise PersistenceError("데이터베이스 스키마를 초기화하지 못했습니다.", "DATABASE_INIT_FAILED") from exc
