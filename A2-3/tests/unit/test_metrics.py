from review_analytics.rules.metrics import calculate_quality_metrics


def test_metrics_use_only_eligible_denominators():
    """Using all clean rows for confidence/agreement would understate their values."""
    metrics = calculate_quality_metrics(total_clean=2, analyzed=[(5, "positive", 0.9)])

    assert metrics.completion_rate == 0.5
    assert metrics.average_confidence == 0.9
    assert metrics.rating_sentiment_agreement == 1.0


def test_metrics_return_none_for_zero_denominators():
    """Returning zero for an unavailable ratio would misrepresent it as a measured value."""
    metrics = calculate_quality_metrics(total_clean=0, analyzed=[])

    assert metrics.completion_rate is None
    assert metrics.average_confidence is None
    assert metrics.rating_sentiment_agreement is None


def test_metrics_exclude_missing_ratings_from_agreement_denominator():
    """Counting unrated analyses as disagreements would corrupt the agreement metric."""
    metrics = calculate_quality_metrics(
        total_clean=3,
        analyzed=[(None, "negative", 0.4), (3, "neutral", 0.7), (1, "positive", 0.6)],
    )

    assert metrics.completion_rate == 1.0
    assert metrics.average_confidence == 0.5666666666666667
    assert metrics.rating_sentiment_agreement == 0.5
