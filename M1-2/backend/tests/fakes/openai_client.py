from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.clients.openai_client import ModelTurn, ToolOutput


class ScriptedOpenAIClient:
    def __init__(self, turns: Sequence[ModelTurn | Exception]) -> None:
        self.turns = list(turns)
        self.start_calls: list[dict[str, Any]] = []
        self.continue_calls: list[dict[str, Any]] = []

    def _next(self) -> ModelTurn:
        if not self.turns:
            raise AssertionError("No scripted model turn remains")
        result = self.turns.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def start(
        self,
        *,
        instructions: str,
        messages: list[dict[str, str]],
        tools: list[dict[str, object]],
    ) -> ModelTurn:
        self.start_calls.append(
            {
                "instructions": instructions,
                "messages": messages,
                "tools": tools,
            }
        )
        return self._next()

    def continue_with_tools(
        self,
        *,
        previous_response_id: str,
        outputs: list[ToolOutput],
        instructions: str,
        tools: list[dict[str, object]],
    ) -> ModelTurn:
        self.continue_calls.append(
            {
                "previous_response_id": previous_response_id,
                "outputs": outputs,
                "instructions": instructions,
                "tools": tools,
            }
        )
        return self._next()
