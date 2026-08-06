from dataclasses import dataclass
import logging

import pytest

from review_analytics.dto import CleanRequest
from review_analytics.errors import NotFoundError, PersistenceError
from review_analytics.models import CleanStatus, RawReview, TargetMode


@dataclass
class FakeReviewRepository:
    targets: tuple[RawReview, ...]

    def __post_init__(self):
        self.cleaned = []
        self.rejected = []

    def select_raw_targets(self, target_mode, review_id=None):
        return self.targets

    def save_clean(self, raw_review_id, clean):
        self.cleaned.append((raw_review_id, clean))

    def reject_clean(self, raw_review_id, rejection_reason):
        self.rejected.append((raw_review_id, rejection_reason))


def _raw(review_id, text, rating="5"):
    return RawReview(
        id=review_id,
        fingerprint=f"fingerprint-{review_id}",
        review_text_raw=text,
        rating_raw=rating,
        review_date_raw="2026-08-01",
        product_name_raw="Bottle",
        source_type="csv",
        source_ref="reviews.csv",
        source_row=review_id + 1,
        clean_status=CleanStatus.PENDING,
        rejection_reason=None,
        created_at="2026-08-01T00:00:00+00:00",
        updated_at="2026-08-01T00:00:00+00:00",
    )


def test_clean_reviews_saves_accepted_rows_and_rejects_invalid_rows_without_logging_text(caplog):
    """Treating a validation rejection as a crash loses useful status, while logging raw text leaks user data."""
    from review_analytics.services.cleaning import clean_reviews

    repo = FakeReviewRepository((_raw(1, "  excellent   bottle "), _raw(2, "bad", "6")))

    summary = clean_reviews(CleanRequest(TargetMode.PENDING), repo, minimum_review_length=5)

    assert summary.processed == 2
    assert (summary.succeeded, summary.skipped, summary.failed, summary.rejected) == (1, 0, 0, 1)
    assert repo.cleaned[0][0] == 1
    assert repo.cleaned[0][1].review_text == "excellent bottle"
    assert repo.rejected == [(2, "INVALID_RATING")]
    assert "bad" not in caplog.text
    rejection = next(record for record in caplog.records if "event=clean.rejected" in record.getMessage())
    assert rejection.levelno == logging.WARNING
    assert "review_id=2 reason_code=INVALID_RATING" in rejection.getMessage()


def test_clean_reviews_uses_requested_target_and_returns_empty_summary_when_none_found():
    """Cleaning a different target than requested would mutate reviews outside the command scope."""
    from review_analytics.services.cleaning import clean_reviews

    repo = FakeReviewRepository(())

    summary = clean_reviews(CleanRequest(TargetMode.ALL), repo, minimum_review_length=5)

    assert summary.processed == 0
    assert (summary.succeeded, summary.skipped, summary.failed, summary.rejected) == (0, 0, 0, 0)
    assert repo.cleaned == []


def test_clean_reviews_raises_not_found_for_a_missing_explicit_id():
    """Treating a missing --id as an empty batch would hide a user-targeting error."""
    from review_analytics.services.cleaning import clean_reviews

    with pytest.raises(NotFoundError) as raised:
        clean_reviews(CleanRequest(TargetMode.ID, review_id=99), FakeReviewRepository(()), minimum_review_length=5)

    assert raised.value.code == "RAW_REVIEW_NOT_FOUND"


def test_clean_reviews_aggregates_persistence_errors_and_continues_with_later_rows(caplog):
    """Aborting later rows after one repository failure would discard recoverable clean work."""
    from review_analytics.services.cleaning import clean_reviews

    class PartiallyFailingRepository(FakeReviewRepository):
        def save_clean(self, raw_review_id, clean):
            if raw_review_id == 1:
                raise PersistenceError("SECRET review", "CLEAN_SAVE_FAILED")
            super().save_clean(raw_review_id, clean)

    repo = PartiallyFailingRepository((_raw(1, "SECRET review one"), _raw(2, "SECRET review two")))
    caplog.set_level(logging.WARNING, logger="review_analytics.services.cleaning")

    summary = clean_reviews(CleanRequest(TargetMode.PENDING), repo, minimum_review_length=5)

    assert (summary.processed, summary.succeeded, summary.skipped, summary.failed, summary.rejected) == (
        2,
        1,
        0,
        1,
        0,
    )
    assert [raw_id for raw_id, _ in repo.cleaned] == [2]
    warning = next(record for record in caplog.records if "event=clean.row.failed" in record.getMessage())
    assert warning.levelno == logging.WARNING
    assert "review_id=1 error_code=CLEAN_SAVE_FAILED" in warning.getMessage()
    assert "SECRET" not in caplog.text
