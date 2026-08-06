"""검증된 파일 입력과 원본 리뷰 저장 순서를 조정한다."""

from __future__ import annotations

import logging
from collections.abc import Callable

from review_analytics.dto import ImportRequest, OperationSummary
from review_analytics.errors import PersistenceError
from review_analytics.file_io.reader import read_reviews
from review_analytics.models import DuplicatePolicy, RawReviewInput, RawSaveAction
from review_analytics.repositories.reviews import ReviewRepository
from review_analytics.rules.duplicate_policy import fingerprint_review


_LOGGER = logging.getLogger("review_analytics.services.ingestion")


# 파일 전체를 읽은 뒤 중복 정책에 따라 원본 리뷰를 저장한다.
def import_reviews(
    request: ImportRequest,
    repository: ReviewRepository,
    reader: Callable[[object], tuple[RawReviewInput, ...]] = read_reviews,
) -> OperationSummary:
    """Read the full file first, then save raw reviews under the requested duplicate policy."""
    inputs = reader(request.file_path)
    policy = request.duplicate_policy or DuplicatePolicy.SKIP
    _LOGGER.info("event=import.file.loaded file_name=%s rows=%s", request.file_path.name, len(inputs))
    succeeded = skipped = failed = 0
    for raw in inputs:
        try:
            result = repository.save_raw(
                raw,
                fingerprint_review(raw.review_text_raw, raw.product_name_raw, raw.review_date_raw),
                policy,
            )
        except PersistenceError as exc:
            failed += 1
            _LOGGER.warning("event=import.row.failed error_code=%s", exc.code)
            continue
        if result.action is RawSaveAction.SKIPPED:
            skipped += 1
            _LOGGER.info("event=duplicate.skipped review_id=%s", result.review_id)
        else:
            succeeded += 1
    return OperationSummary(len(inputs), succeeded, skipped, failed)
