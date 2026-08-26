# Weight AI 에이전트 지침

이 파일은 `M1-2/` 전체에 적용한다. 백엔드와 프론트엔드 작업은 이 지침을 우선해서 수행한다.

## 1. 비밀 파일 접근 금지

- `backend/.env`를 읽거나 열거나 출력하거나 검색하지 않는다.
- `**/*firebase-adminsdk*.json`, `**/firebase-service-account.json` 및 `FIREBASE_SERVICE_ACCOUNT_FILE`이 가리키는 실제 Firebase 서비스 계정 파일을 읽지 않는다.
- 비밀 파일의 내용을 직접 읽는 명령뿐 아니라 `cat`, `sed`, `awk`, `grep`, `rg`, `head`, `tail`, `jq`, Python 스크립트, 셸 확장 등을 통해 간접 출력하는 작업도 금지한다.
- `env`, `printenv`, 디버그 로그, 오류 메시지, 테스트 결과로 API 키나 서비스 계정 값을 노출하지 않는다.
- 비밀 값을 문서, 소스 코드, 테스트 fixture, 스냅샷 또는 Git 커밋에 복사하지 않는다.
- 설정 확인이 필요하면 변수 이름과 파일 존재 여부만 확인하고 값은 확인하지 않는다.
- 실제 비밀 값이 필요한 작업은 중단하고 사용자가 직접 설정하도록 안내한다.

다음 두 파일은 비밀 값이 없는 예제이므로 읽고 수정할 수 있다.

- `backend/.env.sample`
- `backend/firebase-service-account.example.json`

테스트 중 `.env`가 간접 로드되지 않도록 백엔드 테스트는 다음처럼 실행한다.

```bash
PYTHON_DOTENV_DISABLED=1 .venv/bin/python -m pytest -q
```

실제 Firebase 및 AI 서비스에 연결하는 통합 실행은 사용자가 명시적으로 요청하고 안전한 자격 증명 주입 방법을 제공한 경우에만 수행한다. 기본 검증에서는 인메모리 저장소와 가짜 AI 클라이언트를 사용한다.

## 2. 프로젝트 범위

- 서비스 주제는 날짜별 개인 체중 데이터를 관리하고 분석하는 AI 비서다.
- 유효한 `date`, `value`, 선택적 `memo`가 있는 레코드만 사용한다.
- 측정하지 않은 날짜는 제외하며 결측값을 생성, 보간 또는 추정하지 않는다.
- 최소 100건 이상의 유효 레코드를 유지한다. 기본 샘플 `backend/data/weights.csv`는 120건이다.
- 보너스 기능인 그래프, 데이터 내보내기, 다크 모드, MCP/GPT Actions 연동은 구현 범위에 포함하지 않는다.
- 과제 원문인 `subject.md`는 문구를 변경하지 않는다.

## 3. 작업 방식

- 별도 에이전트나 서브에이전트를 만들지 않고 하나의 작업 흐름에서 통합 개발한다.
- 워크트리나 새 브랜치를 만들지 않는다.
- 백엔드 기능을 먼저 구현하고 검증한 뒤 프론트엔드 연동을 수정한다.
- 사용자의 기존 변경을 보존하고 관련 없는 파일을 수정하지 않는다.
- 변경 후 테스트와 코드 리뷰를 반복하며 오류와 요구사항 누락이 없을 때까지 수정한다.
- 사용자가 요청하지 않은 배포, 외부 데이터 변경, Git 커밋 또는 원격 푸시는 수행하지 않는다.

## 4. 백엔드 설계 기준

- 기준 문서는 `backend/docs/`에서 관리한다.
- FastAPI 계층은 `router → service → repository/client` 방향을 유지한다.
- 라우터는 HTTP 계약, Pydantic 스키마는 검증, 서비스는 업무 규칙, 저장소는 Firestore 접근을 담당한다.
- Firestore 컬렉션은 `data`와 `conversations`를 사용한다.
- Firebase Admin SDK는 `FIREBASE_SERVICE_ACCOUNT_FILE` 경로의 파일을 애플리케이션이 실행될 때 읽는다. 에이전트는 실제 파일 내용을 읽지 않는다.
- 입력 검증과 공개 오류 응답에서 내부 예외, 프롬프트 또는 비밀 값을 노출하지 않는다.

필수 API 계약을 유지한다.

- `POST /api/data`
- `GET /api/data`
- `PUT /api/data/{record_id}`
- `DELETE /api/data/{record_id}`
- `GET /api/data/summary`
- `POST /api/conversations`
- `GET /api/conversations`
- `GET /api/conversations/{conversation_id}`
- `DELETE /api/conversations/{conversation_id}`
- `POST /api/chat`

## 5. AI 호출 기준

- Codyssey의 OpenAI 호환 Chat Completions API를 사용한다.
- Base URL은 환경 변수 `OPENAI_BASE_URL`로 받고 기본 예시는 `https://copa.codyssey.kr/v1`이다.
- `OPENAI_API_KEY`에는 Codyssey API 콘솔의 가상 키를 사용한다.
- 기본 모델 예시는 `gpt-5-mini`다.
- 전체 데이터 요약을 매 채팅 요청의 시스템 메시지에 주입한다.
- Function Calling 도구는 `get_weight_summary`, `get_weight_by_date`, `get_weight_records`, `get_weight_statistics` 네 개의 읽기 전용 도구만 제공한다.
- AI 도구에 생성, 수정, 삭제 기능을 추가하지 않는다.
- 도구 이름은 허용 목록으로 확인하고 인자는 Pydantic으로 다시 검증한다.
- Chat Completions의 `assistant.tool_calls`와 동일한 `tool_call_id`를 가진 `role=tool` 메시지로 호출 결과를 연결한다.
- 기록에 없는 체중을 추정하거나 의료 진단 및 치료 지시를 생성하지 않도록 시스템 정책을 유지한다.
- 최종 사용자 질문과 AI 답변만 대화 기록에 저장하고 시스템 메시지와 도구 중간 결과는 저장하지 않는다.

## 6. 프론트엔드 설계 기준

- 기준 문서는 `frontend/docs/`에서 관리한다.
- HTML, CSS, JavaScript만 사용하고 프레임워크를 추가하지 않는다.
- 백엔드 주소는 빌드 환경 변수 `API_BASE_URL`로 주입한다.
- 채팅 메시지, 로딩 상태, 데이터 CRUD, 데이터 요약, 대화 목록과 대화 불러오기 기능을 유지한다.
- 사용자가 데이터를 변경한 뒤 목록과 요약을 다시 불러온다.
- API 오류는 안전한 사용자 메시지로 표시하고 내부 응답이나 비밀 값을 화면에 출력하지 않는다.

## 7. 환경 변수와 배포

환경 변수의 이름만 코드와 문서에서 다룬다.

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`
- `OPENAI_MAX_OUTPUT_TOKENS`
- `FIREBASE_SERVICE_ACCOUNT_FILE`
- `ALLOWED_ORIGINS`
- `API_BASE_URL`

- 백엔드는 Render, 프론트엔드는 Vercel 배포 설정을 유지한다.
- Render에서는 실제 Firebase JSON을 Secret File로 등록하고 파일 경로만 환경 변수에 설정한다.
- 키 파일을 저장소에 추가하거나 배포 설정 본문에 삽입하지 않는다.
- CORS에는 로컬 프론트 Origin과 실제 Vercel Origin만 허용한다.

## 8. 검증 명령

백엔드:

```bash
cd M1-2/backend
PYTHON_DOTENV_DISABLED=1 .venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app scripts
.venv/bin/python scripts/import_csv.py data/weights.csv --dry-run
```

`import_csv.py`는 기본적으로 `--dry-run`만 사용한다. 실제 Firestore 쓰기는 사용자가 명시적으로 요청한 경우에만 수행한다.

프론트엔드:

```bash
cd M1-2/frontend
npm test
API_BASE_URL=http://localhost:8000 npm run build
```

완료 전에 다음을 확인한다.

- 백엔드 및 프론트엔드 테스트 통과
- Python 컴파일과 프론트 빌드 통과
- CSV dry-run에서 유효 레코드 100건 이상
- `git diff --check` 통과
- 실제 `.env`와 Firebase 키 JSON이 Git 변경 목록에 포함되지 않음
- `subject.md`가 변경되지 않음
- 문서, 코드, 테스트 출력에 비밀 값이 없음
