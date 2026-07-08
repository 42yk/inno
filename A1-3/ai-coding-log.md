# AI 코딩 도구 사용 로그

작성일: 2026-07-08

## 개요

`오늘 뭐 먹지?` 웹 서비스를 구현하기 위해 사용자와 Codex가 나눈 대화와 작업 흐름을 요약한 로그입니다. 이 문서는 제출 증빙용으로, 요구사항 원문이나 API 키 같은 민감 정보는 포함하지 않습니다.

## 대화 및 작업 흐름

### 1. 기준 문서와 서비스 기획 확인

- 사용자는 비공개 기준 문서를 Source of Truth로 지정하고, 이후 모든 개발 과정에서 해당 요구사항을 계속 점검해야 한다고 요청했습니다.
- 사용자는 `오늘 뭐 먹지?` 서비스 기획을 제시했습니다.
- 주요 서비스 방향은 식사 시간, 예산, 인원, 음식 종류, 맵기를 입력하면 AI가 메뉴를 추천하고, 추천 횟수를 Redis 랭킹으로 집계하는 웹 서비스로 정리되었습니다.

### 2. 페이지 구조 결정

- 사용자는 여러 페이지 대신 단일 페이지를 섹션으로 나누는 방향을 요청했습니다.
- 최종 화면 구조는 `Home`, `AI 메뉴 추천`, `랭킹` 세 섹션으로 정했습니다.
- 메인 화면에는 서비스 소개와 `메뉴 추천받기`, `랭킹 보기` 이동 버튼을 배치하기로 했습니다.

### 3. 프론트엔드와 백엔드 분리 결정

- 사용자는 기준 문서에서 금지하지 않는다면 프론트엔드와 백엔드를 구분하고 싶다고 요청했습니다.
- Codex는 `frontend/`와 `api/`를 분리하는 구조를 제안했습니다.
- 사용자는 앞으로 UI 등 제안 사항은 Codex 추천안을 따르겠다고 했습니다.
- 설계 문서는 별도 커밋하지 않고 바로 구현계획으로 넘어가기로 했습니다.

### 4. 환경 프로필과 Redis 구성 결정

- 사용자는 Upstash Redis 기준 환경변수만으로 구분하면 복잡하므로 별도 프로필을 두자고 요청했습니다.
- `APP_PROFILE=dev|prod` 기준으로 환경을 나누기로 했습니다.
- `dev`는 로컬 개발 환경이며 Docker Redis를 사용합니다.
- `prod`는 Vercel 배포 환경이며 Upstash Redis REST API를 사용합니다.
- Redis 장애 또는 미설정 상황에 대비해 랭킹 조회 fallback을 두기로 했습니다.

### 5. AI 제공자 변경 및 fallback 결정

- 처음 기획은 OpenAI API 기준이었지만, 사용자가 AI 추천을 Gemini로 변경해 달라고 요청했습니다.
- 모델은 `gemini-3.1-flash-lite`로 정했습니다.
- `dev` 환경에서 Gemini API 키가 없으면 mock 추천을 반환하도록 했습니다.
- `prod` 환경에서는 Gemini API 키가 필수이며, 실패 시 사용자에게 API 오류 메시지를 반환하도록 했습니다.

### 6. 구현계획 작성과 구현

- Codex는 구현계획을 작성한 뒤 작업과 리뷰를 반복하는 방식으로 진행했습니다.
- 사용자는 테스트 코드는 작성하지 않아도 된다고 명시했습니다.
- 구현된 주요 파일은 다음과 같습니다.
  - `frontend/index.html`: 단일 페이지 섹션 구조
  - `frontend/css/style.css`: 반응형 UI 스타일
  - `frontend/js/app.js`: 입력 검증, API 요청, 결과 렌더링
  - `api/recommend.py`: AI 메뉴 추천 API
  - `api/ranking.py`: 랭킹 조회 API
  - `api/lib/config.py`: `dev`, `prod` 환경 설정
  - `api/lib/ai_client.py`: Gemini 호출 및 mock fallback
  - `api/lib/ranking_store.py`: Redis, Upstash Redis, 샘플 fallback
  - `api/lib/validation.py`: 입력값 검증
  - `local_server.py`: 로컬 개발 서버
  - `docker-compose.yml`: 로컬 Redis 실행
  - `vercel.json`: Vercel 라우팅 설정
  - `README.md`: 서비스 소개, 실행 및 배포 안내
  - `service-plan.md`: 서비스 기획 문서

### 7. 첫 번째 코드 리뷰와 수정

- 사용자는 구현 결과에 대한 리뷰를 요청했습니다.
- Codex는 다음 이슈를 발견했습니다.
  - Gemini 실서비스 호출 형식이 최신 API 문서와 맞지 않을 가능성
  - 백엔드 숫자 검증이 소수점을 정수로 잘라 통과시키는 문제
  - 기준 문서 파일이 git ignore 대상이라는 점
- 사용자는 기준 문서 파일은 GitHub에 올라가면 안 되므로 ignore가 맞다고 설명했고, 나머지 두 이슈만 처리해 달라고 요청했습니다.
- Codex는 Gemini 호출을 Interactions API 형식으로 변경했습니다.
- Codex는 백엔드 숫자 검증을 수정해 정수 타입 또는 숫자 문자열만 허용하도록 했습니다.

### 8. 수정 후 재리뷰

- 사용자는 다시 리뷰를 요청했습니다.
- Codex는 수정된 범위를 재검토했습니다.
- 로컬 검증에서 다음 항목을 확인했습니다.
  - Python 컴파일
  - JavaScript 문법 검사
  - 입력 검증 직접 확인
  - Gemini 요청 payload와 fake 응답 파싱 확인
  - `git diff --check`
- 실제 Gemini 및 Upstash 라이브 호출은 API 키가 없어서 수행하지 못했고, 해당 사항을 남은 리스크로 기록했습니다.

### 9. README 제출 항목 점검

- 사용자는 README에 기준 문서의 제출물 요구가 잘 반영되어 있는지 확인해 달라고 요청했습니다.
- Codex는 README를 검토하고 다음을 지적했습니다.
  - 배포 URL은 공란으로 남겨야 함
  - 기준 문서 파일명과 내용은 README에 존재하면 안 됨
  - 단순 제출 체크리스트가 아니라 README 본문에 필수 항목이 있어야 함
- 사용자는 링크는 공란으로 남기고, 기준 문서의 내용이 README에 없어야 하며, 제출 체크리스트가 아닌 README 자체 항목을 검증 또는 수정해야 한다고 정정했습니다.

### 10. README 수정

- Codex는 README를 수정했습니다.
- 배포 URL 섹션은 값 없이 공란으로 유지했습니다.
- 기준 문서 파일명과 제출 체크리스트 섹션을 제거했습니다.
- README 본문에 다음 항목을 섹션으로 정리했습니다.
  - 서비스 소개
  - 주요 기능
  - 서비스 기획
  - 목적
  - 타겟 사용자
  - 화면 구성
  - AI 기능
  - 기술 스택
  - 프로젝트 구조
  - 환경 변수
  - 로컬 실행
  - 배포 방법
  - API

### 11. 프로젝트 구조 설명 방식 변경

- 사용자는 README의 프로젝트 구조에 파일이 무엇인지 설명이 부족하다고 지적했습니다.
- Codex는 처음에는 별도 표로 파일 설명을 추가했습니다.
- 사용자는 별도 테이블이 아니라 프로젝트 구조 코드블록 옆에 `#` 주석으로 작성해 달라고 요청했습니다.
- Codex는 프로젝트 구조 코드블록 내부에 각 파일과 폴더 설명을 `#` 주석으로 붙였습니다.
- 이후 다음을 검증했습니다.
  - 기준 문서 파일명 없음
  - 제출 체크리스트 없음
  - placeholder URL 문구 없음
  - 프로젝트 구조에 `#` 설명 존재
  - `git diff --check` 통과

## 주요 결정 사항

- 화면은 단일 페이지 3섹션 구조로 구현합니다.
- 프론트엔드는 `frontend/`, 백엔드는 `api/`로 분리합니다.
- 백엔드는 Vercel Python Serverless Functions 기준으로 작성합니다.
- AI는 Gemini Interactions API를 사용합니다.
- 모델 기본값은 `gemini-3.1-flash-lite`입니다.
- 로컬 개발은 `APP_PROFILE=dev`, 배포 환경은 `APP_PROFILE=prod`로 구분합니다.
- 로컬 Redis는 Docker Redis를 사용합니다.
- 배포 환경 랭킹 저장소는 Upstash Redis REST API를 사용합니다.
- dev 환경에서는 Gemini 키가 없을 경우 mock 추천을 사용합니다.
- README에는 비공개 기준 문서 파일명이나 원문 내용이 들어가지 않도록 유지합니다.
- 배포 URL은 실제 배포 전까지 공란으로 유지합니다.

## 검증 기록

- Python 컴파일 확인: `python3 -m compileall A1-3/api A1-3/local_server.py`
- JavaScript 문법 확인: `node --check A1-3/frontend/js/app.js`
- Markdown 및 공백 오류 확인: `git diff --check`
- 백엔드 입력 검증 직접 확인
- Gemini Interactions API 요청 payload 및 fake 응답 파싱 확인
- README 필수 항목 및 금지 문자열 확인

## 남은 작업

- 실제 Vercel 배포 후 배포 URL을 README의 `배포 URL` 섹션에 입력합니다.
- 실제 Gemini API 키와 Upstash Redis 환경변수로 배포 환경 동작을 확인합니다.
- 데스크톱, 모바일, AI 기능 동작 화면의 스크린샷을 준비합니다.
