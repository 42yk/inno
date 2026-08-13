# Raw/Clean 및 AI 프롬프트 문서화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** raw/clean 데이터의 보존·정제 계약과 AI 프롬프트의 라벨·출력·점수 규약을 구현과 일치하는 독립 기준 문서로 제공한다.

**Architecture:** raw/clean 계약은 데이터 정책 문서로 분리하고 기존 스키마·흐름 문서에서 연결한다. AI 계약은 분석 문서로 분리하며 감정 프롬프트가 같은 라벨·confidence 규약을 실제로 지시하도록 테스트 우선으로 보강한다.

**Tech Stack:** Markdown, Mermaid, Python, Google GenAI JSON Schema, pytest

## Global Constraints

- 서브에이전트를 사용하지 않고 현재 세션에서 직접 수행한다.
- raw 원본 필드와 clean 파생 필드를 혼동하지 않는다.
- confidence는 정답 확률이나 통계적으로 보정된 확률로 표현하지 않는다.
- 문서 예시는 실제 JSON Schema와 로컬 검증 규칙을 통과하는 형태로 작성한다.
- 사용자가 요청하지 않았으므로 커밋, 푸시, PR을 수행하지 않는다.

---

### Task 1: 감정 프롬프트 계약을 테스트 우선으로 보강

**Files:**
- Modify: `tests/unit/test_gemini_client.py`
- Modify: `review_analytics/clients/gemini.py`

**Interfaces:**
- Consumes: `_SENTIMENT_SYSTEM_INSTRUCTION`, `_SENTIMENT_SCHEMA`
- Produces: positive·negative·neutral 판정 기준과 비확률 confidence 의미를 포함한 시스템 지시

- [x] **Step 1:** 기존 Gemini Client 테스트에 세 라벨의 판정 기준, 복합 감정 처리, confidence 비확률 의미를 요구하는 assertion을 추가한다.
- [x] **Step 2:** `python3 -m pytest tests/unit/test_gemini_client.py::test_analyze_uses_structured_json_and_returns_validated_internal_results -q`를 실행해 새 assertion이 실패하는지 확인한다.
- [x] **Step 3:** 시스템 지시에 라벨 기준, 우세 감정 선택, confidence 자기평가 규약을 최소 문구로 추가한다.
- [x] **Step 4:** 같은 테스트를 다시 실행해 통과를 확인한다.

### Task 2: raw/clean 데이터 정책 문서 추가

**Files:**
- Create: `docs/policies/raw-clean-data.md`
- Modify: `docs/glossary/data-stages.md`
- Modify: `docs/data-flow.md`
- Modify: `docs/architecture/storage-schema.md`

**Interfaces:**
- Consumes: `RawReviewInput`, `RawReview`, `CleanReview`, `clean_review`, SQLite raw·clean 스키마
- Produces: 분리 목적, 필드별 보존·정제·거절 기준, 생명주기와 재처리 계약

- [x] **Step 1:** raw/clean 분리 이유와 경계 원칙을 정의한다.
- [x] **Step 2:** 본문·별점·날짜·제품명·출처·상태 필드별 raw 보존값과 clean 변환값을 표로 작성한다.
- [x] **Step 3:** 성공·거절·upsert·재정제 시 보존 및 파생 데이터 무효화 흐름을 작성한다.
- [x] **Step 4:** 기존 용어집·데이터 흐름·스키마 문서에서 정책 원본으로 연결한다.

### Task 3: AI 프롬프트 설계 문서 추가

**Files:**
- Create: `docs/analysis/prompt-design.md`

**Interfaces:**
- Consumes: 감정·인사이트·병합 시스템 지시, JSON Schema, 로컬 응답 검증, prompt version
- Produces: 입력·출력 예시, 라벨 기준, confidence 해석, 인사이트 근거 규약, 오류 처리 설명

- [x] **Step 1:** 공통 신뢰 경계와 감정 프롬프트의 입력·출력·라벨·점수 계약을 예시로 작성한다.
- [x] **Step 2:** 인사이트 추출·병합 프롬프트의 키워드 근거, 요약, 권고 출력 형식과 예시를 작성한다.
- [x] **Step 3:** JSON Schema와 로컬 검증이 거부하는 응답 사례, prompt version 관리 규칙을 작성한다.

### Task 4: 문서 진입점과 전체 검증

**Files:**
- Modify: `docs/README.md`
- Modify: `README.md`
- Modify: `docs/analysis/decision-policy.md`
- Modify: `docs/quality/sentiment-validation-plan.md`

**Interfaces:**
- Consumes: Tasks 1~3의 최종 문서 경로와 confidence 계약
- Produces: 사용자·개발자용 탐색 링크와 일관된 점수 해석

- [x] **Step 1:** 문서 지도와 프로젝트 README에 두 기준 문서를 등록한다.
- [x] **Step 2:** 운영·검증 문서의 confidence 설명에서 프롬프트 설계 문서를 연결한다.
- [x] **Step 3:** 상대 링크, 구현 근거, 미완료 표식, 공백 오류를 검사한다.
- [x] **Step 4:** Gemini 단위 테스트와 전체 오프라인 테스트를 실행한다.
