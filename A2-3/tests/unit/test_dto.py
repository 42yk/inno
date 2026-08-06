from dataclasses import FrozenInstanceError

import pytest

from review_analytics.dto import (
    DashboardData,
    OperationSummary,
    PartialFailureResult,
    ReviewFilter,
    StatsResult,
)
from review_analytics.models import KeywordEvidence, QualityMetrics, Sentiment


def test_dashboard_data_is_an_immutable_complete_output_snapshot():
    """Omitting dashboard fields or allowing mutation would break the shared Output boundary."""
    stats = StatsResult(
        total_clean=2,
        analyzed_count=1,
        sentiment_counts=((Sentiment.POSITIVE, 1),),
        rating_counts=((5, 1),),
        average_rating=5.0,
        metrics=QualityMetrics(0.5, 0.9, 1.0),
    )
    dashboard = DashboardData(
        stats=stats,
        positive_keywords=(KeywordEvidence("\uc88b\uc740 \ud488\uc9c8", (1,)),),
        negative_keywords=(KeywordEvidence("\ubc30\uc1a1 \uc9c0\uc5f0", (2,)),),
        summary="\uc694\uc57d",
        recommendations=("\uac80\uc218\ub97c \uac15\ud654\ud55c\ub2e4.",),
        filter=ReviewFilter(product="\ud150\ube14\ub7ec"),
    )

    assert dashboard.stats is stats
    assert dashboard.positive_keywords[0].review_ids == (1,)
    assert dashboard.filter.product == "\ud150\ube14\ub7ec"
    with pytest.raises(FrozenInstanceError):
        dashboard.summary = "\ubcc0\uacbd"  # type: ignore[misc]


def test_partial_failure_result_preserves_success_and_safe_failure_id_reason_pairs():
    """Dropping either success output or failure reasons would hide a partial command result."""
    success = OperationSummary(processed=2, succeeded=1, skipped=0, failed=1)
    result = PartialFailureResult(successful_result=success, failures=((7, "AI_TIMEOUT"),))

    assert result.successful_result is success
    assert result.failures == ((7, "AI_TIMEOUT"),)


def test_operation_summary_distinguishes_normal_rejections_from_execution_failures():
    """Clean validation rejection must not force the same exit code as a database failure."""
    summary = OperationSummary(processed=2, succeeded=1, skipped=0, failed=0, rejected=1)

    assert summary.rejected == 1
    assert summary.failed == 0
