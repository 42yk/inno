"""필터 인사이트의 추출·청크 분할·근거 검증·저장을 조정한다."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Callable, Iterable

from review_analytics.dto import ExtractRequest, OperationSummary, ReviewFilter
from review_analytics.errors import NotFoundError
from review_analytics.models import AnalysisInput, InsightInput, InsightResult, KeywordEvidence
from review_analytics.repositories import AnalysisRepository, ReviewRepository
from review_analytics.services._ai_retry import retry_ai


logger = logging.getLogger(__name__)


# 필터 리뷰를 청크로 추출·병합하고 검증한 인사이트를 저장한다.
def extract_insights(
    request: ExtractRequest,
    review_repository: ReviewRepository,
    analysis_repository: AnalysisRepository,
    client: object,
    chunk_characters: int,
    retry_count: int,
    sleep: Callable[[float], object] = time.sleep,
) -> OperationSummary:
    export_rows = review_repository.export_rows(request.filter)
    selected_rows = export_rows[: request.limit] if request.limit is not None else export_rows
    if not selected_rows:
        raise NotFoundError("조건에 맞는 리뷰가 없습니다.", "NO_REVIEWS_FOR_EXTRACTION")

    scope_json, scope_hash = extraction_scope(request.filter, request.limit)
    inputs = tuple(AnalysisInput(row.review_id, row.review_text) for row in selected_rows)
    chunks = _character_chunks(inputs, chunk_characters)
    parts = tuple(
        _retry_extract(
            lambda chunk=chunk: client.extract(InsightInput(scope_hash, chunk)),
            retry_count,
            sleep,
        )
        for chunk in chunks
    )
    if len(parts) == 1:
        combined = parts[0]
    else:
        combined = _retry_extract(lambda: client.merge_insights(parts), retry_count, sleep)
    result = _sanitize_insight(combined, {item.review_id for item in inputs})
    insight_id = analysis_repository.save_insight(
        scope_json,
        scope_hash,
        len(inputs),
        result,
    )
    logger.info(
        "event=insight.saved scope_hash_prefix=%s review_count=%d",
        scope_hash[:8],
        len(inputs),
    )
    return OperationSummary(
        processed=len(inputs),
        succeeded=len(inputs),
        skipped=0,
        failed=0,
        messages=(f"insight_id={insight_id}",),
    )


# 인사이트 범위를 정규 JSON과 안정적인 SHA-256 해시로 표현한다.
def extraction_scope(review_filter: ReviewFilter, limit: int | None) -> tuple[str, str]:
    payload = {
        "date_from": review_filter.date_from,
        "date_to": review_filter.date_to,
        "limit": limit,
        "product": review_filter.product,
        "rating": review_filter.rating,
        "rating_min": review_filter.rating_min,
        "sentiment": review_filter.sentiment.value if review_filter.sentiment is not None else None,
    }
    scope_json = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return scope_json, hashlib.sha256(scope_json.encode("utf-8")).hexdigest()


# 인사이트 AI 작업을 재시도하며 실패 원인을 안전하게 기록한다.
def _retry_extract(operation, retry_count: int, sleep: Callable[[float], object]):
    return retry_ai(
        operation,
        retry_count,
        sleep,
        on_retry=lambda attempt, error: logger.warning(
            "event=ai.retry operation=extract attempt=%d error_code=%s",
            attempt,
            error.code,
        ),
    )


# 전체 리뷰 입력을 최대 문자 수에 맞는 순서 보존 청크로 나눈다.
def _character_chunks(inputs: tuple[AnalysisInput, ...], maximum: int) -> tuple[tuple[AnalysisInput, ...], ...]:
    chunks: list[tuple[AnalysisInput, ...]] = []
    current: list[AnalysisInput] = []
    characters = 0
    for item in inputs:
        item_size = len(item.review_text)
        if current and characters + item_size > maximum:
            chunks.append(tuple(current))
            current = []
            characters = 0
        current.append(item)
        characters += item_size
    if current:
        chunks.append(tuple(current))
    return tuple(chunks)


# AI 인사이트의 키워드 근거를 실제 입력 리뷰 ID로 제한한다.
def _sanitize_insight(result: InsightResult, valid_ids: set[int]) -> InsightResult:
    return InsightResult(
        positive_keywords=_sanitize_keywords(result.positive_keywords, valid_ids),
        negative_keywords=_sanitize_keywords(result.negative_keywords, valid_ids),
        summary=result.summary,
        recommendations=result.recommendations,
        model_name=result.model_name,
        prompt_version=result.prompt_version,
    )


# 키워드를 정규화·중복 제거하고 유효한 근거 ID만 보존한다.
def _sanitize_keywords(
    keywords: Iterable[KeywordEvidence],
    valid_ids: set[int],
) -> tuple[KeywordEvidence, ...]:
    labels: dict[str, str] = {}
    evidence: dict[str, list[int]] = {}
    for item in keywords:
        key = item.keyword.strip().casefold()
        if not key:
            continue
        labels.setdefault(key, item.keyword.strip())
        current = evidence.setdefault(key, [])
        for review_id in item.review_ids:
            if review_id in valid_ids and review_id not in current:
                current.append(review_id)
    return tuple(
        KeywordEvidence(labels[key], tuple(review_ids))
        for key, review_ids in evidence.items()
        if review_ids
    )
