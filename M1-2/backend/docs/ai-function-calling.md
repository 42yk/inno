# AI 컨텍스트 주입과 Function Calling

## 1. 목적

전체 요약은 과제 요구사항에 따라 첫 GPT 호출 전에 시스템 프롬프트에 삽입한다. 특정 날짜와 기간에 대한 사실 조회 및 계산은 Function Calling으로 백엔드 서비스에 위임한다.

GPT의 역할은 다음으로 제한한다.

- 사용자 질문에서 필요한 조회 유형과 날짜 인자를 선택한다.
- 백엔드가 반환한 결과를 이해하기 쉬운 한국어로 설명한다.
- 데이터가 없다는 결과를 그대로 전달한다.

GPT는 Firestore에 직접 접근하거나 체중 통계를 직접 계산하지 않는다.

## 2. 시스템 프롬프트 구성

첫 호출의 시스템 프롬프트에는 AI의 역할, 현재 전체 요약 JSON과 답변 정책을 포함한다. 요약은 `GET /api/data/summary`와 동일한 `SummaryService` 결과로 생성하며 프롬프트 전용 통계 로직을 별도로 만들지 않는다.

### 2.1 요약 데이터 주입 예시

채팅 요청을 받을 때 백엔드는 먼저 `SummaryService.get_summary()`를 호출한다. 반환된 Pydantic 모델을 JSON 객체로 변환한 뒤 `ensure_ascii=False`, 들여쓰기 2칸 형식으로 직렬화하여 시스템 메시지의 `[사용자 데이터 요약]` 아래에 삽입한다. Firestore의 개별 체중 레코드 전체를 프롬프트에 넣지는 않는다.

예를 들어 요약 API 결과가 다음과 같다고 가정한다.

```json
{
  "period": {
    "start": "2025-01-01",
    "end": "2025-06-08"
  },
  "count": 120,
  "metrics": {
    "average": 75.9,
    "max": {
      "value": 78.1,
      "dates": ["2025-01-03"]
    },
    "min": {
      "value": 73.9,
      "dates": ["2025-05-21"]
    },
    "first": {
      "date": "2025-01-01",
      "value": 78.0
    },
    "latest": {
      "date": "2025-06-08",
      "value": 74.2
    },
    "change": -3.8
  },
  "trend": {
    "status": "maintain",
    "label": "유지",
    "previous_average": 74.0,
    "recent_average": 74.1,
    "difference": 0.1
  }
}
```

백엔드가 생성하는 실제 시스템 메시지의 `content`는 다음 형태다.

```text
당신은 개인 체중 기록 분석 비서입니다.

[사용자 데이터 요약]
{
  "period": {
    "start": "2025-01-01",
    "end": "2025-06-08"
  },
  "count": 120,
  "metrics": {
    "average": 75.9,
    "max": {
      "value": 78.1,
      "dates": [
        "2025-01-03"
      ]
    },
    "min": {
      "value": 73.9,
      "dates": [
        "2025-05-21"
      ]
    },
    "first": {
      "date": "2025-01-01",
      "value": 78.0
    },
    "latest": {
      "date": "2025-06-08",
      "value": 74.2
    },
    "change": -3.8
  },
  "trend": {
    "status": "maintain",
    "label": "유지",
    "previous_average": 74.0,
    "recent_average": 74.1,
    "difference": 0.1
  }
}

다음 정책을 반드시 지키세요.
- 저장된 요약과 도구 조회 결과만 근거로 답하세요.
- 특정 날짜나 기간의 구체적인 질문에는 적절한 읽기 전용 도구를 사용하세요.
- 기록이 없는 날짜의 체중을 추정하거나 만들어내지 마세요.
- 체중 변화에 대한 의료 진단, 질병 판단 또는 치료 지시는 하지 마세요.
- 답변은 한국어로 간결하고 명확하게 작성하세요.
```

이 문자열은 Chat Completions 요청의 첫 번째 메시지로 전달된다. 사용자 질문과 기존 대화는 그 뒤에 별도 메시지로 추가된다.

```json
{
  "model": "gpt-5-mini",
  "messages": [
    {
      "role": "system",
      "content": "당신은 개인 체중 기록 분석 비서입니다.\n\n[사용자 데이터 요약]\n{ ...요약 JSON... }\n\n다음 정책을 반드시 지키세요.\n..."
    },
    {
      "role": "user",
      "content": "마지막으로 저장된 체중 값이 몇이야?"
    }
  ],
  "tool_choice": "auto",
  "max_completion_tokens": 500
}
```

위 요청 예시는 데이터 전달 구조를 설명하기 위해 `content`를 축약하고 `tools` 필드를 생략했다. 실제 요청에서는 완전한 시스템 메시지 문자열과 네 개 도구의 JSON 스키마도 함께 전달한다. 모델은 요약의 `metrics.latest`만으로 질문에 답할 수 있으면 도구 없이 최종 `content`를 반환하고, 추가 조회가 필요하면 `message.tool_calls`를 반환한다.

## 3. 전체 처리 흐름

```text
POST /api/chat
  → 현재 데이터 요약 계산 및 시스템 프롬프트 주입
  → 대화 문맥 + 사용자 질문 + 도구 스키마로 Chat Completions 호출
      ├─ message.tool_calls 없음 + content 있음
      │    → 최종 답변 확정
      │    → 사용자 질문과 AI 답변 저장
      │    → API 응답 반환
      └─ message.tool_calls 있음
           → 함수 이름 허용 목록 확인
           → arguments JSON 해석 및 Pydantic 검증
           → 읽기 전용 도구 실행
           → assistant.tool_calls + role=tool 결과로 AI 재호출
           → 최종 content가 생성될 때까지 반복
```

1. 채팅 서비스가 OpenAI 호환 `/v1/chat/completions`에 시스템 프롬프트, 대화 문맥, 현재 질문과 도구 스키마를 보낸다.
2. 텍스트 답변이면 최종 응답으로 사용한다.
3. 함수 호출이면 이름과 JSON 인자를 추출한다.
4. 이름을 허용 목록에서 확인하고 인자를 Pydantic으로 검증한다.
5. 도구 서비스가 공통 데이터 또는 요약 서비스를 호출한다.
6. 모델의 `assistant.tool_calls` 메시지 뒤에 같은 호출 ID를 가진 `role=tool` 결과 메시지를 추가해 다시 요청한다.
7. 모델이 최종 텍스트를 생성할 때까지 반복하되 최대 도구 호출 횟수를 제한한다.
8. 최종 답변과 사용자 질문만 대화 기록에 저장한다.

### 3.1 응답 유형 판별 기준

모델이 도구를 사용할지는 `tool_choice: "auto"` 상태에서 모델이 선택한다. 백엔드는 답변 문장의 의미를 분석하지 않고 `response.choices[0].message`의 구조로 응답 유형을 판별한다. 현재 구현은 `finish_reason`이 아니라 `message.tool_calls`와 `message.content`를 기준으로 한다.

| `message.tool_calls` | `message.content` | 백엔드 판단과 처리 |
|---|---|---|
| 1개 이상 | 없음 | 도구 호출 요청으로 판단하고 모든 호출을 검증·실행한다. |
| 1개 이상 | 있음 | 도구 호출을 우선한다. 함께 반환된 중간 텍스트는 최종 답변으로 사용하지 않는다. |
| 없음 | 비어 있지 않음 | 질문에 대한 최종 자연어 답변으로 판단한다. |
| 없음 | 없거나 공백 | 유효한 답변이 없는 비정상 AI 응답으로 판단하고 `AIProviderError`를 발생시킨다. |

도구 호출 응답은 다음 구조로 수신한다.

```json
{
  "role": "assistant",
  "content": null,
  "tool_calls": [
    {
      "id": "call_abc123",
      "type": "function",
      "function": {
        "name": "get_weight_by_date",
        "arguments": "{\"date\":\"2025-03-10\"}"
      }
    }
  ]
}
```

백엔드는 함수 이름을 허용 목록과 대조하고 `arguments` 문자열을 JSON으로 해석한 뒤 Pydantic 스키마로 검증한다. 도구 실행 결과는 모델이 반환한 호출 ID를 유지해 다음 메시지로 전달한다.

```json
{
  "role": "tool",
  "tool_call_id": "call_abc123",
  "content": "{\"status\":\"found\",\"record\":{\"date\":\"2025-03-10\",\"value\":72.4}}"
}
```

재요청에는 원래의 `assistant.tool_calls` 메시지와 모든 `role: "tool"` 결과 메시지를 함께 포함한다. 다음 응답에도 `tool_calls`가 있으면 같은 절차를 반복하고, `tool_calls` 없이 비어 있지 않은 `content`가 반환되면 최종 답변으로 확정한다. 한 응답에 여러 도구 호출이 있으면 각각을 실행하되 요청 전체의 누적 호출 수가 설정된 최대값을 넘으면 중단한다.

최종 `POST /api/chat` 응답의 `tools_used`에는 실제로 실행한 도구 이름을 호출 순서대로 담는다. 도구를 호출하지 않고 요약 컨텍스트만으로 답한 경우에는 빈 목록을 반환한다.

## 4. 도구 목록

### `get_weight_summary`

전체 데이터의 기간, 개수, 평균, 최고·최저, 최초·최근, 변화량과 추세를 반환한다.

```json
{
  "type": "object",
  "properties": {},
  "additionalProperties": false
}
```

### `get_weight_by_date`

```json
{
  "type": "object",
  "properties": {
    "date": {
      "type": "string",
      "description": "조회 날짜, YYYY-MM-DD"
    }
  },
  "required": ["date"],
  "additionalProperties": false
}
```

반환 상태는 `found` 또는 `not_found`다. 기록이 없을 때 인접 날짜를 대신 반환하거나 값을 추정하지 않는다.

### `get_weight_records`

```json
{
  "type": "object",
  "properties": {
    "start_date": {"type": "string", "description": "시작일, YYYY-MM-DD"},
    "end_date": {"type": "string", "description": "종료일, YYYY-MM-DD"}
  },
  "required": ["start_date", "end_date"],
  "additionalProperties": false
}
```

시작일과 종료일을 포함한 기록 목록을 날짜 오름차순으로 반환한다.

### `get_weight_statistics`

인자 구조는 `get_weight_records`와 같다. 기간 내 개수, 평균, 최고·최저와 날짜, 최초·최근 기록, 변화량과 계산 가능한 경우 추세를 반환한다.

## 5. 도구 선택 정책

| 사용자 질문 | 도구 |
|---|---|
| 전체 기간, 전체 평균, 전체 추세 | `get_weight_summary` |
| 특정 날짜 체중 | `get_weight_by_date` |
| 기간 내 모든 기록 나열 | `get_weight_records` |
| 기간 평균·최고·최저·변화량·추세 | `get_weight_statistics` |
| 인사 또는 서비스 사용법 | 도구 호출 없음 |

기본 `tool_choice`는 자동 선택으로 두되, 시스템 프롬프트에서 데이터에 관한 구체적 사실 질문은 반드시 도구를 사용하도록 지시한다. 모든 도구 호출 이름은 서버의 허용 목록과 대조한다.

## 6. 실패와 안전

- 알 수 없는 도구 이름은 실행하지 않는다.
- 잘못된 날짜와 기간은 도구 오류 결과로 반환하고 모델이 사용자에게 수정 요청을 하게 한다.
- 도구는 읽기 전용 서비스만 참조한다.
- 사용자 문장을 코드, 쿼리 또는 파일 경로로 실행하지 않는다.
- 도구 결과에 서비스 계정, 내부 예외와 스택 트레이스를 포함하지 않는다.
- 지정된 최대 도구 호출 횟수를 넘으면 안전하게 중단하고 재시도 안내를 반환한다.
- 응답 길이 제한과 모델명은 환경 변수로 관리한다.
- 가상 키는 Bearer 인증으로 전달되며 SDK의 Base URL은 `https://copa.codyssey.kr/v1`로 설정한다.

## 7. 대화 문맥

대화를 불러온 경우 기존 `user`와 `assistant` 메시지를 모델 문맥에 포함한다. 시스템 프롬프트는 매 요청마다 현재 요약으로 새로 생성하여 데이터 변경이 다음 질문에 반영되도록 한다. 과거 도구 결과는 Firestore 대화 문서에 저장하지 않고, 필요한 사실은 현재 요청에서 다시 조회한다.
