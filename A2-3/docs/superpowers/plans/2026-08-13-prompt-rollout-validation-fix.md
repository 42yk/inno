# Prompt Rollout Validation Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the `sentiment-v2` rollout explicit and safe, and reject empty AI insight text that violates the documented output contract.

**Architecture:** Keep version migration operator-controlled through the existing `analyze --all --force` command. When any persisted sentiment result is replaced, invalidate current aggregate insights in the same transaction. Enforce non-empty insight summary and recommendations at both JSON Schema and local-validation boundaries.

**Tech Stack:** Python 3, SQLite, Google GenAI structured JSON Schema, pytest, Markdown.

## Global Constraints

- Do not introduce automatic prompt-version coupling between Client and Repository.
- Preserve the current CLI interface and error codes.
- Use test-first red-green cycles for both production behavior changes.
- Do not use subagents.

---

### Task 1: Invalidate insights when sentiment results are replaced

**Files:**
- Modify: `tests/integration/test_analysis_repository.py`
- Modify: `review_analytics/repositories/analyses.py`

**Interfaces:**
- Consumes: `AnalysisRepository.save_sentiment_batch(results: tuple[SentimentResult, ...]) -> int`
- Produces: the same public method, with current insights marked stale when an existing sentiment row is updated

- [x] **Step 1: Write a failing integration test**

Add a test that saves a sentiment result, saves a current insight, replaces the sentiment result, and asserts `is_stale = 1` for the insight.

- [x] **Step 2: Run the focused test and verify RED**

Run: `python3 -m pytest tests/integration/test_analysis_repository.py -q`

Expected: failure because `save_sentiment_batch` currently leaves the insight current.

- [x] **Step 3: Implement transactional invalidation**

Track whether `INSERT ... ON CONFLICT DO UPDATE` replaced an existing analysis and run:

```sql
UPDATE insight_extractions SET is_stale = 1 WHERE is_stale = 0
```

inside the same transaction when replacement occurs.

- [x] **Step 4: Run the focused test and verify GREEN**

Run: `python3 -m pytest tests/integration/test_analysis_repository.py -q`

Expected: all tests pass.

### Task 2: Reject empty insight summary and recommendations

**Files:**
- Modify: `tests/unit/test_gemini_client.py`
- Modify: `review_analytics/clients/gemini.py`

**Interfaces:**
- Consumes: Gemini parsed insight JSON
- Produces: `InsightResult` only when summary and every recommendation contain non-whitespace text

- [x] **Step 1: Write failing unit tests**

Add cases for an empty summary and a whitespace-only recommendation; assert `INVALID_AI_RESPONSE`.

- [x] **Step 2: Run the focused tests and verify RED**

Run: `python3 -m pytest tests/unit/test_gemini_client.py -q`

Expected: new malformed cases are accepted and tests fail.

- [x] **Step 3: Implement Schema and local validation**

Set `minLength: 1` for summary and recommendation strings in `_INSIGHT_SCHEMA`, then reject `not summary.strip()` and recommendations where `not item.strip()` locally.

- [x] **Step 4: Run the focused tests and verify GREEN**

Run: `python3 -m pytest tests/unit/test_gemini_client.py -q`

Expected: all tests pass.

### Task 3: Document the controlled v2 rollout

**Files:**
- Modify: `docs/analysis/prompt-design.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: existing CLI `python3 main.py analyze --all --force`
- Produces: explicit migration and post-migration extraction procedure

- [x] **Step 1: Document rollout order**

State that existing databases must run `analyze --all --force`, that replaced sentiment results stale current insights, and that `extract` must be rerun for report scopes.

- [x] **Step 2: Reconcile the validation-plan wording**

Clarify that `sentiment-v2` is a documented candidate contract until the planned comparison is completed, and do not claim measured improvement.

### Task 4: Verify changes

**Files:**
- Verify all intended modified and new files in `A2-3`

- [x] **Step 1: Run repository checks**

Run:

```bash
git diff --check
python3 -m pytest -q
```

Expected: no diff errors and all tests pass.

- [x] **Step 2: Review the final scope**

Confirm that only the intended A2-3 documentation, implementation, tests, and plans changed. Leave the changes uncommitted because the user narrowed the request to modification only.
