from __future__ import annotations

import logging

from review_analytics.dto import AnalyzeRequest
from review_analytics.errors import AIServiceError
from review_analytics.models import AnalysisInput, Sentiment, SentimentResult, TargetMode


class AnalysisRepositoryFake:
    def __init__(self, targets):
        self.targets = tuple(targets)
        self.target_call = None
        self.saved = []

    def analysis_targets(self, target_mode, review_id=None, limit=None, force=False):
        self.target_call = (target_mode, review_id, limit, force)
        return self.targets

    def save_sentiment_batch(self, results):
        self.saved.append(tuple(results))
        return len(results)


class AnalysisClientFake:
    def __init__(self, failures=0):
        self.failures = failures
        self.calls = []

    def analyze(self, batch):
        self.calls.append(tuple(batch))
        if self.failures:
            self.failures -= 1
            raise AIServiceError("temporary", "AI_REQUEST_FAILED")
        return tuple(SentimentResult(item.review_id, Sentiment.POSITIVE, 0.9, "fake", "v1") for item in batch)


def test_analyze_batches_targets_and_persists_only_validated_results():
    """One giant call or per-row writes would violate configured batch atomicity."""
    from review_analytics.services.sentiment import analyze_reviews

    targets = tuple(AnalysisInput(index, f"text {index}") for index in range(1, 6))
    repository = AnalysisRepositoryFake(targets)
    client = AnalysisClientFake()

    summary = analyze_reviews(AnalyzeRequest(), repository, client, batch_size=2, retry_count=0)

    assert [len(batch) for batch in client.calls] == [2, 2, 1]
    assert [len(batch) for batch in repository.saved] == [2, 2, 1]
    assert (summary.processed, summary.succeeded, summary.failed) == (5, 5, 0)
    assert repository.target_call == (TargetMode.UNANALYZED, None, None, False)


def test_analyze_retries_then_succeeds_with_exponential_delays(caplog):
    """A temporary failure must honor configured retry count before skipping a batch."""
    from review_analytics.services.sentiment import analyze_reviews

    repository = AnalysisRepositoryFake((AnalysisInput(1, "text"),))
    client = AnalysisClientFake(failures=2)
    delays = []

    with caplog.at_level(logging.WARNING):
        summary = analyze_reviews(
            AnalyzeRequest(target_mode=TargetMode.ID, review_id=1, force=True),
            repository,
            client,
            batch_size=20,
            retry_count=2,
            sleep=delays.append,
        )

    assert len(client.calls) == 3
    assert delays == [1.0, 2.0]
    assert summary.succeeded == 1 and summary.failed == 0
    assert repository.target_call == (TargetMode.ID, 1, None, True)
    assert [record.getMessage() for record in caplog.records] == [
        "event=ai.retry operation=analyze attempt=1 error_code=AI_REQUEST_FAILED",
        "event=ai.retry operation=analyze attempt=2 error_code=AI_REQUEST_FAILED",
    ]
    assert "text" not in caplog.text


def test_analyze_keeps_successful_batches_when_another_batch_exhausts_retries():
    """A failed batch must not roll back a later successful batch."""
    from review_analytics.services.sentiment import analyze_reviews

    repository = AnalysisRepositoryFake((AnalysisInput(1, "a"), AnalysisInput(2, "b"), AnalysisInput(3, "c")))

    class FirstBatchFails:
        def __init__(self):
            self.calls = 0

        def analyze(self, batch):
            self.calls += 1
            if batch[0].review_id == 1:
                raise AIServiceError("failed", "AI_REQUEST_FAILED")
            return (SentimentResult(3, Sentiment.NEUTRAL, 0.7, "fake", "v1"),)

    summary = analyze_reviews(AnalyzeRequest(), repository, FirstBatchFails(), batch_size=2, retry_count=1, sleep=lambda _: None)

    assert (summary.processed, summary.succeeded, summary.failed) == (3, 1, 2)
    assert [[item.clean_review_id for item in batch] for batch in repository.saved] == [[3]]


def test_analyze_with_no_targets_does_not_call_client():
    """A normal zero-target run must succeed without requiring an API call."""
    from review_analytics.services.sentiment import analyze_reviews

    repository = AnalysisRepositoryFake(())

    class ForbiddenClient:
        def analyze(self, batch):
            raise AssertionError("client must not be called")

    summary = analyze_reviews(AnalyzeRequest(), repository, ForbiddenClient(), 20, 2)

    assert summary.processed == summary.succeeded == summary.failed == 0
