"""읽기 전용 리뷰 목록·상세·통계 조회 순서를 조정한다."""

from __future__ import annotations

from review_analytics.dto import (
    ReviewDetailRequest,
    ReviewDetailResult,
    ReviewListRequest,
    ReviewListResult,
    StatsRequest,
    StatsResult,
    StatsRow,
)
from review_analytics.errors import NotFoundError
from review_analytics.models import Sentiment
from review_analytics.repositories import ReviewRepository
from review_analytics.rules.metrics import calculate_quality_metrics


_SENTIMENT_ORDER = (Sentiment.POSITIVE, Sentiment.NEUTRAL, Sentiment.NEGATIVE)


# 공통 필터·정렬·페이지 조건으로 리뷰 목록 한 페이지를 조회한다.
def list_reviews(request: ReviewListRequest, repository: ReviewRepository) -> ReviewListResult:
    """Return one stable page using the shared repository filter semantics."""
    return repository.list_reviews(
        request.filter,
        request.page,
        request.size,
        request.sort_by,
        request.order,
    )


# 리뷰 한 건의 원본·정제·감정 상세를 조회하거나 없음 오류를 낸다.
def show_review(request: ReviewDetailRequest, repository: ReviewRepository) -> ReviewDetailResult:
    """Return one raw/clean/analysis detail or a safe not-found error."""
    result = repository.get_review_detail(request.review_id)
    if result is None:
        raise NotFoundError("요청한 리뷰를 찾을 수 없습니다.", "RAW_REVIEW_NOT_FOUND")
    return result


# 필터링한 저장 행으로 통계와 품질 지표를 계산한다.
def get_stats(request: StatsRequest, repository: ReviewRepository) -> StatsResult:
    """Calculate aggregates with the documented clean/analysis denominators."""
    return calculate_stats(repository.stats_rows(request.filter))


# 이미 조회된 행 스냅샷에서 불변 통계 결과를 계산한다.
def calculate_stats(rows: tuple[StatsRow, ...]) -> StatsResult:
    """Calculate one immutable set of aggregates from an already-read row snapshot."""
    ratings = tuple(row.rating for row in rows if row.rating is not None)
    analyzed = tuple(
        (row.rating, row.sentiment, row.confidence)
        for row in rows
        if row.sentiment is not None and row.confidence is not None
    )
    sentiment_counts = tuple(
        (sentiment, sum(row.sentiment is sentiment for row in rows))
        for sentiment in _SENTIMENT_ORDER
    )
    rating_counts = tuple((rating, ratings.count(rating)) for rating in range(1, 6))
    average_rating = sum(ratings) / len(ratings) if ratings else None
    return StatsResult(
        total_clean=len(rows),
        analyzed_count=len(analyzed),
        sentiment_counts=sentiment_counts,
        rating_counts=rating_counts,
        average_rating=average_rating,
        metrics=calculate_quality_metrics(len(rows), analyzed),
    )
