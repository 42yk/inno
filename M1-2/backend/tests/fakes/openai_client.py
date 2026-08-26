from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.clients.openai_client import ModelTurn


class ScriptedOpenAIClient:
    def __init__(self, turns: Sequence[ModelTurn | Exception]) -> None:
        self.turns = list(turns)
        self.complete_calls: list[dict[str, Any]] = []

    def _next(self) -> ModelTurn:
        if not self.turns:
            raise AssertionError("No scripted model turn remains")
        result = self.turns.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def complete(
        self,
        *,
        instructions: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, object]],
    ) -> ModelTurn:
        self.complete_calls.append(
            {
                "instructions": instructions,
                "messages": messages,
                "tools": tools,
            }
        )
        return self._next()
