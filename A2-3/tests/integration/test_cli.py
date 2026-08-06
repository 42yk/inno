from __future__ import annotations

import logging
from dataclasses import replace

import pytest

from review_analytics.config import AppConfig
from review_analytics.dto import (
    AnalyzeRequest,
    CleanRequest,
    DashboardRequest,
    ExportRequest,
    ExtractRequest,
    ImportRequest,
    ReviewDetailResult,
    ReviewDetailRequest,
    ReviewListRequest,
    ReviewListResult,
    ReviewSummary,
    StatsRequest,
    StatsRow,
)
from review_analytics.errors import AIServiceError, PersistenceError
from review_analytics.models import (
    AnalysisInput,
    AnalysisStatus,
    CleanReview,
    CleanStatus,
    RawReview,
    Sentiment,
    SentimentResult,
)


COMMANDS = ("import", "clean", "analyze", "extract", "list", "show", "stats", "dashboard", "export")


@pytest.fixture(autouse=True)
def restore_application_logger():
    yield
    logger = logging.getLogger("review_analytics")
    for handler in tuple(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    logger.setLevel(logging.NOTSET)
    logger.propagate = True


def _config(tmp_path, **changes) -> AppConfig:
    config = AppConfig(
        database_path=tmp_path / "reviews.db",
        analysis_batch_size=1,
        ai_retry_count=0,
        default_page_size=7,
        maximum_page_size=9,
        log_file=tmp_path / "logs" / "app.log",
        output_directory=tmp_path / "output",
    )
    return replace(config, **changes)


class FakeReviewRepository:
    def __init__(self, *, list_result=None, details=None, stats_rows=()) -> None:
        self.list_result = list_result or ReviewListResult((), 0, 1, 7, 0)
        self.details = details or {}
        self.rows = stats_rows

    def list_reviews(self, review_filter, page, size, sort_by, order):
        return self.list_result

    def get_review_detail(self, review_id):
        return self.details.get(review_id)

    def stats_rows(self, review_filter):
        return self.rows

    def export_rows(self, review_filter):
        return ()


class UnusedAnalysisRepository:
    def analysis_targets(self, *args, **kwargs):
        raise AssertionError("AI repository must not be called")


def _dependencies(tmp_path, reviews=None, analyses=None, client_factory=None, **config_changes):
    from review_analytics.cli import AppDependencies

    return AppDependencies(
        config=_config(tmp_path, **config_changes),
        review_repository=reviews or FakeReviewRepository(),
        analysis_repository=analyses or UnusedAnalysisRepository(),
        client_factory=client_factory,
    )


@pytest.mark.parametrize("command", COMMANDS)
def test_every_command_has_help_without_database_or_api_key(tmp_path, monkeypatch, command, capsys):
    import review_analytics.cli as cli

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(cli, "load_config", lambda path: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "_default_dependencies",
        lambda config: (_ for _ in ()).throw(AssertionError("DB must not initialize for help")),
    )

    assert cli.run([command, "--help"]) == 0
    assert command in capsys.readouterr().out


def test_root_help_also_returns_before_database_initialization(tmp_path, monkeypatch, capsys):
    import review_analytics.cli as cli

    monkeypatch.setattr(cli, "load_config", lambda path: _config(tmp_path))
    monkeypatch.setattr(
        cli,
        "_default_dependencies",
        lambda config: (_ for _ in ()).throw(AssertionError("DB must not initialize for help")),
    )

    assert cli.run(["--help"]) == 0
    assert "고객 리뷰 감정 분석 CLI" in capsys.readouterr().out


def test_parser_defaults_come_from_config_and_all_selectors_are_mutually_exclusive(tmp_path):
    from review_analytics.cli import build_parser

    parser = build_parser(_config(tmp_path))
    listed = parser.parse_args(["list"])
    imported = parser.parse_args(["import", "--file", "reviews.csv"])

    assert (listed.page, listed.size, listed.sort_by, listed.order) == (1, 7, "id", "asc")
    assert imported.duplicate_policy == "skip"
    with pytest.raises(SystemExit):
        parser.parse_args(["clean", "--pending", "--all"])
    with pytest.raises(SystemExit):
        parser.parse_args(["analyze", "--unanalyzed", "--id", "1"])


@pytest.mark.parametrize(
    ("argv", "request_type"),
    (
        (["import", "--file", "reviews.csv"], ImportRequest),
        (["clean", "--pending"], CleanRequest),
        (["analyze", "--unanalyzed"], AnalyzeRequest),
        (["extract", "--product", "텀블러"], ExtractRequest),
        (["list", "--page", "2"], ReviewListRequest),
        (["show", "1"], ReviewDetailRequest),
        (["stats"], StatsRequest),
        (["dashboard"], DashboardRequest),
        (["export", "--format", "csv", "--output", "reviews.csv"], ExportRequest),
    ),
)
def test_every_namespace_is_immediately_converted_to_a_named_frozen_request(tmp_path, argv, request_type):
    import review_analytics.cli as cli

    namespace = cli.build_parser(_config(tmp_path)).parse_args(argv)

    assert isinstance(cli._request_from_namespace(namespace), request_type)


def test_product_filter_is_normalized_before_entering_the_request_dto(tmp_path):
    import review_analytics.cli as cli

    namespace = cli.build_parser(_config(tmp_path)).parse_args(
        ["extract", "--product", "  Ｔｕｍｂｌｅｒ   Pro  "]
    )
    request = cli._request_from_namespace(namespace)

    assert request.filter.product == "Tumbler Pro"


@pytest.mark.parametrize(
    "argv",
    (
        ["show", "0"],
        ["list", "--rating", "6"],
        ["list", "--size", "10"],
        ["extract", "--date-from", "2026-08-32"],
        ["extract", "--date-from", "2026-08-02", "--date-to", "2026-08-01"],
        ["dashboard", "--top", "0"],
        ["export", "--format", "csv", "--output", "reviews.xlsx"],
    ),
)
def test_parser_rejects_ranges_dates_and_export_extension_mismatches(tmp_path, argv):
    from review_analytics.cli import build_parser

    with pytest.raises(SystemExit):
        build_parser(_config(tmp_path)).parse_args(argv)


def test_list_show_and_stats_have_stable_human_readable_semantics(tmp_path, capsys):
    from review_analytics.cli import run

    clean = CleanReview(
        id=3,
        raw_review_id=2,
        review_text="정제된 리뷰",
        rating=5,
        review_date="2026-08-01",
        product_name="텀블러",
        cleaning_version="v1",
        cleaned_at="now",
    )
    reviews = FakeReviewRepository(
        list_result=ReviewListResult(
            items=(
                ReviewSummary(1, "아주 만족해요", 5, "2026-08-01", "텀블러", AnalysisStatus.ANALYZED, Sentiment.POSITIVE, 0.94),
                ReviewSummary(2, "아직 분석 전", None, None, None, AnalysisStatus.UNANALYZED, None, None),
            ),
            total_items=2,
            page=1,
            size=7,
            total_pages=1,
        ),
        details={
            1: ReviewDetailResult(1, "거절 원문", None, CleanStatus.REJECTED, "INVALID_RATING", AnalysisStatus.UNANALYZED, None, None, None, None),
            2: ReviewDetailResult(2, "원문", clean, CleanStatus.CLEANED, None, AnalysisStatus.ANALYZED, Sentiment.POSITIVE, 0.94, "fake-model", "now"),
        },
        stats_rows=(
            StatsRow(1, 5, Sentiment.POSITIVE, 0.9),
            StatsRow(2, 1, Sentiment.NEGATIVE, 0.8),
            StatsRow(3, None, None, None),
        ),
    )
    dependencies = _dependencies(tmp_path, reviews=reviews)

    assert run(["list"], dependencies) == 0
    listed = capsys.readouterr().out
    assert "=== 리뷰 목록: 1/1 페이지, 총 2건 ===" in listed
    assert "★★★★★" in listed
    assert "positive (0.94)" in listed
    assert "미분석" in listed

    assert run(["show", "1"], dependencies) == 0
    rejected = capsys.readouterr().out
    assert "정제문: N/A" in rejected
    assert "거절 사유: INVALID_RATING" in rejected
    assert "분석 상태: 미분석" in rejected
    assert "감정: N/A" in rejected

    assert run(["show", "2"], dependencies) == 0
    analyzed = capsys.readouterr().out
    assert "정제문: 정제된 리뷰" in analyzed
    assert "분석 상태: 완료" in analyzed
    assert "감정: positive" in analyzed
    assert "신뢰도: 0.94" in analyzed

    assert run(["stats"], dependencies) == 0
    stats = capsys.readouterr().out
    assert "clean 리뷰: 3건" in stats
    assert "분석 완료: 2건 (66.7%)" in stats
    assert "긍정 1건 (50.0%) | 중립 0건 (0.0%) | 부정 1건 (50.0%)" in stats
    assert "평균 별점: 3.00" in stats
    assert "평균 신뢰도: 0.85" in stats
    assert "별점·감정 일치율: 100.0%" in stats


def test_missing_entity_is_exit_1_and_ai_partial_batch_is_exit_2(tmp_path, capsys):
    from review_analytics.cli import run

    assert run(["show", "99"], _dependencies(tmp_path)) == 1
    assert "RAW_REVIEW_NOT_FOUND" in capsys.readouterr().err

    class PartialAnalysisRepository:
        def analysis_targets(self, *args, **kwargs):
            return (AnalysisInput(1, "첫 리뷰"), AnalysisInput(2, "둘째 리뷰"))

        def save_sentiment_batch(self, results):
            return len(results)

    class PartialClient:
        def analyze(self, batch):
            if batch[0].review_id == 2:
                raise AIServiceError("안전한 API 오류", "AI_API_ERROR")
            return (SentimentResult(1, Sentiment.POSITIVE, 0.9, "fake", "v1"),)

    dependencies = _dependencies(
        tmp_path,
        analyses=PartialAnalysisRepository(),
        client_factory=PartialClient,
    )
    assert run(["analyze"], dependencies) == 2
    assert "처리: 2건 | 성공: 1건 | 스킵: 0건 | 실패: 1건" in capsys.readouterr().out


def test_stats_without_analyzed_rows_shows_na_sentiment_ratios(tmp_path, capsys):
    from review_analytics.cli import run

    reviews = FakeReviewRepository(stats_rows=(StatsRow(1, 4, None, None),))

    assert run(["stats"], _dependencies(tmp_path, reviews=reviews)) == 0
    output = capsys.readouterr().out
    assert "긍정 0건 (N/A) | 중립 0건 (N/A) | 부정 0건 (N/A)" in output


def test_clean_rejection_is_success_and_mixed_persistence_failure_is_partial(tmp_path, capsys):
    from review_analytics.cli import run

    invalid = RawReview(
        id=1,
        fingerprint="hash",
        review_text_raw="짧음",
        rating_raw="9",
        review_date_raw=None,
        product_name_raw=None,
        source_type="csv",
        source_ref="sample.csv",
        source_row=2,
        clean_status=CleanStatus.PENDING,
        rejection_reason=None,
        created_at="now",
        updated_at="now",
    )

    class CleanRepository(FakeReviewRepository):
        def __init__(self, partial=False):
            super().__init__()
            self.partial = partial

        def select_raw_targets(self, *args):
            return (invalid, replace(invalid, id=2)) if self.partial else (invalid,)

        def reject_clean(self, review_id, reason):
            if self.partial and review_id == 1:
                raise PersistenceError("원문 비밀", "CLEAN_REJECT_FAILED")

    assert run(["clean"], _dependencies(tmp_path, reviews=CleanRepository())) == 0
    assert "거절: 1건" in capsys.readouterr().out

    assert run(["clean"], _dependencies(tmp_path, reviews=CleanRepository(partial=True))) == 2


def test_only_ai_execution_requires_api_key_and_logs_never_include_review_or_key(tmp_path, monkeypatch, capsys):
    import review_analytics.cli as cli
    import review_analytics.composition as composition

    secret_review = "VERY_SECRET_REVIEW_TEXT"
    secret_key = "TOP_SECRET_API_KEY"
    monkeypatch.setenv("GEMINI_API_KEY", secret_key)
    reviews = FakeReviewRepository(
        list_result=ReviewListResult(
            (ReviewSummary(1, secret_review, 5, None, None, AnalysisStatus.UNANALYZED, None, None),),
            1,
            1,
            7,
            1,
        )
    )
    dependencies = _dependencies(tmp_path, reviews=reviews)

    assert cli.run(["list"], dependencies) == 0
    assert secret_review in capsys.readouterr().out
    log_text = dependencies.config.log_file.read_text(encoding="utf-8")
    assert secret_review not in log_text
    assert secret_key not in log_text
    assert "event=command.started command=list" in log_text
    assert "event=command.completed command=list" in log_text

    monkeypatch.delenv("GEMINI_API_KEY")
    monkeypatch.setattr(composition, "load_dotenv", lambda *args, **kwargs: False)
    assert cli.run(["stats"], dependencies) == 0
    capsys.readouterr()
    one_target_dependencies = _dependencies(
        tmp_path,
        analyses=type(
            "OneTargetRepository",
            (),
            {"analysis_targets": lambda self, *args, **kwargs: (AnalysisInput(1, "리뷰"),)},
        )(),
    )
    assert cli.run(["analyze"], one_target_dependencies) == 1
    error = capsys.readouterr().err
    assert "GEMINI_API_KEY_REQUIRED" in error


def test_empty_ai_targets_do_not_require_key_or_construct_client(tmp_path, monkeypatch, capsys):
    import review_analytics.cli as cli
    import review_analytics.composition as composition

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(composition, "load_dotenv", lambda *args, **kwargs: False)

    class EmptyAnalysisRepository:
        def analysis_targets(self, *args, **kwargs):
            return ()

    def forbidden_factory():
        raise AssertionError("client must stay lazy")

    analyze_dependencies = _dependencies(
        tmp_path,
        analyses=EmptyAnalysisRepository(),
        client_factory=forbidden_factory,
    )
    assert cli.run(["analyze"], analyze_dependencies) == 0
    assert "처리: 0건" in capsys.readouterr().out

    extract_dependencies = _dependencies(
        tmp_path,
        reviews=FakeReviewRepository(),
        client_factory=forbidden_factory,
    )
    assert cli.run(["extract"], extract_dependencies) == 1
    assert "NO_REVIEWS_FOR_EXTRACTION" in capsys.readouterr().err
