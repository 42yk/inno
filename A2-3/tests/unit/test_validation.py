from datetime import datetime

from review_analytics.models import RawReviewInput
from review_analytics.rules.validation import CleanRejectionCode, clean_review


def test_clean_review_normalizes_valid_raw_input():
    """Skipping clean normalization would store raw formatting in the clean stage."""
    result = clean_review(
        RawReviewInput("  \uc88b\uc740\n\uc81c\ud488\uc785\ub2c8\ub2e4  ", "5", "2026/08/01", " \ud150\ube14\ub7ec "),
        minimum_review_length=5,
    )

    assert result.accepted is True
    assert result.clean_review is not None
    assert result.clean_review.review_text == "\uc88b\uc740 \uc81c\ud488\uc785\ub2c8\ub2e4"
    assert result.clean_review.rating == 5
    assert result.clean_review.review_date == "2026-08-01"
    assert result.clean_review.product_name == "\ud150\ube14\ub7ec"


def test_clean_review_accepts_excel_datetime_date_values():
    """Rejecting an Excel datetime would prevent clean rows from being created from XLSX input."""
    result = clean_review(
        RawReviewInput("\uc88b\uc740 \uc81c\ud488\uc785\ub2c8\ub2e4", "5", datetime(2026, 8, 1, 14, 30), None),
        minimum_review_length=5,
    )

    assert result.accepted is True
    assert result.clean_review is not None
    assert result.clean_review.review_date == "2026-08-01"


def test_clean_review_returns_missing_text_rejection_code():
    """Accepting blank text would violate the clean-stage required-field contract."""
    result = clean_review(RawReviewInput(" \t\n ", None, None, None), minimum_review_length=5)

    assert result.accepted is False
    assert result.clean_review is None
    assert result.rejection_code is CleanRejectionCode.MISSING_REVIEW_TEXT


def test_clean_review_returns_invalid_rating_rejection_code():
    """Accepting an out-of-range rating would violate the persisted clean model."""
    result = clean_review(RawReviewInput("\ucd5c\uace0\uc785\ub2c8\ub2e4", "6", None, None), minimum_review_length=5)

    assert result.accepted is False
    assert result.rejection_code is CleanRejectionCode.INVALID_RATING


def test_clean_review_returns_invalid_date_and_short_text_rejection_codes():
    """Removing date or length checks would accept values the schema forbids."""
    invalid_date = clean_review(RawReviewInput("\uc88b\uc740 \uc81c\ud488\uc785\ub2c8\ub2e4", "5", "not-a-date", None), minimum_review_length=5)
    short_text = clean_review(RawReviewInput("\uc88b\uc544", "5", None, None), minimum_review_length=5)

    assert invalid_date.rejection_code is CleanRejectionCode.INVALID_REVIEW_DATE
    assert short_text.rejection_code is CleanRejectionCode.REVIEW_TEXT_TOO_SHORT
