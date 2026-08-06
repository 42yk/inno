from __future__ import annotations

from review_analytics.dto import (
    ExportRequest,
    ReviewDetailRequest,
    ReviewFilter,
    ReviewListRequest,
    StatsRequest,
)
from review_analytics.models import (
    AnalysisStatus,
    CleanReview,
    DuplicatePolicy,
    ExportFormat,
    RawReviewInput,
    Sentiment,
    SentimentResult,
    SortField,
    SortOrder,
)


def _raw(text: str, rating: str, date: str, product: str) -> RawReviewInput:
    return RawReviewInput(text, rating, date, product, "csv", "query.csv", 2)


def _seed_clean(reviews, raw: RawReviewInput, fingerprint: str):
    saved = reviews.save_raw(raw, fingerprint, DuplicatePolicy.SKIP)
    clean = reviews.save_clean(
        saved.review_id,
        CleanReview(str(raw.review_text_raw), int(raw.rating_raw), str(raw.review_date_raw), str(raw.product_name_raw)),
    )
    return saved, clean


def test_list_includes_unanalyzed_rows_and_sentiment_filter_excludes_them(initialized_repositories):
    """Default list must preserve clean rows that have no sentiment result."""
    from review_analytics.services.query import list_reviews

    reviews, analyses = initialized_repositories
    first, first_clean = _seed_clean(reviews, _raw("배송이 늦어요", "2", "2026-08-01", "Bottle"), "list-1")
    second, _ = _seed_clean(reviews, _raw("아직 분석 전", "3", "2026-08-02", "Bottle"), "list-2")
    analyses.save_sentiment_batch(
        (SentimentResult(first_clean.id, Sentiment.NEGATIVE, 0.91, "fake", "v1"),)
    )

    all_result = list_reviews(ReviewListRequest(size=10), reviews)
    filtered = list_reviews(
        ReviewListRequest(filter=ReviewFilter(sentiment=Sentiment.NEGATIVE), size=10),
        reviews,
    )

    assert [item.review_id for item in all_result.items] == [first.review_id, second.review_id]
    assert [item.analysis_status for item in all_result.items] == [AnalysisStatus.ANALYZED, AnalysisStatus.UNANALYZED]
    assert [item.review_id for item in filtered.items] == [first.review_id]


def test_list_out_of_range_page_is_empty_but_keeps_page_metadata(initialized_repositories):
    """An out-of-range page is a successful empty page, not a not-found error."""
    from review_analytics.services.query import list_reviews

    reviews, _ = initialized_repositories
    _seed_clean(reviews, _raw("좋아요", "5", "2026-08-01", "Bottle"), "page-1")

    result = list_reviews(
        ReviewListRequest(page=3, size=1, sort_by=SortField.ID, order=SortOrder.ASC),
        reviews,
    )

    assert result.items == ()
    assert (result.total_items, result.page, result.size, result.total_pages) == (1, 3, 1, 1)


def test_show_preserves_pending_rejected_and_analyzed_states(initialized_repositories):
    """All raw lifecycle states need the same stable detail DTO fields."""
    from review_analytics.services.query import show_review

    reviews, analyses = initialized_repositories
    pending = reviews.save_raw(_raw("대기 리뷰", "4", "2026-08-01", "Bottle"), "show-pending", DuplicatePolicy.SKIP)
    rejected = reviews.save_raw(_raw("x", "9", "bad", "Bottle"), "show-rejected", DuplicatePolicy.SKIP)
    reviews.reject_clean(rejected.review_id, "INVALID_RATING")
    analyzed, analyzed_clean = _seed_clean(reviews, _raw("아주 좋아요", "5", "2026-08-03", "Bottle"), "show-analyzed")
    analyses.save_sentiment_batch(
        (SentimentResult(analyzed_clean.id, Sentiment.POSITIVE, 0.96, "fake", "v1", "2026-08-06T00:00:00+00:00"),)
    )

    pending_result = show_review(ReviewDetailRequest(pending.review_id), reviews)
    rejected_result = show_review(ReviewDetailRequest(rejected.review_id), reviews)
    analyzed_result = show_review(ReviewDetailRequest(analyzed.review_id), reviews)

    assert pending_result.clean_review is None and pending_result.analysis_status is AnalysisStatus.UNANALYZED
    assert rejected_result.clean_review is None and rejected_result.rejection_reason == "INVALID_RATING"
    assert analyzed_result.clean_review is not None
    assert (analyzed_result.sentiment, analyzed_result.model_name) == (Sentiment.POSITIVE, "fake")


def test_stats_and_export_share_product_date_and_sentiment_filter_semantics(initialized_repositories, tmp_path):
    """Stats and export must select the same rows for one common filter."""
    from openpyxl import load_workbook
    from review_analytics.services.exporting import export_reviews
    from review_analytics.services.query import get_stats

    reviews, analyses = initialized_repositories
    first, first_clean = _seed_clean(reviews, _raw("나쁨", "1", "2026-08-02", "Bottle"), "filter-1")
    second, second_clean = _seed_clean(reviews, _raw("좋음", "5", "2026-07-01", "Bottle"), "filter-2")
    _seed_clean(reviews, _raw("다른 제품", "1", "2026-08-02", "Cup"), "filter-3")
    analyses.save_sentiment_batch(
        (
            SentimentResult(first_clean.id, Sentiment.NEGATIVE, 0.8, "fake", "v1"),
            SentimentResult(second_clean.id, Sentiment.POSITIVE, 0.9, "fake", "v1"),
        )
    )
    review_filter = ReviewFilter(
        sentiment=Sentiment.NEGATIVE,
        product="Bottle",
        date_from="2026-08-01",
        date_to="2026-08-31",
    )
    stats = get_stats(StatsRequest(review_filter), reviews)
    output = tmp_path / "filtered.xlsx"
    generated = export_reviews(ExportRequest(review_filter, ExportFormat.XLSX, output), reviews)

    assert stats.total_clean == 1
    assert stats.sentiment_counts == (
        (Sentiment.POSITIVE, 0),
        (Sentiment.NEUTRAL, 0),
        (Sentiment.NEGATIVE, 1),
    )
    assert generated.record_count == 1
    workbook = load_workbook(output, read_only=True)
    try:
        values = list(workbook.active.values)
    finally:
        workbook.close()
    assert values[1][0] == first.review_id

