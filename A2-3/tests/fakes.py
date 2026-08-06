"""공개 Gemini Client DTO 계약을 따르는 네트워크 없는 테스트 대역을 제공한다."""

from __future__ import annotations

from review_analytics.models import (
    AnalysisInput,
    InsightInput,
    InsightResult,
    KeywordEvidence,
    Sentiment,
    SentimentResult,
)


class FakeGeminiClient:
    """Deterministic sentiment and insight client used only by offline tests."""

    def __init__(self) -> None:
        self.closed = False

    def analyze(self, batch: tuple[AnalysisInput, ...]) -> tuple[SentimentResult, ...]:
        return tuple(
            SentimentResult(
                clean_review_id=item.review_id,
                sentiment=_sentiment(item.review_text),
                confidence=0.9,
                model_name="fake-gemini-offline",
                prompt_version="fake-sentiment-v1",
            )
            for item in batch
        )

    def extract(self, insight_input: InsightInput) -> InsightResult:
        positive_ids = tuple(
            item.review_id
            for item in insight_input.reviews
            if _sentiment(item.review_text) is Sentiment.POSITIVE
        )
        negative_ids = tuple(
            item.review_id
            for item in insight_input.reviews
            if _sentiment(item.review_text) is Sentiment.NEGATIVE
        )
        return InsightResult(
            positive_keywords=_keyword("만족과 편의", positive_ids),
            negative_keywords=_keyword("사용 불편", negative_ids),
            summary="오프라인 Fake Gemini 요약",
            recommendations=("불편 근거 리뷰를 우선 점검하세요.",),
            model_name="fake-gemini-offline",
            prompt_version="fake-insight-v1",
        )

    def merge_insights(self, parts: tuple[InsightResult, ...]) -> InsightResult:
        return InsightResult(
            positive_keywords=_merged_keyword("만족과 편의", parts, positive=True),
            negative_keywords=_merged_keyword("사용 불편", parts, positive=False),
            summary="오프라인 Fake Gemini 요약",
            recommendations=("불편 근거 리뷰를 우선 점검하세요.",),
            model_name="fake-gemini-offline",
            prompt_version="fake-merge-v1",
        )

    def close(self) -> None:
        self.closed = True


def _sentiment(review_text: str) -> Sentiment:
    if any(
        keyword in review_text
        for keyword in ("불편", "아쉬", "헐거", "작다고", "끊겨", "약해", "흔들", "눈부", "짧아서")
    ):
        return Sentiment.NEGATIVE
    if any(keyword in review_text for keyword in ("보통", "무난", "조금")):
        return Sentiment.NEUTRAL
    return Sentiment.POSITIVE


def _keyword(label: str, review_ids: tuple[int, ...]) -> tuple[KeywordEvidence, ...]:
    return (KeywordEvidence(label, review_ids),) if review_ids else ()


def _merged_keyword(
    label: str,
    parts: tuple[InsightResult, ...],
    *,
    positive: bool,
) -> tuple[KeywordEvidence, ...]:
    review_ids: list[int] = []
    for part in parts:
        keywords = part.positive_keywords if positive else part.negative_keywords
        for keyword in keywords:
            for review_id in keyword.review_ids:
                if review_id not in review_ids:
                    review_ids.append(review_id)
    return _keyword(label, tuple(review_ids))
