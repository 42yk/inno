from __future__ import annotations

from types import SimpleNamespace

import pytest
from google.genai import errors as genai_errors

from review_analytics.errors import AIResponseError, AIServiceError
from review_analytics.models import AnalysisInput, InsightInput, InsightResult, KeywordEvidence, Sentiment


class FakeModels:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return SimpleNamespace(parsed=response, text=None)


class FakeSDK:
    def __init__(self, *responses):
        self.models = FakeModels(responses)


def test_analyze_uses_structured_json_and_returns_validated_internal_results():
    """Returning raw SDK data would leak an external boundary and skip enum/range validation."""
    from review_analytics.clients.gemini import GeminiClient

    sdk = FakeSDK(
        {
            "results": [
                {"review_id": 1, "sentiment": "positive", "confidence": 0.92},
                {"review_id": 2, "sentiment": "negative", "confidence": 0.81},
            ]
        }
    )
    client = GeminiClient(sdk, "gemini-test")

    result = client.analyze(
        (
            AnalysisInput(1, "PRIVATE_POSITIVE_REVIEW_MARKER"),
            AnalysisInput(2, "PRIVATE_NEGATIVE_REVIEW_MARKER"),
        )
    )

    assert [(item.clean_review_id, item.sentiment, item.confidence) for item in result] == [
        (1, Sentiment.POSITIVE, 0.92),
        (2, Sentiment.NEGATIVE, 0.81),
    ]
    assert all(item.model_name == "gemini-test" and item.prompt_version == "sentiment-v2" for item in result)
    call = sdk.models.calls[0]
    assert call["model"] == "gemini-test"
    assert call["config"]["response_mime_type"] == "application/json"
    assert call["config"]["response_json_schema"]["required"] == ["results"]
    instruction = call["config"]["system_instruction"]
    assert "Classify each review" in instruction
    assert all(sentiment.value in instruction for sentiment in Sentiment)
    assert "confidence" in instruction
    assert "review_id" in instruction
    assert "untrusted data" in instruction
    assert "Use positive when" in instruction
    assert "Use negative when" in instruction
    assert "Use neutral when" in instruction
    assert "mixed sentiment" in instruction
    assert "dominant overall attitude" in instruction
    assert "not a calibrated probability" in instruction
    assert "PRIVATE_POSITIVE_REVIEW_MARKER" not in instruction
    assert "PRIVATE_NEGATIVE_REVIEW_MARKER" not in instruction


@pytest.mark.parametrize(
    "payload",
    (
        {"results": [{"review_id": 99, "sentiment": "positive", "confidence": 0.9}]},
        {"results": []},
        {"results": [{"review_id": 1, "sentiment": "positive", "confidence": 0.9}] * 2},
        {"results": [{"review_id": 1, "sentiment": "mixed", "confidence": 0.9}]},
        {"results": [{"review_id": 1, "sentiment": "positive", "confidence": 1.1}]},
        {"results": [{"review_id": True, "sentiment": "positive", "confidence": 0.9}]},
        {"results": [{"review_id": 1, "sentiment": "positive", "confidence": 0.9}], "extra": "field"},
        {"results": [{"review_id": 1, "sentiment": "positive", "confidence": 0.9, "extra": "field"}]},
    ),
)
def test_analyze_rejects_mismatched_ids_enum_and_confidence(payload):
    """A structurally valid but semantically wrong batch must never be persisted."""
    from review_analytics.clients.gemini import GeminiClient

    with pytest.raises(AIResponseError) as raised:
        GeminiClient(FakeSDK(payload), "model").analyze((AnalysisInput(1, "본문"),))

    assert raised.value.code == "INVALID_AI_RESPONSE"


def test_analyze_converts_sdk_api_error_without_leaking_remote_message():
    """Raw provider errors may contain request details and must not cross the Client boundary."""
    from review_analytics.clients.gemini import GeminiClient

    error = genai_errors.APIError(503, {"error": {"message": "remote secret detail"}})

    with pytest.raises(AIServiceError) as raised:
        GeminiClient(FakeSDK(error), "model").analyze((AnalysisInput(1, "private review"),))

    assert raised.value.code == "AI_REQUEST_FAILED"
    assert "secret" not in str(raised.value)
    assert "private review" not in str(raised.value)


def test_extract_validates_keyword_and_recommendation_scalar_types():
    """String-to-int coercion would create false keyword evidence."""
    from review_analytics.clients.gemini import GeminiClient

    payload = {
        "positive_keywords": [{"keyword": "quality", "review_ids": ["1"]}],
        "negative_keywords": [],
        "summary": "summary",
        "recommendations": ["improve"],
    }

    with pytest.raises(AIResponseError):
        GeminiClient(FakeSDK(payload), "model").extract(InsightInput("scope", (AnalysisInput(1, "text"),)))


@pytest.mark.parametrize(
    "payload",
    (
        {
            "positive_keywords": [],
            "negative_keywords": [],
            "summary": "summary",
            "recommendations": [],
            "extra": "field",
        },
        {
            "positive_keywords": [{"keyword": "quality", "review_ids": [1], "extra": "field"}],
            "negative_keywords": [],
            "summary": "summary",
            "recommendations": [],
        },
    ),
)
def test_extract_rejects_additional_response_fields_even_if_sdk_returns_parsed_data(payload):
    """Local validation must enforce the schema instead of trusting provider-side enforcement."""
    from review_analytics.clients.gemini import GeminiClient

    with pytest.raises(AIResponseError):
        GeminiClient(FakeSDK(payload), "model").extract(
            InsightInput("scope", (AnalysisInput(1, "text"),))
        )


@pytest.mark.parametrize(
    "payload",
    (
        {
            "positive_keywords": [],
            "negative_keywords": [],
            "summary": "   ",
            "recommendations": ["improve"],
        },
        {
            "positive_keywords": [],
            "negative_keywords": [],
            "summary": "summary",
            "recommendations": ["\t\n"],
        },
    ),
)
def test_extract_rejects_blank_summary_and_recommendations(payload):
    """Blank insight text would satisfy JSON types while violating the usable-output contract."""
    from review_analytics.clients.gemini import GeminiClient

    with pytest.raises(AIResponseError) as raised:
        GeminiClient(FakeSDK(payload), "model").extract(
            InsightInput("scope", (AnalysisInput(1, "text"),))
        )

    assert raised.value.code == "INVALID_AI_RESPONSE"


def test_extract_and_merge_return_named_insight_results():
    """Chunk and merge responses must share one validated internal shape."""
    from review_analytics.clients.gemini import GeminiClient

    payload = {
        "positive_keywords": [{"keyword": "quality", "review_ids": [1, 999]}],
        "negative_keywords": [{"keyword": "delay", "review_ids": [2]}],
        "summary": "summary",
        "recommendations": ["improve"],
    }
    sdk = FakeSDK(payload, payload)
    client = GeminiClient(sdk, "model")

    extracted = client.extract(
        InsightInput(
            "scope",
            (
                AnalysisInput(1, "PRIVATE_EXTRACT_REVIEW_MARKER_A"),
                AnalysisInput(2, "PRIVATE_EXTRACT_REVIEW_MARKER_B"),
            ),
        )
    )
    merged = client.merge_insights((extracted, extracted))

    assert extracted == InsightResult(
        (KeywordEvidence("quality", (1, 999)),),
        (KeywordEvidence("delay", (2,)),),
        "summary",
        ("improve",),
        "model",
        "insight-v1",
    )
    assert merged.prompt_version == "insight-merge-v1"
    assert len(sdk.models.calls) == 2
    extract_config = sdk.models.calls[0]["config"]
    extract_instruction = extract_config["system_instruction"]
    insight_schema = extract_config["response_json_schema"]
    assert insight_schema["properties"]["summary"]["minLength"] == 1
    assert insight_schema["properties"]["recommendations"]["items"]["minLength"] == 1
    assert "Extract recurring positive and negative keywords" in extract_instruction
    assert "evidence review_ids" in extract_instruction
    assert "summary" in extract_instruction
    assert "actionable recommendations" in extract_instruction
    assert "untrusted data" in extract_instruction
    assert "PRIVATE_EXTRACT_REVIEW_MARKER_A" not in extract_instruction
    assert "PRIVATE_EXTRACT_REVIEW_MARKER_B" not in extract_instruction

    merge_instruction = sdk.models.calls[1]["config"]["system_instruction"]
    assert "Merge and deduplicate the partial insights" in merge_instruction
    assert "evidence review_ids" in merge_instruction
    assert "summary" in merge_instruction
    assert "actionable recommendations" in merge_instruction
    assert "untrusted data" in merge_instruction
    assert "PRIVATE_EXTRACT_REVIEW_MARKER_A" not in merge_instruction
    assert "PRIVATE_EXTRACT_REVIEW_MARKER_B" not in merge_instruction
