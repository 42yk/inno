"""원본·정제 리뷰 저장과 조회용 SQLite 작업을 담당한다."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from review_analytics.dto import (
    ExportRow,
    RawSaveResult,
    ReviewDetailResult,
    ReviewFilter,
    ReviewListResult,
    ReviewSummary,
    StatsRow,
)
from review_analytics.errors import PersistenceError
from review_analytics.models import (
    AnalysisStatus,
    CleanReview,
    CleanStatus,
    DuplicatePolicy,
    RawReview,
    RawReviewInput,
    RawSaveAction,
    Sentiment,
    SortField,
    SortOrder,
    TargetMode,
)
from review_analytics.repositories.database import _begin_write, _connection


_SORT_COLUMNS = {
    SortField.ID: "r.id",
    SortField.REVIEW_DATE: "c.review_date",
    SortField.RATING: "c.rating",
    SortField.SENTIMENT: "a.sentiment",
    SortField.CONFIDENCE: "a.confidence",
}


class ReviewRepository:
    # 원본·정제 리뷰를 조회할 SQLite 경로를 보관한다.
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = database_path

    # 중복 정책에 따라 원본 리뷰를 삽입·스킵·갱신한다.
    def save_raw(
        self,
        raw: RawReviewInput,
        fingerprint: str,
        duplicate_policy: DuplicatePolicy,
    ) -> RawSaveResult:
        now = _utc_now()
        try:
            with _connection(self._database_path) as connection:
                with connection:
                    _begin_write(connection)
                    existing = connection.execute(
                        "SELECT id FROM raw_reviews WHERE fingerprint = ?",
                        (fingerprint,),
                    ).fetchone()
                    if existing is None:
                        cursor = connection.execute(
                            """
                            INSERT INTO raw_reviews (
                                fingerprint, review_text_raw, rating_raw, review_date_raw,
                                product_name_raw, source_type, source_ref, source_row,
                                clean_status, rejection_reason, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', NULL, ?, ?)
                            """,
                            (
                                fingerprint,
                                _required_text(raw.review_text_raw),
                                _optional_text(raw.rating_raw),
                                _optional_text(raw.review_date_raw),
                                _optional_text(raw.product_name_raw),
                                raw.source_type,
                                raw.source_ref,
                                raw.source_row,
                                now,
                                now,
                            ),
                        )
                        return RawSaveResult(int(cursor.lastrowid), RawSaveAction.INSERTED)

                    review_id = int(existing["id"])
                    if duplicate_policy is DuplicatePolicy.SKIP:
                        return RawSaveResult(review_id, RawSaveAction.SKIPPED)

                    connection.execute(
                        """
                        UPDATE raw_reviews
                        SET review_text_raw = ?, rating_raw = ?, review_date_raw = ?,
                            product_name_raw = ?, source_type = ?, source_ref = ?, source_row = ?,
                            clean_status = 'pending', rejection_reason = NULL, updated_at = ?
                        WHERE id = ?
                        """,
                        (
                            _required_text(raw.review_text_raw),
                            _optional_text(raw.rating_raw),
                            _optional_text(raw.review_date_raw),
                            _optional_text(raw.product_name_raw),
                            raw.source_type,
                            raw.source_ref,
                            raw.source_row,
                            now,
                            review_id,
                        ),
                    )
                    connection.execute("DELETE FROM clean_reviews WHERE raw_review_id = ?", (review_id,))
                    connection.execute("UPDATE insight_extractions SET is_stale = 1 WHERE is_stale = 0")
                    return RawSaveResult(review_id, RawSaveAction.UPSERTED)
        except sqlite3.Error as exc:
            raise PersistenceError("원본 리뷰를 저장하지 못했습니다.", "RAW_SAVE_FAILED") from exc

    # 대상 모드에 맞는 원본 정제 대상 리뷰를 ID 순으로 조회한다.
    def select_raw_targets(
        self,
        target_mode: TargetMode,
        review_id: int | None = None,
    ) -> tuple[RawReview, ...]:
        where = ""
        parameters: tuple[object, ...] = ()
        if target_mode is TargetMode.PENDING:
            where = "WHERE clean_status = ?"
            parameters = (CleanStatus.PENDING.value,)
        elif target_mode is TargetMode.ID:
            where = "WHERE id = ?"
            parameters = (review_id,)
        try:
            with _connection(self._database_path) as connection:
                rows = connection.execute(
                    f"SELECT * FROM raw_reviews {where} ORDER BY id ASC",  # noqa: S608 - fixed fragments only
                    parameters,
                ).fetchall()
            return tuple(_raw_review(row) for row in rows)
        except sqlite3.Error as exc:
            raise PersistenceError("정제 대상 리뷰를 조회하지 못했습니다.", "RAW_TARGET_QUERY_FAILED") from exc

    # 정제 리뷰를 저장하고 변경된 파생 분석과 인사이트를 무효화한다.
    def save_clean(self, raw_review_id: int, clean: CleanReview) -> CleanReview:
        cleaned_at = clean.cleaned_at or _utc_now()
        try:
            with _connection(self._database_path) as connection:
                with connection:
                    _begin_write(connection)
                    existing = connection.execute(
                        "SELECT * FROM clean_reviews WHERE raw_review_id = ?",
                        (raw_review_id,),
                    ).fetchone()
                    changed = existing is None or _clean_values(existing) != (
                        clean.review_text,
                        clean.rating,
                        clean.review_date,
                        clean.product_name,
                        clean.cleaning_version,
                    )
                    connection.execute(
                        """
                        INSERT INTO clean_reviews (
                            raw_review_id, review_text, rating, review_date, product_name,
                            cleaning_version, cleaned_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(raw_review_id) DO UPDATE SET
                            review_text = excluded.review_text,
                            rating = excluded.rating,
                            review_date = excluded.review_date,
                            product_name = excluded.product_name,
                            cleaning_version = excluded.cleaning_version,
                            cleaned_at = excluded.cleaned_at
                        """,
                        (
                            raw_review_id,
                            clean.review_text,
                            clean.rating,
                            clean.review_date,
                            clean.product_name,
                            clean.cleaning_version,
                            cleaned_at,
                        ),
                    )
                    connection.execute(
                        "UPDATE raw_reviews SET clean_status = 'cleaned', rejection_reason = NULL, updated_at = ? WHERE id = ?",
                        (_utc_now(), raw_review_id),
                    )
                    if changed:
                        if existing is not None:
                            connection.execute(
                                "DELETE FROM sentiment_analyses WHERE clean_review_id = ?",
                                (int(existing["id"]),),
                            )
                        connection.execute("UPDATE insight_extractions SET is_stale = 1 WHERE is_stale = 0")
                    saved = connection.execute(
                        "SELECT * FROM clean_reviews WHERE raw_review_id = ?",
                        (raw_review_id,),
                    ).fetchone()
            return _clean_review(saved)
        except sqlite3.Error as exc:
            raise PersistenceError("정제 리뷰를 저장하지 못했습니다.", "CLEAN_SAVE_FAILED") from exc

    # 정제 실패 리뷰를 거절 상태로 저장하고 기존 파생 데이터를 무효화한다.
    def reject_clean(self, raw_review_id: int, rejection_reason: str) -> None:
        try:
            with _connection(self._database_path) as connection:
                with connection:
                    connection.execute("DELETE FROM clean_reviews WHERE raw_review_id = ?", (raw_review_id,))
                    connection.execute(
                        "UPDATE raw_reviews SET clean_status = 'rejected', rejection_reason = ?, updated_at = ? WHERE id = ?",
                        (rejection_reason, _utc_now(), raw_review_id),
                    )
                    connection.execute("UPDATE insight_extractions SET is_stale = 1 WHERE is_stale = 0")
        except sqlite3.Error as exc:
            raise PersistenceError("리뷰 정제 거절 상태를 저장하지 못했습니다.", "CLEAN_REJECT_FAILED") from exc

    # 필터·정렬·페이지 조건에 맞는 리뷰 요약 목록을 조회한다.
    def list_reviews(
        self,
        review_filter: ReviewFilter,
        page: int,
        size: int,
        sort_by: SortField,
        order: SortOrder,
    ) -> ReviewListResult:
        where, parameters = _filter_sql(review_filter)
        column = _SORT_COLUMNS[sort_by]
        direction = "ASC" if order is SortOrder.ASC else "DESC"
        nullable_prefix = ""
        if sort_by in (SortField.SENTIMENT, SortField.CONFIDENCE):
            nullable_prefix = "CASE WHEN a.id IS NULL THEN 1 ELSE 0 END ASC, "
        order_sql = f"{nullable_prefix}{column} {direction}, r.id ASC"
        offset = (page - 1) * size
        try:
            with _connection(self._database_path) as connection:
                total = int(
                    connection.execute(
                        f"SELECT COUNT(*) {_query_from()} {where}",  # noqa: S608 - generated placeholders only
                        parameters,
                    ).fetchone()[0]
                )
                rows = connection.execute(
                    f"SELECT {_query_columns()} {_query_from()} {where} ORDER BY {order_sql} LIMIT ? OFFSET ?",  # noqa: S608
                    (*parameters, size, offset),
                ).fetchall()
            items = tuple(_review_summary(row) for row in rows)
            total_pages = (total + size - 1) // size if total else 0
            return ReviewListResult(items, total, page, size, total_pages)
        except (KeyError, sqlite3.Error) as exc:
            raise PersistenceError("리뷰 목록을 조회하지 못했습니다.", "REVIEW_LIST_FAILED") from exc

    # 원본·정제·감정 정보를 결합한 리뷰 한 건의 상세를 조회한다.
    def get_review_detail(self, review_id: int) -> ReviewDetailResult | None:
        try:
            with _connection(self._database_path) as connection:
                row = connection.execute(
                    """
                    SELECT r.*, c.id AS clean_id, c.review_text, c.rating, c.review_date,
                           c.product_name, c.cleaning_version, c.cleaned_at,
                           a.sentiment, a.confidence, a.model_name, a.analyzed_at
                    FROM raw_reviews r
                    LEFT JOIN clean_reviews c ON c.raw_review_id = r.id
                    LEFT JOIN sentiment_analyses a ON a.clean_review_id = c.id
                    WHERE r.id = ?
                    """,
                    (review_id,),
                ).fetchone()
            if row is None:
                return None
            clean = None
            if row["clean_id"] is not None:
                clean = CleanReview(
                    id=int(row["clean_id"]),
                    raw_review_id=int(row["id"]),
                    review_text=str(row["review_text"]),
                    rating=row["rating"],
                    review_date=row["review_date"],
                    product_name=row["product_name"],
                    cleaning_version=str(row["cleaning_version"]),
                    cleaned_at=str(row["cleaned_at"]),
                )
            sentiment = Sentiment(row["sentiment"]) if row["sentiment"] is not None else None
            return ReviewDetailResult(
                review_id=int(row["id"]),
                review_text_raw=str(row["review_text_raw"]),
                clean_review=clean,
                clean_status=CleanStatus(row["clean_status"]),
                rejection_reason=row["rejection_reason"],
                analysis_status=AnalysisStatus.ANALYZED if sentiment is not None else AnalysisStatus.UNANALYZED,
                sentiment=sentiment,
                confidence=row["confidence"],
                model_name=row["model_name"],
                analyzed_at=row["analyzed_at"],
            )
        except sqlite3.Error as exc:
            raise PersistenceError("리뷰 상세를 조회하지 못했습니다.", "REVIEW_DETAIL_FAILED") from exc

    # 통계 계산에 필요한 별점과 감정 결과 행을 필터링해 조회한다.
    def stats_rows(self, review_filter: ReviewFilter) -> tuple[StatsRow, ...]:
        where, parameters = _filter_sql(review_filter)
        try:
            with _connection(self._database_path) as connection:
                rows = connection.execute(
                    f"SELECT r.id, c.rating, a.sentiment, a.confidence {_query_from()} {where} ORDER BY r.id ASC",  # noqa: S608
                    parameters,
                ).fetchall()
            return tuple(
                StatsRow(
                    review_id=int(row["id"]),
                    rating=row["rating"],
                    sentiment=Sentiment(row["sentiment"]) if row["sentiment"] is not None else None,
                    confidence=row["confidence"],
                )
                for row in rows
            )
        except sqlite3.Error as exc:
            raise PersistenceError("통계 대상 리뷰를 조회하지 못했습니다.", "STATS_QUERY_FAILED") from exc

    # 외부 파일로 내보낼 정제 리뷰와 감정 결과 행을 조회한다.
    def export_rows(self, review_filter: ReviewFilter) -> tuple[ExportRow, ...]:
        where, parameters = _filter_sql(review_filter)
        try:
            with _connection(self._database_path) as connection:
                rows = connection.execute(
                    f"SELECT {_query_columns()}, a.analyzed_at {_query_from()} {where} ORDER BY r.id ASC",  # noqa: S608
                    parameters,
                ).fetchall()
            return tuple(
                ExportRow(
                    review_id=int(row["id"]),
                    review_text=str(row["review_text"]),
                    rating=row["rating"],
                    review_date=row["review_date"],
                    product_name=row["product_name"],
                    sentiment=Sentiment(row["sentiment"]) if row["sentiment"] is not None else None,
                    confidence=row["confidence"],
                    analyzed_at=row["analyzed_at"],
                )
                for row in rows
            )
        except sqlite3.Error as exc:
            raise PersistenceError("내보내기 대상 리뷰를 조회하지 못했습니다.", "EXPORT_QUERY_FAILED") from exc


# 목록과 내보내기 SELECT에서 공유하는 허용 열 목록을 만든다.
def _query_columns() -> str:
    return (
        "r.id, c.review_text, c.rating, c.review_date, c.product_name, "
        "a.sentiment, a.confidence"
    )


# 정제 리뷰를 원본·감정 결과와 결합하는 고정 JOIN 절을 만든다.
def _query_from() -> str:
    return (
        "FROM clean_reviews c "
        "JOIN raw_reviews r ON r.id = c.raw_review_id "
        "LEFT JOIN sentiment_analyses a ON a.clean_review_id = c.id"
    )


# 리뷰 필터를 매개변수화된 WHERE 절과 값 튜플로 변환한다.
def _filter_sql(review_filter: ReviewFilter) -> tuple[str, tuple[object, ...]]:
    clauses: list[str] = []
    parameters: list[object] = []
    if review_filter.sentiment is not None:
        clauses.append("a.sentiment = ?")
        parameters.append(review_filter.sentiment.value)
    if review_filter.rating is not None:
        clauses.append("c.rating = ?")
        parameters.append(review_filter.rating)
    if review_filter.rating_min is not None:
        clauses.append("c.rating >= ?")
        parameters.append(review_filter.rating_min)
    if review_filter.date_from is not None:
        clauses.append("c.review_date >= ?")
        parameters.append(review_filter.date_from)
    if review_filter.date_to is not None:
        clauses.append("c.review_date <= ?")
        parameters.append(review_filter.date_to)
    if review_filter.product is not None:
        clauses.append("c.product_name = ?")
        parameters.append(review_filter.product)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    return where, tuple(parameters)


# SQLite 조회 행을 CLI용 리뷰 요약 DTO로 변환한다.
def _review_summary(row: sqlite3.Row) -> ReviewSummary:
    sentiment = Sentiment(row["sentiment"]) if row["sentiment"] is not None else None
    return ReviewSummary(
        review_id=int(row["id"]),
        review_text=str(row["review_text"]),
        rating=row["rating"],
        review_date=row["review_date"],
        product_name=row["product_name"],
        analysis_status=AnalysisStatus.ANALYZED if sentiment is not None else AnalysisStatus.UNANALYZED,
        sentiment=sentiment,
        confidence=row["confidence"],
    )


# SQLite 조회 행을 원본 리뷰 내부 모델로 변환한다.
def _raw_review(row: sqlite3.Row) -> RawReview:
    return RawReview(
        id=int(row["id"]),
        fingerprint=str(row["fingerprint"]),
        review_text_raw=str(row["review_text_raw"]),
        rating_raw=row["rating_raw"],
        review_date_raw=row["review_date_raw"],
        product_name_raw=row["product_name_raw"],
        source_type=str(row["source_type"]),
        source_ref=str(row["source_ref"]),
        source_row=row["source_row"],
        clean_status=CleanStatus(row["clean_status"]),
        rejection_reason=row["rejection_reason"],
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


# 저장된 정제 필드만 비교 가능한 값 튜플로 추출한다.
def _clean_values(row: sqlite3.Row) -> tuple[object, ...]:
    return (
        row["review_text"],
        row["rating"],
        row["review_date"],
        row["product_name"],
        row["cleaning_version"],
    )


# SQLite 조회 행을 정제 리뷰 내부 모델로 변환한다.
def _clean_review(row: sqlite3.Row) -> CleanReview:
    return CleanReview(
        id=int(row["id"]),
        raw_review_id=int(row["raw_review_id"]),
        review_text=str(row["review_text"]),
        rating=row["rating"],
        review_date=row["review_date"],
        product_name=row["product_name"],
        cleaning_version=str(row["cleaning_version"]),
        cleaned_at=str(row["cleaned_at"]),
    )


# 필수 원본 값을 손실 없는 문자열로 바꾼다.
def _required_text(value: object) -> str:
    return "" if value is None else str(value)


# 선택 원본 값을 None 또는 문자열로 바꾼다.
def _optional_text(value: object | None) -> str | None:
    return None if value is None else str(value)


# 저장·갱신 시각으로 사용할 UTC ISO 문자열을 만든다.
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
