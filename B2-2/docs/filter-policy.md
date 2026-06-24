# 주제 필터링 정책

## 목적

RSS에서 수집한 기술 뉴스 중 과제 주제에 맞는 기사 1건만 선택하기 위해 주제 키워드 기반 필터를 사용한다.

## 기본 주제

초기 주제는 AI 및 업무 자동화로 둔다.

초기 키워드 예시:

- AI
- artificial intelligence
- 인공지능
- 생성형 AI
- generative AI
- LLM
- large language model
- agent
- AI agent
- automation
- workflow automation
- Ollama
- n8n

## 선택 이유

- 과제의 핵심이 RSS 수집, AI 요약, 자동화 파이프라인이므로 AI와 자동화 관련 뉴스를 우선한다.
- Ollama와 n8n 키워드를 포함해 프로젝트 구현 도구와 직접 연결되는 뉴스를 포착한다.
- 한국어/영어 키워드를 함께 둬 국내외 RSS를 모두 처리할 수 있게 한다.

## 변경 방식

- 키워드는 n8n 워크플로우에 직접 적지 않는다.
- Notion Topic Keywords DB에서 `Enabled = true`인 키워드를 매 실행마다 읽는다.
- 주제를 바꾸려면 Topic Keywords DB에서 키워드를 추가, 삭제, 비활성화한다.
- 활성 키워드가 0건이면 모든 뉴스를 저장하지 않고 `TOPIC_CONFIG_EMPTY` 로그를 남긴다.

## 매칭 기준

1. RSS 항목에서 `title`, `content`, `category`를 추출한다.
2. HTML 태그를 제거하고 대소문자를 통일한다.
3. 활성 키워드 중 하나라도 포함되면 후보로 분류한다.
4. 후보가 여러 건이면 발행일시 최신순으로 1건만 선택한다.
5. 발행일시가 없으면 RSS 수집 순서를 보조 기준으로 사용한다.

## 스킵 기준

- RSS 설정 DB에 활성 RSS가 없으면 `NO_RSS_SOURCES`
- RSS 수집 결과가 0건이면 `NO_RSS_ITEMS`
- 활성 주제 키워드가 없으면 `TOPIC_CONFIG_EMPTY`
- 키워드에 매칭된 기사가 없으면 `NO_TOPIC_MATCH`
- Notion 결과 DB에 이미 존재하면 `DUPLICATE_SKIPPED`

위 스킵은 오류가 아니므로 Discord 알림을 보내지 않고 n8n execution log로만 처리한다.
