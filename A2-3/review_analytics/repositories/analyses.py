"""감정 분석과 인사이트의 SQLite 작업을 담당한다."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from review_analytics.errors import PersistenceError
from review_analytics.models import (
    AnalysisInput,
    InsightResult,
    KeywordEvidence,
    SentimentResult,
    StoredInsight,
    TargetMode,
)
from review_analytics.repositories.database import _connection


class AnalysisRepository:
    # 감정·인사이트 데이터를 조회할 SQLite 경로를 보관한다.
    def __init__(self, database_path: str | Path) -> None:
        self._database_path = database_path

    # 대상 모드와 분석 상태에 맞는 감정 분석 입력을 조회한다.
    def analysis_targets(
        self,
        target_mode: TargetMode,
        review_id: int | None = None,
        limit: int | None = None,
        force: bool = False,
    ) -> tuple[AnalysisInput, ...]:
        clauses: list[str] = []
        parameters: list[object] = []
        if target_mode is TargetMode.ID:
            clauses.append("c.id = ?")
            parameters.append(review_id)
        if not force:
            clauses.append("a.id IS NULL")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        limit_sql = ""
        if limit is not None:
            limit_sql = "LIMIT ?"
            parameters.append(limit)
        try:
            with _connection(self._database_path) as connection:
                rows = connection.execute(
                    f"""
                    SELECT c.id, c.review_text
                    FROM clean_reviews c
                    LEFT JOIN sentiment_analyses a ON a.clean_review_id = c.id
                    {where}
                    ORDER BY c.id ASC
                    {limit_sql}
                    """,  # noqa: S608 - fixed clauses and placeholders only
                    tuple(parameters),
                ).fetchall()
            return tuple(AnalysisInput(int(row["id"]), str(row["review_text"])) for row in rows)
        except sqlite3.Error as exc:
            raise PersistenceError("감정 분석 대상을 조회하지 못했습니다.", "ANALYSIS_TARGET_QUERY_FAILED") from exc

    # 감정 분석 결과 배치를 하나의 트랜잭션으로 삽입하거나 갱신한다.
    def save_sentiment_batch(self, results: tuple[SentimentResult, ...]) -> int:
        try:
            with _connection(self._database_path) as connection:
                with connection:
                    for result in results:
                        connection.execute(
                            """
                            INSERT INTO sentiment_analyses (
                                clean_review_id, sentiment, confidence, model_name,
                                prompt_version, analyzed_at
                            ) VALUES (?, ?, ?, ?, ?, ?)
                            ON CONFLICT(clean_review_id) DO UPDATE SET
                                sentiment = excluded.sentiment,
                                confidence = excluded.confidence,
                                model_name = excluded.model_name,
                                prompt_version = excluded.prompt_version,
                                analyzed_at = excluded.analyzed_at
                            """,
                            (
                                result.clean_review_id,
                                result.sentiment.value,
                                result.confidence,
                                result.model_name,
                                result.prompt_version,
                                result.analyzed_at or _utc_now(),
                            ),
                        )
            return len(results)
        except sqlite3.Error as exc:
            raise PersistenceError("감정 분석 배치를 저장하지 못했습니다.", "SENTIMENT_BATCH_SAVE_FAILED") from exc

    # 필터 범위와 AI 인사이트를 새 추출 이력으로 저장한다.
    def save_insight(
        self,
        scope_json: str,
        scope_hash: str,
        review_count: int,
        result: InsightResult,
        created_at: str | None = None,
    ) -> int:
        try:
            with _connection(self._database_path) as connection:
                with connection:
                    cursor = connection.execute(
                        """
                        INSERT INTO insight_extractions (
                            scope_json, scope_hash, review_count,
                            positive_keywords_json, negative_keywords_json,
                            summary, recommendations_json, model_name,
                            prompt_version, is_stale, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                        """,
                        (
                            scope_json,
                            scope_hash,
                            review_count,
                            _keyword_json(result.positive_keywords),
                            _keyword_json(result.negative_keywords),
                            result.summary,
                            json.dumps(result.recommendations, ensure_ascii=False, separators=(",", ":")),
                            result.model_name,
                            result.prompt_version,
                            created_at or _utc_now(),
                        ),
                    )
                    return int(cursor.lastrowid)
        except sqlite3.Error as exc:
            raise PersistenceError("인사이트를 저장하지 못했습니다.", "INSIGHT_SAVE_FAILED") from exc

    # 범위 해시에 맞는 가장 최근의 유효 인사이트를 복원한다.
    def latest_valid_insight(self, scope_hash: str) -> StoredInsight | None:
        try:
            with _connection(self._database_path) as connection:
                row = connection.execute(
                    """
                    SELECT * FROM insight_extractions
                    WHERE scope_hash = ? AND is_stale = 0
                    ORDER BY created_at DESC, id DESC
                    LIMIT 1
                    """,
                    (scope_hash,),
                ).fetchone()
            if row is None:
                return None
            result = InsightResult(
                positive_keywords=_keywords(row["positive_keywords_json"]),
                negative_keywords=_keywords(row["negative_keywords_json"]),
                summary=str(row["summary"]),
                recommendations=_recommendations(row["recommendations_json"]),
                model_name=str(row["model_name"]),
                prompt_version=str(row["prompt_version"]),
            )
            return StoredInsight(
                id=int(row["id"]),
                scope_json=str(row["scope_json"]),
                scope_hash=str(row["scope_hash"]),
                review_count=int(row["review_count"]),
                result=result,
                is_stale=bool(row["is_stale"]),
                created_at=str(row["created_at"]),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError, sqlite3.Error) as exc:
            raise PersistenceError("인사이트를 조회하지 못했습니다.", "INSIGHT_QUERY_FAILED") from exc


# 키워드 근거 튜플을 저장 가능한 JSON 문자열로 직렬화한다.
def _keyword_json(keywords: tuple[KeywordEvidence, ...]) -> str:
    payload = [
        {"keyword": keyword.keyword, "review_ids": list(keyword.review_ids)}
        for keyword in keywords
    ]
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


# 저장된 키워드 JSON을 타입 검증된 근거 튜플로 복원한다.
def _keywords(value: str) -> tuple[KeywordEvidence, ...]:
    payload = json.loads(value)
    if type(payload) is not list:
        raise ValueError("keyword payload must be a list")
    keywords = []
    for item in payload:
        if type(item) is not dict:
            raise ValueError("keyword item must be an object")
        keyword = item.get("keyword")
        review_ids = item.get("review_ids")
        if type(keyword) is not str or type(review_ids) is not list:
            raise ValueError("keyword fields have invalid types")
        if any(type(review_id) is not int for review_id in review_ids):
            raise ValueError("evidence IDs must be integers")
        keywords.append(KeywordEvidence(keyword=keyword, review_ids=tuple(review_ids)))
    return tuple(keywords)


# 저장된 개선 제안 JSON을 문자열 튜플로 복원한다.
def _recommendations(value: str) -> tuple[str, ...]:
    payload = json.loads(value)
    if type(payload) is not list or any(type(item) is not str for item in payload):
        raise ValueError("recommendations must be a list of strings")
    return tuple(payload)


# 저장 시각으로 사용할 UTC ISO 문자열을 만든다.
def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
