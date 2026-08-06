"""원본 리뷰 입력의 순수 정제·검증 규칙을 제공한다."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum

from review_analytics.models import CleanReview, RawReviewInput
from review_analytics.rules.normalization import normalize_date, normalize_text


class CleanRejectionCode(str, Enum):
    MISSING_REVIEW_TEXT = "MISSING_REVIEW_TEXT"
    INVALID_RATING = "INVALID_RATING"
    INVALID_REVIEW_DATE = "INVALID_REVIEW_DATE"
    REVIEW_TEXT_TOO_SHORT = "REVIEW_TEXT_TOO_SHORT"


@dataclass(frozen=True)
class CleanReviewResult:
    clean_review: CleanReview | None
    rejection_code: CleanRejectionCode | None = None

    # 정제 결과에 저장 가능한 리뷰가 있는지 알려준다.
    @property
    def accepted(self) -> bool:
        return self.clean_review is not None


# 원본 리뷰를 검증·정규화하여 정제 결과 또는 거절 코드를 만든다.
def clean_review(raw: RawReviewInput, minimum_review_length: int) -> CleanReviewResult:
    """Validate raw values and either return a clean review or one stable rejection code."""
    review_text = normalize_text(raw.review_text_raw)
    if not review_text:
        return CleanReviewResult(None, CleanRejectionCode.MISSING_REVIEW_TEXT)

    rating = _normalize_rating(raw.rating_raw)
    if rating is _INVALID:
        return CleanReviewResult(None, CleanRejectionCode.INVALID_RATING)

    review_date = normalize_date(raw.review_date_raw)
    if raw.review_date_raw is not None and normalize_text(raw.review_date_raw) and review_date is None:
        return CleanReviewResult(None, CleanRejectionCode.INVALID_REVIEW_DATE)

    if len(review_text) < minimum_review_length:
        return CleanReviewResult(None, CleanRejectionCode.REVIEW_TEXT_TOO_SHORT)

    product_name = normalize_text(raw.product_name_raw) or None
    return CleanReviewResult(CleanReview(review_text, rating, review_date, product_name))


_INVALID = object()


# 선택 별점을 1~5 정수로 정규화하거나 잘못된 값을 표시한다.
def _normalize_rating(value: object) -> int | None | object:
    if value is None or not normalize_text(value):
        return None
    if isinstance(value, bool):
        return _INVALID
    try:
        decimal = Decimal(normalize_text(value))
    except InvalidOperation:
        return _INVALID
    if not decimal.is_finite() or decimal != decimal.to_integral_value():
        return _INVALID
    rating = int(decimal)
    return rating if 1 <= rating <= 5 else _INVALID
