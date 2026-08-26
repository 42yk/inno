# Weight AI 백엔드

날짜별 체중을 Firestore에 저장하고 통계를 계산하며, 현재 데이터 요약과 읽기 전용 Function Calling 결과를 근거로 OpenAI 답변을 생성하는 FastAPI 서비스다.

## 실행 환경

- Python 3.10 이상(권장 3.12)
- Firebase Firestore 프로젝트와 서비스 계정
- OpenAI API 키

## 로컬 실행

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

`.env`에 실제 값을 입력한다.

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_MAX_OUTPUT_TOKENS=500
FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
ALLOWED_ORIGINS=http://localhost:5173
```

샘플 CSV는 120개의 유효한 날짜·체중 레코드를 포함한다. 데이터가 없는 날짜는 CSV에 넣지 않는다.

```bash
.venv/bin/python scripts/generate_sample_csv.py
.venv/bin/python scripts/import_csv.py data/weights.csv --dry-run
.venv/bin/python scripts/import_csv.py data/weights.csv
```

첫 번째 명령은 샘플을 다시 만들고, 두 번째 명령은 Firestore에 쓰지 않고 검증만 하며, 세 번째 명령은 실제로 가져온다. 이미 저장된 날짜는 건너뛴다.

서버는 애플리케이션 팩토리로 실행한다.

```bash
.venv/bin/uvicorn app.main:create_app --factory --reload
```

- 상태 확인: `http://localhost:8000/health`
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## 테스트

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m compileall -q app scripts
.venv/bin/python scripts/import_csv.py data/weights.csv --dry-run
```

테스트는 인메모리 저장소와 가짜 OpenAI 클라이언트를 사용하므로 외부 서비스에 연결하지 않는다.

## API

- `POST/GET /api/data`
- `PUT/DELETE /api/data/{record_id}`
- `GET /api/data/summary`
- `POST/GET /api/conversations`
- `GET/DELETE /api/conversations/{conversation_id}`
- `POST /api/chat`

AI 도구는 전체 요약, 날짜별 기록, 기간 목록과 기간 통계 조회만 허용한다. 쓰기 도구는 제공하지 않으며 시스템 프롬프트와 도구 입출력은 대화 기록에 저장하지 않는다.

## Render 배포

저장소 루트의 Blueprint에서 `M1-2/backend/render.yaml`을 사용하거나 다음 값을 직접 설정한다.

- Root Directory: `M1-2/backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:create_app --factory --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`

비밀 값은 Render 환경 변수로만 등록한다. 배포 뒤 Vercel 주소를 `ALLOWED_ORIGINS`에 지정하고 배포 URL의 `/docs`까지 확인한다.
