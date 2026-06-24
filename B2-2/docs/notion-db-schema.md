# Notion 데이터베이스 설계

## 1. News Summaries DB

AI가 요약한 최종 뉴스가 저장되는 결과 DB다.

| 속성명 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| Title | Title | Y | 뉴스 제목 |
| Summary | Rich text | Y | Ollama가 생성한 3줄 이내 요약 |
| Original URL | URL | Y | 원문 링크 |
| Published At | Date | Y | RSS 발행일시 |
| Dedupe Key | Rich text | Y | `guid` 우선, 없으면 원문 링크 |
| Source | Rich text | N | RSS 출처 이름 |
| Matched Keywords | Multi-select | N | 매칭된 주제 키워드 |
| Status | Select | Y | `Saved`, `Skipped`, `Failed` 중 저장 결과 |
| AI Model | Rich text | N | 사용한 Ollama 모델명 |
| Saved At | Date | Y | Notion 저장 시각 |

## 2. RSS Sources DB

RSS URL을 실시간으로 추가/삭제하기 위한 설정 DB다. n8n은 매 실행마다 이 DB를 조회한다.

| 속성명 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| Name | Title | Y | RSS 출처 이름 |
| Feed URL | URL | Y | RSS 피드 URL |
| Enabled | Checkbox | Y | 체크된 RSS만 수집 대상 |
| Priority | Number | N | 같은 발행일일 때 우선순위 |
| Note | Rich text | N | RSS 선택 이유나 담당자 메모 |

운영 방식:

- RSS를 추가하려면 새 행을 만들고 `Enabled`를 체크한다.
- RSS를 잠시 제외하려면 행을 삭제하지 않고 `Enabled` 체크를 해제한다.
- RSS를 영구 삭제하려면 행을 삭제한다.
- 활성 RSS가 0건이면 워크플로우는 실패하지 않고 `NO_RSS_SOURCES` 로그만 남긴다.

## 3. Topic Keywords DB

주제 필터를 실시간으로 변경하기 위한 설정 DB다. n8n은 매 실행마다 이 DB를 조회한다.

| 속성명 | 타입 | 필수 | 설명 |
|---|---|---:|---|
| Keyword | Title | Y | 매칭할 키워드 |
| Enabled | Checkbox | Y | 체크된 키워드만 사용 |
| Match Target | Select | N | `All`, `Title`, `Content`, `Category` |
| Reason | Rich text | N | 키워드 선택 이유 |
| Weight | Number | N | 향후 우선순위 확장용 |

운영 방식:

- 주제를 바꾸려면 키워드 행을 추가하거나 `Enabled` 상태를 변경한다.
- 활성 키워드가 0건이면 워크플로우는 `TOPIC_CONFIG_EMPTY` 로그를 남기고 종료한다.
- 키워드 DB 변경은 다음 스케줄 실행부터 반영된다.

## 중복 확인 조건

Ollama 호출 전에 News Summaries DB에서 아래 조건으로 먼저 조회한다.

```text
Dedupe Key == candidate.dedupeKey
OR
Original URL == candidate.originalUrl
```

조회 결과가 1건 이상이면 다음 동작을 하지 않는다.

- Ollama 호출 안 함
- Notion 신규 저장 안 함
- Discord 알림 안 함
- n8n execution log에 `DUPLICATE_SKIPPED`만 기록
