# 오늘 뭐 먹지?

현재 상황에 맞는 메뉴를 AI가 추천하고, 추천된 메뉴를 Redis 랭킹으로 집계하는 바닐라 웹 서비스입니다.

## 배포 URL

## 주요 기능

- `Home`, `AI 메뉴 추천`, `랭킹` 3개 섹션으로 구성된 단일 페이지
- 식사 시간, 예산, 인원, 음식 종류, 맵기를 입력받는 추천 폼
- Gemini Interactions API 기반 메뉴 추천
- 추천 메뉴명, 추천 이유, 예상 가격, 함께 먹기 좋은 사이드 메뉴/음료 표시
- Redis Sorted Set 기반 인기 메뉴 TOP 10 랭킹
- `APP_PROFILE=dev|prod` 기준 로컬/배포 환경 분리
- API 오류, 필수값 누락, 입력 범위 오류, 응답 지연 안내

## 서비스 기획

### 목적

식사 메뉴를 빠르게 정하지 못하는 사용자가 현재 상황을 입력하면 조건에 맞는 메뉴를 추천받을 수 있도록 돕습니다. 추천된 메뉴는 랭킹에 집계되어 다른 사용자가 많이 추천받은 메뉴도 확인할 수 있습니다.

### 타겟 사용자

- 점심이나 저녁 메뉴를 고민하는 직장인
- 메뉴 선택이 어려운 학생
- 빠르게 메뉴를 추천받고 싶은 사용자

### 화면 구성

- `Home`: 서비스 소개와 주요 이동 버튼
- `AI 메뉴 추천`: 조건 입력 폼, 추천 결과, 오류/지연 상태 메시지
- `랭킹`: 인기 메뉴 TOP 10, 추천 횟수, 새로고침

### AI 기능

- 입력: 식사 시간, 예산, 인원, 음식 종류, 맵기
- 출력: 추천 메뉴명, 추천 이유, 예상 가격, 함께 먹기 좋은 사이드 메뉴 또는 음료
- 실패 처리: 필수값 누락, 예산/인원 범위 오류, API 오류, 응답 지연 메시지

## 기술 스택

| 구분     | 기술                                |
| -------- | ----------------------------------- |
| Frontend | HTML, CSS, Vanilla JavaScript       |
| Backend  | Python, Vercel Serverless Functions |
| AI       | Gemini Interactions API             |
| Database | Redis, Upstash Redis                |
| Deploy   | Vercel                              |

## 프로젝트 구조

```text
A1-3/
  README.md              # 서비스 소개, 실행 방법, 배포 방법, API 안내 문서
  ai-coding-log.md       # AI 코딩 도구 사용 과정 요약 로그
  service-plan.md        # 서비스 목적, 사용자, 화면 구성, 핵심 기능 기획 문서
  .env.example           # 로컬/배포 환경 변수 예시
  log.png                # AI 코딩 도구 사용 과정 증빙 이미지
  docker-compose.yml     # 로컬 개발용 Redis 컨테이너 설정
  local_server.py        # 정적 파일과 API를 함께 확인하는 로컬 개발 서버
  requirements.txt       # Python API 실행 패키지 목록
  vercel.json            # Vercel 프론트엔드 정적 파일 라우팅 설정
  frontend/              # 프론트엔드 정적 파일
    index.html           # 단일 페이지 화면 구조와 섹션 네비게이션
    css/
      style.css          # 반응형 레이아웃, 폼, 결과 패널, 랭킹 UI 스타일
    js/
      app.js             # 입력 검증, API 요청, 추천 결과 렌더링, 랭킹 조회
    images/
      favicon.svg        # 브라우저 탭에 표시되는 서비스 아이콘
  api/                   # Vercel Python Serverless Functions
    __init__.py          # api 패키지 인식 파일
    recommend.py         # 메뉴 추천 요청 검증 및 Gemini 추천 결과 반환 API
    ranking.py           # 인기 메뉴 TOP 10 조회 API
    lib/                 # 환경 설정, 입력 검증, AI 호출, Redis 저장 공용 모듈
      __init__.py        # lib 패키지 인식 파일
      ai_client.py       # Gemini 호출 및 mock 추천 fallback
      config.py          # APP_PROFILE과 환경 변수 설정
      http.py            # JSON 요청/응답 처리 헬퍼
      ranking_store.py   # Redis/Upstash 랭킹 저장 및 fallback
      validation.py      # 추천 요청 입력값 검증
```

## 환경 변수

API 키와 토큰은 코드에 저장하지 말고 `.env` 또는 Vercel Environment Variables에 등록합니다.

### dev

```bash
APP_PROFILE=dev
REDIS_URL=redis://localhost:6379/0
# 선택: 있으면 실제 Gemini 호출, 없으면 mock 추천 사용
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.1-flash-lite
```

### prod

```bash
APP_PROFILE=prod
GEMINI_API_KEY=발급받은_Gemini_API_KEY
GEMINI_MODEL=gemini-3.1-flash-lite
UPSTASH_REDIS_REST_URL=Upstash_REST_URL
UPSTASH_REDIS_REST_TOKEN=Upstash_REST_TOKEN
```

## 로컬 실행

1. 의존성을 설치합니다.

```bash
python3 -m pip install -r requirements.txt
```

2. 로컬 Redis를 실행합니다.

```bash
docker compose up -d redis
```

3. 로컬 개발 서버를 실행합니다.

```bash
APP_PROFILE=dev REDIS_URL=redis://localhost:6379/0 python3 local_server.py
```

4. 브라우저에서 `http://127.0.0.1:8000`에 접속합니다.

Gemini 키가 없으면 dev profile에서는 mock 추천이 반환됩니다. 배포용 prod profile에서는 `GEMINI_API_KEY`가 필수입니다.

Vercel CLI가 설치되어 있다면 아래 명령으로 Vercel 환경에 더 가깝게 확인할 수 있습니다.

```bash
APP_PROFILE=dev REDIS_URL=redis://localhost:6379/0 vercel dev
```

## 배포 방법

1. GitHub 저장소에 코드를 업로드합니다.
2. Vercel에서 프로젝트 Root Directory를 `A1-3`로 설정합니다.
3. Vercel Environment Variables에 prod 환경 변수를 등록합니다.
4. 배포 후 `/`, `/api/recommend`, `/api/ranking` 동작을 확인합니다.

## API

### `POST /api/recommend`

요청 예시:

```json
{
  "mealTime": "점심",
  "budget": 12000,
  "people": 1,
  "foodType": "한식",
  "spicyLevel": "보통"
}
```

응답 예시:

```json
{
  "result": {
    "menuName": "제육볶음",
    "reason": "점심에 어울리고 예산 안에서 먹기 좋습니다.",
    "estimatedPrice": 10000,
    "sideMenu": "계란찜"
  },
  "profile": "dev"
}
```

### `GET /api/ranking`

응답 예시:

```json
{
  "items": [
    { "menuName": "제육볶음", "count": 12 },
    { "menuName": "김치찌개", "count": 9 }
  ],
  "profile": "dev"
}
```
