"""명령 계약과 의존성 조립 진입점, 안정적인 콘솔 출력을 argparse로 제공한다."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date
from pathlib import Path
from typing import Sequence

from review_analytics.composition import (
    AppDependencies,
    build_default_dependencies,
    create_live_client,
)
from review_analytics.config import AppConfig, load_config
from review_analytics.dto import (
    AnalyzeRequest,
    CleanRequest,
    DashboardRequest,
    ExportRequest,
    ExtractRequest,
    GeneratedFile,
    GeneratedFilesResult,
    ImportRequest,
    OperationSummary,
    ReviewDetailRequest,
    ReviewDetailResult,
    ReviewFilter,
    ReviewListRequest,
    ReviewListResult,
    StatsRequest,
    StatsResult,
)
from review_analytics.errors import ProjectError
from review_analytics.logging_config import configure_logging
from review_analytics.models import (
    AnalysisStatus,
    DuplicatePolicy,
    ExportFormat,
    ReportFormat,
    Sentiment,
    SortField,
    SortOrder,
    TargetMode,
)
from review_analytics.services.cleaning import clean_reviews
from review_analytics.services.exporting import export_reviews
from review_analytics.services.extraction import extract_insights
from review_analytics.services.ingestion import import_reviews
from review_analytics.services.query import get_stats, list_reviews, show_review
from review_analytics.services.sentiment import analyze_reviews
from review_analytics.rules.normalization import normalize_text


logger = logging.getLogger(__name__)


class _CommandParser(argparse.ArgumentParser):
    # 기본 인수 파싱 후 명령 간 교차 옵션 계약을 검증한다.
    def parse_args(self, args=None, namespace=None):
        parsed = super().parse_args(args, namespace)
        if getattr(parsed, "command", None) is not None:
            _validate_cross_options(self, parsed)
        return parsed


# 외부 자원에 접근하지 않고 아홉 개 서브커맨드 파서를 구성한다.
def build_parser(config: AppConfig) -> argparse.ArgumentParser:
    """Build all nine commands without touching SQLite, files, or Gemini."""
    parser = _CommandParser(
        prog="python main.py",
        description="고객 리뷰 감정 분석 CLI",
    )
    commands = parser.add_subparsers(dest="command", required=True, metavar="command")

    import_parser = commands.add_parser("import", help="CSV/XLSX 리뷰 수집")
    import_parser.add_argument("--file", required=True, type=Path, help="입력 CSV/XLSX 경로")
    import_parser.add_argument(
        "--duplicate-policy",
        choices=_values(DuplicatePolicy),
        default=config.duplicate_policy.value,
    )

    clean_parser = commands.add_parser("clean", help="원본 리뷰 검증 및 정제")
    clean_targets = clean_parser.add_mutually_exclusive_group()
    clean_targets.add_argument("--pending", action="store_true", help="미정제 raw만 처리")
    clean_targets.add_argument("--all", action="store_true", help="모든 raw 재정제")
    clean_targets.add_argument("--id", type=_bounded_int("ID", minimum=1), help="raw 리뷰 ID")

    analyze_parser = commands.add_parser("analyze", help="Gemini 감정 분석")
    analyze_targets = analyze_parser.add_mutually_exclusive_group()
    analyze_targets.add_argument("--unanalyzed", action="store_true", help="미분석 clean만 처리")
    analyze_targets.add_argument("--all", action="store_true", help="모든 clean 선택")
    analyze_targets.add_argument("--id", type=_bounded_int("ID", minimum=1), help="clean 리뷰 ID")
    analyze_parser.add_argument("--limit", type=_bounded_int("limit", minimum=1))
    analyze_parser.add_argument("--force", action="store_true", help="기존 감정 결과 교체")

    extract_parser = commands.add_parser("extract", help="키워드·요약·개선 제안 추출")
    _add_sentiment(extract_parser)
    _add_product(extract_parser)
    _add_dates(extract_parser)
    extract_parser.add_argument("--limit", type=_bounded_int("limit", minimum=1))

    list_parser = commands.add_parser("list", help="리뷰 목록 조회")
    _add_sentiment(list_parser)
    list_parser.add_argument("--rating", type=_bounded_int("rating", minimum=1, maximum=5))
    _add_dates(list_parser)
    list_parser.add_argument("--page", type=_bounded_int("page", minimum=1), default=1)
    list_parser.add_argument(
        "--size",
        type=_bounded_int("size", minimum=1, maximum=config.maximum_page_size),
        default=config.default_page_size,
    )
    list_parser.add_argument("--sort-by", choices=_values(SortField), default=SortField.ID.value)
    list_parser.add_argument("--order", choices=_values(SortOrder), default=SortOrder.ASC.value)

    show_parser = commands.add_parser("show", help="리뷰 상세 조회")
    show_parser.add_argument("id", type=_bounded_int("ID", minimum=1))

    stats_parser = commands.add_parser("stats", help="통계와 품질 지표 조회")
    _add_sentiment(stats_parser)
    _add_product(stats_parser)
    _add_dates(stats_parser)

    dashboard_parser = commands.add_parser("dashboard", help="종합 리포트와 PNG 차트 생성")
    _add_product(dashboard_parser)
    _add_dates(dashboard_parser)
    dashboard_parser.add_argument("--top", type=_bounded_int("top", minimum=1), default=5)
    dashboard_parser.add_argument("--output-dir", type=Path, default=config.output_directory)
    dashboard_parser.add_argument(
        "--report-format",
        choices=_values(ReportFormat),
        default=ReportFormat.MD.value,
    )

    export_parser = commands.add_parser("export", help="분석 결과 CSV/XLSX 내보내기")
    export_parser.add_argument("--format", required=True, choices=_values(ExportFormat))
    export_parser.add_argument("--output", required=True, type=Path)
    _add_sentiment(export_parser)
    export_parser.add_argument(
        "--rating-min",
        type=_bounded_int("rating-min", minimum=1, maximum=5),
    )
    return parser


# 명령 하나를 파싱·실행·출력하고 안정적인 종료 코드를 반환한다.
def run(argv: Sequence[str] | None = None, dependencies: AppDependencies | None = None) -> int:
    """Parse, execute one command, print stable output, and return 0/1/2."""
    try:
        config = dependencies.config if dependencies is not None else load_config(Path("config.json"))
    except ProjectError as exc:
        _print_error(exc)
        return 1

    parser = build_parser(config)
    try:
        namespace = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 1

    command = namespace.command
    request = _request_from_namespace(namespace)
    started = time.perf_counter()
    try:
        configure_logging(config)
        logger.info("event=command.started command=%s", command)
        active = dependencies or _default_dependencies(config)
        result = _dispatch(command, request, active)
        _print_result(command, result)
        exit_code = _result_exit_code(result)
        _log_result(command, result, exit_code, started)
        return exit_code
    except ProjectError as exc:
        duration_ms = _duration_ms(started)
        logger.error(
            "event=command.failed command=%s error_code=%s duration_ms=%d",
            command,
            exc.code,
            duration_ms,
        )
        _print_error(exc)
        return 1
    except Exception:
        duration_ms = _duration_ms(started)
        logger.error(
            "event=command.failed command=%s error_code=UNEXPECTED_ERROR duration_ms=%d",
            command,
            duration_ms,
        )
        print("오류 [UNEXPECTED_ERROR]: 명령을 완료하지 못했습니다.", file=sys.stderr)
        return 1


# 실제 실행에 사용할 기본 저장소 의존성을 조립한다.
def _default_dependencies(config: AppConfig) -> AppDependencies:
    return build_default_dependencies(config)


# 명령 이름에 대응하는 Service를 호출하고 결과 DTO를 반환한다.
def _dispatch(command: str, request: object, dependencies: AppDependencies) -> object:
    config = dependencies.config
    if command == "import":
        return import_reviews(request, dependencies.review_repository)
    if command == "clean":
        return clean_reviews(request, dependencies.review_repository, config.minimum_review_length)
    if command == "analyze":
        client = _ai_client(dependencies)
        try:
            return analyze_reviews(
                request,
                dependencies.analysis_repository,
                client,
                config.analysis_batch_size,
                config.ai_retry_count,
            )
        finally:
            _close_client(client)
    if command == "extract":
        client = _ai_client(dependencies)
        try:
            return extract_insights(
                request,
                dependencies.review_repository,
                dependencies.analysis_repository,
                client,
                config.extraction_chunk_characters,
                config.ai_retry_count,
            )
        finally:
            _close_client(client)
    if command == "list":
        return list_reviews(request, dependencies.review_repository)
    if command == "show":
        return show_review(request, dependencies.review_repository)
    if command == "stats":
        return get_stats(request, dependencies.review_repository)
    if command == "dashboard":
        from review_analytics.services.reporting import build_dashboard

        return build_dashboard(
            request,
            dependencies.review_repository,
            dependencies.analysis_repository,
            config.chart_font_candidates,
        )
    if command == "export":
        return export_reviews(request, dependencies.review_repository)
    raise RuntimeError("unreachable command")


# API 키 조회를 실제 첫 AI 호출까지 미루는 Client를 만든다.
def _ai_client(dependencies: AppDependencies) -> object:
    return _LazyAIClient(dependencies)


class _LazyAIClient:
    """Defer key lookup and SDK construction until a service makes its first AI call."""

    # Client 생성에 필요한 의존성을 보관하고 실제 Client는 비워 둔다.
    def __init__(self, dependencies: AppDependencies) -> None:
        self._dependencies = dependencies
        self._client: object | None = None

    # 첫 호출에 실제 Client를 만든 뒤 감정 분석을 위임한다.
    def analyze(self, batch):
        return self._get().analyze(batch)

    # 첫 호출에 실제 Client를 만든 뒤 인사이트 추출을 위임한다.
    def extract(self, insight_input):
        return self._get().extract(insight_input)

    # 첫 호출에 실제 Client를 만든 뒤 부분 인사이트 병합을 위임한다.
    def merge_insights(self, parts):
        return self._get().merge_insights(parts)

    # 생성된 실제 Client가 있을 때만 자원을 닫는다.
    def close(self) -> None:
        if self._client is not None:
            _close_client(self._client)

    # 의존성 팩터리 또는 환경 설정으로 실제 AI Client를 한 번 생성한다.
    def _get(self):
        if self._client is None:
            factory = self._dependencies.client_factory
            if factory is not None:
                self._client = factory()
            else:
                self._client = create_live_client(self._dependencies.config)
        return self._client


# 객체가 제공하는 선택적 close 메서드를 안전하게 호출한다.
def _close_client(client: object) -> None:
    close = getattr(client, "close", None)
    if callable(close):
        close()


# argparse 결과를 명령별 이름 있는 Request DTO로 변환한다.
def _request_from_namespace(namespace: argparse.Namespace) -> object:
    command = namespace.command
    if command == "import":
        return ImportRequest(namespace.file, DuplicatePolicy(namespace.duplicate_policy))
    if command == "clean":
        return CleanRequest(_clean_target(namespace), namespace.id)
    if command == "analyze":
        return AnalyzeRequest(
            _analyze_target(namespace),
            namespace.id,
            namespace.limit,
            namespace.force,
        )
    if command == "extract":
        return ExtractRequest(_review_filter(namespace), namespace.limit)
    if command == "list":
        return ReviewListRequest(
            _review_filter(namespace),
            namespace.page,
            namespace.size,
            SortField(namespace.sort_by),
            SortOrder(namespace.order),
        )
    if command == "show":
        return ReviewDetailRequest(namespace.id)
    if command == "stats":
        return StatsRequest(_review_filter(namespace))
    if command == "dashboard":
        return DashboardRequest(
            _review_filter(namespace),
            namespace.top,
            namespace.output_dir,
            ReportFormat(namespace.report_format),
        )
    if command == "export":
        return ExportRequest(
            _review_filter(namespace),
            ExportFormat(namespace.format),
            namespace.output,
        )
    raise RuntimeError("unreachable command")


# 명령 옵션에서 공통 리뷰 필터 DTO를 구성한다.
def _review_filter(namespace: argparse.Namespace) -> ReviewFilter:
    sentiment = getattr(namespace, "sentiment", None)
    return ReviewFilter(
        sentiment=Sentiment(sentiment) if sentiment is not None else None,
        rating=getattr(namespace, "rating", None),
        rating_min=getattr(namespace, "rating_min", None),
        date_from=getattr(namespace, "date_from", None),
        date_to=getattr(namespace, "date_to", None),
        product=getattr(namespace, "product", None),
    )


# clean 대상 플래그를 ID·전체·대기 모드로 결정한다.
def _clean_target(namespace: argparse.Namespace) -> TargetMode:
    if namespace.id is not None:
        return TargetMode.ID
    if namespace.all:
        return TargetMode.ALL
    return TargetMode.PENDING


# analyze 대상 플래그를 ID·전체·미분석 모드로 결정한다.
def _analyze_target(namespace: argparse.Namespace) -> TargetMode:
    if namespace.id is not None:
        return TargetMode.ID
    if namespace.all:
        return TargetMode.ALL
    return TargetMode.UNANALYZED


# 날짜 순서와 내보내기 확장자 같은 교차 옵션을 검증한다.
def _validate_cross_options(parser: argparse.ArgumentParser, namespace: argparse.Namespace) -> None:
    date_from = getattr(namespace, "date_from", None)
    date_to = getattr(namespace, "date_to", None)
    if date_from is not None and date_to is not None and date_from > date_to:
        parser.error("--date-from은 --date-to보다 늦을 수 없습니다")
    if namespace.command == "export":
        expected = f".{namespace.format}"
        if namespace.output.suffix.lower() != expected:
            parser.error("--output 확장자는 --format과 일치해야 합니다")


# 파서에 공통 감정 필터 선택지를 추가한다.
def _add_sentiment(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--sentiment", choices=_values(Sentiment))


# 파서에 비어 있지 않은 제품 필터를 추가한다.
def _add_product(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--product", type=_non_empty_text)


# 파서에 ISO 시작일·종료일 필터를 추가한다.
def _add_dates(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--date-from", type=_iso_date)
    parser.add_argument("--date-to", type=_iso_date)


# argparse에서 재사용할 범위 제한 정수 변환기를 만든다.
def _bounded_int(label: str, minimum: int, maximum: int | None = None):
    # 입력 문자열을 허용 범위의 정수로 변환한다.
    def parse(value: str) -> int:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"{label}은 정수여야 합니다") from exc
        if parsed < minimum or maximum is not None and parsed > maximum:
            range_text = f"{minimum} 이상" if maximum is None else f"{minimum}..{maximum}"
            raise argparse.ArgumentTypeError(f"{label} 허용 범위: {range_text}")
        return parsed

    return parse


# 날짜 문자열이 정확한 ISO 달력 날짜인지 검증한다.
def _iso_date(value: str) -> str:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("날짜는 YYYY-MM-DD 형식이어야 합니다") from exc
    if parsed.isoformat() != value:
        raise argparse.ArgumentTypeError("날짜는 YYYY-MM-DD 형식이어야 합니다")
    return value


# CLI 텍스트를 정규화하고 빈 값은 인수 오류로 거절한다.
def _non_empty_text(value: str) -> str:
    normalized = normalize_text(value)
    if not normalized:
        raise argparse.ArgumentTypeError("빈 문자열은 허용되지 않습니다")
    return normalized


# enum 멤버의 문자열 값만 argparse 선택지로 추출한다.
def _values(enum_type) -> tuple[str, ...]:
    return tuple(item.value for item in enum_type)


# Service 결과 DTO 유형에 맞는 안정적인 콘솔 출력을 선택한다.
def _print_result(command: str, result: object) -> None:
    if isinstance(result, OperationSummary):
        print(
            f"처리: {result.processed}건 | 성공: {result.succeeded}건 | "
            f"스킵: {result.skipped}건 | 실패: {result.failed}건"
        )
        if result.rejected:
            print(f"거절: {result.rejected}건")
        for message in result.messages:
            print(message)
        return
    if isinstance(result, ReviewListResult):
        _print_review_list(result)
        return
    if isinstance(result, ReviewDetailResult):
        _print_review_detail(result)
        return
    if isinstance(result, StatsResult):
        _print_stats(result)
        return
    if isinstance(result, GeneratedFilesResult):
        if result.summary.messages:
            print(result.summary.messages[0], end="")
        for generated in result.files:
            _print_generated_file(generated)
        for message in result.summary.messages[1:]:
            print(f"부분 실패: {message}")
        return
    if isinstance(result, GeneratedFile):
        _print_generated_file(result)
        return
    raise RuntimeError("unsupported result type")


# 리뷰 목록 페이지를 별점과 분석 상태가 포함된 행으로 출력한다.
def _print_review_list(result: ReviewListResult) -> None:
    print(
        f"=== 리뷰 목록: {result.page}/{result.total_pages} 페이지, "
        f"총 {result.total_items}건 ==="
    )
    for item in result.items:
        rating = "N/A" if item.rating is None else "★" * item.rating + "☆" * (5 - item.rating)
        status = (
            "미분석"
            if item.analysis_status is AnalysisStatus.UNANALYZED
            else f"{item.sentiment.value} ({item.confidence:.2f})"
        )
        print(
            f"[{item.review_id}] {rating} | {item.review_date or 'N/A'} | "
            f"{_one_line(item.review_text)} | {status}"
        )


# 리뷰 한 건의 원본·정제·감정 상세 정보를 출력한다.
def _print_review_detail(result: ReviewDetailResult) -> None:
    clean = result.clean_review
    print(f"=== 리뷰 ID={result.review_id} ===")
    print(f"원문: {_one_line(result.review_text_raw)}")
    print(f"정제문: {_one_line(clean.review_text) if clean is not None else 'N/A'}")
    print(f"별점: {clean.rating if clean is not None and clean.rating is not None else 'N/A'}")
    print(f"작성일: {clean.review_date if clean is not None and clean.review_date is not None else 'N/A'}")
    print(f"제품: {clean.product_name if clean is not None and clean.product_name is not None else 'N/A'}")
    print(f"정제 상태: {result.clean_status.value}")
    if result.rejection_reason is not None:
        print(f"거절 사유: {result.rejection_reason}")
    analyzed = result.analysis_status is AnalysisStatus.ANALYZED
    print(f"분석 상태: {'완료' if analyzed else '미분석'}")
    print(f"감정: {result.sentiment.value if result.sentiment is not None else 'N/A'}")
    print(f"신뢰도: {result.confidence:.2f}" if result.confidence is not None else "신뢰도: N/A")
    print(f"분석 모델: {result.model_name or 'N/A'}")
    print(f"분석 시각: {result.analyzed_at or 'N/A'}")


# 통계와 품질 지표를 사람이 읽을 수 있는 요약으로 출력한다.
def _print_stats(result: StatsResult) -> None:
    counts = dict(result.sentiment_counts)
    completion = _percent(result.metrics.completion_rate)
    print("=== 리뷰 분석 통계 ===")
    print(f"clean 리뷰: {result.total_clean}건")
    print(f"분석 완료: {result.analyzed_count}건 ({completion})")
    print(
        f"긍정 {_count_ratio(counts.get(Sentiment.POSITIVE, 0), result.analyzed_count)} | "
        f"중립 {_count_ratio(counts.get(Sentiment.NEUTRAL, 0), result.analyzed_count)} | "
        f"부정 {_count_ratio(counts.get(Sentiment.NEGATIVE, 0), result.analyzed_count)}"
    )
    print(f"평균 별점: {_decimal(result.average_rating)}")
    print(f"평균 신뢰도: {_decimal(result.metrics.average_confidence)}")
    print(f"별점·감정 일치율: {_percent(result.metrics.rating_sentiment_agreement)}")


# 생성 파일 경로와 선택 건수를 출력하고 안전한 로그를 남긴다.
def _print_generated_file(result: GeneratedFile) -> None:
    count = "" if result.record_count is None else f" ({result.record_count}건)"
    print(f"생성 파일 [{result.role}]: {result.path}{count}")
    logger.info(
        "event=output.created output_type=%s file_name=%s",
        result.role,
        result.path.name,
    )


# 결과의 성공·부분 실패·전체 실패 상태를 0·2·1로 변환한다.
def _result_exit_code(result: object) -> int:
    summary = result.summary if isinstance(result, GeneratedFilesResult) else result
    if not isinstance(summary, OperationSummary) or summary.failed == 0:
        return 0
    completed = summary.succeeded + summary.skipped + summary.rejected
    return 2 if completed > 0 else 1


# 명령 결과 건수와 소요 시간을 종료 상태에 맞는 레벨로 기록한다.
def _log_result(command: str, result: object, exit_code: int, started: float) -> None:
    processed, succeeded, skipped, failed = _result_counts(result)
    duration_ms = _duration_ms(started)
    if exit_code == 2:
        logger.warning(
            "event=command.partial command=%s processed=%d succeeded=%d skipped=%d "
            "failed=%d duration_ms=%d error_code=PARTIAL_FAILURE",
            command,
            processed,
            succeeded,
            skipped,
            failed,
            duration_ms,
        )
    elif exit_code == 1:
        logger.error(
            "event=command.failed command=%s error_code=OPERATION_FAILED duration_ms=%d",
            command,
            duration_ms,
        )
    else:
        logger.info(
            "event=command.completed command=%s processed=%d succeeded=%d skipped=%d "
            "failed=%d duration_ms=%d",
            command,
            processed,
            succeeded,
            skipped,
            failed,
            duration_ms,
        )


# 서로 다른 결과 DTO에서 공통 처리·성공·스킵·실패 건수를 얻는다.
def _result_counts(result: object) -> tuple[int, int, int, int]:
    if isinstance(result, GeneratedFilesResult):
        result = result.summary
    if isinstance(result, OperationSummary):
        return result.processed, result.succeeded, result.skipped, result.failed
    if isinstance(result, ReviewListResult):
        return len(result.items), len(result.items), 0, 0
    if isinstance(result, StatsResult):
        return result.total_clean, result.total_clean, 0, 0
    if isinstance(result, (ReviewDetailResult, GeneratedFile)):
        return 1, 1, 0, 0
    return 0, 0, 0, 0


# 시작 시각부터 지난 시간을 음수가 아닌 밀리초로 계산한다.
def _duration_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))


# 안전한 프로젝트 오류 코드와 메시지를 표준 오류에 출력한다.
def _print_error(error: ProjectError) -> None:
    print(f"오류 [{error.code}]: {error.message}", file=sys.stderr)


# 선택 비율을 백분율 문자열 또는 N/A로 표시한다.
def _percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value * 100:.1f}%"


# 선택적 실수값을 소수점 둘째 자리 문자열 또는 N/A로 표시한다.
def _decimal(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2f}"


# 건수와 전체 대비 비율을 함께 표시한다.
def _count_ratio(count: int, total: int) -> str:
    ratio = "N/A" if total == 0 else f"{count / total * 100:.1f}%"
    return f"{count}건 ({ratio})"


# 여러 줄 텍스트를 콘솔 한 줄 표현으로 축약한다.
def _one_line(value: str) -> str:
    return " ".join(value.split())
