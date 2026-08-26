from datetime import date
from decimal import Decimal

import pytest

from app.errors import DuplicateDateError, InvalidPeriodError, RecordNotFoundError
from app.schemas.data import DataCreate, DataUpdate
from app.services.data_service import DataService
from app.services.summary_service import SummaryService
from tests.fakes.repositories import InMemoryDataRepository


@pytest.fixture
def data_service() -> DataService:
    return DataService(InMemoryDataRepository())


def create(
    service: DataService,
    day: int,
    value: str = "72.4",
) -> None:
    service.create_record(
        DataCreate(
            date=date(2025, 1, day),
            value=Decimal(value),
        )
    )


def test_create_rejects_duplicate_date(data_service: DataService) -> None:
    create(data_service, 1)

    with pytest.raises(DuplicateDateError):
        create(data_service, 1)


def test_list_filters_inclusive_range_and_orders_descending(
    data_service: DataService,
) -> None:
    for day in (1, 2, 3, 4):
        create(data_service, day)

    records = data_service.list_records(
        start_date=date(2025, 1, 2),
        end_date=date(2025, 1, 3),
        descending=True,
    )

    assert [record.date for record in records] == [
        date(2025, 1, 3),
        date(2025, 1, 2),
    ]


def test_list_rejects_reversed_period(data_service: DataService) -> None:
    with pytest.raises(InvalidPeriodError):
        data_service.list_records(
            start_date=date(2025, 1, 2),
            end_date=date(2025, 1, 1),
        )


def test_update_moves_document_id_and_preserves_created_at(
    data_service: DataService,
) -> None:
    create(data_service, 1)
    original = data_service.find_record("2025-01-01")

    updated = data_service.update_record(
        "2025-01-01",
        DataUpdate(date=date(2025, 1, 2), value=Decimal("72.2")),
    )

    assert updated.id == "2025-01-02"
    assert updated.created_at == original.created_at
    assert data_service.find_record("2025-01-01") is None


def test_update_rejects_target_date_collision(data_service: DataService) -> None:
    create(data_service, 1)
    create(data_service, 2)

    with pytest.raises(DuplicateDateError):
        data_service.update_record(
            "2025-01-01",
            DataUpdate(date=date(2025, 1, 2), value=Decimal("72.2")),
        )


def test_update_and_delete_raise_for_missing_record(
    data_service: DataService,
) -> None:
    with pytest.raises(RecordNotFoundError):
        data_service.update_record(
            "missing",
            DataUpdate(date=date(2025, 1, 2), value=Decimal("72.2")),
        )
    with pytest.raises(RecordNotFoundError):
        data_service.delete_record("missing")


def test_summary_service_reuses_data_service_records(
    data_service: DataService,
) -> None:
    create(data_service, 1, "72.0")
    create(data_service, 2, "71.0")

    summary = SummaryService(data_service).get_summary()

    assert summary.count == 2
    assert summary.metrics.change == Decimal("-1.0")
