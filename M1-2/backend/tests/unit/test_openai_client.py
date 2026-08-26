from types import SimpleNamespace

from app.clients.openai_client import OpenAIClient, ToolOutput


class FakeResponses:
    def __init__(self, responses: list[object]) -> None:
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return self.responses.pop(0)


def sdk_with(responses: list[object]) -> tuple[object, FakeResponses]:
    fake = FakeResponses(responses)
    return SimpleNamespace(responses=fake), fake


def test_start_maps_function_calls_and_uses_responses_api_contract() -> None:
    response = SimpleNamespace(
        id="response-1",
        output_text="",
        output=[
            SimpleNamespace(
                type="function_call",
                call_id="call-1",
                name="get_weight_by_date",
                arguments='{"date":"2025-03-10"}',
            )
        ],
    )
    sdk, responses = sdk_with([response])
    client = OpenAIClient(
        api_key="test-key",
        model="test-model",
        max_output_tokens=321,
        sdk_client=sdk,
    )
    tools = [{"type": "function", "name": "get_weight_by_date"}]

    turn = client.start(
        instructions="policy",
        messages=[{"role": "user", "content": "질문"}],
        tools=tools,
    )

    assert turn.response_id == "response-1"
    assert turn.final_text is None
    assert turn.function_calls[0].call_id == "call-1"
    assert responses.calls[0] == {
        "model": "test-model",
        "instructions": "policy",
        "input": [{"role": "user", "content": "질문"}],
        "tools": tools,
        "max_output_tokens": 321,
        "parallel_tool_calls": False,
        "store": True,
    }


def test_continue_sends_call_outputs_with_previous_response_id() -> None:
    response = SimpleNamespace(id="response-2", output_text="최종 답변", output=[])
    sdk, responses = sdk_with([response])
    client = OpenAIClient(
        api_key="test-key",
        model="test-model",
        max_output_tokens=321,
        sdk_client=sdk,
    )
    tools = [{"type": "function", "name": "get_weight_summary"}]

    turn = client.continue_with_tools(
        previous_response_id="response-1",
        outputs=[ToolOutput(call_id="call-1", output='{"count":120}')],
        instructions="policy",
        tools=tools,
    )

    assert turn.final_text == "최종 답변"
    assert responses.calls[0]["previous_response_id"] == "response-1"
    assert responses.calls[0]["instructions"] == "policy"
    assert responses.calls[0]["tools"] == tools
    assert responses.calls[0]["input"] == [
        {
            "type": "function_call_output",
            "call_id": "call-1",
            "output": '{"count":120}',
        }
    ]


def test_text_is_ignored_until_function_calls_are_resolved() -> None:
    response = SimpleNamespace(
        id="response-mixed",
        output_text="중간 문장",
        output=[
            SimpleNamespace(
                type="function_call",
                call_id="call-1",
                name="get_weight_summary",
                arguments="{}",
            )
        ],
    )
    sdk, _responses = sdk_with([response])
    client = OpenAIClient("test-key", "test-model", 321, sdk_client=sdk)

    turn = client.start(instructions="policy", messages=[], tools=[])

    assert turn.final_text is None
    assert len(turn.function_calls) == 1
