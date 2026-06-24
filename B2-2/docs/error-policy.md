# 에러 처리 정책

## 공통 원칙

- 최대 재시도 횟수는 `MAX_RETRY_COUNT=2`로 제한한다.
- 정상 스킵과 오류를 구분한다.
- 정상 스킵은 Discord 알림 없이 n8n execution log에만 남긴다.
- API 실패, 인증 실패, 저장 실패처럼 조치가 필요한 오류는 Discord 알림을 시도한다.
- Discord 알림 실패는 전체 워크플로우 결과를 실패로 되돌리지 않고 로그로만 남긴다.
- 중복 확인은 Ollama 호출보다 반드시 앞에 둔다.

## 정상 스킵 로그

| 코드 | 상황 | 처리 |
|---|---|---|
| NO_RSS_SOURCES | 활성 RSS 설정이 0건 | 로그 후 정상 종료 |
| NO_RSS_ITEMS | 모든 RSS에서 수집된 항목이 0건 | 로그 후 정상 종료 |
| TOPIC_CONFIG_EMPTY | 활성 주제 키워드가 0건 | 로그 후 정상 종료 |
| NO_TOPIC_MATCH | 주제에 맞는 기사가 없음 | 로그 후 정상 종료 |
| DUPLICATE_SKIPPED | Notion 결과 DB에 이미 존재 | Ollama 호출 없이 로그 후 정상 종료 |

## RSS 단계

| 실패 유형 | 처리 |
|---|---|
| RSS URL 응답 없음 | 해당 피드 최대 2회 재시도 |
| RSS 파싱 실패 | 해당 피드 최대 2회 재시도 |
| 특정 피드만 실패 | 실패 피드는 `RSS_FETCH_FAILED` 로그, 나머지 피드는 계속 처리 |
| 모든 피드 실패 | `RSS_ALL_FAILED`로 Discord 오류 알림 |

RSS 목록 자체가 0건인 경우는 오류가 아니다. 스케줄은 계속 실행되어야 하므로 `NO_RSS_SOURCES` 로그만 남긴다.

## Notion 설정 DB 조회 단계

| 실패 유형 | 처리 |
|---|---|
| RSS Sources DB 조회 실패 | 최대 2회 재시도 후 Discord 알림 |
| Topic Keywords DB 조회 실패 | 최대 2회 재시도 후 Discord 알림 |
| Notion 인증 실패 | 재시도 후에도 실패하면 `NOTION_CONFIG_AUTH_FAILED` 알림 |

설정 DB 조회가 실패하면 수집 범위와 주제를 알 수 없으므로 워크플로우를 중단한다.

## Notion 결과 DB 중복 조회 단계

| 실패 유형 | 처리 |
|---|---|
| 결과 DB 조회 실패 | 최대 2회 재시도 |
| 속성명 불일치 | `NOTION_DEDUPE_SCHEMA_FAILED` 알림 |
| 인증 실패 | `NOTION_DEDUPE_AUTH_FAILED` 알림 |

중복 조회가 실패하면 Ollama를 호출하지 않는다. 중복 여부를 모르는 상태에서 AI를 호출하면 비용과 중복 저장 위험이 생기기 때문이다.

## Ollama 단계

| 실패 유형 | 처리 |
|---|---|
| 연결 실패 | 최대 2회 재시도 |
| 타임아웃 | 최대 2회 재시도 |
| HTTP 오류 | 최대 2회 재시도 |
| 빈 응답 | `OLLAMA_EMPTY_RESPONSE` 실패 처리 |
| JSON 파싱 실패 | `OLLAMA_PARSE_FAILED` 실패 처리 |
| 3줄 초과 | `SUMMARY_INVALID` 실패 처리 |

Ollama 실패 시 Notion 결과 DB에 저장하지 않는다. 실패 원인, 기사 제목, execution ID를 Discord로 알린다.

## Notion 저장 단계

| 실패 유형 | 처리 |
|---|---|
| 페이지 생성 실패 | 최대 2회 재시도 |
| 필수 속성 누락 | `NOTION_SAVE_SCHEMA_FAILED` 알림 |
| URL 또는 Date 타입 오류 | `NOTION_SAVE_MAPPING_FAILED` 알림 |
| 인증 실패 | `NOTION_SAVE_AUTH_FAILED` 알림 |

Notion 저장 실패 시 Discord로 알린다. 같은 실행에서 Ollama를 다시 호출하지 않는다.

## Discord 알림 단계

| 실패 유형 | 처리 |
|---|---|
| Discord webhook 실패 | 최대 2회 재시도 |
| 재시도 후 실패 | n8n execution log에만 `DISCORD_NOTIFY_FAILED` 기록 |

Discord는 오류 알림 보조 채널이다. Discord 실패 때문에 저장이 성공한 뉴스를 실패 처리하지 않는다.

## 비용 및 중복 방지

Ollama 호출 전 필수 순서:

```text
RSS 수집
-> 주제 필터
-> 최신 1건 선택
-> Notion 결과 DB 중복 조회
-> 중복이 아닌 경우에만 Ollama 호출
```

이 순서를 지키면 이미 저장된 기사에는 AI 호출이 발생하지 않는다.
