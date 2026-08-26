# Weight AI — 내 체중 데이터를 아는 AI 비서

날짜별 체중 기록을 저장·분석하고, 현재 데이터 요약과 필요한 기간 조회 결과를 근거로 대화하는 웹 서비스다. 측정하지 않은 날짜는 결측값으로 채우거나 추정하지 않고 제외한다. 샘플 CSV에는 유효한 날짜·체중 120건이 들어 있다.

## 구현 범위

- 체중 데이터 등록·목록·수정·삭제와 전체 요약 API
- Firestore `data`, `conversations` 컬렉션 저장
- 대화 저장·목록·상세 불러오기·삭제
- 요약 컨텍스트 주입과 OpenAI 호환 Chat Completions Function Calling 채팅
- 바닐라 HTML/CSS/JavaScript 대시보드
- Render와 Vercel 배포 설정, Swagger UI

그래프, 내보내기, 다크 모드와 MCP 연동은 구현 범위에서 제외했다.

## 기술 스택

| 구분 | 기술 |
|---|---|
| 백엔드 | Python 3.12, FastAPI, Pydantic, Uvicorn |
| 데이터베이스 | Firebase Firestore |
| AI | Codyssey OpenAI 호환 Chat Completions API, Function Calling |
| 프론트엔드 | HTML, CSS, JavaScript ES Modules |
| 배포 | Render, Vercel |
| 테스트 | pytest, FastAPI TestClient, Node.js test runner, 브라우저 통합 QA |

## 배포 URL

프론트엔드는 Vercel에 배포하고 가비아 도메인을 연결했다. 백엔드는 Render에 배포하고 `api.harubang.store` 커스텀 도메인을 연결했다.

| 항목 | URL |
|---|---|
| 프론트엔드 | [https://www.harubang.store](https://www.harubang.store) |
| 백엔드 API | [https://api.harubang.store](https://api.harubang.store) |
| Swagger UI | [https://api.harubang.store/docs](https://api.harubang.store/docs) |

## 저장 데이터와 결측치

CSV 형식은 다음 하나로 고정한다.

```csv
date,value,memo
2025-01-01,78.0,
```

- `date`: 측정한 날짜, 중복·미래 날짜 금지
- `value`: 20.0kg 이상 300.0kg 이하, 소수점 첫째 자리까지
- `memo`: 선택 입력, 최대 200자
- 날짜나 체중이 빈 행: 가져오기에서 제외
- 형식이 잘못된 행: 오류로 보고하고 저장하지 않음
- 날짜가 없는 날: 레코드를 만들지 않으며 보간하지 않음

샘플 생성과 검증:

```bash
cd backend
.venv/bin/python scripts/generate_sample_csv.py
.venv/bin/python scripts/import_csv.py data/weights.csv --dry-run
```

dry-run 결과는 `valid: 120`, `created: 0`, `failed: 0`이어야 한다. 실제 Firestore 등록은 `--dry-run`을 제거한다.

## 로컬 실행

### 백엔드

```bash
cd M1-2/backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.sample .env
.venv/bin/uvicorn app.main:create_app --factory --reload
```

### 프론트엔드

```bash
cd M1-2/frontend
npm test
API_BASE_URL=http://localhost:8000 npm run build
python3 -m http.server 5173 -d dist
```

브라우저는 `http://localhost:5173`, Swagger UI는 `http://localhost:8000/docs`에서 확인한다.

## 환경 변수

| 이름 | 위치 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | 백엔드 | Codyssey API 콘솔에서 발급한 가상 키 |
| `OPENAI_BASE_URL` | 백엔드 | OpenAI 호환 API Base URL (`https://copa.codyssey.kr/v1`) |
| `OPENAI_MODEL` | 백엔드 | 사용할 모델 ID |
| `OPENAI_MAX_OUTPUT_TOKENS` | 백엔드 | 응답 최대 토큰 수 |
| `FIREBASE_SERVICE_ACCOUNT_FILE` | 백엔드 | Firebase 서비스 계정 JSON 파일 경로 |
| `ALLOWED_ORIGINS` | 백엔드 | 쉼표로 구분한 프론트 Origin |
| `API_BASE_URL` | 프론트 빌드 | 공개된 Render 백엔드 주소 |

비밀 값은 `.env`, Render 환경 변수에만 저장하고 Git, 프론트 코드, 로그와 오류 응답에 넣지 않는다.

운영 백엔드의 CORS 허용 Origin은 다음과 같이 설정한다.

```dotenv
ALLOWED_ORIGINS=https://www.harubang.store
```

## API와 Function Calling 흐름

필수 API:

- `POST/GET /api/data`
- `PUT/DELETE /api/data/{record_id}`
- `GET /api/data/summary`
- `POST/GET /api/conversations`
- `GET/DELETE /api/conversations/{conversation_id}`
- `POST /api/chat`

채팅 처리 순서:

1. 공통 `SummaryService`로 현재 전체 요약을 계산한다.
2. 같은 요약을 시스템 instructions에 주입한다.
3. 기존 대화와 새 질문, 읽기 전용 도구 정의를 OpenAI 호환 Chat Completions API에 전달한다.
4. 모델이 요청한 도구 이름과 JSON 인자를 허용 목록과 Pydantic으로 재검증한다.
5. `call_id`를 유지한 도구 결과를 모델에 돌려주고 최종 답변을 받는다.
6. 최종 사용자 질문과 AI 답변만 Firestore에 저장한다.

허용 도구는 `get_weight_summary`, `get_weight_by_date`, `get_weight_records`, `get_weight_statistics` 네 개다. 생성·수정·삭제 도구는 제공하지 않으며 호출은 요청당 최대 네 번으로 제한한다.

## 배포

- 백엔드: `backend/render.yaml`을 사용하고 `/health`, `/docs`를 확인한다.
- Render에는 서비스 계정 JSON을 Secret File `firebase-service-account.json`으로 등록한다.
- 프론트엔드: `frontend/vercel.json`을 사용하고 `API_BASE_URL`을 Render URL로 설정한다.
- 프론트엔드 Origin `https://www.harubang.store`를 `ALLOWED_ORIGINS`에 넣은 뒤 백엔드를 다시 배포한다.
- Render 무료 티어의 첫 연결은 지연될 수 있어 채팅이 8초 이상 걸리면 콜드스타트 안내를 표시한다.

## 제출 스크린샷

### 데이터 요약이 보이는 AI 채팅

저장된 체중 데이터 요약과 사용자의 질문, AI 답변이 함께 표시되는 화면이다.

![데이터 요약이 보이는 AI 채팅 화면](screenshots/chat-summary.png)

### 데이터 관리(CRUD)

새 체중 기록 입력 폼, 저장된 데이터 목록과 수정·삭제 기능이 표시되는 화면이다.

![체중 데이터 관리 화면](screenshots/data-crud.png)

### 대화 기록 불러오기

저장된 대화를 선택하고 해당 대화의 메시지를 다시 표시한 화면이다.

![저장된 대화 불러오기 화면](screenshots/conversation-load.png)

### Swagger UI

로컬 백엔드의 `http://localhost:8000/docs`에서 필수 API 엔드포인트를 확인한 화면이다.

![로컬 백엔드 Swagger UI 화면](screenshots/swagger-ui.png)

## 검증

```bash
cd M1-2/backend
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app scripts
.venv/bin/python scripts/import_csv.py data/weights.csv --dry-run

cd ../frontend
npm test
API_BASE_URL=http://localhost:8000 npm run build
```

브라우저 통합 QA에서는 120건 초기 표시, 신규 등록 후 121건 요약 갱신, 중복 날짜 오류, 채팅 자동 저장, 새 대화·불러오기와 390px 모바일 레이아웃을 확인했다.
