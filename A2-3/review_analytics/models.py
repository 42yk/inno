"""인프라 의존성이 없는 불변 도메인 모델을 정의한다."""

from dataclasses import dataclass
from enum import Enum


class DuplicatePolicy(str, Enum):
    SKIP = "skip"
    UPSERT = "upsert"


class CleanStatus(str, Enum):
    PENDING = "pending"
    CLEANED = "cleaned"
    REJECTED = "rejected"


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class AnalysisStatus(str, Enum):
    UNANALYZED = "unanalyzed"
    ANALYZED = "analyzed"


class TargetMode(str, Enum):
    PENDING = "pending"
    ALL = "all"
    ID = "id"
    UNANALYZED = "unanalyzed"


class SortField(str, Enum):
    ID = "id"
    REVIEW_DATE = "review_date"
    RATING = "rating"
    SENTIMENT = "sentiment"
    CONFIDENCE = "confidence"


class SortOrder(str, Enum):
    ASC = "asc"
    DESC = "desc"


class ReportFormat(str, Enum):
    TXT = "txt"
    MD = "md"


class ExportFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"


class RawSaveAction(str, Enum):
    INSERTED = "inserted"
    SKIPPED = "skipped"
    UPSERTED = "upserted"


@dataclass(frozen=True)
class RawReviewInput:
    review_text_raw: object
    rating_raw: object | None = None
    review_date_raw: object | None = None
    product_name_raw: object | None = None
    source_type: str | None = None
    source_ref: str | None = None
    source_row: int | None = None


@dataclass(frozen=True)
class RawReview:
    id: int
    fingerprint: str
    review_text_raw: str
    rating_raw: str | None
    review_date_raw: str | None
    product_name_raw: str | None
    source_type: str
    source_ref: str
    source_row: int | None
    clean_status: CleanStatus
    rejection_reason: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class CleanReview:
    review_text: str
    rating: int | None
    review_date: str | None
    product_name: str | None
    id: int | None = None
    raw_review_id: int | None = None
    cleaning_version: str = "1"
    cleaned_at: str | None = None


@dataclass(frozen=True)
class SentimentResult:
    clean_review_id: int
    sentiment: Sentiment
    confidence: float
    model_name: str
    prompt_version: str
    analyzed_at: str | None = None
    id: int | None = None


@dataclass(frozen=True)
class AnalysisInput:
    review_id: int
    review_text: str


@dataclass(frozen=True)
class KeywordEvidence:
    keyword: str
    review_ids: tuple[int, ...]


@dataclass(frozen=True)
class InsightInput:
    scope_hash: str
    reviews: tuple[AnalysisInput, ...]


@dataclass(frozen=True)
class InsightResult:
    positive_keywords: tuple[KeywordEvidence, ...]
    negative_keywords: tuple[KeywordEvidence, ...]
    summary: str
    recommendations: tuple[str, ...]
    model_name: str
    prompt_version: str


@dataclass(frozen=True)
class StoredInsight:
    id: int
    scope_json: str
    scope_hash: str
    review_count: int
    result: InsightResult
    is_stale: bool
    created_at: str


@dataclass(frozen=True)
class QualityMetrics:
    completion_rate: float | None
    average_confidence: float | None
    rating_sentiment_agreement: float | None
