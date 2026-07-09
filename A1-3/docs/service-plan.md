# 서비스 기획서

## 서비스명

오늘 뭐 먹지?

## 서비스 목적

사용자가 식사 시간, 예산, 인원, 음식 종류, 맵기를 입력하면 AI가 조건에 맞는 메뉴를 추천하는 웹 서비스입니다. 추천된 메뉴는 Redis에 집계되어 인기 메뉴 랭킹으로 확인할 수 있습니다.

## 타겟 사용자

- 점심이나 저녁 메뉴를 고민하는 직장인
- 메뉴 선택이 어려운 학생
- 빠르게 메뉴를 추천받고 싶은 사용자

## 페이지 구성

단일 페이지 안에서 헤더는 고정하고, 상단 메뉴와 버튼으로 본문 HTML fragment를 fetch해 화면만 전환합니다.

| 화면 | 목적 | 주요 내용 |
| --- | --- | --- |
| Home | 서비스 소개 및 진입 | Hero, 서비스 설명, 추천/랭킹 이동 버튼 |
| AI 메뉴 추천 | 조건 기반 메뉴 추천 | 입력 폼, 추천 결과, 오류/지연 메시지 |
| 랭킹 | 인기 메뉴 확인 | TOP 10 메뉴, 추천 횟수, 새로고침 |

## 입력 항목

| 항목 | 입력 방식 | 값 |
| --- | --- | --- |
| 식사 시간 | Select | 아침, 점심, 저녁, 야식 |
| 예산 | Number | 1,000원 이상 100,000원 이하 |
| 인원 | Number | 1명 이상 20명 이하 |
| 음식 종류 | Select | 한식, 중식, 일식, 양식, 분식, 패스트푸드, 상관없음 |
| 맵기 | Select | 안 매움, 보통, 매움 |

## AI 기능

### 입력

- 식사 시간
- 예산
- 인원
- 음식 종류
- 맵기

### 출력

- 메뉴명
- 추천 이유
- 예상 가격
- 함께 먹으면 좋은 사이드 메뉴 또는 음료

## 실패 처리 기준

| 상황 | 메시지 |
| --- | --- |
| 필수값 누락 | 필수 항목을 입력해주세요. |
| 예산 형식 오류 | 예산은 숫자로 입력해주세요. |
| 예산 범위 오류 | 예산은 1,000원 이상 입력해주세요. |
| 인원 범위 오류 | 인원은 1명 이상 입력해주세요. |
| API 오류 | 추천 결과를 가져오지 못했습니다. 잠시 후 다시 시도해주세요. |
| 응답 지연 | AI가 메뉴를 추천하고 있습니다... |

## 시스템 구성

```text
Browser
  │
  ▼
frontend/index.html + views/*.html + css/style.css + js/app.js
  │
  ├── fetch("/api/recommend")
  └── fetch("/api/ranking")
        │
        ▼
Vercel Serverless Functions (Python)
  │
  ├── Gemini API
  └── Redis
        ├── dev: Docker Redis
        └── prod: Upstash Redis
```

## API

| Method | URL | 설명 |
| --- | --- | --- |
| POST | `/api/recommend` | AI 메뉴 추천 및 추천 횟수 증가 |
| GET | `/api/ranking` | 인기 메뉴 TOP 10 조회 |

## 환경 프로필

| 프로필 | 목적 | AI | Redis |
| --- | --- | --- | --- |
| dev | 로컬 개발 | Gemini 키가 있으면 실제 호출, 없으면 mock 추천 | Docker Redis |
| prod | Vercel 배포 | Gemini API 필수 | Upstash Redis |

## Redis 구조

- 자료구조: Sorted Set
- Key: `menu:ranking`

추천 발생 시:

```text
ZINCRBY menu:ranking 1 "제육볶음"
```

랭킹 조회 시:

```text
ZRANGE menu:ranking 0 9 REV WITHSCORES
```
