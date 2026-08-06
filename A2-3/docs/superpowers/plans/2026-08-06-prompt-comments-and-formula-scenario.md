# Prompt, Function Comments, and Formula Scenario Implementation Plan

> **Execution note:** The user requires direct execution without subagents. Steps use checkbox (`- [ ]`) syntax for tracking, and no commit, push, or PR is authorized.

**Goal:** Add explicit Gemini task instructions, document spreadsheet-formula input as an undefined failure scenario without changing export behavior, and place a concise Korean role comment above every production function and method.

**Architecture:** Keep CLI options, Gemini model selection, DTOs, and persistence unchanged. Operation-specific system instructions remain inside the Gemini Client boundary and untrusted review text remains JSON data. Function comments are documentation-only and enforced by an AST-based test over `main.py` and `review_analytics/`.

**Tech Stack:** Python 3.10+, pytest, official `google-genai`, Markdown.

## Global Constraints

- Keep `gemini-3.1-flash-lite` and the existing `sentiment-v1`, `insight-v1`, and `insight-merge-v1` identifiers.
- Do not add spreadsheet formula neutralization or rejection behavior.
- Do not alter `--sentiment` CLI semantics.
- Preserve unrelated worktree changes and do not commit.

---

### Task 1: Document the undefined spreadsheet-formula scenario

**Files:**
- Create: `docs/failure-scenarios/spreadsheet-formula-input.md`
- Modify: `docs/README.md`

**Interfaces:**
- Consumes: current CSV/XLSX export behavior.
- Produces: a registered standalone document that states scope, trigger, current behavior, operator guidance, and the absence of runtime mitigation.

- [x] **Step 1:** Write the scenario document without changing application behavior.
- [x] **Step 2:** Register it in the documentation map.
- [x] **Step 3:** Verify the new local Markdown link resolves.

### Task 2: Add explicit Gemini operation instructions with TDD

**Files:**
- Modify: `tests/unit/test_gemini_client.py`
- Modify: `review_analytics/clients/gemini.py`
- Modify: `docs/architecture/data-communication.md`

**Interfaces:**
- Consumes: `GeminiClient.analyze`, `extract`, `merge_insights`, and `_generate`.
- Produces: separate system instructions for classification, insight extraction, and partial-insight merging while review content stays in `contents` JSON.

- [x] **Step 1:** Add tests asserting each SDK call contains its operation-specific task, allowed sentiment labels or extraction duties, and untrusted-data instruction.
- [x] **Step 2:** Run the focused test and confirm it fails because the generic instruction lacks the task.
- [x] **Step 3:** Add the three instructions and pass the selected instruction through `_generate`.
- [x] **Step 4:** Run the focused Gemini Client suite and confirm it passes.

### Task 3: Add concise comments above every production function

**Files:**
- Create: `tests/unit/test_function_comments.py`
- Modify: `main.py`
- Modify: every Python module under `review_analytics/` that defines a function or method.

**Interfaces:**
- Consumes: Python AST line numbers and existing production functions.
- Produces: one immediately preceding Korean `#` role comment per function or method, placed above decorators when present.

- [x] **Step 1:** Add an AST-based test that reports every production function lacking a preceding comment.
- [x] **Step 2:** Run the test and confirm it fails with the current uncommented function list.
- [x] **Step 3:** Add concise role comments without changing behavior or signatures.
- [x] **Step 4:** Run the comment test and focused behavior suites.

### Task 4: Verify and review

**Files:**
- Review: all files changed by Tasks 1-3.

**Interfaces:**
- Consumes: implementation diff and fresh test output.
- Produces: verified behavior and documentation with no unresolved P1 finding.

- [x] **Step 1:** Run `python -m pytest -q -W error`.
- [x] **Step 2:** Run the offline E2E test, compileall, Markdown link check, placeholder scan, trailing-whitespace scan, and `git diff --check`.
- [x] **Step 3:** Directly review that formula handling remains documentation-only, `--sentiment` is unchanged, and no review text appears in a system instruction or log.
