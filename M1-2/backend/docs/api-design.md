# HTTP API 설계

## 1. 공통 규칙

- 기본 경로는 `/api`다.
- JSON 요청과 응답을 사용한다.
- 날짜는 `YYYY-MM-DD`, 시각은 ISO 8601 문자열로 표현한다.
- 오류 응답은 일관된 구조를 사용한다.

```json
{
  "error": {
    "code": "duplicate_date",
    "message": "해당 날짜의 기록이 이미 존재합니다.",
    "details": null
  }
}
```

## 2. 상태 확인

### `GET /health`

애플리케이션 프로세스가 요청을 받을 수 있는지 확인한다.

```json
{
  "status": "ok"
}
```

## 3. 데이터 API

### `POST /api/data`

요청:

```json
{
  "date": "2026-08-25",
  "value": 72.4,
  "memo": ""
}
```

성공: `201 Created`

```json
{
  "id": "2026-08-25",
  "date": "2026-08-25",
  "value": 72.4,
  "memo": "",
  "created_at": "2026-08-25T10:00:00Z",
  "updated_at": "2026-08-25T10:00:00Z"
}
```

중복 날짜는 `409`, 본문 검증 실패는 `422`를 반환한다.

### `GET /api/data`

선택 쿼리:

- `start_date`
- `end_date`

기본 응답 순서는 날짜 내림차순이다.

```json
{
  "items": [
    {
      "id": "2026-08-25",
      "date": "2026-08-25",
      "value": 72.4,
      "memo": ""
    }
  ],
  "count": 1
}
```

시작일이 종료일보다 늦으면 `400`을 반환한다. 페이지네이션은 적용하지 않는다.

### `PUT /api/data/{id}`

모든 수정 가능 필드를 받는 전체 수정 요청으로 정의한다.

```json
{
  "date": "2026-08-24",
  "value": 72.3,
  "memo": "저녁 측정"
}
```

성공 시 수정된 문서를 반환한다. 기존 문서가 없으면 `404`, 변경할 날짜가 다른 문서와 중복되면 `409`를 반환한다.

### `DELETE /api/data/{id}`

성공: `204 No Content`

문서가 없으면 `404`를 반환한다.

### `GET /api/data/summary`

```json
{
  "period": {
    "start": "2025-01-01",
    "end": "2026-08-25"
  },
  "count": 128,
  "metrics": {
    "average": 72.3,
    "max": {
      "value": 75.1,
      "dates": ["2025-02-10"]
    },
    "min": {
      "value": 69.8,
      "dates": ["2026-07-14"]
    },
    "first": {
      "date": "2025-01-01",
      "value": 74.2
    },
    "latest": {
      "date": "2026-08-25",
      "value": 70.1
    },
    "change": -4.1
  },
  "trend": {
    "status": "decrease",
    "label": "감소",
    "previous_average": 70.8,
    "recent_average": 70.2,
    "difference": -0.6
  }
}
```

데이터가 없으면 `count: 0`과 `period: null`, `metrics: null`, `trend.status: no_data`를 반환한다.

## 4. 대화 API

### `POST /api/conversations`

명시적인 대화 저장 API다. 채팅 API도 내부적으로 같은 대화 서비스를 사용한다.

```json
{
  "title": "3월 평균 체중",
  "messages": [
    {"role": "user", "content": "3월 평균 체중은?"},
    {"role": "assistant", "content": "3월 평균은 72.1kg입니다."}
  ]
}
```

성공: `201 Created`와 생성된 대화 ID를 반환한다.

### `GET /api/conversations`

`updated_at` 내림차순으로 목록을 반환하며 목록에는 전체 `messages`를 포함하지 않는다.

```json
{
  "items": [
    {
      "id": "conversation-id",
      "title": "3월 평균 체중은?",
      "message_count": 2,
      "created_at": "2026-08-25T10:00:00Z",
      "updated_at": "2026-08-25T10:00:02Z"
    }
  ]
}
```

### `GET /api/conversations/{id}`

선택한 대화의 전체 메시지를 반환한다.

```json
{
  "id": "conversation-id",
  "title": "3월 평균 체중은?",
  "messages": [
    {
      "role": "user",
      "content": "3월 평균 체중은?",
      "created_at": "2026-08-25T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "3월 평균은 72.1kg입니다.",
      "created_at": "2026-08-25T10:00:02Z"
    }
  ]
}
```

대화가 없으면 `404`를 반환한다.

### `DELETE /api/conversations/{id}`

성공: `204 No Content`. 대화가 없으면 `404`를 반환한다.

## 5. 채팅 API

### `POST /api/chat`

요청:

```json
{
  "message": "2025년 3월부터 5월까지 평균 체중은?",
  "conversation_id": null
}
```

성공:

```json
{
  "conversation_id": "conversation-id",
  "answer": "해당 기간의 평균 체중은 72.1kg입니다.",
  "tools_used": ["get_weight_statistics"]
}
```

`message`는 공백이 아닌 문자열이어야 하며 최대 길이를 제한한다. 기존 `conversation_id`가 없으면 새 대화를 생성한다. OpenAI 호출에 실패하면 `502`를 반환하고 실패한 답변은 저장하지 않는다.

## 6. 라우팅 주의사항

`/api/data/summary`가 동적 경로로 오인되지 않도록 데이터 라우터에서 정적 경로를 동적 `/{id}` 경로보다 먼저 등록한다. 현재 필수 API에는 `GET /api/data/{id}`가 없지만 이후 확장 시에도 이 순서를 유지한다.
