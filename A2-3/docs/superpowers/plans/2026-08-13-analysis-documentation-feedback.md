# 분석 문서 피드백 반영 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 모듈 의존성, 감정 임계치와 개선 우선순위, 시각화 근거, 정확도 검증, 급증 원인 분석 절차를 현재 구현과 구분되는 독립 기준 문서로 제공한다.

**Architecture:** 기존 모듈 구조 문서는 실제 `AppDependencies` 조립 관계까지 보강한다. 운영 의사결정, 분석 방법론, 모델 품질 검증은 책임이 다르므로 각각 독립 문서로 만들고 `docs/README.md`와 프로젝트 `README.md`에서 연결한다.

**Tech Stack:** Markdown, Mermaid, Python 소스 계약

## Global Constraints

- 서브에이전트를 사용하지 않고 현재 세션에서 직접 수행한다.
- 현재 코드에 없는 자동 알림·자동 우선순위 기능을 구현된 기능처럼 표현하지 않는다.
- 정확도 수치나 프롬프트 개선 효과를 실험 전 사실처럼 기재하지 않는다.
- 현재 데이터 모델에 없는 리뷰 소스는 추가 수집이 필요한 지표로 구분한다.
- 사용자가 요청하지 않았으므로 커밋, 푸시, PR을 수행하지 않는다.

---

### Task 1: 모듈 책임과 의존성 보강

**Files:**
- Modify: `docs/architecture/modules.md`

**Interfaces:**
- Consumes: `review_analytics/composition.py`의 `AppDependencies`, `build_default_dependencies`, `create_live_client`
- Produces: 패키지별 책임표와 런타임 의존성 Mermaid 다이어그램

- [x] **Step 1:** 패키지별 책임, 입력·출력, 허용 의존성을 표로 명시한다.
- [x] **Step 2:** `AppDependencies`가 Config, Repository, 지연 Client factory를 Service에 제공하는 흐름을 다이어그램과 수명주기로 설명한다.
- [x] **Step 3:** 문서 설명이 실제 import 경계와 일치하는지 `tests/unit/test_import_boundaries.py` 기준으로 대조한다.

### Task 2: 운영 의사결정 정책 추가

**Files:**
- Create: `docs/analysis/decision-policy.md`

**Interfaces:**
- Consumes: 감정 분포, 부정 키워드 근거 ID, 추천 목록, `DashboardData.rows`
- Produces: 임계치, 알림→조치 흐름, 키워드 영향도·우선순위 산식, 급증 조사 지표와 가설 템플릿

- [x] **Step 1:** 최소 표본 조건과 관심·경고·심각 단계의 절대 부정률 및 기준선 대비 증가폭을 정의한다.
- [x] **Step 2:** 탐지→데이터 품질 확인→세분화→근거 검수→담당 배정→사후 확인 흐름과 사례를 작성한다.
- [x] **Step 3:** 부정 키워드 우선순위 점수의 빈도·심각도·증가도·신뢰도 기준, 키워드 정규화·과거 스냅샷 조건, 추천 연결 규칙을 정의한다.
- [x] **Step 4:** 상품, 리뷰 소스, 별점, 본문 길이 등 추가 지표 목록과 검증 가능한 가설 템플릿을 작성한다.

### Task 3: 시각화와 집계 방법론 추가

**Files:**
- Create: `docs/analysis/visualization-methodology.md`

**Interfaces:**
- Consumes: `review_analytics/output/charts.py::_rating_sentiment_matrix`, `rules/metrics.py::calculate_quality_metrics`
- Produces: 누적 막대 선택 이유, 통계적 해석 범위, 장단점과 대안 비교

- [x] **Step 1:** 현재 차트가 별점×감정 교차표의 건수를 표현한다는 사실과 누적 막대 선택 이유를 기록한다.
- [x] **Step 2:** 표본 크기 영향, 인과·상관 추론 불가 등 한계를 명시한다.
- [x] **Step 3:** 100% 누적 막대, 히트맵, 평균 감정 점수, 순서형 회귀의 용도와 트레이드오프를 비교한다.

### Task 4: 감정 분석 검증 계획 추가

**Files:**
- Create: `docs/quality/sentiment-validation-plan.md`

**Interfaces:**
- Consumes: `positive|negative|neutral`, confidence `0.0..1.0`, `prompt_version`
- Produces: 층화 샘플링, 이중 검수, 정량 메트릭, 프롬프트 A/B 비교와 기록 양식

- [x] **Step 1:** 상품·별점·예측 감정별 상호 배타 층, 설계 가중치, 탐색·운영 전환 표본 크기 규칙을 정의한다.
- [x] **Step 2:** 두 명의 검수자, 불일치 조정, 정답셋 동결 절차를 정의한다.
- [x] **Step 3:** 정확도, macro F1, 클래스별 precision/recall, Cohen's kappa와 확률로 해석하지 않는 confidence 구간별 경험 정확도를 정의한다.
- [x] **Step 4:** 동일 정답셋에서 프롬프트 버전을 비교하는 층화 bootstrap·McNemar 승인 기준과 실험 기록 표를 작성한다.

### Task 5: 문서 진입점과 링크 검증

**Files:**
- Modify: `docs/README.md`
- Modify: `README.md`
- Modify: `docs/architecture/README.md`

**Interfaces:**
- Consumes: Tasks 1~4의 독립 문서 경로
- Produces: 문서 지도와 사용자용 안내 링크

- [x] **Step 1:** 문서 지도에 분석·의사결정 문서와 품질 문서를 등록한다.
- [x] **Step 2:** 프로젝트 README에 분석 기준과 운영 활용 문서 링크를 추가한다.
- [x] **Step 3:** Markdown 상대 링크, 미완료 표식, 공백 오류를 검사한다.
- [x] **Step 4:** 문서 변경임을 고려해 import-boundary 테스트와 전체 오프라인 테스트를 실행한다.
