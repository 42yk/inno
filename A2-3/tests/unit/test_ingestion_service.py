from dataclasses import dataclass
import logging

import pytest

from review_analytics.dto import ImportRequest, RawSaveResult
from review_analytics.errors import InputFileError, PersistenceError
from review_analytics.models import DuplicatePolicy, RawReviewInput, RawSaveAction


@dataclass
class FakeReviewRepository:
    results: list[RawSaveAction]

    def __post_init__(self):
        self.saved: list[tuple[RawReviewInput, str, DuplicatePolicy]] = []

    def save_raw(self, raw, fingerprint, duplicate_policy):
        self.saved.append((raw, fingerprint, duplicate_policy))
        return RawSaveResult(len(self.saved), self.results[len(self.saved) - 1])


def test_import_reviews_counts_insert_skip_and_upsert(tmp_path):
    """Collapsing duplicate actions into success would hide whether policy selection worked."""
    from review_analytics.services.ingestion import import_reviews

    path = tmp_path / "reviews.csv"
    inputs = (
        RawReviewInput("first", product_name_raw="Bottle", review_date_raw="2026-08-01"),
        RawReviewInput("first", product_name_raw="Bottle", review_date_raw="2026-08-01"),
        RawReviewInput("second"),
    )
    repo = FakeReviewRepository([RawSaveAction.INSERTED, RawSaveAction.SKIPPED, RawSaveAction.UPSERTED])

    summary = import_reviews(ImportRequest(path, DuplicatePolicy.UPSERT), repo, lambda _: inputs)

    assert summary.processed == 3
    assert (summary.succeeded, summary.skipped, summary.failed) == (2, 1, 0)
    assert [saved[2] for saved in repo.saved] == [DuplicatePolicy.UPSERT] * 3


def test_import_reviews_validates_entire_file_before_any_database_write(tmp_path):
    """Saving before the reader validates its header would leave an invalid import partially stored."""
    from review_analytics.services.ingestion import import_reviews

    path = tmp_path / "bad.csv"
    repo = FakeReviewRepository([])

    def invalid_reader(_):
        raise InputFileError("missing review_text", "MISSING_REVIEW_TEXT_COLUMN")

    with pytest.raises(InputFileError):
        import_reviews(ImportRequest(path), repo, invalid_reader)

    assert repo.saved == []


def test_import_reviews_aggregates_persistence_failure_and_logs_only_safe_fields(tmp_path, caplog):
    """Stopping at one failed row or logging its raw values would break partial-import safety."""
    from review_analytics.services.ingestion import import_reviews

    class PartiallyFailingRepository:
        def __init__(self):
            self.saved = []

        def save_raw(self, raw, fingerprint, duplicate_policy):
            self.saved.append(raw)
            if len(self.saved) == 2:
                raise PersistenceError("SECRET review and product", "RAW_SAVE_FAILED")
            return RawSaveResult(len(self.saved), RawSaveAction.INSERTED)

    inputs = (
        RawReviewInput("SECRET review 1", product_name_raw="SECRET product"),
        RawReviewInput("SECRET review 2", product_name_raw="SECRET product"),
        RawReviewInput("SECRET review 3", product_name_raw="SECRET product"),
    )
    caplog.set_level(logging.INFO, logger="review_analytics.services.ingestion")

    summary = import_reviews(ImportRequest(tmp_path / "reviews.csv"), PartiallyFailingRepository(), lambda _: inputs)

    assert (summary.processed, summary.succeeded, summary.skipped, summary.failed) == (3, 2, 0, 1)
    warning = next(record for record in caplog.records if "event=import.row.failed" in record.getMessage())
    assert warning.levelno == logging.WARNING
    assert "error_code=RAW_SAVE_FAILED" in warning.getMessage()
    assert "SECRET" not in caplog.text
