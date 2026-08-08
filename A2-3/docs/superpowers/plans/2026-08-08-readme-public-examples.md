# README Public Examples Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** README의 설치 절차를 승인된 pip 명령으로 갱신하고 실제 결과 파일을 공개 예시로 제공한다.

**Architecture:** 실행 중 생성되는 `output/`은 기존처럼 무시하고, 문서에서 참조할 고정 스냅샷만 `public/examples/`에 둔다. README는 이 공개 파일을 상대 링크로 표시하며 애플리케이션 동작은 변경하지 않는다.

**Tech Stack:** Markdown, Bash, PNG, CSV, XLSX

## Global Constraints

- 지원 Python 버전은 `3.10 이상`이다.
- 설치 명령은 `python3 -m pip install --user --break-system-packages -r requirements.txt`이다.
- 현재 셸에 `python` 명령이 없으므로 CLI 실행과 테스트 예시도 `python3`로 통일한다.
- 원본 `output/` 파일을 수정하거나 다시 생성하지 않는다.
- Git 커밋, 푸시, PR은 수행하지 않는다.

---

### Task 1: 공개 결과 예시 복사

**Files:**
- Create: `public/examples/sentiment_distribution.png`
- Create: `public/examples/sentiment_trend.png`
- Create: `public/examples/rating_sentiment_matrix.png`
- Create: `public/examples/reviews.csv`
- Create: `public/examples/reviews.xlsx`

**Interfaces:**
- Consumes: `output/sentiment_distribution.png`, `output/sentiment_trend.png`, `output/rating_sentiment_matrix.png`, `output/test.csv`, `output/test.xlsx`
- Produces: README에서 참조할 고정 상대 경로 `public/examples/*`

- [x] **Step 1: 공개 예시 디렉터리를 만든다**

  Run: `mkdir -p public/examples`

- [x] **Step 2: 이미지 파일을 원래 이름으로 복사한다**

  Run: `cp output/sentiment_distribution.png output/sentiment_trend.png output/rating_sentiment_matrix.png public/examples/`

- [x] **Step 3: 내보내기 파일을 설명적인 이름으로 복사한다**

  Run: `cp output/test.csv public/examples/reviews.csv`

  Run: `cp output/test.xlsx public/examples/reviews.xlsx`

- [x] **Step 4: 원본과 복사본의 SHA-256을 비교한다**

  Run: `shasum -a 256 output/sentiment_distribution.png public/examples/sentiment_distribution.png output/sentiment_trend.png public/examples/sentiment_trend.png output/rating_sentiment_matrix.png public/examples/rating_sentiment_matrix.png output/test.csv public/examples/reviews.csv output/test.xlsx public/examples/reviews.xlsx`

  Expected: 각 원본과 대응 복사본의 해시가 일치한다.

### Task 2: README 설치 및 결과 예시 갱신

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 1의 `public/examples/*` 상대 경로
- Produces: Python 버전 확인·설치 안내와 렌더링 가능한 결과 예시 문서

- [x] **Step 1: 가상환경 설치 안내를 승인된 전역 사용자 설치 안내로 교체한다**

  설치 절에는 `python3 --version`과 `python3 -m pip install --user --break-system-packages -r requirements.txt`를 넣고 `.venv` 및 Windows 활성화 안내를 제거한다.

- [x] **Step 2: 빠른 시작 다음에 완성 결과 예시를 추가한다**

  PNG 세 개는 Markdown 이미지 문법으로 표시하고 `reviews.csv`, `reviews.xlsx`는 다운로드 링크로 제공한다. `output/`과 `public/examples/`의 역할 차이를 설명한다.

- [x] **Step 3: 실행 및 테스트 명령을 `python3`로 통일했는지 확인한다**

  Run: `rg -n 'python3 main.py|python3 -m pytest' README.md`

  Expected: CLI 및 테스트 예시가 모두 검색되고, 실행할 수 없는 `python main.py`와 `python -m pytest` 표기는 없다.

### Task 3: 문서와 예시 자산 검증

**Files:**
- Verify: `README.md`
- Verify: `public/examples/*`

**Interfaces:**
- Consumes: Task 1과 Task 2 결과
- Produces: 링크·파일 형식·Git 제외 정책 검증 결과

- [x] **Step 1: README의 로컬 상대 링크가 모두 존재하는지 검사한다**

  Markdown 링크와 이미지 경로 중 로컬 경로를 추출해 프로젝트 루트에서 존재 여부를 확인한다.

- [x] **Step 2: 공개 예시 형식을 검사한다**

  Run: `file public/examples/sentiment_distribution.png public/examples/sentiment_trend.png public/examples/rating_sentiment_matrix.png public/examples/reviews.csv public/examples/reviews.xlsx`

  Expected: PNG 3개, CSV 텍스트 1개, Microsoft Excel 2007+ 파일 1개로 인식된다.

- [x] **Step 3: Git 제외 정책을 검사한다**

  Run: `git check-ignore -v output/test.csv`

  Expected: `.gitignore`의 `/output/` 규칙이 출력된다.

  Run: `git check-ignore -q public/examples/reviews.csv; test $? -eq 1`

  Expected: 공개 예시는 Git에서 제외되지 않는다.

- [x] **Step 4: diff와 공백 오류를 확인한다**

  Run: `git diff -- README.md docs/superpowers/specs/2026-08-08-readme-public-examples-design.md docs/superpowers/plans/2026-08-08-readme-public-examples.md`

  Run: `git diff --check`

  Expected: 요청 범위의 변경만 보이며 공백 오류가 없다.
