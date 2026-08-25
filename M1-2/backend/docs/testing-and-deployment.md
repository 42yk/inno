# 백엔드 테스트 및 배포 설계

## 1. 테스트 계층

### 단위 테스트

- Pydantic 날짜·체중·메모 검증
- 미래 날짜, 범위 밖 체중과 중복 날짜 처리
- 전체 및 기간 통계 계산
- 추세의 `-0.2`, `+0.2` 경계와 20건 미만 처리
- 대화 제목 생성과 메시지 추가
- 도구 이름 허용 목록과 인자 검증
- 도구 선택 결과를 서비스 호출로 연결하는 디스패처

단위 테스트는 인메모리 저장소와 가짜 OpenAI 클라이언트를 사용한다.

### API 통합 테스트

- 데이터 CRUD 상태 코드와 응답 구조
- 전체·시작일·종료일·양쪽 기간 조회
- `/api/data/summary` 응답
- 대화 생성·목록·상세·삭제
- 새 대화와 기존 대화의 `/api/chat`
- OpenAI 실패 시 `502` 및 대화 미저장
- Firestore 실패 시 공개 오류 응답

FastAPI 테스트 클라이언트를 사용하고 외부 네트워크를 호출하지 않는다.

### 수동 통합 확인

- Firebase 테스트 프로젝트에 CSV 100건 이상 등록
- Swagger UI에서 필수 API 실행
- 실제 OpenAI API로 전체·특정일·기간 질문 각 1회 확인
- Render 배포 후 `/health`와 `/docs` 확인

## 2. 주요 테스트 데이터

- 정확히 20건인 데이터
- 19건인 데이터
- 최근 평균 차이가 정확히 `-0.2`, `0`, `+0.2`인 데이터
- 최고 또는 최저 체중 날짜가 여러 개인 데이터
- 조회 기간에 기록이 없는 데이터
- 시작일과 종료일이 같은 데이터
- 같은 날짜 등록과 날짜 변경 충돌

## 3. 환경 변수

`.env.example`에는 값 없이 다음 키만 제공한다.

```dotenv
OPENAI_API_KEY=
OPENAI_MODEL=
OPENAI_MAX_OUTPUT_TOKENS=
FIREBASE_SERVICE_ACCOUNT_JSON=
ALLOWED_ORIGINS=http://localhost:5173
```

- `FIREBASE_SERVICE_ACCOUNT_JSON`은 JSON 전체 문자열을 사용한다.
- `ALLOWED_ORIGINS`는 쉼표로 구분해 파싱하고 공백을 제거한다.
- 키와 서비스 계정은 `.env`, 로그, Git 및 프론트 코드에 노출하지 않는다.
- 운영 환경에서는 Vercel 실제 도메인만 추가한다.

## 4. 로컬 실행

README에는 다음 순서를 문서화한다.

1. Python 3.10 이상 확인
2. 가상환경 생성 및 활성화
3. `requirements.txt` 설치
4. `.env.example`을 기준으로 `.env` 작성
5. CSV 정제 및 일회성 가져오기 실행
6. `uvicorn app.main:app --reload` 실행
7. `/health`와 `/docs` 확인

## 5. Render 배포

- Root Directory: `M1-2/backend`
- Build Command: 의존성 설치
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`
- 비밀 값은 Render 환경 변수로 등록한다.
- 배포 완료 후 Vercel 도메인을 `ALLOWED_ORIGINS`에 반영한다.

`render.yaml`을 제공하되 비밀 값은 선언하지 않는다. 무료 티어의 콜드스타트를 고려해 프론트에는 첫 응답이 지연될 수 있다는 안내를 표시한다.

## 6. 관찰 가능성과 로그

- 요청마다 요청 ID, 경로, 상태 코드와 처리 시간을 기록한다.
- OpenAI 호출은 성공 여부, 모델명, 도구 이름과 지연만 기록한다.
- 전체 프롬프트, 사용자 체중 목록, API 키와 서비스 계정은 기록하지 않는다.
- 예상 가능한 사용자 오류는 경고가 아닌 정보 수준으로 기록한다.
- 외부 서비스 오류는 예외 정보와 함께 기록하되 공개 응답은 일반화한다.

## 7. 완료 기준

- 모든 필수 엔드포인트가 Swagger에 노출된다.
- 정제된 100건 이상의 데이터가 Firestore에 존재한다.
- CRUD와 요약 테스트가 통과한다.
- 특정 날짜·기간 조회가 Function Calling을 거쳐 정확히 답변된다.
- 대화가 자동 저장되고 목록과 상세 조회가 가능하다.
- Render URL의 `/health`와 `/docs`에 접속할 수 있다.
