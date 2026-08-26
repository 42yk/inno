from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ValidationError

from app.errors import InvalidToolArgumentsError, UnknownToolError
from app.schemas.tools import DateArguments, EmptyArguments, PeriodArguments
from app.services.data_service import DataService
from app.services.summary_service import SummaryService


ToolHandler = Callable[[BaseModel], dict[str, Any]]


class ToolService:
    def __init__(
        self,
        data_service: DataService,
        summary_service: SummaryService,
    ) -> None:
        self._data_service = data_service
        self._summary_service = summary_service
        self._tools: dict[
            str,
            tuple[type[BaseModel], ToolHandler, str],
        ] = {
            "get_weight_summary": (
                EmptyArguments,
                self._get_summary,
                "저장된 전체 체중 기록의 기간, 통계와 최근 추세를 조회합니다.",
            ),
            "get_weight_by_date": (
                DateArguments,
                self._get_by_date,
                "특정 날짜에 저장된 체중 기록을 정확히 조회합니다.",
            ),
            "get_weight_records": (
                PeriodArguments,
                self._get_records,
                "시작일과 종료일을 포함한 기간의 체중 기록을 조회합니다.",
            ),
            "get_weight_statistics": (
                PeriodArguments,
                self._get_statistics,
                "시작일과 종료일을 포함한 기간의 체중 통계를 계산합니다.",
            ),
        }

    def definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": arguments_model.model_json_schema(),
                    "strict": True,
                },
            }
            for name, (arguments_model, _handler, description) in self._tools.items()
        ]

    def execute(
        self,
        name: str,
        raw_arguments: str | dict[str, object],
    ) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            raise UnknownToolError(name)
        arguments_model, handler, _description = tool
        try:
            if isinstance(raw_arguments, str):
                decoded = json.loads(raw_arguments)
            else:
                decoded = raw_arguments
            if not isinstance(decoded, dict):
                raise TypeError("tool arguments must be an object")
            arguments = arguments_model.model_validate(decoded)
        except (json.JSONDecodeError, TypeError, ValidationError) as exc:
            raise InvalidToolArgumentsError(name) from exc
        return handler(arguments)

    def _get_summary(self, _arguments: BaseModel) -> dict[str, Any]:
        return self._summary_service.get_summary().model_dump(mode="json")

    def _get_by_date(self, arguments: BaseModel) -> dict[str, Any]:
        validated = DateArguments.model_validate(arguments)
        record = self._data_service.find_record(validated.date.isoformat())
        if record is None:
            return {"status": "not_found", "date": validated.date.isoformat()}
        return {
            "status": "found",
            "record": record.model_dump(mode="json"),
        }

    def _get_records(self, arguments: BaseModel) -> dict[str, Any]:
        validated = PeriodArguments.model_validate(arguments)
        records = self._data_service.list_records(
            start_date=validated.start_date,
            end_date=validated.end_date,
            descending=False,
        )
        return {
            "items": [record.model_dump(mode="json") for record in records],
            "count": len(records),
        }

    def _get_statistics(self, arguments: BaseModel) -> dict[str, Any]:
        validated = PeriodArguments.model_validate(arguments)
        statistics = self._summary_service.get_period_statistics(
            validated.start_date,
            validated.end_date,
        )
        return statistics.model_dump(mode="json")
