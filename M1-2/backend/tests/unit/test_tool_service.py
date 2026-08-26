import json
from datetime import date
from decimal import Decimal

import pytest

from app.errors import InvalidToolArgumentsError, UnknownToolError
from app.schemas.data import DataCreate
from app.services.data_service import DataService
from app.services.summary_service import SummaryService
from app.services.tool_service import ToolService
from tests.fakes.repositories import InMemoryDataRepository


@pytest.fixture
def tool_service() -> ToolService:
    data_service = DataService(InMemoryDataRepository())
    for day, value in ((1, "72.4"), (3, "72.0"), (5, "71.8")):
        data_service.create_record(
            DataCreate(
                date=date(2025, 1, day),
                value=Decimal(value),
                memo="",
            )
        )
    return ToolService(data_service, SummaryService(data_service))


def test_tool_definitions_are_strict_and_read_only(
    tool_service: ToolService,
) -> None:
    definitions = tool_service.definitions()

    assert {tool["function"]["name"] for tool in definitions} == {
        "get_weight_summary",
        "get_weight_by_date",
        "get_weight_records",
        "get_weight_statistics",
    }
    assert all(tool["type"] == "function" for tool in definitions)
    assert all(tool["function"]["strict"] is True for tool in definitions)
    assert all(
        tool["function"]["parameters"]["additionalProperties"] is False
        for tool in definitions
    )


def test_unknown_tool_is_rejected(tool_service: ToolService) -> None:
    with pytest.raises(UnknownToolError):
        tool_service.execute("remove_weight", {})


@pytest.mark.parametrize(
    "arguments",
    ["not-json", "[]", {"date": "invalid"}, {"date": "2025-01-01", "extra": 1}],
)
def test_invalid_arguments_are_rejected(
    tool_service: ToolService,
    arguments: str | dict[str, object],
) -> None:
    with pytest.raises(InvalidToolArgumentsError):
        tool_service.execute("get_weight_by_date", arguments)


def test_exact_date_returns_found_and_not_found(tool_service: ToolService) -> None:
    found = tool_service.execute(
        "get_weight_by_date",
        json.dumps({"date": "2025-01-03"}),
    )
    missing = tool_service.execute(
        "get_weight_by_date",
        {"date": "2025-01-02"},
    )

    assert found["status"] == "found"
    assert found["record"]["value"] == 72.0
    assert missing == {"status": "not_found", "date": "2025-01-02"}


def test_range_records_are_in_ascending_order(tool_service: ToolService) -> None:
    result = tool_service.execute(
        "get_weight_records",
        {"start_date": "2025-01-02", "end_date": "2025-01-05"},
    )

    assert [record["date"] for record in result["items"]] == [
        "2025-01-03",
        "2025-01-05",
    ]
    assert result["count"] == 2


def test_period_statistics_are_calculated_on_server(
    tool_service: ToolService,
) -> None:
    result = tool_service.execute(
        "get_weight_statistics",
        {"start_date": "2025-01-01", "end_date": "2025-01-05"},
    )

    assert result["count"] == 3
    assert result["metrics"]["average"] == 72.1
    assert result["period"] == {"start": "2025-01-01", "end": "2025-01-05"}


def test_summary_dispatches_shared_summary_service(
    tool_service: ToolService,
) -> None:
    result = tool_service.execute("get_weight_summary", {})

    assert result["count"] == 3
    assert result["metrics"]["latest"] == {
        "date": "2025-01-05",
        "value": 71.8,
    }


@pytest.mark.parametrize(
    "name",
    ["get_weight_records", "get_weight_statistics"],
)
def test_reversed_period_is_rejected_as_invalid_tool_arguments(
    tool_service: ToolService,
    name: str,
) -> None:
    with pytest.raises(InvalidToolArgumentsError):
        tool_service.execute(
            name,
            {"start_date": "2025-01-05", "end_date": "2025-01-01"},
        )
