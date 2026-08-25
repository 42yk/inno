# 프론트엔드 아키텍처

## 1. 구성

```text
index.html
   │
   ▼
app.js ── initial load + event wiring
   │
   ├── api.js ───────────── FastAPI
   ├── state.js ─────────── client state
   ├── chat.js ──────────── chat rendering/actions
   ├── conversations.js ─── history rendering/actions
   ├── data.js ──────────── CRUD rendering/actions
   ├── summary.js ───────── summary rendering
   └── utils.js ─────────── formatting/safe DOM helpers
```

각 기능 모듈은 필요한 DOM 요소, API 클라이언트와 상태 접근 함수를 명시적으로 전달받는다. 모듈이 전역 변수를 직접 수정하지 않도록 한다.

## 2. 모듈 책임

### `app.js`

- 애플리케이션 시작점
- 필수 DOM 요소 확인
- 이벤트 핸들러 연결
- 첫 데이터, 요약과 대화 목록 병렬 조회
- 기능 모듈 초기화

### `api.js`

- `fetch` 공통 래퍼
- `API_BASE_URL` 결합
- JSON 직렬화와 역직렬화
- HTTP 오류를 일관된 `ApiError`로 변환
- 데이터, 대화와 채팅 API 함수 제공

### `state.js`

- 단일 상태 객체와 제한된 갱신 함수 제공
- 상태 변경 후 필요한 렌더 함수를 호출할 수 있도록 구독 지원
- Firestore나 OpenAI의 세부 구조를 알지 않는다.

### `chat.js`

- 사용자·AI 메시지 렌더링
- 질문 전송과 로딩 버블 표시
- `conversation_id` 갱신
- 새 대화 초기화
- 전송 중 중복 제출 차단

### `conversations.js`

- 대화 목록 렌더링
- 현재 대화 강조
- 대화 상세 불러오기
- 대화 삭제 확인과 목록 갱신

### `data.js`

- 체중 입력 폼과 데이터 목록 렌더링
- 신규 등록과 수정 모드 전환
- 삭제 확인
- CRUD 성공 후 데이터와 요약 갱신

### `summary.js`

- 기간, 기록 수, 평균, 최고·최저, 최근 변화와 추세 렌더링
- 데이터가 없거나 추세를 계산할 수 없는 상태 표시

### `utils.js`

- 날짜, kg, 변화량과 시각 포맷
- 사용자 텍스트를 안전하게 DOM에 추가하는 도우미
- 디바운스가 필요한 경우 범용 도우미 제공

## 3. 상태 모델

```js
{
  data: [],
  summary: null,
  conversations: [],
  currentConversationId: null,
  messages: [],
  editingDataId: null,
  loading: {
    initial: false,
    chat: false,
    data: false,
    conversations: false
  },
  notice: null
}
```

- 서버 데이터의 원본은 백엔드다.
- 새로고침 후 로컬 상태는 API 응답으로 다시 구성한다.
- 대화 ID 외에 개인 데이터를 `localStorage`에 저장하지 않는다.
- MVP에서는 URL 라우팅과 클라이언트 캐시를 사용하지 않는다.

## 4. 초기화 흐름

```text
DOMContentLoaded
  → config validation
  → bind events
  → Promise.allSettled([
       loadData(),
       loadSummary(),
       loadConversations()
     ])
  → each panel renders success or local error
```

한 패널의 실패가 다른 패널 렌더링을 막지 않도록 초기 조회는 독립적으로 처리한다.

## 5. 데이터 변경 흐름

```text
form submit
  → client validation
  → disable form
  → POST or PUT
  → Promise.all([loadData(), loadSummary()])
  → reset edit mode
  → success notice
```

실패하면 사용자가 입력한 값을 유지한다. 삭제는 확인 후 실행하며 성공했을 때만 목록과 요약을 다시 가져온다.

## 6. 채팅 흐름

```text
submit question
  → append user bubble
  → disable input + show loading bubble
  → POST /api/chat
  → append assistant bubble
  → update conversation_id
  → refresh conversation list
```

실패 시 질문은 화면에 유지하고 재시도할 수 있는 오류를 표시한다. 실패 응답을 AI 메시지처럼 렌더링하지 않는다.

## 7. 대화 불러오기 흐름

```text
conversation item click
  → GET /api/conversations/{id}
  → set currentConversationId
  → replace messages
  → render all messages
  → focus chat input
```

대화를 불러오는 동안 기존 메시지를 즉시 지우지 않고 로딩 상태를 표시한다. 성공하면 교체하고 실패하면 현재 대화를 유지한다.
