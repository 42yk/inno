"""공통 리뷰 필터 계약으로 조회와 내보내기 순서를 조정한다."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from review_analytics.dto import ExportRequest, ExportRow, GeneratedFile
from review_analytics.errors import ValidationError
from review_analytics.file_io.exporter import write_export
from review_analytics.models import ExportFormat
from review_analytics.repositories import ReviewRepository


ExportWriter = Callable[[Iterable[ExportRow], ExportFormat, Path], GeneratedFile]


# 공통 필터로 조회한 리뷰를 요청된 파일 형식으로 내보낸다.
def export_reviews(
    request: ExportRequest,
    repository: ReviewRepository,
    writer: ExportWriter = write_export,
) -> GeneratedFile:
    """Write the filtered rows, including a header-only successful export."""
    if request.output_path is None:
        raise ValidationError("내보내기 출력 경로가 필요합니다.", "EXPORT_OUTPUT_REQUIRED")
    rows = repository.export_rows(request.filter)
    return writer(rows, request.format, request.output_path)
