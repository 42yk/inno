"""모듈 경계에서 사용하는 불변 요청·결과 DTO를 정의한다."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from review_analytics.models import (
    AnalysisStatus,
    CleanReview,
    CleanStatus,
    DuplicatePolicy,
    ExportFormat,
    KeywordEvidence,
    QualityMetrics,
    RawSaveAction,
    ReportFormat,
    Sentiment,
    SortField,
    SortOrder,
    TargetMode,
)


@dataclass(frozen=True)
class ReviewFilter:
    sentiment: Sentiment | None = None
    rating: int | None = None
    rating_min: int | None = None
    date_from: str | None = None
    date_to: str | None = None
    product: str | None = None


@dataclass(frozen=True)
class PageRequest:
    page: int = 1
    size: int = 20


@dataclass(frozen=True)
class ImportRequest:
    file_path: Path
    duplicate_policy: DuplicatePolicy | None = None


@dataclass(frozen=True)
class CleanRequest:
    target_mode: TargetMode = TargetMode.PENDING
    review_id: int | None = None


@dataclass(frozen=True)
class AnalyzeRequest:
    target_mode: TargetMode = TargetMode.UNANALYZED
    review_id: int | None = None
    limit: int | None = None
    force: bool = False


@dataclass(frozen=True)
class ExtractRequest:
    filter: ReviewFilter = ReviewFilter()
    limit: int | None = None


@dataclass(frozen=True)
class ReviewListRequest:
    filter: ReviewFilter = ReviewFilter()
    page: int = 1
    size: int = 20
    sort_by: SortField = SortField.ID
    order: SortOrder = SortOrder.ASC


@dataclass(frozen=True)
class ReviewDetailRequest:
    review_id: int


@dataclass(frozen=True)
class StatsRequest:
    filter: ReviewFilter = ReviewFilter()


@dataclass(frozen=True)
class DashboardRequest:
    filter: ReviewFilter = ReviewFilter()
    top_n: int = 5
    output_dir: Path | None = None
    report_format: ReportFormat = ReportFormat.MD


@dataclass(frozen=True)
class ExportRequest:
    filter: ReviewFilter = ReviewFilter()
    format: ExportFormat = ExportFormat.CSV
    output_path: Path | None = None


@dataclass(frozen=True)
class OperationSummary:
    processed: int
    succeeded: int
    skipped: int
    failed: int
    messages: tuple[str, ...] = ()
    rejected: int = 0


@dataclass(frozen=True)
class RawSaveResult:
    review_id: int
    action: RawSaveAction


@dataclass(frozen=True)
class ReviewSummary:
    review_id: int
    review_text: str
    rating: int | None
    review_date: str | None
    product_name: str | None
    analysis_status: AnalysisStatus
    sentiment: Sentiment | None
    confidence: float | None


@dataclass(frozen=True)
class ReviewListResult:
    items: tuple[ReviewSummary, ...]
    total_items: int
    page: int
    size: int
    total_pages: int


@dataclass(frozen=True)
class ReviewDetailResult:
    review_id: int
    review_text_raw: str
    clean_review: CleanReview | None
    clean_status: CleanStatus
    rejection_reason: str | None
    analysis_status: AnalysisStatus
    sentiment: Sentiment | None
    confidence: float | None
    model_name: str | None
    analyzed_at: str | None


@dataclass(frozen=True)
class StatsRow:
    review_id: int
    rating: int | None
    sentiment: Sentiment | None
    confidence: float | None


@dataclass(frozen=True)
class StatsResult:
    total_clean: int
    analyzed_count: int
    sentiment_counts: tuple[tuple[Sentiment, int], ...]
    rating_counts: tuple[tuple[int, int], ...]
    average_rating: float | None
    metrics: QualityMetrics


@dataclass(frozen=True)
class DashboardData:
    stats: StatsResult
    positive_keywords: tuple[KeywordEvidence, ...]
    negative_keywords: tuple[KeywordEvidence, ...]
    summary: str
    recommendations: tuple[str, ...]
    filter: ReviewFilter
    generated_at: str | None = None
    rows: tuple[ExportRow, ...] = ()
    chart_paths: tuple[Path, ...] = ()


@dataclass(frozen=True)
class ExportRow:
    review_id: int
    review_text: str
    rating: int | None
    review_date: str | None
    product_name: str | None
    sentiment: Sentiment | None
    confidence: float | None
    analyzed_at: str | None


@dataclass(frozen=True)
class GeneratedFile:
    role: str
    path: Path
    record_count: int | None = None
    size_bytes: int | None = None


@dataclass(frozen=True)
class GeneratedFilesResult:
    files: tuple[GeneratedFile, ...]
    summary: OperationSummary


@dataclass(frozen=True)
class PartialFailureResult:
    successful_result: object
    failures: tuple[tuple[int, str], ...]
