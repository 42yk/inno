from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.data import DataCreate


@pytest.mark.parametrize(
    "value",
    [Decimal("19.9"), Decimal("300.1"), Decimal("72.45")],
)
def test_invalid_weight_is_rejected(value: Decimal) -> None:
    with pytest.raises(ValidationError):
        DataCreate(date=date.today(), value=value, memo="")


def test_boundary_weights_are_accepted() -> None:
    assert DataCreate(date=date.today(), value=Decimal("20.0")).value == (
        Decimal("20.0")
    )
    assert DataCreate(date=date.today(), value=Decimal("300.0")).value == (
        Decimal("300.0")
    )


def test_future_date_is_rejected() -> None:
    with pytest.raises(ValidationError, match="future dates"):
        DataCreate(
            date=date.today() + timedelta(days=1),
            value=Decimal("72.4"),
        )


def test_memo_longer_than_200_characters_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DataCreate(
            date=date.today(),
            value=Decimal("72.4"),
            memo="a" * 201,
        )
