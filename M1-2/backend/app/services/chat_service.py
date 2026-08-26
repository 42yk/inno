from __future__ import annotations

import json
from typing import Any, Protocol

from app.clients.openai_client import ModelTurn
from app.errors import (
    AIProviderError,
    InvalidToolArgumentsError,
    ToolCallLimitError,
    UnknownToolError,
)
from app.schemas.chat import ChatRequest, ChatResult
from app.services.conversation_service import ConversationService
from app.services.summary_service import SummaryService
from app.services.tool_service import ToolService


class AIClient(Protocol):
    def complete(
        self,
        *,
        instructions: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, object]],
    ) -> ModelTurn: ...


def build_instructions(summary: dict[str, Any]) -> str:
    summary_json = json.dumps(summary, ensure_ascii=False, indent=2)
    return f"""당신은 개인 체중 기록 분석 비서입니다.

[사용자 데이터 요약]
{summary_json}

다음 정책을 반드시 지키세요.
- 저장된 요약과 도구 조회 결과만 근거로 답하세요.
- 특정 날짜나 기간의 구체적인 질문에는 적절한 읽기 전용 도구를 사용하세요.
- 기록이 없는 날짜의 체중을 추정하거나 만들어내지 마세요.
- 체중 변화에 대한 의료 진단, 질병 판단 또는 치료 지시는 하지 마세요.
- 답변은 한국어로 간결하고 명확하게 작성하세요.
"""


class ChatService:
    def __init__(
        self,
        *,
        ai_client: AIClient,
        summary_service: SummaryService,
        tool_service: ToolService,
        conversation_service: ConversationService,
        max_tool_calls: int,
    ) -> None:
        self._ai_client = ai_client
        self._summary_service = summary_service
        self._tool_service = tool_service
        self._conversation_service = conversation_service
        self._max_tool_calls = max_tool_calls

    def _complete(
        self,
        instructions: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, object]],
    ) -> ModelTurn:
        try:
            return self._ai_client.complete(
                instructions=instructions,
                messages=messages,
                tools=tools,
            )
        except Exception as exc:
            raise AIProviderError() from exc

    def chat(self, request: ChatRequest) -> ChatResult:
        summary = self._summary_service.get_summary()
        instructions = build_instructions(summary.model_dump(mode="json"))
        messages: list[dict[str, Any]] = []
        if request.conversation_id is not None:
            conversation = self._conversation_service.get(request.conversation_id)
            messages.extend(
                {"role": message.role, "content": message.content}
                for message in conversation.messages
            )
        messages.append({"role": "user", "content": request.message})
        tools = self._tool_service.definitions()
        turn = self._complete(instructions, messages, tools)
        tools_used: list[str] = []
        call_count = 0

        while True:
            if turn.final_text is not None:
                saved = self._conversation_service.append_exchange(
                    request.conversation_id,
                    request.message,
                    turn.final_text,
                )
                return ChatResult(
                    conversation_id=saved.id,
                    answer=turn.final_text,
                    tools_used=tools_used,
                )
            if not turn.function_calls:
                raise AIProviderError()
            if call_count + len(turn.function_calls) > self._max_tool_calls:
                raise ToolCallLimitError()

            messages.append(
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": call.call_id,
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": call.arguments,
                            },
                        }
                        for call in turn.function_calls
                    ],
                }
            )
            for call in turn.function_calls:
                call_count += 1
                tools_used.append(call.name)
                try:
                    result = self._tool_service.execute(call.name, call.arguments)
                except InvalidToolArgumentsError:
                    result = {
                        "ok": False,
                        "error": {"code": "invalid_tool_arguments"},
                    }
                except UnknownToolError:
                    result = {
                        "ok": False,
                        "error": {"code": "unknown_tool"},
                    }
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.call_id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
            turn = self._complete(instructions, messages, tools)
