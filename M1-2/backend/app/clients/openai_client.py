from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openai import OpenAI as SDKOpenAI


@dataclass(frozen=True)
class FunctionCall:
    call_id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class ToolOutput:
    call_id: str
    output: str


@dataclass(frozen=True)
class ModelTurn:
    response_id: str
    final_text: str | None
    function_calls: list[FunctionCall]


class OpenAIClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        max_output_tokens: int,
        *,
        sdk_client: Any | None = None,
    ) -> None:
        self._client = sdk_client or SDKOpenAI(api_key=api_key)
        self._model = model
        self._max_output_tokens = max_output_tokens

    @staticmethod
    def _to_turn(response: Any) -> ModelTurn:
        function_calls = [
            FunctionCall(
                call_id=item.call_id,
                name=item.name,
                arguments=item.arguments,
            )
            for item in response.output
            if item.type == "function_call"
        ]
        text = (response.output_text or "").strip()
        return ModelTurn(
            response_id=response.id,
            final_text=None if function_calls else (text or None),
            function_calls=function_calls,
        )

    def start(
        self,
        *,
        instructions: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]],
    ) -> ModelTurn:
        response = self._client.responses.create(
            model=self._model,
            instructions=instructions,
            input=messages,
            tools=tools,
            max_output_tokens=self._max_output_tokens,
            parallel_tool_calls=False,
            store=True,
        )
        return self._to_turn(response)

    def continue_with_tools(
        self,
        *,
        previous_response_id: str,
        outputs: list[ToolOutput],
        instructions: str,
        tools: list[dict[str, object]],
    ) -> ModelTurn:
        response = self._client.responses.create(
            model=self._model,
            previous_response_id=previous_response_id,
            instructions=instructions,
            input=[
                {
                    "type": "function_call_output",
                    "call_id": output.call_id,
                    "output": output.output,
                }
                for output in outputs
            ],
            tools=tools,
            max_output_tokens=self._max_output_tokens,
            parallel_tool_calls=False,
            store=True,
        )
        return self._to_turn(response)
