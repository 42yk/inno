# Review Sentiment CLI Implementation Plan

> **Execution note:** The user explicitly required direct execution without subagents. The primary agent implements and reviews each checkbox itself; steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete nine-command Python CLI described by the approved review-sentiment design, including SQLite persistence, Gemini boundaries, static reporting, two export formats, and an offline test suite.

**Architecture:** Use the approved simple layered monolith: `argparse` converts input to frozen DTOs, services orchestrate work, rules remain pure, and SQLite/Gemini/file/chart modules own their external types. Keep Gemini calls outside write transactions and pass only named internal models between layers.

**Tech Stack:** Python 3.10+, SQLite, `google-genai`, `python-dotenv`, `openpyxl`, matplotlib, pytest.

## Global Constraints

- Implement only the required scope in `subject.md`; do not add bonus features.
- Preserve raw input, generate clean data only through `clean`, and invalidate derived data exactly as documented.
- Default Gemini model is `gemini-3.1-flash-lite`; only `analyze` and `extract` require `GEMINI_API_KEY`.
- Support exit codes `0` (success), `1` (fatal/usage failure), and `2` (partial success).
- Never expose `argparse.Namespace`, `sqlite3.Row`, Gemini SDK responses, workbook objects, or matplotlib figures across their owning module boundary.
- Default tests must not use the network or a real Gemini API key.
- Do not commit, push, or open a pull request unless the user asks; repository instructions override generic skill commit steps.

---

### Task 1: Independent standards, configuration, models, DTOs, and pure rules

**Files:**
- Create: `docs/architecture/storage-schema.md`
- Create: `docs/policies/configuration.md`
- Modify: `docs/README.md`
- Create: `config.json`, `.env.sample`, `.gitignore`, `requirements.txt`
- Create: `review_analytics/__init__.py`, `review_analytics/errors.py`, `review_analytics/config.py`, `review_analytics/models.py`, `review_analytics/dto.py`
- Create: `review_analytics/rules/{__init__,normalization,validation,duplicate_policy,metrics}.py`
- Test: `tests/unit/test_config.py`, `tests/unit/test_normalization.py`, `tests/unit/test_validation.py`, `tests/unit/test_metrics.py`

**Interfaces:**
- Produces: `AppConfig`, `load_config(path: Path) -> AppConfig`, project error classes, request/result DTOs, `normalize_text`, `normalize_date`, `fingerprint_review`, `clean_review`, and `calculate_quality_metrics`.
- Consumes: approved schema/config values and CLI contracts only.

- [x] **Step 1: Write failing tests for defaults, invalid config paths/types, normalization/fingerprints, cleaning rejection codes, and metric denominator-zero behavior.**

```python
def test_fingerprint_ignores_rating_and_normalizes_components():
    assert fingerprint_review(" 좋은\n제품 ", "Cup", "2026/08/01") == fingerprint_review(
        "좋은 제품", "cup", "2026-08-01"
    )

def test_metrics_use_only_eligible_denominators():
    metrics = calculate_quality_metrics(total_clean=2, analyzed=[(5, "positive", 0.9)])
    assert metrics.completion_rate == 0.5
    assert metrics.average_confidence == 0.9
    assert metrics.rating_sentiment_agreement == 1.0
```

- [x] **Step 2: Run the focused unit tests and confirm they fail because the modules do not exist.**

Run: `python -m pytest tests/unit/test_config.py tests/unit/test_normalization.py tests/unit/test_validation.py tests/unit/test_metrics.py -q`

- [x] **Step 3: Add the two independent standard documents and register them in `docs/README.md`; define every schema column, index, foreign key, config key, type, default, path resolution rule, and validation rule.**

- [x] **Step 4: Implement immutable configuration/types and pure rules with standard-library-only imports in models/rules/DTO modules.**

```python
@dataclass(frozen=True)
class AppConfig:
    database_path: Path
    gemini_model: str = "gemini-3.1-flash-lite"
    minimum_review_length: int = 5

def fingerprint_review(text: object, product: object, review_date: object) -> str:
    payload = [normalize_fingerprint_text(text), normalize_fingerprint_text(product), normalize_fingerprint_date(review_date)]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
```

- [x] **Step 5: Re-run focused tests and run an import-boundary test proving models/rules do not import external libraries or upper layers.**

Run: `python -m pytest tests/unit -q`

### Task 2: SQLite schema and repository transaction boundaries

**Files:**
- Create: `review_analytics/repositories/{__init__,database,reviews,analyses}.py`
- Test: `tests/integration/test_repository_schema.py`, `tests/integration/test_review_repository.py`, `tests/integration/test_analysis_repository.py`

**Interfaces:**
- Consumes: models/DTOs from Task 1.
- Produces: `initialize_database`, `ReviewRepository.save_raw`, `select_raw_targets`, `save_clean`, `reject_clean`, `list_reviews`, `get_review_detail`, `stats_rows`, `export_rows`; `AnalysisRepository.analysis_targets`, `save_sentiment_batch`, `save_insight`, `latest_valid_insight`.

- [x] **Step 1: Write failing temporary-SQLite tests for idempotent schema/FKs, skip/upsert, raw-ID retention, cascade deletion, stale insight invalidation, clean change invalidation, stable list sorting, and transactional batch saves.**

```python
def test_upsert_keeps_raw_id_and_invalidates_derivatives(repositories, raw_input):
    first = repositories.reviews.save_raw(raw_input, "fp", DuplicatePolicy.SKIP)
    repositories.seed_clean_sentiment_and_insight(first.review_id)
    second = repositories.reviews.save_raw(replace(raw_input, rating_raw="1"), "fp", DuplicatePolicy.UPSERT)
    assert second.review_id == first.review_id
    assert repositories.count("clean_reviews") == 0
    assert repositories.scalar("SELECT is_stale FROM insight_extractions") == 1
```

- [x] **Step 2: Run repository tests and verify failure before implementation.**

Run: `python -m pytest tests/integration/test_repository_schema.py tests/integration/test_review_repository.py tests/integration/test_analysis_repository.py -q`

- [x] **Step 3: Implement connection creation with `PRAGMA foreign_keys=ON`, idempotent DDL, constraints/indexes, and safe row-to-model mapping.**

- [x] **Step 4: Implement raw/clean mutations as short `with connection:` transactions, including all documented derivative invalidation.**

- [x] **Step 5: Implement parameterized filters and enum-to-column sorting; force unanalyzed rows last for nullable sentiment/confidence sorts and use raw ID as a stable tie-breaker.**

- [x] **Step 6: Re-run all repository tests and inspect transactions by injecting a failing statement to prove rollback.**

Run: `python -m pytest tests/integration/test_repository_schema.py tests/integration/test_review_repository.py tests/integration/test_analysis_repository.py -q`

### Task 3: File import/export and ingestion/cleaning services

**Files:**
- Create: `review_analytics/file_io/{__init__,reader,exporter}.py`
- Create: `review_analytics/services/{__init__,ingestion,cleaning}.py`
- Test: `tests/integration/test_file_io.py`, `tests/unit/test_ingestion_service.py`, `tests/unit/test_cleaning_service.py`

**Interfaces:**
- Consumes: `RawReviewInput`, `ExportRow`, `ImportRequest`, `CleanRequest`, repositories, and Task 1 rules.
- Produces: `read_reviews(path: Path) -> tuple[RawReviewInput, ...]`, `write_export(rows, format, path) -> GeneratedFile`, `import_reviews(...) -> OperationSummary`, `clean_reviews(...) -> OperationSummary`.

- [x] **Step 1: Write failing tests for CSV/XLSX input, missing `review_text`, unsupported extensions, UTF-8-BOM CSV output, XLSX output, header-only exports, skip/upsert summaries, and clean accepted/rejected counts.**

```python
def test_import_validates_entire_file_before_writing(tmp_path, repo):
    path = tmp_path / "bad.csv"
    path.write_text("rating\n5\n", encoding="utf-8")
    with pytest.raises(InputFileError):
        import_reviews(ImportRequest(path), repo, read_reviews)
    assert repo.raw_count() == 0
```

- [x] **Step 2: Run the focused tests and confirm expected missing-module failures.**

Run: `python -m pytest tests/integration/test_file_io.py tests/unit/test_ingestion_service.py tests/unit/test_cleaning_service.py -q`

- [x] **Step 3: Implement readers that fully validate workbook/header structure before yielding named inputs and preserve cell values without cleaning.**

- [x] **Step 4: Implement CSV/XLSX writers that create parent directories, flatten only `ExportRow`, and return `GeneratedFile`.**

- [x] **Step 5: Implement ingestion and cleaning orchestration, summaries, and warning-safe rejection logging without review text.**

- [x] **Step 6: Re-run focused tests.**

Run: `python -m pytest tests/integration/test_file_io.py tests/unit/test_ingestion_service.py tests/unit/test_cleaning_service.py -q`

### Task 4: Query, detail, statistics, and export services

**Files:**
- Create: `review_analytics/services/query.py`, `review_analytics/services/exporting.py`
- Test: `tests/unit/test_query_service.py`, `tests/integration/test_query_flows.py`

**Interfaces:**
- Consumes: `ReviewListRequest`, `ReviewDetailRequest`, `StatsRequest`, `ExportRequest`, repository query methods, and `write_export`.
- Produces: `list_reviews`, `show_review`, `get_stats`, and `export_reviews` service functions returning documented Result DTOs.

- [x] **Step 1: Write failing tests for analyzed/unanalyzed list rows, sentiment filtering, out-of-range empty pages, pending/rejected/analyzed detail states, stats before/after partial analysis, filter semantics, and empty exports.**

```python
def test_stats_before_analysis_keeps_clean_denominator(query_service):
    result = query_service.stats(StatsRequest(ReviewFilter()))
    assert result.total_clean == 2
    assert result.analyzed_count == 0
    assert result.metrics.completion_rate == 0.0
    assert result.metrics.average_confidence is None
```

- [x] **Step 2: Run focused tests and verify failures.**

Run: `python -m pytest tests/unit/test_query_service.py tests/integration/test_query_flows.py -q`

- [x] **Step 3: Implement query/result assembly without CLI display strings inside repositories or DTOs.**

- [x] **Step 4: Implement export orchestration using the same filter semantics as query/statistics.**

- [x] **Step 5: Re-run focused tests.**

Run: `python -m pytest tests/unit/test_query_service.py tests/integration/test_query_flows.py -q`

### Task 5: Gemini boundary, sentiment analysis, and insight extraction

**Files:**
- Create: `review_analytics/clients/{__init__,gemini}.py`
- Create: `review_analytics/services/sentiment.py`, `review_analytics/services/extraction.py`
- Test: `tests/unit/test_gemini_client.py`, `tests/unit/test_sentiment_service.py`, `tests/unit/test_extraction_service.py`

**Interfaces:**
- Consumes: official `google-genai` client, `AnalysisInput`, `InsightInput`, repository target/save methods, batch/retry configuration.
- Produces: `GeminiClient.analyze(batch) -> tuple[SentimentResult, ...]`, `extract(input) -> InsightResult`, `merge_insights(parts) -> InsightResult`, plus analyze/extract service functions returning summaries.

- [x] **Step 1: Confirm current official SDK construction and structured-output API; keep SDK imports and response parsing inside `clients/gemini.py`.**

- [x] **Step 2: Write failing fake-SDK tests for exact response IDs, duplicate/missing/extra IDs, invalid enum/confidence, invalid evidence IDs, and safe project-error conversion.**

```python
def test_analysis_response_requires_exact_requested_ids(fake_sdk):
    client = GeminiClient(fake_sdk, "model")
    fake_sdk.response = {"results": [{"review_id": 99, "sentiment": "positive", "confidence": 0.9}]}
    with pytest.raises(AIResponseError):
        client.analyze((AnalysisInput(1, "본문"),))
```

- [x] **Step 3: Write failing service tests for target selection, force/skip behavior, batch boundaries, retry count, partial success codes, character chunks, merge calls, no-target behavior, scope hashes, and evidence de-duplication.**

- [x] **Step 4: Run focused tests and verify failures.**

Run: `python -m pytest tests/unit/test_gemini_client.py tests/unit/test_sentiment_service.py tests/unit/test_extraction_service.py -q`

- [x] **Step 5: Implement prompt/schema builders that explicitly treat reviews as untrusted data, validate the parsed response, and never log prompts, full texts, raw responses, or keys.**

- [x] **Step 6: Implement service retry/batch/chunk orchestration with no open SQLite write transaction during network calls; store only validated batches/results.**

- [x] **Step 7: Re-run focused tests.**

Run: `python -m pytest tests/unit/test_gemini_client.py tests/unit/test_sentiment_service.py tests/unit/test_extraction_service.py -q`

### Task 6: Dashboard snapshot, charts, and reports

**Files:**
- Create: `review_analytics/output/{__init__,charts,reports}.py`
- Create: `review_analytics/services/reporting.py`
- Test: `tests/unit/test_reporting_service.py`, `tests/integration/test_dashboard_output.py`

**Interfaces:**
- Consumes: `DashboardRequest`, `DashboardData`, query rows/statistics, exact-scope latest valid insight, font candidates.
- Produces: `render_charts(data, dir, fonts) -> tuple[GeneratedFile, ...]`, `render_report_text(data, format) -> str`, `write_report(...) -> GeneratedFile`, and `build_dashboard(...) -> GeneratedFilesResult`.

- [x] **Step 1: Write failing tests for exact filter/scope matching, stale/missing insight rejection before file writes, three nonempty PNGs, no-data placeholders, TOP-N evidence counts, MD/TXT content, and partial output failure.**

```python
def test_dashboard_without_current_insight_writes_nothing(tmp_path, service):
    with pytest.raises(StaleInsightError):
        service.build(DashboardRequest(output_dir=tmp_path))
    assert list(tmp_path.iterdir()) == []
```

- [x] **Step 2: Run focused tests and verify failures.**

Run: `python -m pytest tests/unit/test_reporting_service.py tests/integration/test_dashboard_output.py -q`

- [x] **Step 3: Build one immutable dashboard snapshot and render all outputs only from that object.**

- [x] **Step 4: Implement headless matplotlib charts, configured Korean-font selection/fallback warning, and placeholder plots when date/rating data is absent.**

- [x] **Step 5: Implement TXT/MD reports containing filters, timestamp, metrics, verified keyword evidence counts, summary, recommendations, and chart paths.**

- [x] **Step 6: Re-run focused tests.**

Run: `python -m pytest tests/unit/test_reporting_service.py tests/integration/test_dashboard_output.py -q`

### Task 7: Logging, CLI parser, composition root, and exit semantics

**Files:**
- Create: `review_analytics/logging_config.py`, `review_analytics/cli.py`, `main.py`
- Test: `tests/unit/test_logging_config.py`, `tests/integration/test_cli.py`

**Interfaces:**
- Consumes: `AppConfig`, service public functions/results, project errors.
- Produces: `build_parser(config) -> argparse.ArgumentParser`, `run(argv, dependencies=None) -> int`, and `main() -> int`.

- [x] **Step 1: Write failing parser tests for all nine command help screens, constraints, mutually exclusive selectors, ISO date/range validation, page-size maximum, export extension matching, and API-key-free non-AI help.**

- [x] **Step 2: Write failing execution tests for fixed list/show/stats display semantics and exit codes 0/1/2.**

- [x] **Step 3: Write failing logging tests for exactly one console/file handler, rotation settings, severity, timezone timestamp, safe fields, and secret/review-text absence.**

- [x] **Step 4: Run focused tests and verify failures.**

Run: `python -m pytest tests/unit/test_logging_config.py tests/integration/test_cli.py -q`

- [x] **Step 5: Implement parser/type validators and convert every Namespace immediately to the documented frozen request DTO.**

- [x] **Step 6: Implement composition and command dispatch; initialize SQLite lazily after help parsing and require `GEMINI_API_KEY` only for AI commands.**

- [x] **Step 7: Implement stable human-readable Korean output and safe project-error/partial-result exit mapping.**

- [x] **Step 8: Re-run focused tests and exercise `python main.py --help` plus every subcommand `--help`.**

Run: `python -m pytest tests/unit/test_logging_config.py tests/integration/test_cli.py -q`

### Task 8: Sample data, offline end-to-end flow, and user documentation

**Files:**
- Create: `data/sample_reviews.csv`
- Create: `tests/fixtures/sample_reviews.csv`, `tests/fakes.py`, `tests/e2e/test_offline_pipeline.py`
- Create: `README.md`
- Modify: architecture/policy docs only if implementation exposed a necessary contract clarification.

**Interfaces:**
- Consumes: the public CLI/composition interface and injectable fake Gemini implementation.
- Produces: a reproducible 30+ row sample and one offline acceptance test covering every command/output.

- [x] **Step 1: Add at least 32 varied Korean sample rows with multiple products/dates/ratings, duplicates, and cleanable/rejectable cases.**

- [x] **Step 2: Write a failing E2E test that performs import → clean → analyze(fake) → extract(fake) → list/show/stats → dashboard → CSV/XLSX export in a temporary workspace.**

```python
def test_full_offline_pipeline(app, sample_csv, tmp_path):
    assert app.run(["import", "--file", str(sample_csv)]) == 0
    assert app.run(["clean", "--pending"]) == 0
    assert app.run(["analyze", "--unanalyzed"]) == 0
    assert app.run(["extract"]) == 0
    assert app.run(["dashboard", "--output-dir", str(tmp_path / "out")]) == 0
```

- [x] **Step 3: Run the E2E test and verify failure before its remaining fixture/injection support is implemented.**

Run: `python -m pytest tests/e2e/test_offline_pipeline.py -q`

- [x] **Step 4: Complete fake injection and sample data until the entire flow passes without API key/network access.**

- [x] **Step 5: Write `README.md` as the single installation/usage source with virtualenv setup, `.env.sample`, config, all nine commands, output locations, test commands, and fake-vs-live API expectations.**

- [x] **Step 6: Run the complete suite, coverage-oriented command groups, help smoke tests, doc link scan, placeholder scan, and `git diff --check`.**

Run: `python -m pytest -q`

Run: `python main.py --help`

Run: `rg -n "TBD|T[O]DO|FIXME|미정|추후" README.md docs review_analytics tests`

Run: `git diff --check`

### Task 9: Direct review and fix loop

**Files:**
- Review: all changed implementation, tests, configuration, sample data, and standards.
- Modify: only files implicated by concrete review findings.

**Interfaces:**
- Consumes: approved design, independent standards, implementation plan, complete diff, and fresh verification evidence.
- Produces: a zero-finding approval or a prioritized finding list with file/line evidence.

- [x] **Step 1: Perform a direct specification-compliance review and require requirement-by-requirement evidence.**

- [x] **Step 2: Perform a separate direct code-quality review only after specification review passes.**

- [x] **Step 3: For every finding, add or strengthen a regression test first, reproduce the issue, implement the minimal fix, and re-run the focused and full suites.**

- [x] **Step 4: Repeat both direct review stages until both pass with no blocking findings.**

- [x] **Step 5: Run final verification from a clean process and report exact commands/results plus any unavoidable residual risk.**
