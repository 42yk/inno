"""원본 리뷰 검증과 정제·거절 상태 저장 순서를 조정한다."""

from __future__ import annotations

import logging

from review_analytics.dto import CleanRequest, OperationSummary
from review_analytics.errors import NotFoundError, PersistenceError
from review_analytics.models import RawReview, RawReviewInput, TargetMode
from review_analytics.repositories.reviews import ReviewRepository
from review_analytics.rules.validation import clean_review


_LOGGER = logging.getLogger("review_analytics.services.cleaning")


# 선택한 원본 리뷰를 검증하고 정제 또는 거절 상태로 저장한다.
def clean_reviews(
    request: CleanRequest,
    repository: ReviewRepository,
    minimum_review_length: int = 5,
) -> OperationSummary:
    """Validate selected raw reviews and persist either a clean value or stable rejection code."""
    targets = repository.select_raw_targets(request.target_mode, request.review_id)
    if request.target_mode is TargetMode.ID and not targets:
        raise NotFoundError("요청한 리뷰를 찾을 수 없습니다.", "RAW_REVIEW_NOT_FOUND")

    succeeded = rejected = failed = 0
    for raw in targets:
        result = clean_review(_as_raw_input(raw), minimum_review_length)
        try:
            if result.accepted:
                repository.save_clean(raw.id, result.clean_review)
                succeeded += 1
            else:
                reason_code = result.rejection_code.value
                repository.reject_clean(raw.id, reason_code)
                rejected += 1
                _LOGGER.warning("event=clean.rejected review_id=%s reason_code=%s", raw.id, reason_code)
        except PersistenceError as exc:
            failed += 1
            _LOGGER.warning("event=clean.row.failed review_id=%s error_code=%s", raw.id, exc.code)
    return OperationSummary(len(targets), succeeded, 0, failed, rejected=rejected)


# 저장된 원본 리뷰를 정제 규칙 입력 모델로 변환한다.
def _as_raw_input(raw: RawReview) -> RawReviewInput:
    return RawReviewInput(
        review_text_raw=raw.review_text_raw,
        rating_raw=raw.rating_raw,
        review_date_raw=raw.review_date_raw,
        product_name_raw=raw.product_name_raw,
        source_type=raw.source_type,
        source_ref=raw.source_ref,
        source_row=raw.source_row,
    )
