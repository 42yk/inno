# Credential Strategy

이 프로젝트는 n8n workflow를 UI에서 손으로 조립하는 방식이 아니라, `.env` 설정 후 `npm run setup:docker` 한 번으로 Docker n8n에 반영되는 방식을 목표로 한다.

그래서 외부 연동 credential은 가능하면 n8n 내부 Credential 저장소가 아니라 `.env`와 HTTP 요청 설정으로 관리한다.

## 기본 원칙

| 원칙 | 이유 |
| --- | --- |
| 비밀값은 `.env`에 둔다 | 문서, 스크린샷, workflow JSON에 token/webhook URL이 노출되지 않게 한다. |
| workflow JSON은 재생성 가능해야 한다 | 로컬 n8n을 새로 띄워도 같은 설정을 다시 import할 수 있어야 한다. |
| n8n Credential 수동 생성 의존을 줄인다 | 사용자가 UI에서 credential을 만들지 않아도 setup 스크립트가 최대한 자동 반영되게 한다. |
| 토큰 값 자체는 workflow JSON에 저장하지 않는다 | JSON에는 `$env.*` 참조만 남기고 실제 값은 Docker container 환경변수에서 읽는다. |

## Notion을 HTTP Request로 호출하는 이유

n8n의 Notion 노드는 Notion API integration token을 사용할 수 있다. 다만 이 방식은 n8n 내부 Credential을 먼저 만들어야 한다.

이 프로젝트에서는 아래 요구가 더 중요하다.

- `NOTION_API_TOKEN`을 `.env`에서 관리한다.
- Docker compose가 `.env` 값을 n8n container 환경변수로 전달한다.
- workflow JSON은 코드로 생성하고 n8n CLI로 import한다.
- 별도 n8n Credential 생성 없이 workflow가 같은 방식으로 재현되어야 한다.

그래서 Notion 조회/저장은 n8n Notion 노드 대신 HTTP Request 노드로 구성한다.

```text
.env
  NOTION_API_TOKEN=secret_...
        |
docker-compose.yml
  NOTION_API_TOKEN: ${NOTION_API_TOKEN}
        |
n8n HTTP Request node
  Authorization: Bearer {{$env.NOTION_API_TOKEN}}
        |
Notion API
```

이 방식의 장점은 자동화 재현성이다. `.env`와 workflow JSON만 있으면 로컬 Docker n8n에 다시 import할 수 있다.

단점은 HTTP Request body를 직접 맞춰야 한다는 점이다. Notion 노드가 대신 처리해주는 database query, page create body, JSON expression 형식을 직접 관리해야 하므로 테스트로 workflow JSON 구조를 검증한다.

## Discord도 같은 맥락인가?

Discord도 같은 맥락이다.

Discord 알림은 n8n Discord credential을 만들기보다 `DISCORD_WEBHOOK_URL`을 `.env`에 두고 webhook HTTP 요청으로 보내는 편이 이 프로젝트 목표와 맞다.

```text
.env
  DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
        |
docker-compose.yml
  DISCORD_WEBHOOK_URL: ${DISCORD_WEBHOOK_URL}
        |
n8n HTTP Request node 또는 Error workflow
  URL: {{$env.DISCORD_WEBHOOK_URL}}
        |
Discord webhook
```

Discord webhook URL도 secret으로 취급한다. 문서와 스크린샷에는 전체 URL을 노출하지 않는다.

## Ollama는 왜 credential이 없는가?

Ollama는 로컬 모델 서버를 HTTP로 호출한다.

```text
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen3.6:latest
```

기본 로컬 구성에서는 별도 API token이 없으므로 n8n Credential이 필요하지 않다. Docker n8n container에서 호스트의 Ollama로 접근하기 위해 `host.docker.internal`을 사용한다.

## native node로 바꿔도 되는 경우

아래 조건이면 n8n Notion 노드나 Discord 노드로 바꿔도 된다.

| 바꿔도 되는 조건 | 영향 |
| --- | --- |
| n8n UI에서 Credential을 한 번 수동 생성해도 된다 | workflow JSON만으로는 완전 재현되지 않는다. |
| 팀이 같은 n8n instance를 계속 사용한다 | Credential이 n8n 내부에 남아 있으므로 운영은 편해진다. |
| JSON body를 직접 관리하는 부담을 줄이고 싶다 | Notion 노드가 UI로 속성 매핑을 도와준다. |

다만 이 프로젝트의 기본 제출물은 로컬 Docker 환경에서 재현 가능해야 하므로, 기본 구조는 `.env` 기반 HTTP Request 방식을 유지한다.

