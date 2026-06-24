# B2-2 뉴스 요약 자동화 실행 가이드

이 README는 로컬 Docker n8n 실행과 workflow 반영 절차만 다룬다.
설계 문서는 [docs](docs/README.md)에서 확인한다.

## 1. 실행 전 준비

- Docker Desktop을 실행한다.
- 호스트에서 Ollama를 실행하고 `qwen3:6b` 모델을 사용할 수 있게 준비한다.
- Notion integration token을 만든 뒤, 대상 부모 페이지에 integration을 connect한다.
- Discord 오류 알림을 사용할 경우 webhook URL을 준비한다.

## 2. 환경 변수 설정

```bash
cd B2-2
cp .env.example .env
```

`.env`에서 최소 아래 값을 채운다.

```bash
NOTION_API_TOKEN=
NOTION_PARENT_PAGE_ID=
DISCORD_WEBHOOK_URL=
```

Docker에서 호스트 Ollama를 호출하므로 기본값은 아래처럼 둔다.

```bash
OLLAMA_BASE_URL="http://host.docker.internal:11434"
OLLAMA_MODEL="qwen3:6b"
```

실행 시간은 필요할 때 바꾼다.

```bash
NEWS_CRON_EXPRESSION="0 9 * * *"
NEWS_TIMEZONE="Asia/Seoul"
```

자동 활성화가 필요하면 아래 값을 바꾼다.

```bash
N8N_ACTIVATE_WORKFLOW="true"
```

`NOTION_NEWS_DB_ID`, `NOTION_RSS_CONFIG_DB_ID`, `NOTION_TOPIC_CONFIG_DB_ID`가 비어 있으면 setup 스크립트가 생성 후 `.env`에 기록한다.

## 3. Docker n8n 실행 및 workflow 반영

```bash
npm run setup:docker
```

이 명령이 수행하는 일:

1. 누락된 Notion DB 3개를 생성한다.
2. 생성된 DB ID를 `.env`에 기록한다.
3. 기본 RSS와 기본 주제 키워드가 없으면 Notion 설정 DB에 등록한다.
4. `dist/n8n-news-summary.workflow.json`을 생성한다.
5. `docker compose up -d`로 n8n을 실행한다.
6. n8n 컨테이너 CLI로 workflow를 import한다.

처음 접속했을 때 n8n owner 계정 생성 화면이 나오면 계정을 만든 뒤 아래 명령을 한 번 더 실행한다.

```bash
npm run setup:docker
```

## 4. 접속 및 확인

```text
http://localhost:5678
```

n8n에서 아래 workflow가 보이는지 확인한다.

```text
B2-2 RSS AI News Summary
```

`Manual Start`는 `Daily Schedule`과 같은 운영 경로를 실행한다.
기본 RSS와 기본 주제 키워드 등록은 `npm run setup:docker`가 담당한다.

## 5. 자주 쓰는 명령

```bash
npm test
npm run setup:docker
```

Docker 상태 확인:

```bash
docker compose ps
docker compose logs -f n8n
```

중지:

```bash
docker compose down
```

n8n volume까지 지우고 초기화:

```bash
docker compose down -v
```

## 6. 문서

- [프로젝트 개요](docs/overview.md)
- [setup 스크립트와 lib 구조](docs/setup-script-flow.md)
- [인증/credential 관리 전략](docs/credential-strategy.md)
- [워크플로우 설계](docs/workflow.md)
- [Notion DB 설계](docs/notion-db-schema.md)
- [주제 필터링 정책](docs/filter-policy.md)
- [에러 처리 정책](docs/error-policy.md)
- [워크플로우 청사진 JSON](docs/workflow-blueprint.json)
