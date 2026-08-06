"""검증된 분석 결과로 품질 지표를 순수 계산한다."""

from collections.abc import Iterable

from review_analytics.models import QualityMetrics, Sentiment


# 정제·분석 건수와 결과로 완료율, 신뢰도, 별점 일치율을 계산한다.
def calculate_quality_metrics(
    total_clean: int,
    analyzed: Iterable[tuple[int | None, Sentiment | str, float]],
) -> QualityMetrics:
    """Calculate documented ratios, returning ``None`` for unavailable denominators."""
    rows = tuple(analyzed)
    completion_rate = len(rows) / total_clean if total_clean else None
    average_confidence = sum(confidence for _, _, confidence in rows) / len(rows) if rows else None

    eligible = tuple((rating, Sentiment(sentiment)) for rating, sentiment, _ in rows if rating is not None)
    if not eligible:
        agreement = None
    else:
        agreement = sum(_rating_matches_sentiment(rating, sentiment) for rating, sentiment in eligible) / len(eligible)

    return QualityMetrics(completion_rate, average_confidence, agreement)


# 별점 구간에서 기대하는 감정과 분석 감정이 일치하는지 판정한다.
def _rating_matches_sentiment(rating: int, sentiment: Sentiment) -> bool:
    expected = Sentiment.NEGATIVE if rating <= 2 else Sentiment.NEUTRAL if rating == 3 else Sentiment.POSITIVE
    return sentiment is expected
