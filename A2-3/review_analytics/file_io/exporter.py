"""평탄한 내보내기 DTO를 지원하는 외부 파일 형식으로 기록한다."""

from __future__ import annotations

import csv
import logging
from collections.abc import Iterable
from pathlib import Path

from openpyxl import Workbook

from review_analytics.dto import ExportRow, GeneratedFile
from review_analytics.errors import OutputWriteError
from review_analytics.models import ExportFormat


_HEADERS = (
    "review_id",
    "review_text",
    "rating",
    "review_date",
    "product_name",
    "sentiment",
    "confidence",
    "analyzed_at",
)
logger = logging.getLogger(__name__)


# 평탄화한 리뷰 행을 요청 형식으로 기록하고 생성 파일 정보를 반환한다.
def write_export(rows: Iterable[ExportRow], export_format: ExportFormat | str, path: Path) -> GeneratedFile:
    """Write flat ``ExportRow`` values and return metadata for the generated file."""
    output_path = Path(path)
    format_value = _export_format(export_format)
    if output_path.suffix.lower() != f".{format_value.value}":
        raise OutputWriteError("출력 파일 확장자가 형식과 일치하지 않습니다.", "EXPORT_EXTENSION_MISMATCH")
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if format_value is ExportFormat.CSV:
            record_count = _write_csv(rows, output_path)
        else:
            record_count = _write_xlsx(rows, output_path)
        return GeneratedFile(
            role="export",
            path=output_path,
            record_count=record_count,
            size_bytes=output_path.stat().st_size,
        )
    except OutputWriteError:
        raise
    except (OSError, ValueError) as exc:
        logger.error(
            "event=output.failed output_type=export file_name=%s error_code=EXPORT_WRITE_FAILED",
            output_path.name,
        )
        raise OutputWriteError("내보내기 파일을 생성하지 못했습니다.", "EXPORT_WRITE_FAILED") from exc


# 문자열 또는 enum 형식을 지원 가능한 내보내기 enum으로 변환한다.
def _export_format(value: ExportFormat | str) -> ExportFormat:
    try:
        return value if isinstance(value, ExportFormat) else ExportFormat(value)
    except ValueError as exc:
        raise OutputWriteError("지원하지 않는 내보내기 형식입니다.", "UNSUPPORTED_EXPORT_FORMAT") from exc


# 리뷰 행을 UTF-8 BOM이 포함된 CSV 파일로 기록한다.
def _write_csv(rows: Iterable[ExportRow], path: Path) -> int:
    count = 0
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(_HEADERS)
        for row in rows:
            writer.writerow(_flat_values(row))
            count += 1
    return count


# 리뷰 행을 XLSX 워크북으로 기록하고 저장 건수를 반환한다.
def _write_xlsx(rows: Iterable[ExportRow], path: Path) -> int:
    workbook = Workbook()
    try:
        sheet = workbook.active
        sheet.append(_HEADERS)
        count = 0
        for row in rows:
            sheet.append(_flat_values(row))
            count += 1
        workbook.save(path)
        return count
    finally:
        workbook.close()


# 내보내기 DTO를 파일 열 순서에 맞는 평탄 튜플로 바꾼다.
def _flat_values(row: ExportRow) -> tuple[object, ...]:
    return (
        row.review_id,
        row.review_text,
        row.rating,
        row.review_date,
        row.product_name,
        row.sentiment.value if row.sentiment is not None else None,
        row.confidence,
        row.analyzed_at,
    )
