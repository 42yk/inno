from datetime import datetime

from review_analytics.rules.duplicate_policy import fingerprint_review
from review_analytics.rules.normalization import normalize_date, normalize_text


def test_normalize_text_nfkc_trims_and_collapses_whitespace():
    """Dropping any normalization step would make equivalent review text diverge."""
    assert normalize_text("  \uff26\uff55\uff4c\uff4c\u3000width\n\ttext  ") == "Full width text"


def test_normalize_date_accepts_documented_slash_format_as_iso_date():
    """Changing accepted date parsing would prevent equivalent dates from matching."""
    assert normalize_date("2026/08/01") == "2026-08-01"


def test_normalize_date_accepts_excel_datetime_values_directly():
    """Stringifying an Excel datetime would reject a valid review date."""
    assert normalize_date(datetime(2026, 8, 1, 14, 30)) == "2026-08-01"


def test_fingerprint_ignores_rating_and_normalizes_components():
    """Including a rating or skipping normalization would break documented duplicate detection."""
    assert fingerprint_review(" \uc88b\uc740\n\uc81c\ud488 ", "Cup", "2026/08/01") == fingerprint_review(
        "\uc88b\uc740 \uc81c\ud488", "cup", "2026-08-01"
    )


def test_fingerprint_changes_when_normalized_product_or_date_differs():
    """Omitting a fingerprint component would merge distinct reviews."""
    original = fingerprint_review("same text", "cup", "2026-08-01")
    assert original != fingerprint_review("same text", "bottle", "2026-08-01")
    assert original != fingerprint_review("same text", "cup", "2026-08-02")
