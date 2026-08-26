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
class ModelTurn:
    final_text: str | None
    function_calls: list[FunctionCall]


class OpenAIClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        max_output_tokens: int,
        *,
        sdk_client: Any | None = None,
    ) -> None:
        self._client = sdk_client or SDKOpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        self._model = model
        self._max_output_tokens = max_output_tokens

    @staticmethod
    def _to_turn(response: Any) -> ModelTurn:
        if not response.choices:
            raise ValueError("Chat completion returned no choices")
        message = response.choices[0].message
        function_calls = [
            FunctionCall(
                call_id=tool_call.id,
                name=tool_call.function.name,
                arguments=tool_call.function.arguments,
            )
            for tool_call in (message.tool_calls or [])
            if tool_call.type == "function"
        ]
        text = (message.content or "").strip()
        return ModelTurn(
            final_text=None if function_calls else (text or None),
            function_calls=function_calls,
        )

    def complete(
        self,
        *,
        instructions: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, object]],
    ) -> ModelTurn:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": instructions},
                *messages,
            ],
            tools=tools,
            tool_choice="auto",
            max_completion_tokens=self._max_output_tokens,
        )
        return self._to_turn(response)
