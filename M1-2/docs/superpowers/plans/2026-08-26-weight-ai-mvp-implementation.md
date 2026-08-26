# Weight AI MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Execution constraint:** Implement inline with the primary agent. Do not dispatch subagents or create separate Codex tasks. Complete the backend quality gate before starting frontend feature work.

**Goal:** Build and deploy a vanilla JavaScript service that stores at least 100 date-and-weight records, exposes FastAPI CRUD and conversation APIs, and answers summary, exact-date, and date-range questions through OpenAI Function Calling.

**Architecture:** A FastAPI backend separates routers, Pydantic schemas, services, Firestore repositories, and an OpenAI Responses API client. HTTP APIs and read-only Function Calling tools share the same data and summary services. After the backend contract and tests pass, a vanilla HTML/CSS/ES Module frontend consumes those APIs in a single-page dashboard.

**Tech Stack:** Python 3.10+, FastAPI, Uvicorn, Pydantic, Firebase Admin/Firestore, OpenAI Python SDK, python-dotenv, pytest, httpx, vanilla HTML/CSS/JavaScript, Node.js built-in test runner, Render, Vercel

**Spec:** `M1-2/docs/superpowers/specs/2026-08-25-weight-ai-mvp-design.md`

## Global Constraints

- Work only under `M1-2` and preserve unrelated repository changes.
- Do not use subagents; execute and review every task in one integrated session.
- Pass the backend quality gate before writing frontend feature code.
- Use Python 3.10 or later and a local `venv`.
- Use `fastapi`, `uvicorn`, `firebase-admin`, `openai`, and `python-dotenv` as runtime packages.
- Use Firestore collections named `data` and `conversations`.
- Use each `YYYY-MM-DD` date as its `data` document ID.
- Accept 20.0kg through 300.0kg with at most one decimal place.
- Reject future and duplicate dates; limit memo text to 200 characters.
- Compare the recent 10 records with the previous 10; `-0.2kg` through `+0.2kg` means `유지`.
- Inject the same summary service result exposed by `/api/data/summary` before the first model call.
- Allow AI tools to read and analyze only; never expose write tools.
- Store final user and assistant messages only, excluding prompts and tool payloads.
- Use vanilla HTML, CSS, and JavaScript without a frontend framework or bundler.
- Keep secrets out of Git, browser code, logs, screenshots, and API errors.
- Repeat review and verification until every check passes and no finding remains.

## Command Convention

- Run Task 1 through Task 9 command blocks from `M1-2/backend`.
- Run Task 10 through Task 14 command blocks from `M1-2/frontend`.
- Run Task 15 command blocks from the repository root unless the block changes directory explicitly.
- Treat each shell code block as a fresh shell; a `cd` affects only that block.

## Planned File Map

```text
M1-2/backend/
├── app/
│   ├── main.py, config.py, firebase.py, dependencies.py, errors.py
│   ├── logging_config.py, middleware.py
│   ├── routers/{data,conversations,chat}.py
│   ├── schemas/{common,data,conversations,chat,tools}.py
│   ├── repositories/{data_repository,conversation_repository}.py
│   ├── services/{data_service,summary_service,conversation_service,tool_service,chat_service}.py
│   └── clients/openai_client.py
├── data/weights.csv
├── scripts/{generate_sample_csv,import_csv}.py
├── tests/{unit,integration,fakes}/
├── .env.example, .gitignore, README.md, requirements.txt
└── render.yaml

M1-2/frontend/
├── src/index.html
├── src/css/styles.css
├── src/js/{app,api,state,utils,summary,data,conversations,chat}.js
├── scripts/build.mjs
├── tests/{api,state,utils}.test.js
├── .gitignore, package.json, README.md
└── vercel.json

M1-2/
├── README.md
└── screenshots/{chat-summary,data-crud,conversation-load}.png
```

---

### Task 1: Backend Runtime Foundation and Health Endpoint

**Files:**
- Create: `M1-2/backend/app/__init__.py`
- Create: `M1-2/backend/app/config.py`
- Create: `M1-2/backend/app/errors.py`
- Create: `M1-2/backend/app/main.py`
- Create: `M1-2/backend/app/routers/__init__.py`
- Create: `M1-2/backend/requirements.txt`
- Create: `M1-2/backend/.env.example`
- Create: `M1-2/backend/.gitignore`
- Test: `M1-2/backend/tests/unit/test_config.py`
- Test: `M1-2/backend/tests/integration/test_health.py`

**Interfaces:**
- Produces: `Settings.from_env() -> Settings`
- Produces: `create_app(settings: Settings | None = None) -> FastAPI`
- Produces: `GET /health -> {"status": "ok"}`

- [ ] **Step 1: Define dependencies and create the virtual environment**

```text
fastapi>=0.115,<1
uvicorn[standard]>=0.30,<1
firebase-admin>=6.5,<8
openai>=1.50,<3
python-dotenv>=1.0,<2
pytest>=8,<9
httpx>=0.27,<1
```

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

- [ ] **Step 2: Write failing configuration and health tests**

```python
def test_settings_parses_origins(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-model")
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_JSON", '{"project_id":"test"}')
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:5173, https://app.example")
    settings = Settings.from_env()
    assert settings.allowed_origins == ("http://localhost:5173", "https://app.example")

def test_health_returns_ok():
    client = TestClient(create_app(Settings.for_test()))
    assert client.get("/health").json() == {"status": "ok"}
```

- [ ] **Step 3: Confirm the tests fail**

Run: `.venv/bin/python -m pytest tests/unit/test_config.py tests/integration/test_health.py -v`

Expected: FAIL because `Settings` and `create_app` do not exist.

- [ ] **Step 4: Implement settings, CORS, common errors, and health**

```python
@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    openai_max_output_tokens: int
    firebase_service_account_json: str
    allowed_origins: tuple[str, ...]
    max_tool_calls: int = 4

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        return cls(
            openai_api_key=_required("OPENAI_API_KEY"),
            openai_model=_required("OPENAI_MODEL"),
            openai_max_output_tokens=int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "500")),
            firebase_service_account_json=_required("FIREBASE_SERVICE_ACCOUNT_JSON"),
            allowed_origins=tuple(x.strip() for x in _required("ALLOWED_ORIGINS").split(",") if x.strip()),
        )
```

`create_app` registers CORS and `/health` but does not initialize Firebase or OpenAI yet.

- [ ] **Step 5: Verify and commit**

```bash
.venv/bin/python -m pytest tests/unit/test_config.py tests/integration/test_health.py -v
.venv/bin/python -m compileall -q app
git diff --check
git add .
git commit -m "M1-2: 백엔드 실행 기반 구성"
```

---

### Task 2: Deterministic Sample Dataset

**Files:**
- Create: `M1-2/backend/scripts/generate_sample_csv.py`
- Create: `M1-2/backend/data/weights.csv`
- Test: `M1-2/backend/tests/unit/test_sample_csv.py`

**Interfaces:**
- Produces: `build_rows(count: int = 120) -> list[dict[str, str]]`
- Produces: `write_csv(path: Path, rows: Sequence[dict[str, str]]) -> None`
- Produces: UTF-8 CSV with `date,value,memo` and 120 valid records

- [ ] **Step 1: Write the failing generator test**

```python
def test_build_rows_produces_valid_irregular_time_series():
    rows = build_rows(120)
    dates = [date.fromisoformat(row["date"]) for row in rows]
    values = [Decimal(row["value"]) for row in rows]
    assert len(rows) == 120
    assert dates == sorted(dates)
    assert len(set(dates)) == 120
    assert any((right - left).days > 1 for left, right in pairwise(dates))
    assert all(Decimal("20.0") <= value <= Decimal("300.0") for value in values)
    assert all(value == value.quantize(Decimal("0.1")) for value in values)
```

- [ ] **Step 2: Confirm the test fails**

Run: `.venv/bin/python -m pytest tests/unit/test_sample_csv.py -v`

Expected: FAIL because the generator module does not exist.

- [ ] **Step 3: Implement deterministic generation**

```python
def build_rows(count: int = 120) -> list[dict[str, str]]:
    start = date(2025, 1, 1)
    rows = []
    for index in range(count):
        measured_on = start + timedelta(days=index + index // 3)
        weight = 78.0 - (0.035 * index) + (0.4 * math.sin(index / 6))
        rows.append({"date": measured_on.isoformat(), "value": f"{weight:.1f}", "memo": ""})
    return rows
```

Write with `newline=""`, UTF-8, and `csv.DictWriter` field order `date,value,memo`.

- [ ] **Step 4: Generate and verify `weights.csv`**

```bash
.venv/bin/python scripts/generate_sample_csv.py
wc -l data/weights.csv
head -n 4 data/weights.csv
tail -n 3 data/weights.csv
.venv/bin/python -m pytest tests/unit/test_sample_csv.py -v
```

Expected: 121 lines including the header and all tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/generate_sample_csv.py data/weights.csv tests/unit/test_sample_csv.py
git commit -m "M1-2: 체중 샘플 데이터 생성"
```

---

### Task 3: Data Schemas, Validation, and Analytics

**Files:**
- Create: `M1-2/backend/app/schemas/{__init__,common,data}.py`
- Create: `M1-2/backend/app/services/{__init__,summary_service}.py`
- Test: `M1-2/backend/tests/unit/test_data_schemas.py`
- Test: `M1-2/backend/tests/unit/test_summary_service.py`

**Interfaces:**
- Produces: `DataCreate`, `DataUpdate`, `DataRecord`
- Produces: `DataSummary`, `PeriodStatistics`, `TrendResult`
- Produces: `calculate_summary(records) -> DataSummary`
- Produces: `calculate_period_statistics(records) -> PeriodStatistics`

- [ ] **Step 1: Write failing validation tests**

```python
@pytest.mark.parametrize("value", [Decimal("19.9"), Decimal("300.1"), Decimal("72.45")])
def test_invalid_weight_is_rejected(value):
    with pytest.raises(ValidationError):
        DataCreate(date=date.today(), value=value, memo="")
```

Also reject future dates and a 201-character memo.

- [ ] **Step 2: Write failing summary tests**

```python
assert calculate_summary([]).count == 0
assert calculate_summary(records_19).trend.status == "insufficient_data"
assert calculate_summary(diff_minus_point_two).trend.status == "maintain"
assert calculate_summary(diff_below_minus_point_two).trend.status == "decrease"
assert calculate_summary(diff_plus_point_two).trend.status == "maintain"
assert calculate_summary(diff_above_plus_point_two).trend.status == "increase"
```

Assert all tied minimum and maximum dates are returned in sorted order.

- [ ] **Step 3: Confirm both test files fail**

Run: `.venv/bin/python -m pytest tests/unit/test_data_schemas.py tests/unit/test_summary_service.py -v`

- [ ] **Step 4: Implement Pydantic models**

```python
class DataCreate(BaseModel):
    date: date
    value: Decimal = Field(ge=Decimal("20.0"), le=Decimal("300.0"), decimal_places=1)
    memo: str = Field(default="", max_length=200)

    @field_validator("date")
    @classmethod
    def reject_future_date(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("future dates are not allowed")
        return value
```

- [ ] **Step 5: Implement Decimal analytics**

Sort ascending, quantize with `Decimal("0.1")` and `ROUND_HALF_UP`, and classify:

```python
if len(records) < 20:
    status = "insufficient_data"
elif difference < Decimal("-0.2"):
    status = "decrease"
elif difference > Decimal("0.2"):
    status = "increase"
else:
    status = "maintain"
```

- [ ] **Step 6: Verify and commit**

```bash
.venv/bin/python -m pytest tests/unit/test_data_schemas.py tests/unit/test_summary_service.py -v
.venv/bin/python -m pytest -q
git add app/schemas app/services tests
git commit -m "M1-2: 체중 검증과 통계 계산 구현"
```

---

### Task 4: Firestore Data Repository and Service

**Files:**
- Create: `M1-2/backend/app/firebase.py`
- Create: `M1-2/backend/app/repositories/{__init__,data_repository}.py`
- Create: `M1-2/backend/app/services/data_service.py`
- Create: `M1-2/backend/app/dependencies.py`
- Create: `M1-2/backend/tests/fakes/{__init__,repositories}.py`
- Test: `M1-2/backend/tests/unit/test_data_service.py`
- Test: `M1-2/backend/tests/integration/test_firestore_data_repository.py`

**Interfaces:**
- Produces: `DataRepository` protocol with `list`, `get`, `create`, `replace`, `delete`
- Produces: `FirestoreDataRepository(client)`
- Produces: `DataService.list_records`, `find_record`, `create_record`, `update_record`, `delete_record`
- Produces: `SummaryService.get_summary()` and `SummaryService.get_period_statistics(start_date, end_date)`

- [ ] **Step 1: Write failing service tests with an in-memory repository**

```python
def test_create_rejects_duplicate_date(data_service):
    payload = DataCreate(date=date(2025, 1, 1), value=Decimal("72.4"))
    data_service.create_record(payload)
    with pytest.raises(DuplicateDateError):
        data_service.create_record(payload)

def test_update_moves_document_id(data_service):
    original = data_service.create_record(DataCreate(date=date(2025, 1, 1), value=Decimal("72.4")))
    updated = data_service.update_record(original.id, DataUpdate(date=date(2025, 1, 2), value=Decimal("72.2")))
    assert updated.id == "2025-01-02"
    assert data_service.find_record("2025-01-01") is None
```

Also cover inclusive range filtering, descending order, missing IDs, and date-move collisions.

- [ ] **Step 2: Confirm the service tests fail**

Run: `.venv/bin/python -m pytest tests/unit/test_data_service.py -v`

- [ ] **Step 3: Implement Firebase initialization and repository protocol**

Parse the service-account JSON with `json.loads`, initialize Firebase once, and return `firestore.client()`. Type all date bounds and return models.

```python
class DataRepository(Protocol):
    def list(self, start_date: date | None, end_date: date | None, descending: bool) -> list[DataRecord]: ...
    def get(self, record_id: str) -> DataRecord | None: ...
    def create(self, payload: DataCreate) -> DataRecord: ...
    def replace(self, record_id: str, payload: DataUpdate) -> DataRecord: ...
    def delete(self, record_id: str) -> bool: ...
```

- [ ] **Step 4: Implement Firestore operations and service rules**

Use `data/{YYYY-MM-DD}`. Use server timestamps. For a date change, run a Firestore transaction that checks the new ID, creates the replacement while retaining `created_at`, and deletes the old document atomically. The service translates duplicate, missing, and reversed-period conditions to domain exceptions.

`SummaryService` loads records through `DataService`, then delegates calculation to the pure functions from Task 3. Both `/api/data/summary` and chat tools consume this class.

- [ ] **Step 5: Verify and commit**

```bash
.venv/bin/python -m pytest tests/unit/test_data_service.py tests/integration/test_firestore_data_repository.py -v
.venv/bin/python -m pytest -q
git add app tests
git commit -m "M1-2: Firestore 체중 저장 계층 구현"
```

Normal tests use a fake Firestore client or emulator fixture and never contact production.

---

### Task 5: Data CRUD, Summary API, and CSV Import

**Files:**
- Create: `M1-2/backend/app/routers/data.py`
- Create: `M1-2/backend/scripts/import_csv.py`
- Test: `M1-2/backend/tests/integration/test_data_api.py`
- Test: `M1-2/backend/tests/unit/test_import_csv.py`
- Modify: `M1-2/backend/app/main.py`
- Modify: `M1-2/backend/app/dependencies.py`

**Interfaces:**
- Produces: all required endpoints under `/api/data`
- Produces: `parse_csv(path: Path) -> ImportBatch`
- Produces: `import_records(service, batch, dry_run) -> ImportReport`

- [ ] **Step 1: Write failing endpoint contract tests**

```text
POST /api/data                  201, 409, 422
GET /api/data                   200
GET /api/data with date bounds  200 or 400
PUT /api/data/{id}              200, 404, 409, 422
DELETE /api/data/{id}           204, 404
GET /api/data/summary           200
```

Assert the complete summary shape: period, count, metrics, tied min/max dates, first/latest/change, and trend.

- [ ] **Step 2: Confirm endpoint tests fail**

Run: `.venv/bin/python -m pytest tests/integration/test_data_api.py -v`

- [ ] **Step 3: Implement routes and error envelopes**

Register `/summary` before any dynamic ID route. Return:

```json
{"error":{"code":"duplicate_date","message":"해당 날짜의 기록이 이미 존재합니다.","details":null}}
```

Map bad periods to 400, duplicates to 409, missing data to 404, and Pydantic failures to 422.

- [ ] **Step 4: Write failing import tests and implement import**

Test exact headers, blank-row skips, malformed values, duplicates inside the file, dry-run behavior, and report counts. Provide:

```bash
.venv/bin/python scripts/import_csv.py data/weights.csv --dry-run
.venv/bin/python scripts/import_csv.py data/weights.csv
```

Dry-run must report 120 valid records and zero writes. Real import preserves existing dates and reports created/skipped/failed counts.

- [ ] **Step 5: Verify and commit**

```bash
.venv/bin/python -m pytest tests/integration/test_data_api.py tests/unit/test_import_csv.py -v
.venv/bin/python -m pytest -q
git add .
git commit -m "M1-2: 데이터 API와 CSV 가져오기 구현"
```

---

### Task 6: Conversation Persistence and APIs

**Files:**
- Create: `M1-2/backend/app/schemas/conversations.py`
- Create: `M1-2/backend/app/repositories/conversation_repository.py`
- Create: `M1-2/backend/app/services/conversation_service.py`
- Create: `M1-2/backend/app/routers/conversations.py`
- Test: `M1-2/backend/tests/unit/test_conversation_service.py`
- Test: `M1-2/backend/tests/integration/test_conversation_api.py`
- Modify: `M1-2/backend/tests/fakes/repositories.py`
- Modify: `M1-2/backend/app/main.py`

**Interfaces:**
- Produces: `Message(role: Literal["user", "assistant"], content: str, created_at: datetime)`
- Produces: `ConversationService.create`, `list`, `get`, `delete`, `append_exchange`
- Produces: `POST/GET /api/conversations` and `GET/DELETE /api/conversations/{id}`

- [ ] **Step 1: Write failing service and API tests**

```python
def test_append_exchange_creates_title_from_first_question(service):
    conversation = service.append_exchange(None, "3월 평균 체중은?", "72.1kg입니다.")
    assert conversation.title == "3월 평균 체중은?"
    assert [message.role for message in conversation.messages] == ["user", "assistant"]

def test_append_exchange_preserves_order(service):
    first = service.append_exchange(None, "첫 질문", "첫 답변")
    second = service.append_exchange(first.id, "둘째 질문", "둘째 답변")
    assert [m.content for m in second.messages] == ["첫 질문", "첫 답변", "둘째 질문", "둘째 답변"]
```

Also test 60-character normalized titles, updated-time ordering, 404 responses, deletion, list responses without messages, and detail responses with messages.

- [ ] **Step 2: Confirm tests fail**

Run: `.venv/bin/python -m pytest tests/unit/test_conversation_service.py tests/integration/test_conversation_api.py -v`

- [ ] **Step 3: Implement persistence and service rules**

Use Firestore automatic IDs. Store only user and assistant roles. Use server timestamps and a transaction when appending each user/assistant exchange.

- [ ] **Step 4: Implement API routes**

`GET /api/conversations` returns metadata without messages. Detail returns all messages. Delete returns 204. POST accepts a title and a validated user/assistant message list to satisfy the assignment endpoint.

- [ ] **Step 5: Verify and commit**

```bash
.venv/bin/python -m pytest tests/unit/test_conversation_service.py tests/integration/test_conversation_api.py -v
.venv/bin/python -m pytest -q
git add app tests
git commit -m "M1-2: 대화 기록 저장 API 구현"
```

---

### Task 7: Read-only Function Calling Tools

**Files:**
- Create: `M1-2/backend/app/schemas/tools.py`
- Create: `M1-2/backend/app/services/tool_service.py`
- Test: `M1-2/backend/tests/unit/test_tool_service.py`

**Interfaces:**
- Produces: `ToolService.execute(name: str, raw_arguments: str | dict[str, object]) -> dict[str, object]`
- Produces: `ToolService.definitions() -> list[dict[str, object]]`
- Produces: `get_weight_summary`, `get_weight_by_date`, `get_weight_records`, `get_weight_statistics`

- [ ] **Step 1: Write failing definition and dispatch tests**

```python
def test_tool_definitions_are_strict_and_read_only(tool_service):
    definitions = tool_service.definitions()
    assert {tool["name"] for tool in definitions} == {
        "get_weight_summary", "get_weight_by_date",
        "get_weight_records", "get_weight_statistics",
    }
    assert all(tool["parameters"]["additionalProperties"] is False for tool in definitions)

def test_unknown_tool_is_rejected(tool_service):
    with pytest.raises(UnknownToolError):
        tool_service.execute("delete_weight", {})
```

Also test malformed JSON, invalid/reversed dates, exact-date `not_found`, ascending records, and server-calculated period statistics.

- [ ] **Step 2: Confirm tests fail**

Run: `.venv/bin/python -m pytest tests/unit/test_tool_service.py -v`

- [ ] **Step 3: Implement strict schemas and explicit dispatch**

```python
self._handlers = {
    "get_weight_summary": self._get_summary,
    "get_weight_by_date": self._get_by_date,
    "get_weight_records": self._get_records,
    "get_weight_statistics": self._get_statistics,
}
```

Validate arguments with Pydantic. Every handler delegates to `DataService` or `SummaryService`; no handler writes to a repository.

- [ ] **Step 4: Verify the read-only boundary and commit**

```bash
.venv/bin/python -m pytest tests/unit/test_tool_service.py -v
! rg -n 'create_weight|update_weight|delete_weight' app/schemas/tools.py app/services/tool_service.py
git add app tests/unit/test_tool_service.py
git commit -m "M1-2: 읽기 전용 AI 도구 구현"
```

---

### Task 8: OpenAI Client, Chat Service, and Chat API

**Files:**
- Create: `M1-2/backend/app/schemas/chat.py`
- Create: `M1-2/backend/app/clients/{__init__,openai_client}.py`
- Create: `M1-2/backend/app/services/chat_service.py`
- Create: `M1-2/backend/app/routers/chat.py`
- Create: `M1-2/backend/tests/fakes/openai_client.py`
- Test: `M1-2/backend/tests/unit/test_chat_service.py`
- Test: `M1-2/backend/tests/integration/test_chat_api.py`
- Modify: `M1-2/backend/app/main.py`
- Modify: `M1-2/backend/app/dependencies.py`

**Interfaces:**
- Produces: `ChatRequest(message: str, conversation_id: str | None)` with 1000-character limit
- Produces: `ChatResult(conversation_id: str, answer: str, tools_used: list[str])`
- Produces: `OpenAIClient.start(...) -> ModelTurn`
- Produces: `OpenAIClient.continue_with_tools(...) -> ModelTurn`
- Produces: `ChatService.chat(request: ChatRequest) -> ChatResult`
- Produces: `POST /api/chat`

- [ ] **Step 1: Write failing tests with a scripted fake OpenAI client**

Prove these flows:

```text
summary loads before the first model call
current summary appears in system instructions
direct final text saves one exchange
date question dispatches get_weight_by_date
range question dispatches get_weight_statistics
invalid tool arguments return safe tool errors
more than four tool calls stop
OpenAI failure stores no exchange
existing conversation history is supplied
```

The fake records instructions, messages, definitions, outputs, and call count.

- [ ] **Step 2: Confirm tests fail**

Run: `.venv/bin/python -m pytest tests/unit/test_chat_service.py tests/integration/test_chat_api.py -v`

- [ ] **Step 3: Implement prompt and OpenAI Responses adapter**

The fixed policy states that answers use stored summary/tool results only, concrete data questions use tools, missing values are never estimated, and medical diagnosis or treatment instructions are forbidden. Map SDK output items into internal `ModelTurn(text, function_calls, response_id)` and preserve every tool `call_id`.

- [ ] **Step 4: Implement the bounded tool loop**

```python
for _ in range(settings.max_tool_calls + 1):
    if turn.final_text is not None:
        saved = conversations.append_exchange(conversation_id, request.message, turn.final_text)
        return ChatResult(conversation_id=saved.id, answer=turn.final_text, tools_used=tools_used)
    outputs = [execute_call(call) for call in turn.function_calls]
    tools_used.extend(call.name for call in turn.function_calls)
    turn = ai_client.continue_with_tools(turn.response_id, outputs)
raise ToolCallLimitError()
```

Do not save before final text exists.

- [ ] **Step 5: Implement `/api/chat` errors**

Map OpenAI errors to 502, Firestore failures to 503, and request validation to 422. Do not return raw prompts, tool exceptions, stack traces, or credentials.

- [ ] **Step 6: Verify and commit**

```bash
.venv/bin/python -m pytest tests/unit/test_chat_service.py tests/integration/test_chat_api.py -v
.venv/bin/python -m pytest -q
git add app tests
git commit -m "M1-2: Function Calling 채팅 API 구현"
```

---

### Task 9: Backend Assembly, Documentation, and Quality Gate

**Files:**
- Create: `M1-2/backend/README.md`
- Create: `M1-2/backend/render.yaml`
- Create: `M1-2/backend/app/logging_config.py`
- Create: `M1-2/backend/app/middleware.py`
- Modify: `M1-2/backend/app/main.py`
- Modify: `M1-2/backend/.env.example`
- Test: `M1-2/backend/tests/integration/test_app_contract.py`

**Interfaces:**
- Produces: fully wired production `create_app()`
- Produces: Render start command and `/health` health check
- Gates: every frontend task

- [ ] **Step 1: Write the failing OpenAPI contract test**

```python
required = {
    "/api/data": {"get", "post"},
    "/api/data/{id}": {"put", "delete"},
    "/api/data/summary": {"get"},
    "/api/conversations": {"get", "post"},
    "/api/conversations/{id}": {"get", "delete"},
    "/api/chat": {"post"},
}
```

Assert `/health` and `/docs` return 200 with test dependencies.

- [ ] **Step 2: Wire production dependencies once at startup**

Create Firebase, repositories, services, ToolService, OpenAI client, and ChatService once and store them in `app.state`. Dependency functions retrieve those instances per request.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.services = build_services(app.state.settings)
    yield
```

Add request-ID/timing middleware. Log method, path, status, elapsed time, model name, and tool name only; exclude prompts, complete weight data, API keys, and service-account JSON.

- [ ] **Step 3: Add Render and local instructions**

```yaml
services:
  - type: web
    name: weight-ai-backend
    runtime: python
    rootDir: M1-2/backend
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
```

Document environment setup, sample regeneration, dry-run/real import, Uvicorn, and Swagger.

- [ ] **Step 4: Run the backend quality gate**

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app scripts
.venv/bin/python scripts/import_csv.py data/weights.csv --dry-run
git diff --check
```

Pass only when tests pass, compilation exits 0, dry-run reports 120 valid rows and zero writes, diff check is clean, and every required OpenAPI route exists.

- [ ] **Step 5: Repeat the backend review until clear**

Review spec/API coverage, validation, error mapping, Firestore transactions, tool allow-list/arguments, secret exposure, logs, test gaps, and dead code. For every finding, add or strengthen a failing test, implement the smallest correction, rerun the focused test, then rerun Step 4. Continue until no finding remains.

- [ ] **Step 6: Commit the passing backend**

```bash
git add .
git commit -m "M1-2: 백엔드 MVP 품질 게이트 통과"
```

Do not start Task 10 until this task passes completely.

---

### Task 10: Frontend Static Build, API Client, and State Foundation

**Files:**
- Create: `M1-2/frontend/package.json`
- Create: `M1-2/frontend/.gitignore`
- Create: `M1-2/frontend/scripts/build.mjs`
- Create: `M1-2/frontend/src/index.html`
- Create: `M1-2/frontend/src/css/styles.css`
- Create: `M1-2/frontend/src/js/{app,api,state,utils}.js`
- Test: `M1-2/frontend/tests/{api,state,utils}.test.js`

**Interfaces:**
- Produces: `request(path, options)`, `ApiError`, and endpoint wrappers
- Produces: `createStore(initialState) -> {getState, setState, subscribe}`
- Produces: date, weight, change, and time formatters
- Produces: `npm test` and `npm run build`

- [ ] **Step 1: Create scripts and failing tests**

```json
{
  "name": "weight-ai-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node --test tests/*.test.js",
    "build": "node scripts/build.mjs"
  }
}
```

Test URL joining, JSON and 204 responses, error envelope parsing, store subscriptions, and outputs `72.4kg`, `+0.6kg`, `-0.6kg`, and `0.0kg`.

- [ ] **Step 2: Confirm tests fail**

Run: `npm test`

- [ ] **Step 3: Implement API and state foundations**

Read the base URL only from `window.APP_CONFIG.API_BASE_URL`. Provide wrappers for every backend route and make `fetch` injectable in tests.

```javascript
const initialState = {
  data: [], summary: null, conversations: [],
  currentConversationId: null, messages: [], editingDataId: null,
  loading: { initial: false, chat: false, data: false, conversations: false },
  notice: null,
};
```

- [ ] **Step 4: Implement the dependency-free build**

```javascript
const apiBaseUrl = process.env.API_BASE_URL;
if (!apiBaseUrl) throw new Error("API_BASE_URL is required");
await writeFile(
  join(distDir, "config.js"),
  `window.APP_CONFIG = ${JSON.stringify({ API_BASE_URL: apiBaseUrl })};\n`,
  "utf8",
);
```

Copy `src` to `dist`; do not commit `dist`.

- [ ] **Step 5: Verify and commit**

```bash
npm test
API_BASE_URL=http://localhost:8000 npm run build
test -f dist/index.html
test -f dist/config.js
git diff --check
git add .
git commit -m "M1-2: 프론트엔드 실행 기반 구성"
```

---

### Task 11: Summary and Data CRUD Interface

**Files:**
- Create: `M1-2/frontend/src/js/summary.js`
- Create: `M1-2/frontend/src/js/data.js`
- Modify: `M1-2/frontend/src/index.html`
- Modify: `M1-2/frontend/src/css/styles.css`
- Modify: `M1-2/frontend/src/js/app.js`
- Modify: `M1-2/frontend/src/js/state.js`
- Test: `M1-2/frontend/tests/utils.test.js`

**Interfaces:**
- Consumes: `listData`, `createData`, `updateData`, `deleteData`, `getSummary`
- Produces: `initSummaryPanel`, `renderSummary`, `initDataPanel`, `renderDataList`

- [ ] **Step 1: Add failing validation and view-model tests**

```javascript
assert.deepEqual(validateWeightInput({ date: "", value: "72.4", memo: "" }), {
  date: "날짜를 입력해 주세요.",
});
assert.equal(toSummaryView({ count: 0 }).empty, true);
assert.equal(toSummaryView(summary).trendLabel, "감소");
```

- [ ] **Step 2: Confirm tests fail**

Run: `npm test`

- [ ] **Step 3: Build semantic summary and CRUD markup**

Add visible labels for date, weight, and memo; save/cancel controls; an `aria-live` notice; all summary fields; and edit/delete controls. Non-submit actions use `type="button"`.

- [ ] **Step 4: Implement safe CRUD behavior**

Use `textContent` and `createElement`, never memo interpolation into HTML. After success:

```javascript
await Promise.all([loadData(), loadSummary()]);
```

Preserve form values on failure, map 409 to the date field, and confirm deletion with date and weight.

- [ ] **Step 5: Verify against the completed local backend**

```bash
npm test
API_BASE_URL=http://localhost:8000 npm run build
python3 -m http.server 5173 -d dist
```

Check initial list/summary, create, date-changing edit, duplicate rejection, delete cancel/confirm, and summary refresh.

- [ ] **Step 6: Review and commit**

```bash
git diff --check
git add .
git commit -m "M1-2: 체중 요약과 CRUD 화면 연동"
```

---

### Task 12: Conversation History Interface

**Files:**
- Create: `M1-2/frontend/src/js/conversations.js`
- Modify: `M1-2/frontend/src/index.html`
- Modify: `M1-2/frontend/src/css/styles.css`
- Modify: `M1-2/frontend/src/js/app.js`
- Modify: `M1-2/frontend/src/js/state.js`
- Test: `M1-2/frontend/tests/state.test.js`

**Interfaces:**
- Consumes: `listConversations`, `getConversation`, `deleteConversation`
- Produces: `initConversationPanel`, `loadConversations`, `selectConversation`, `startNewConversation`

- [ ] **Step 1: Write failing state-transition tests**

```javascript
assert.equal(startNewConversationState(existing).currentConversationId, null);
assert.deepEqual(startNewConversationState(existing).messages, []);
assert.equal(afterDeletingSelected.currentConversationId, null);
assert.deepEqual(afterDeletingUnselected.messages, existing.messages);
```

Test that only the latest requested conversation detail is applied.

- [ ] **Step 2: Confirm tests fail**

Run: `npm test`

- [ ] **Step 3: Implement history markup and behavior**

Render updated-time descending items, `aria-current` selection, per-item delete, empty state, and new-chat. Keep current messages during another detail request and replace only after success.

```javascript
export function startNewConversationState(state) {
  return { ...state, currentConversationId: null, messages: [] };
}
```

- [ ] **Step 4: Verify and commit**

Check new-chat reset, saved conversation load, selected/unselected delete, and failure recovery.

```bash
npm test
git diff --check
git add .
git commit -m "M1-2: 대화 기록 불러오기 화면 연동"
```

---

### Task 13: Chat Interface and Automatic Conversation Refresh

**Files:**
- Create: `M1-2/frontend/src/js/chat.js`
- Modify: `M1-2/frontend/src/index.html`
- Modify: `M1-2/frontend/src/css/styles.css`
- Modify: `M1-2/frontend/src/js/app.js`
- Modify: `M1-2/frontend/src/js/state.js`
- Test: `M1-2/frontend/tests/state.test.js`

**Interfaces:**
- Consumes: `sendChat({message, conversation_id})`
- Produces: `initChatPanel`, `renderMessages`, `sendCurrentMessage`
- Updates: current conversation, messages, chat loading, and conversation list

- [ ] **Step 1: Write failing chat-state tests**

```javascript
assert.equal(buildChatPayload("질문", null).conversation_id, null);
assert.equal(buildChatPayload("다음 질문", "conv-1").conversation_id, "conv-1");
assert.throws(() => buildChatPayload("   ", null), /질문/);
```

Cover one active request, optimistic user bubble, success, failure, and continuation.

- [ ] **Step 2: Confirm tests fail**

Run: `npm test`

- [ ] **Step 3: Implement safe message rendering and input**

Use separate bubbles, `textContent`, Enter to send, Shift+Enter for newline, auto-scroll, `aria-busy`, and disabled controls during requests.

- [ ] **Step 4: Implement API flow and cold-start notice**

Show a loading bubble immediately. At eight seconds, change its label to a Render cold-start notice without a second request. On success append the answer, save returned ID, and refresh history. On failure remove loading and retain the question for retry.

- [ ] **Step 5: Verify Function Calling scenarios through the UI**

```text
전체 체중 추세가 어때?
2025-03-10의 체중은?
2025-03-01부터 2025-05-31까지 평균 체중은?
기록이 없는 날짜의 체중은?
```

Match responses against stored data and confirm no value is estimated.

- [ ] **Step 6: Verify and commit**

```bash
npm test
API_BASE_URL=http://localhost:8000 npm run build
git diff --check
git add .
git commit -m "M1-2: AI 채팅 화면과 자동 저장 연동"
```

---

### Task 14: Responsive UI, Accessibility, and Frontend Quality Gate

**Files:**
- Modify: `M1-2/frontend/src/index.html`
- Modify: `M1-2/frontend/src/css/styles.css`
- Modify: `M1-2/frontend/src/js/app.js`
- Modify: `M1-2/frontend/tests/{api,state,utils}.test.js`

**Interfaces:**
- Gates: deployment and final documentation

- [ ] **Step 1: Complete responsive layout**

Implement three-column desktop, two-stage tablet, and one-column mobile layouts. Keep chat widest, make side panels independently scrollable, and render data rows as cards on small screens.

```css
.dashboard { display: grid; grid-template-columns: 16rem minmax(0, 1fr) 22rem; }
@media (max-width: 1100px) { .dashboard { grid-template-columns: 16rem minmax(0, 1fr); } }
@media (max-width: 760px) { .dashboard { grid-template-columns: 1fr; } }
```

- [ ] **Step 2: Complete accessibility behavior**

Verify visible labels, keyboard navigation, focus indicators, `aria-live`, `aria-current`, `aria-busy`, touch spacing, and focus restoration after canceled deletion.

- [ ] **Step 3: Run the frontend automated gate**

```bash
npm test
API_BASE_URL=http://localhost:8000 npm run build
test -f dist/index.html
test -f dist/config.js
git diff --check
```

- [ ] **Step 4: Run the integrated browser checklist**

Check desktop and mobile initial load, CRUD/summary refresh, chat loading/success/failure, date/range questions, history load/delete/new, keyboard-only use, and HTML-like text rendered safely.

- [ ] **Step 5: Repeat the frontend review until clear**

Review API consistency, stale-request races, unsafe DOM insertion, loading deadlocks, mobile overflow, keyboard behavior, and missing empty/error states. For every finding, add or strengthen a test where possible, fix it, rerun the focused check, and rerun Step 3. Continue until no finding remains.

- [ ] **Step 6: Commit the passing frontend**

```bash
git add .
git commit -m "M1-2: 프론트엔드 품질 게이트 통과"
```

---

### Task 15: Deployment, README, Evidence, and Final Review Loop

**Files:**
- Create: `M1-2/frontend/README.md`
- Create: `M1-2/frontend/vercel.json`
- Create: `M1-2/README.md`
- Create: `M1-2/screenshots/chat-summary.png`
- Create: `M1-2/screenshots/data-crud.png`
- Create: `M1-2/screenshots/conversation-load.png`
- Modify: `M1-2/backend/README.md`

**Interfaces:**
- Produces: Render backend and Swagger URLs
- Produces: Vercel frontend URL
- Produces: assignment-complete documentation and screenshots

- [ ] **Step 1: Deploy and verify backend**

Create the Render service from `M1-2/backend`, configure backend environment variables, deploy, and run:

```bash
curl -fsS "$RENDER_URL/health"
curl -fsS "$RENDER_URL/openapi.json"
```

Import `weights.csv` once and verify `/api/data/summary` reports at least 100 records.

- [ ] **Step 2: Deploy and verify frontend**

Set Vercel Root Directory to `M1-2/frontend`, Build Command to `npm run build`, Output Directory to `dist`, and `API_BASE_URL` to the Render URL. Add the Vercel origin to backend `ALLOWED_ORIGINS`, redeploy backend, then deploy frontend.

- [ ] **Step 3: Write the complete root README**

Include service purpose, stack, actual frontend/backend/Swagger URLs, local commands, environment variable names, CSV generation/import, Function Calling tools/flow, cold-start notice, and three screenshots. Finished documentation must contain no example deployment URL.

- [ ] **Step 4: Capture exact evidence**

```text
chat-summary.png: summary panel plus a question and tool-backed answer
data-crud.png: form/list showing a completed create, update, or delete
conversation-load.png: selected saved conversation with restored messages
```

No screenshot may expose a secret.

- [ ] **Step 5: Run final automated verification**

```bash
cd M1-2/backend
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app scripts
.venv/bin/python scripts/import_csv.py data/weights.csv --dry-run
cd ../frontend
npm test
API_BASE_URL="$RENDER_URL" npm run build
cd ../..
git diff --check -- M1-2
```

- [ ] **Step 6: Run the final requirements review**

Check every line of `M1-2/subject.md` against implementation evidence. Pass only when all backend/frontend tests and builds pass, dry-run validates 120 records, required Swagger routes exist, deployed CRUD/summary/chat/history work, date/range answers match Firestore, README has actual URLs, screenshots exist, diff check is clean, and no review finding remains.

- [ ] **Step 7: Repeat until passing**

For any failure, reproduce it, add or strengthen the closest automated test, implement the smallest fix, rerun the focused test, rerun Step 5, and repeat Step 6. Do not declare completion while any check or finding remains unresolved.

- [ ] **Step 8: Commit the verified deliverable**

```bash
git add M1-2
git commit -m "M1-2: 체중 분석 AI MVP 완성"
```

Record final test counts, deployment URLs, review result, and commit ID in the completion handoff.
