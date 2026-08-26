from types import SimpleNamespace

from app.clients.openai_client import OpenAIClient


class FakeChatCompletions:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self.responses.pop(0)


def sdk_with(responses: list[object]) -> tuple[object, FakeChatCompletions]:
    fake = FakeChatCompletions(responses)
    sdk = SimpleNamespace(chat=SimpleNamespace(completions=fake))
    return sdk, fake


def completion_message(
    *,
    content: str | None,
    tool_calls: list[object] | None = None,
) -> object:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=content,
                    tool_calls=tool_calls,
                )
            )
        ]
    )


def test_complete_maps_function_calls_and_uses_chat_completions_contract() -> None:
    response = completion_message(
        content=None,
        tool_calls=[
            SimpleNamespace(
                id="call-1",
                type="function",
                function=SimpleNamespace(
                    name="get_weight_by_date",
                    arguments='{"date":"2025-03-10"}',
                ),
            )
        ],
    )
    sdk, completions = sdk_with([response])
    client = OpenAIClient(
        api_key="test-key",
        base_url="https://copa.example/v1",
        model="test-model",
        max_output_tokens=321,
        sdk_client=sdk,
    )
    tools = [
        {
            "type": "function",
            "function": {"name": "get_weight_by_date"},
        }
    ]

    turn = client.complete(
        instructions="policy",
        messages=[{"role": "user", "content": "질문"}],
        tools=tools,
    )

    assert turn.final_text is None
    assert turn.function_calls[0].call_id == "call-1"
    assert completions.calls[0] == {
        "model": "test-model",
        "messages": [
            {"role": "system", "content": "policy"},
            {"role": "user", "content": "질문"},
        ],
        "tools": tools,
        "tool_choice": "auto",
        "max_completion_tokens": 321,
    }


def test_complete_maps_final_text() -> None:
    response = completion_message(content=" 최종 답변 ")
    sdk, _completions = sdk_with([response])
    client = OpenAIClient(
        "test-key",
        "https://copa.example/v1",
        "test-model",
        321,
        sdk_client=sdk,
    )

    turn = client.complete(instructions="policy", messages=[], tools=[])

    assert turn.final_text == "최종 답변"
    assert turn.function_calls == []


def test_text_is_ignored_until_function_calls_are_resolved() -> None:
    response = completion_message(
        content="중간 문장",
        tool_calls=[
            SimpleNamespace(
                id="call-1",
                type="function",
                function=SimpleNamespace(
                    name="get_weight_summary",
                    arguments="{}",
                ),
            )
        ],
    )
    sdk, _completions = sdk_with([response])
    client = OpenAIClient(
        "test-key",
        "https://copa.example/v1",
        "test-model",
        321,
        sdk_client=sdk,
    )

    turn = client.complete(instructions="policy", messages=[], tools=[])

    assert turn.final_text is None
    assert len(turn.function_calls) == 1


def test_sdk_is_initialized_with_virtual_key_and_custom_base_url(
    monkeypatch,
) -> None:
    captured: dict[str, str] = {}

    def fake_sdk(**kwargs: str) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("app.clients.openai_client.SDKOpenAI", fake_sdk)

    OpenAIClient("virtual-key", "https://copa.codyssey.kr/v1", "gpt-5-mini", 500)

    assert captured == {
        "api_key": "virtual-key",
        "base_url": "https://copa.codyssey.kr/v1",
    }
