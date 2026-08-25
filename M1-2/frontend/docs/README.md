# 프론트엔드 설계 문서

개인 체중 변화 기록 분석 AI MVP의 바닐라 HTML/CSS/JavaScript 프론트엔드 설계를 관리한다. 프론트엔드는 단일 페이지에서 채팅, 체중 요약, 데이터 CRUD와 대화 기록을 제공한다.

## 문서 구성

1. [architecture.md](architecture.md): 파일, 모듈, 상태와 이벤트 흐름
2. [ui-design.md](ui-design.md): 화면 영역, 컴포넌트, 반응형 및 접근성
3. [api-integration.md](api-integration.md): 백엔드 API 매핑, 로딩과 오류 처리
4. [testing-and-deployment.md](testing-and-deployment.md): 프론트 테스트, 환경 설정과 Vercel 배포

백엔드의 HTTP 계약은 [백엔드 API 설계](../../backend/docs/api-design.md)를 기준으로 한다.

## 설계 원칙

- 프레임워크 없이 표준 HTML, CSS와 ES Module을 사용한다.
- DOM 조작, 상태 변경과 API 호출의 책임을 분리한다.
- 사용자 작업마다 로딩·성공·실패 상태를 명확히 표시한다.
- 데이터 변경 성공 후 목록과 요약을 다시 조회한다.
- AI 답변을 HTML로 직접 주입하지 않고 텍스트로 렌더링한다.
- 데스크톱과 모바일에서 같은 기능을 제공한다.

## 구현 기준 디렉터리

```text
frontend/
├── src/
│   ├── index.html
│   ├── css/
│   │   └── styles.css
│   └── js/
│       ├── app.js
│       ├── api.js
│       ├── state.js
│       ├── utils.js
│       ├── chat.js
│       ├── conversations.js
│       ├── data.js
│       └── summary.js
├── scripts/
│   └── build.mjs
├── tests/
├── docs/
├── package.json
└── vercel.json
```

빌드 스크립트는 프레임워크나 번들러를 사용하지 않는다. 정적 파일을 `dist`로 복사하고 Vercel의 `API_BASE_URL` 환경 변수로 런타임 설정 파일만 생성한다.
