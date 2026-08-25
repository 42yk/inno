# 백엔드 아키텍처

## 1. 책임 경계

```text
HTTP Request
    │
    ▼
Router ── Pydantic Schema
    │
    ▼
Application Service
    ├── Repository ── Firestore
    └── OpenAI Client ── OpenAI API
```

### Router

- URL, HTTP 메서드와 상태 코드를 정의한다.
- 경로·쿼리·본문을 Pydantic 스키마로 검증한다.
- 서비스 결과를 응답 스키마로 변환한다.
- Firestore SDK나 OpenAI SDK를 직접 호출하지 않는다.

### Schema

- 데이터, 대화, 채팅 및 도구 인자의 입력·출력 형태를 정의한다.
- 날짜 범위, 체중 범위, 메모 길이와 메시지 길이를 검증한다.
- 외부에서 전달된 Function Calling 인자도 같은 방식으로 재검증한다.

### Service

- 데이터 중복 검사, 기간 조회, 통계, 추세와 대화 저장 흐름을 구현한다.
- 여러 저장소나 외부 클라이언트를 조합한다.
- HTTP 상태 코드 대신 도메인 예외를 발생시킨다.

### Repository

- Firestore 컬렉션과 문서 형태를 외부 계층에서 숨긴다.
- 조회 결과를 도메인에서 사용하는 구조로 정규화한다.
- 생성·수정·삭제와 트랜잭션을 담당한다.
- 통계 계산이나 사용자 메시지를 만들지 않는다.

### Client

- OpenAI SDK 초기화와 모델 호출을 캡슐화한다.
- API 키, 모델명과 출력 토큰 제한을 설정에서 전달받는다.
- OpenAI 응답 항목을 채팅 서비스가 다룰 수 있는 구조로 변환한다.

## 2. 의존성 방향

의존성은 바깥 계층에서 안쪽 계층으로만 흐른다.

```text
routers → schemas + services
services → schemas + repositories + clients
repositories → firebase
clients → config
```

서비스가 구체적인 Firestore 객체나 OpenAI SDK 객체를 직접 생성하지 않도록 생성자 또는 FastAPI dependency로 주입한다. 테스트에서는 같은 인터페이스를 구현한 인메모리 저장소와 가짜 OpenAI 클라이언트로 교체한다.

## 3. 앱 시작

1. 환경 변수를 읽고 필수 값과 CORS 목록을 검증한다.
2. 서비스 계정 JSON으로 Firebase Admin 앱을 한 번만 초기화한다.
3. Firestore 클라이언트와 저장소를 생성한다.
4. OpenAI 클라이언트와 서비스를 생성한다.
5. FastAPI에 라우터, CORS와 공통 예외 처리기를 등록한다.
6. `/docs`와 상태 확인용 `GET /health`를 제공한다.

필수 환경 변수가 없거나 서비스 계정 JSON을 해석할 수 없으면 애플리케이션 시작을 실패시킨다. 운영 중 첫 요청에서 설정 오류가 발견되도록 미루지 않는다.

## 4. 데이터 CRUD 흐름

```text
Frontend
  → Data Router
  → Data Schema validation
  → Data Service duplicate/business validation
  → Data Repository
  → Firestore data
  → Response Schema
```

- 등록과 수정 시 문서 ID로 사용하는 날짜의 중복을 검사한다.
- 날짜를 수정하면 Firestore 트랜잭션 안에서 새 날짜 문서를 생성하고 기존 문서를 삭제한다.
- 삭제 후 프론트가 목록과 요약을 다시 요청한다.

## 5. 요약 흐름

```text
GET /api/data/summary
  → Summary Service
  → Data Repository.list_all(order=ascending)
  → statistics + trend
  → Summary Response
```

같은 `SummaryService`는 `POST /api/chat`의 시스템 프롬프트 구성과 `get_weight_summary` 도구에서도 재사용한다.

## 6. 채팅 흐름

```text
POST /api/chat
  → request validation
  → SummaryService.get_summary()
  → system prompt composition
  → OpenAI first response
      ├── final text → save exchange
      └── function call
            → allow-list check
            → tool argument validation
            → read-only service execution
            → OpenAI continuation
            → final text
            → save exchange
```

도구 호출은 최대 횟수를 제한해 반복 호출을 방지한다. 최종 텍스트가 생성된 경우에만 사용자 질문과 AI 답변을 한 묶음으로 저장한다.

## 7. 대화 저장 흐름

- `conversation_id`가 없으면 새 문서를 만든다.
- 첫 사용자 질문의 앞부분을 제목으로 사용한다.
- `conversation_id`가 있으면 문서 존재 여부를 확인한다.
- 사용자 질문과 최종 AI 답변을 시간 순서대로 추가한다.
- 실패한 AI 호출과 도구 중간 결과는 사용자 메시지 기록에 저장하지 않는다.
- 대화 목록은 `updated_at` 내림차순으로 반환한다.

## 8. 오류 변환

| 도메인 상황 | HTTP 상태 | 공개 메시지 |
|---|---:|---|
| 잘못된 입력 | 422 | 입력 값을 확인해 주세요. |
| 시작일이 종료일보다 늦음 | 400 | 조회 기간이 올바르지 않습니다. |
| 중복 날짜 | 409 | 해당 날짜의 기록이 이미 존재합니다. |
| 데이터 또는 대화 없음 | 404 | 요청한 기록을 찾을 수 없습니다. |
| OpenAI 호출 실패 | 502 | AI 답변을 생성하지 못했습니다. 잠시 후 다시 시도해 주세요. |
| Firestore 호출 실패 | 503 | 데이터를 처리하지 못했습니다. 잠시 후 다시 시도해 주세요. |

서버 로그에는 예외 종류와 추적 가능한 요청 ID를 남기되 API 키, 서비스 계정 JSON, 전체 프롬프트와 개인 데이터 전체를 기록하지 않는다.
