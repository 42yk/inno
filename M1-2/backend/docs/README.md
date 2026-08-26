# 백엔드 설계 문서

개인 체중 변화 기록 분석 AI MVP의 FastAPI 백엔드 설계를 관리한다. 백엔드의 책임은 입력 검증, Firestore 영속화, OpenAI 호환 Chat Completions Function Calling 실행, 대화 자동 저장과 API 오류 변환이다.

## 문서 구성

1. [architecture.md](architecture.md): 계층, 모듈, 의존성 및 주요 처리 흐름
2. [data-design.md](data-design.md): CSV, Firestore 스키마, 검증 및 통계 규칙
3. [api-design.md](api-design.md): HTTP 엔드포인트와 요청·응답 계약
4. [ai-function-calling.md](ai-function-calling.md): 시스템 프롬프트 주입과 도구 호출 루프
5. [testing-and-deployment.md](testing-and-deployment.md): 테스트 전략, 환경 변수와 Render 배포

## 설계 원칙

- 라우터는 HTTP 계약만 담당한다.
- 서비스는 업무 규칙과 유스케이스를 담당한다.
- 저장소는 Firestore 접근을 캡슐화한다.
- API와 Function Calling은 같은 서비스 함수를 재사용한다.
- GPT는 데이터 조회나 통계를 직접 계산하지 않는다.
- 데이터 변경은 CRUD API에서만 허용하고 AI 도구는 읽기 전용으로 유지한다.
- 외부 서비스 오류와 비밀 값은 사용자 응답에 노출하지 않는다.

## 구현 기준 디렉터리

```text
backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── firebase.py
│   ├── errors.py
│   ├── routers/
│   │   ├── data.py
│   │   ├── conversations.py
│   │   └── chat.py
│   ├── schemas/
│   │   ├── data.py
│   │   ├── conversations.py
│   │   ├── chat.py
│   │   └── tools.py
│   ├── repositories/
│   │   ├── data_repository.py
│   │   └── conversation_repository.py
│   ├── services/
│   │   ├── data_service.py
│   │   ├── summary_service.py
│   │   ├── conversation_service.py
│   │   ├── chat_service.py
│   │   └── tool_service.py
│   └── clients/
│       └── openai_client.py
├── scripts/
│   └── import_csv.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fakes/
├── .env.sample
├── firebase-service-account.example.json
├── requirements.txt
└── render.yaml
```

`main.py`는 앱 생성, CORS, 라우터와 예외 처리기 등록만 담당한다. 구체적인 Firestore 쿼리나 통계 계산을 포함하지 않는다.
