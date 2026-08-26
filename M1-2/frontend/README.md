# Weight AI 프론트엔드

바닐라 HTML, CSS와 JavaScript로 만든 단일 페이지 대시보드다. 체중 요약, 데이터 CRUD, AI 채팅과 저장된 대화 불러오기를 한 화면에서 제공한다.

## 요구 환경

- Node.js 20 이상(외부 npm 패키지는 사용하지 않음)
- 실행 중인 Weight AI FastAPI 백엔드

## 테스트와 빌드

```bash
npm test
API_BASE_URL=http://localhost:8000 npm run build
python3 -m http.server 5173 -d dist
```

`API_BASE_URL`은 빌드 시 `dist/config.js`에 공개 API 주소로 기록된다. OpenAI 키나 Firebase 서비스 계정처럼 비밀인 값은 프론트 환경 변수에 넣지 않는다.

브라우저에서 `http://localhost:5173`에 접속한다. 백엔드 `ALLOWED_ORIGINS`에도 같은 Origin을 등록해야 한다.

## 화면 기능

- 전체 기간, 기록 수, 평균·최고·최저·최초·최근·변화량·추세 요약
- 날짜·체중·메모 등록과 수정·삭제
- 저장된 데이터 컨텍스트를 사용하는 AI 채팅과 로딩 표시
- 대화 목록, 상세 불러오기, 삭제와 새 대화
- 1100px 및 760px 반응형 구간, 키보드 전송과 접근성 상태 알림

모든 사용자 메모와 AI 메시지는 `textContent`로 렌더링한다. HTTP 변경 요청은 자동 재시도하지 않으며 공개 오류 envelope만 표시한다.

## Vercel 배포

1. Vercel 프로젝트 Root Directory를 `M1-2/frontend`로 지정한다.
2. Build Command는 `npm run build`, Output Directory는 `dist`로 지정한다.
3. `API_BASE_URL` 환경 변수에 Render 백엔드 URL을 입력한다.
4. 배포된 Vercel Origin을 백엔드 `ALLOWED_ORIGINS`에 추가하고 백엔드를 다시 배포한다.

`vercel.json`에 빌드와 출력 디렉터리가 정의되어 있다.
