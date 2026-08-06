"""감정 분석 배치 실행을 SQLite 쓰기 트랜잭션 밖에서 조정한다."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from review_analytics.dto import AnalyzeRequest, OperationSummary
from review_analytics.errors import AIServiceError
from review_analytics.repositories import AnalysisRepository
from review_analytics.services._ai_retry import retry_ai


logger = logging.getLogger(__name__)


# 분석 대상을 배치 호출하고 성공 결과를 배치 단위로 저장한다.
def analyze_reviews(
    request: AnalyzeRequest,
    repository: AnalysisRepository,
    client: object,
    batch_size: int,
    retry_count: int,
    sleep: Callable[[float], object] = time.sleep,
) -> OperationSummary:
    targets = repository.analysis_targets(
        request.target_mode,
        request.review_id,
        request.limit,
        request.force,
    )
    succeeded = 0
    failed = 0
    for batch_number, start in enumerate(range(0, len(targets), batch_size), start=1):
        batch = targets[start : start + batch_size]
        try:
            results = retry_ai(
                lambda: client.analyze(batch),
                retry_count,
                sleep,
                on_retry=lambda attempt, error: logger.warning(
                    "event=ai.retry operation=analyze attempt=%d error_code=%s",
                    attempt,
                    error.code,
                ),
            )
        except AIServiceError as exc:
            failed += len(batch)
            logger.warning(
                "event=ai.batch.skipped operation=analyze batch=%d error_code=%s",
                batch_number,
                exc.code,
            )
            continue
        succeeded += repository.save_sentiment_batch(tuple(results))
        logger.info(
            "event=analysis.batch.completed batch=%d succeeded=%d failed=0",
            batch_number,
            len(results),
        )
    return OperationSummary(
        processed=len(targets),
        succeeded=succeeded,
        skipped=0,
        failed=failed,
    )
