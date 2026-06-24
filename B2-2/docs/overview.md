# 프로젝트 개요

## 미션

RSS 기반 기술 뉴스를 자동 수집하고, 주제 필터링을 거친 최신 기사 1건을 Ollama로 요약한 뒤 Notion 데이터베이스에 저장하는 n8n 자동화 워크플로우를 구축한다.

핵심 흐름은 아래와 같다.

```text
Manual Start 또는 Schedule Trigger
-> Notion RSS 설정 조회
-> RSS 수집
-> Notion 주제 키워드 조회
-> 주제 필터링
-> 최신 1건 선택
-> Notion 중복 조회
-> Ollama 3줄 요약
-> Notion 저장
```

중복 조회는 Ollama 호출보다 먼저 수행한다. 이미 저장된 기사는 AI로 보내지 않는다.
기본 RSS와 기본 주제 키워드는 n8n workflow 안에서 만들지 않고 `npm run setup:docker`가 Notion 설정 DB에 한 번 등록한다.

## 사용 도구

| 구분 | 도구 | 사용 이유 |
|---|---|---|
| 자동화 | n8n | 스케줄, RSS 수집, 조건 분기, API 호출 연결 |
| AI 요약 | Ollama | 로컬 모델을 `http://host.docker.internal:11434`로 호출 |
| 저장소 | Notion database | 제목, 요약, 원문 링크, 발행일시를 구조화해 저장 |
| 오류 알림 | Discord webhook | 조치가 필요한 실패 상황만 팀 채널로 전달 |
| 운영 로그 | n8n execution log | 정상 스킵과 Discord 실패를 기록 |

## 산출물

- n8n 자동화 워크플로우
- 워크플로우 구조 스크린샷
- 단계별 역할과 연결 구조 문서
- Notion 뉴스 요약 데이터베이스
- RSS 설정 데이터베이스
- 주제 키워드 설정 데이터베이스
- 실행 README
- 필터링 기준과 에러 처리 정책 문서

## 테스트 케이스

| 케이스 | 입력/상황 | 기대 결과 |
|---|---|---|
| 정상 저장 | RSS 항목 있음, 키워드 매칭, 중복 아님 | Ollama 요약 후 Notion 저장 |
| RSS 설정 0건 | RSS Sources DB에 활성 RSS 없음 | `NO_RSS_SOURCES` 로그 후 정상 종료 |
| RSS 항목 0건 | RSS는 있으나 새 항목 없음 | `NO_RSS_ITEMS` 로그 후 정상 종료 |
| 주제 키워드 0건 | Topic Keywords DB에 활성 키워드 없음 | `TOPIC_CONFIG_EMPTY` 로그 후 정상 종료 |
| 주제 매칭 없음 | 수집 기사 중 키워드 매칭 없음 | `NO_TOPIC_MATCH` 로그 후 정상 종료 |
| 중복 기사 | Notion 결과 DB에 같은 dedupe key 있음 | `DUPLICATE_SKIPPED`, Ollama 호출 없음 |
| Ollama 실패 | Ollama 연결 실패 또는 빈 응답 | 최대 2회 재시도 후 Discord 오류 알림 |
| Notion 중복 조회 실패 | 결과 DB 조회 실패 | Ollama 호출 없이 Discord 오류 알림 |
| Notion 저장 실패 | 페이지 생성 실패 | Ollama 재호출 없이 저장 재시도 후 Discord 오류 알림 |
| Discord 실패 | 오류 알림 webhook 실패 | 최대 2회 재시도 후 `DISCORD_NOTIFY_FAILED` 로그 |

## 팀 역할 예시

| 역할 | 담당 업무 |
|---|---|
| 워크플로우 담당 | n8n 노드 구성, 조건 분기, 재시도 설정, 실행 로그 확인 |
| 데이터 담당 | Notion 결과 DB, RSS 설정 DB, 주제 설정 DB 생성과 속성 관리 |
| AI 담당 | Ollama 모델 선택, 요약 프롬프트 작성, 요약 응답 검증 |
| 문서 담당 | README 작성, 정책 문서 정리, 스크린샷 마스킹 확인 |

## 제출 체크리스트

- [ ] n8n 워크플로우가 매일 설정된 시간에 실행된다.
- [ ] 실행 시간은 `NEWS_CRON_EXPRESSION`, `NEWS_TIMEZONE`으로 변경할 수 있다.
- [ ] RSS 설정 DB에서 `Enabled = true`인 RSS만 읽는다.
- [ ] RSS 설정 DB가 0건이어도 스케줄 실행이 실패하지 않는다.
- [ ] 주제 키워드는 Topic Keywords DB에서 읽는다.
- [ ] 주제 키워드는 운영 중 추가, 삭제, 비활성화할 수 있다.
- [ ] 주제에 맞는 최신 기사 1건만 선택한다.
- [ ] Notion 결과 DB를 먼저 조회해 중복 저장을 막는다.
- [ ] 중복 기사는 Ollama로 보내지 않는다.
- [ ] Ollama 요약은 3줄 이내로 검증된다.
- [ ] Notion DB에 제목, 요약, 원문 링크, 발행일시, 중복 키가 저장된다.
- [ ] Ollama, Notion, Discord 실패 처리 정책이 문서화되어 있다.
- [ ] 정상 스킵은 Discord가 아니라 n8n execution log로만 처리한다.
- [ ] 문서와 스크린샷에 Notion token, Discord webhook URL이 노출되지 않는다.

## 보조 산출물

- `scripts/setup-docker.js`: DB 생성, `.env` 갱신, Docker n8n 실행, workflow CLI import를 한 번에 수행한다.
- `docs/workflow.md`: n8n 노드 흐름과 연결 구조를 설명한다.
- `docs/notion-db-schema.md`: Notion 데이터베이스 속성 설계를 설명한다.
- `docs/filter-policy.md`: 주제 필터링 기준과 변경 방식을 설명한다.
- `docs/error-policy.md`: 단계별 에러 처리 정책을 설명한다.
- `docs/workflow-blueprint.json`: n8n 구현용 워크플로우 청사진이다.
- `screenshots/`: n8n 워크플로우와 Notion 저장 결과 캡처 보관 위치다.
