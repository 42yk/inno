# 과제 요구사항 구현 추적표

이 문서는 `subject.md`의 요구사항이 실제 구현에서 어디에 반영되어 있는지 추적하기 위한 문서입니다.

- 기준 과제 파일: `A1-2/subject.md`
- 구현 기준 파일: `travel_planner.py`, `config.py`, `gemini_client.py`, `kakao_client.py`, `result_writer.py`, `README.md`
- 작성 기준: 2026-07-07 현재 파일의 줄 번호

## 1. 최종 결과물 요구사항

| 과제 요구사항 | 구현 위치 | 구현 및 예외 처리 설명 |
| --- | --- | --- |
| CLI 기반 Python 프로그램: `-date "YYYY-MM-DD"` 필수 입력 | `A1-2/subject.md:17`, `A1-2/subject.md:18`, `A1-2/travel_planner.py:21`, `A1-2/travel_planner.py:24` | `argparse.ArgumentParser`를 사용해 CLI를 구성하고 `-date`, `--date` 옵션을 등록합니다. `required=True`로 필수 입력을 강제합니다. |
| 날짜 형식 검증 | `A1-2/subject.md:43`, `A1-2/travel_planner.py:12`, `A1-2/travel_planner.py:13`, `A1-2/travel_planner.py:15`, `A1-2/travel_planner.py:17` | `parse_date()`가 `datetime.strptime(value, "%Y-%m-%d")`로 날짜 형식을 검증합니다. 형식이 맞지 않으면 `argparse.ArgumentTypeError`를 발생시켜 argparse가 사용법과 에러 메시지를 출력하고 종료합니다. |
| 진행 로그 출력 | `A1-2/subject.md:19`, `A1-2/travel_planner.py:55`, `A1-2/travel_planner.py:65`, `A1-2/travel_planner.py:72` | 실행 단계별로 `[1/3]`, `[2/3]`, `[3/3]` 진행 로그를 출력합니다. 추천 도시, 맛집 검색 결과, 리포트 생성 여부도 함께 출력합니다. |
| 결과 저장 경로 안내 | `A1-2/subject.md:19`, `A1-2/travel_planner.py:91`, `A1-2/travel_planner.py:92`, `A1-2/travel_planner.py:93` | 작업 완료 후 원본 JSON 경로와 Markdown 리포트 경로를 터미널에 출력합니다. |
| `results/` 폴더에 원본 JSON과 최종 Markdown 생성 | `A1-2/subject.md:21`, `A1-2/subject.md:24`, `A1-2/result_writer.py:7`, `A1-2/result_writer.py:11`, `A1-2/result_writer.py:22` | `RESULTS_DIR`을 `A1-2/results`로 지정하고, 저장 전 `mkdir(parents=True, exist_ok=True)`로 폴더를 생성합니다. 원본 JSON은 `{date}_raw.json`, 리포트는 `{date}_travel_plan.md`로 저장합니다. |
| README 작성: 개요, 실행 방법, API 키 설정, 결과물 확인, 보안 주의 | `A1-2/subject.md:26`, `A1-2/subject.md:28`, `A1-2/README.md:1`, `A1-2/README.md:14`, `A1-2/README.md:41`, `A1-2/README.md:106`, `A1-2/README.md:137` | README에 프로그램 개요, 실행 환경, API 키 설정, 실행 방법, 실행 흐름, 결과 파일, 오류 처리, 보안 주의를 분리해 작성했습니다. |

## 2. CLI 인터페이스

| 과제 요구사항 | 구현 위치 | 구현 및 예외 처리 설명 |
| --- | --- | --- |
| argparse 활용 | `A1-2/subject.md:41`, `A1-2/travel_planner.py:3`, `A1-2/travel_planner.py:21`, `A1-2/travel_planner.py:22` | Python 표준 라이브러리 `argparse`를 사용합니다. 별도 외부 패키지는 필요하지 않습니다. |
| 필수 옵션 `-date "YYYY-MM-DD"` | `A1-2/subject.md:42`, `A1-2/travel_planner.py:24`, `A1-2/travel_planner.py:25`, `A1-2/travel_planner.py:26`, `A1-2/travel_planner.py:28` | `-date`와 `--date`를 모두 지원하며, `required=True`로 필수화합니다. |
| 입력값이 잘못되면 사용법 출력 후 종료 | `A1-2/subject.md:43`, `A1-2/travel_planner.py:13`, `A1-2/travel_planner.py:17` | 날짜 형식이 틀리면 `ArgumentTypeError`가 발생합니다. argparse는 자동으로 `usage: ...` 문구와 오류 메시지를 출력하고 비정상 종료 코드로 종료합니다. |

## 3. API 제공자 선택 규칙

| 과제 요구사항 | 구현 위치 | 구현 및 예외 처리 설명 |
| --- | --- | --- |
| LLM API는 Gemini 계열 사용 | `A1-2/subject.md:45`, `A1-2/subject.md:48`, `A1-2/gemini_client.py:10`, `A1-2/gemini_client.py:27` | Gemini Interactions API 엔드포인트 `https://generativelanguage.googleapis.com/v1beta/interactions`로 POST 요청합니다. |
| Gemini 모델은 `gemini-3.1-flash-lite` 기준, `gemini-2.5-flash-lite`도 허용 | `A1-2/config.py:9`, `A1-2/config.py:10`, `A1-2/config.py:55`, `A1-2/config.py:72`, `A1-2/README.md:26`, `A1-2/README.md:29` | 기본 모델은 `gemini-3.1-flash-lite`입니다. 환경변수 `GEMINI_MODEL`로 `gemini-2.5-flash-lite`를 선택할 수 있고, 허용 목록 외 모델은 `ConfigError`로 즉시 종료됩니다. |
| 지도/장소 검색 API는 Kakao Local 사용 | `A1-2/subject.md:49`, `A1-2/subject.md:50`, `A1-2/kakao_client.py:11`, `A1-2/kakao_client.py:37` | Kakao Local 키워드 검색 API `https://dapi.kakao.com/v2/local/search/keyword.json`로 GET 요청합니다. |
| 장소 검색 응답을 JSON으로 받고 최소 필드 확보 | `A1-2/subject.md:52`, `A1-2/subject.md:54`, `A1-2/kakao_client.py:49`, `A1-2/kakao_client.py:51`, `A1-2/kakao_client.py:62`, `A1-2/kakao_client.py:68` | Kakao 응답을 `json.loads()`로 파싱하고 `normalize_place()`에서 `name`, `address`, `category`, `url`, `x`, `y`로 정규화합니다. |

## 4. LLM API 연동 - 1차 추천 JSON

| 과제 요구사항 | 구현 위치 | 구현 및 예외 처리 설명 |
| --- | --- | --- |
| 입력은 사용자가 입력한 `date` | `A1-2/subject.md:57`, `A1-2/travel_planner.py:46`, `A1-2/travel_planner.py:57`, `A1-2/gemini_client.py:175`, `A1-2/gemini_client.py:178` | CLI에서 받은 `date`를 `generate_recommendation(date, settings)`로 전달하고, 프롬프트에 `여행 날짜: {date}`를 포함합니다. |
| 반드시 JSON으로 파싱 가능한 텍스트 생성 | `A1-2/subject.md:58`, `A1-2/gemini_client.py:142`, `A1-2/gemini_client.py:145`, `A1-2/gemini_client.py:146`, `A1-2/gemini_client.py:147`, `A1-2/gemini_client.py:222` | Gemini 요청에 `response_format`을 전달하고 `mime_type`을 `application/json`으로 지정합니다. 시스템 지시문에서도 JSON만 출력하도록 요청합니다. |
| `recommended_city`, `weather`, `events`, `reason` 필수 스키마 | `A1-2/subject.md:59`, `A1-2/subject.md:63`, `A1-2/gemini_client.py:149`, `A1-2/gemini_client.py:170` | `build_recommendation_response_format()`에서 JSON schema의 `properties`와 `required`를 정의합니다. |
| `events`는 문자열 배열 1~3개 | `A1-2/subject.md:62`, `A1-2/gemini_client.py:158`, `A1-2/gemini_client.py:163`, `A1-2/gemini_client.py:207`, `A1-2/gemini_client.py:212` | JSON schema에서 `minItems: 1`, `maxItems: 3`을 설정하고, `validate_recommendation()`에서 한 번 더 검증합니다. |
| JSON 파싱 실패 시 재요청 1회 | `A1-2/subject.md:95`, `A1-2/gemini_client.py:184`, `A1-2/gemini_client.py:233`, `A1-2/gemini_client.py:235`, `A1-2/gemini_client.py:249`, `A1-2/gemini_client.py:251` | `generate_recommendation()`은 최대 2회 시도합니다. 첫 시도 실패 시 `build_retry_prompt()`로 필수 키만 다시 JSON으로 출력하도록 프롬프트를 보정합니다. 두 번째도 실패하면 `GeminiError`를 발생시킵니다. |

## 5. Kakao Local 연동 - 맛집 검색

| 과제 요구사항 | 구현 위치 | 구현 및 예외 처리 설명 |
| --- | --- | --- |
| 입력은 1차 JSON의 `recommended_city` | `A1-2/subject.md:67`, `A1-2/travel_planner.py:62`, `A1-2/travel_planner.py:66`, `A1-2/kakao_client.py:92`, `A1-2/kakao_client.py:93` | Gemini 추천 결과에서 `recommended_city`를 꺼내 `search_restaurants()`에 전달합니다. |
| 해당 도시 기준 맛집 권장 5곳 검색 | `A1-2/subject.md:68`, `A1-2/travel_planner.py:66`, `A1-2/kakao_client.py:25`, `A1-2/kakao_client.py:29`, `A1-2/kakao_client.py:31` | 검색어는 `{city} 맛집`으로 만들고, `size=5`를 전달해 5건 검색을 요청합니다. |
| 음식점 카테고리 기반 검색 | `A1-2/subject.md:50`, `A1-2/kakao_client.py:30` | Kakao Local의 음식점 카테고리 코드인 `FD6`를 `category_group_code`로 전달합니다. |
| Kakao 인증 헤더 사용 | `A1-2/subject.md:75`, `A1-2/subject.md:76`, `A1-2/kakao_client.py:41`, `A1-2/kakao_client.py:44` | `Authorization: KakaoAK {settings.kakao_rest_api_key}` 헤더로 REST API 키를 전달합니다. |
| 맛집 아이템 최소 필드 | `A1-2/subject.md:69`, `A1-2/subject.md:74`, `A1-2/kakao_client.py:62`, `A1-2/kakao_client.py:68`, `A1-2/kakao_client.py:80` | Kakao 응답을 `name`, `address`, `category`, `url`, `x`, `y`로 정규화합니다. 좌표는 문자열에서 `float`로 변환 가능한 경우만 포함합니다. |
| 0건이면 중단하지 않고 데이터 없음 처리 | `A1-2/subject.md:78`, `A1-2/kakao_client.py:117`, `A1-2/kakao_client.py:120`, `A1-2/travel_planner.py:69`, `A1-2/travel_planner.py:70` | `documents`가 비어 있거나 리스트가 아니면 `EMPTY_RESULT`를 errors에 추가하고 빈 리스트를 반환합니다. CLI는 맛집 데이터 없음 메시지를 출력한 뒤 리포트 생성을 계속합니다. |
| 인증/네트워크/쿼터/파싱 실패 처리 | `A1-2/subject.md:91`, `A1-2/subject.md:94`, `A1-2/kakao_client.py:83`, `A1-2/kakao_client.py:103`, `A1-2/kakao_client.py:115` | HTTP 401/403은 `AUTH_ERROR`, 429는 `QUOTA_ERROR`, 나머지는 `HTTP_ERROR`로 분류합니다. 네트워크 오류, 타임아웃, JSON 파싱 실패도 errors에 기록하고 빈 리스트를 반환합니다. |

## 6. LLM API 연동 - 최종 리포트 생성

| 과제 요구사항 | 구현 위치 | 구현 및 예외 처리 설명 |
| --- | --- | --- |
| 입력은 1차 추천 JSON + 맛집 목록 | `A1-2/subject.md:81`, `A1-2/gemini_client.py:256`, `A1-2/gemini_client.py:258`, `A1-2/gemini_client.py:262`, `A1-2/travel_planner.py:73`, `A1-2/travel_planner.py:74` | `build_report_prompt()`가 `date`, `recommendation`, `restaurants`, `errors`를 JSON 문자열로 직렬화해 Gemini 리포트 생성 프롬프트에 넣습니다. |
| 출력은 Markdown 텍스트 | `A1-2/subject.md:82`, `A1-2/gemini_client.py:293`, `A1-2/gemini_client.py:314`, `A1-2/result_writer.py:22`, `A1-2/result_writer.py:25` | Gemini에서 받은 Markdown 문자열을 `{date}_travel_plan.md` 파일로 저장합니다. |
| 추천 지역, 추천 이유, 날씨, 행사, 맛집, 1일 일정 포함 | `A1-2/subject.md:83`, `A1-2/subject.md:88`, `A1-2/gemini_client.py:11`, `A1-2/gemini_client.py:19`, `A1-2/gemini_client.py:301`, `A1-2/gemini_client.py:305` | `REQUIRED_REPORT_SECTIONS`에 필수 섹션을 정의하고 시스템 지시문에서도 모든 섹션을 포함하도록 요청합니다. |
| 리포트 필수 섹션 누락 시 보정 | `A1-2/gemini_client.py:271`, `A1-2/gemini_client.py:280`, `A1-2/gemini_client.py:310`, `A1-2/gemini_client.py:326` | `find_missing_report_sections()`로 누락 섹션을 찾고, 한 번 더 리포트 전체 재작성을 요청합니다. 재시도 후에도 누락되면 `GeminiError`를 발생시킵니다. |
| 맛집 0건이면 데이터 없음 표기 | `A1-2/subject.md:87`, `A1-2/gemini_client.py:264`, `A1-2/gemini_client.py:266`, `A1-2/gemini_client.py:340`, `A1-2/gemini_client.py:341` | Gemini 프롬프트에서 맛집 목록이 비어 있으면 데이터 없음이라고 쓰도록 지시합니다. Gemini 리포트 생성이 실패해 fallback을 쓰는 경우에도 맛집 섹션에 `데이터 없음`이 들어갑니다. |
| 리포트 생성 실패 시에도 결과물 유지 | `A1-2/travel_planner.py:76`, `A1-2/travel_planner.py:84`, `A1-2/gemini_client.py:329`, `A1-2/gemini_client.py:375` | 최종 리포트 생성이 실패하면 errors에 `REPORT_GENERATION_ERROR`를 추가하고 로컬 fallback Markdown을 생성해 저장합니다. |

## 7. 에러 처리와 errors 목록

| 과제 요구사항 | 구현 위치 | 구현 및 예외 처리 설명 |
| --- | --- | --- |
| API 호출/파싱 오류를 try-except로 처리 | `A1-2/subject.md:91`, `A1-2/gemini_client.py:57`, `A1-2/gemini_client.py:68`, `A1-2/kakao_client.py:101`, `A1-2/travel_planner.py:47`, `A1-2/travel_planner.py:56` | Gemini, Kakao, 설정 로딩, 리포트 생성 단계에서 예외를 처리합니다. |
| API 키 미설정 시 즉시 종료 + 설정 방법 안내 | `A1-2/subject.md:93`, `A1-2/config.py:57`, `A1-2/config.py:65`, `A1-2/config.py:69`, `A1-2/travel_planner.py:47`, `A1-2/travel_planner.py:51` | `load_settings()`가 누락된 키를 찾으면 `ConfigError`를 발생시키고 설정 예시를 메시지에 포함합니다. `run()`은 이를 출력하고 `return 1`로 종료합니다. |
| 지도/장소 API 실패 시 리포트 생성 계속 | `A1-2/subject.md:94`, `A1-2/kakao_client.py:103`, `A1-2/kakao_client.py:115`, `A1-2/travel_planner.py:66`, `A1-2/travel_planner.py:72` | Kakao 오류는 `search_restaurants()`에서 errors에 기록 후 빈 리스트를 반환합니다. `travel_planner.py`는 빈 리스트여도 최종 리포트 생성 단계로 진행합니다. |
| LLM JSON 파싱 실패 시 재시도 1회 | `A1-2/subject.md:95`, `A1-2/gemini_client.py:233`, `A1-2/gemini_client.py:249`, `A1-2/gemini_client.py:251` | 1차 추천 JSON은 최대 2회만 시도합니다. 두 번째 실패 후에는 `GeminiError`를 발생시켜 초기 추천 실패로 종료합니다. |
| 오류 목록 관리 | `A1-2/subject.md:96`, `A1-2/travel_planner.py:53`, `A1-2/kakao_client.py:14`, `A1-2/kakao_client.py:21`, `A1-2/travel_planner.py:77`, `A1-2/travel_planner.py:82` | `errors` 리스트를 전체 흐름에서 공유합니다. Kakao 오류와 리포트 생성 오류는 `step`, `type`, `message` 형태로 기록됩니다. |
| 리포트에 errors 섹션 포함 | `A1-2/subject.md:96`, `A1-2/gemini_client.py:19`, `A1-2/gemini_client.py:373`, `A1-2/gemini_client.py:374` | 필수 리포트 섹션에 `## 오류 요약(errors)`를 포함하고, fallback 리포트에도 오류 목록을 출력합니다. |

## 8. API 키 관리와 보안

| 과제 요구사항 | 구현 위치 | 구현 및 예외 처리 설명 |
| --- | --- | --- |
| API 키를 코드에 직접 작성하지 않음 | `A1-2/subject.md:99`, `A1-2/config.py:53`, `A1-2/config.py:54`, `A1-2/kakao_client.py:44`, `A1-2/gemini_client.py:52` | 키 값은 환경변수에서 읽은 `Settings` 객체를 통해 주입됩니다. 코드에는 실제 키 문자열이 없습니다. |
| 환경변수 또는 `.env` 파일에서 키 읽기 | `A1-2/subject.md:100`, `A1-2/config.py:32`, `A1-2/config.py:46`, `A1-2/config.py:50`, `A1-2/.env.example:1`, `A1-2/.env.example:7` | `load_env_file()`이 `A1-2/.env`를 읽어 환경변수에 반영하고, 이후 `load_settings()`가 `GEMINI_API_KEY`, `KAKAO_REST_API_KEY`, `GEMINI_MODEL`을 읽습니다. |
| 제출물/README/로그/결과 파일에 키 노출 방지 | `A1-2/subject.md:101`, `A1-2/README.md:39`, `A1-2/README.md:137`, `A1-2/README.md:141`, `.gitignore:4` | README에 키 노출 금지를 명시하고, `.gitignore`에 `.env`가 포함되어 실제 키 파일이 Git에 올라가지 않도록 했습니다. |

## 9. 결과 저장

| 과제 요구사항 | 구현 위치 | 구현 및 예외 처리 설명 |
| --- | --- | --- |
| `results/` 폴더 생성 | `A1-2/subject.md:103`, `A1-2/subject.md:104`, `A1-2/result_writer.py:8`, `A1-2/result_writer.py:13`, `A1-2/result_writer.py:24` | JSON과 Markdown 저장 시 각각 `RESULTS_DIR.mkdir(parents=True, exist_ok=True)`를 호출합니다. |
| 실행 날짜 기준 파일명 | `A1-2/subject.md:104`, `A1-2/result_writer.py:14`, `A1-2/result_writer.py:25` | 입력받은 `date`를 파일명 앞에 붙여 `{date}_raw.json`, `{date}_travel_plan.md`로 저장합니다. |
| 원본 JSON에 추천 JSON, 맛집 검색 결과, 오류 요약 포함 | `A1-2/subject.md:105`, `A1-2/subject.md:108`, `A1-2/travel_planner.py:35`, `A1-2/travel_planner.py:42`, `A1-2/travel_planner.py:87` | `build_raw_data()`가 `date`, `recommendation`, `restaurants`, `errors`를 하나의 dict로 구성합니다. |
| 최종 리포트는 `.md` 파일로 저장 | `A1-2/subject.md:109`, `A1-2/result_writer.py:22`, `A1-2/result_writer.py:25`, `A1-2/result_writer.py:26` | `save_report()`가 Markdown 문자열을 `{date}_travel_plan.md`에 UTF-8로 저장합니다. |

## 10. 개발 환경과 제약 사항

| 과제 요구사항 | 구현 위치 | 구현 및 예외 처리 설명 |
| --- | --- | --- |
| Python 3.10 이상, 터미널 실행 | `A1-2/subject.md:122`, `A1-2/subject.md:125`, `A1-2/README.md:7`, `A1-2/README.md:10`, `A1-2/README.md:41` | README에 Python 3.10 이상과 터미널 실행 방법을 안내했습니다. 구현은 표준 라이브러리만 사용합니다. |
| 웹 UI 불필요 | `A1-2/subject.md:125`, `A1-2/travel_planner.py:21`, `A1-2/README.md:41` | 구현은 CLI 진입점만 제공합니다. |
| 보너스 과제는 선택 | `A1-2/subject.md:111`, `A1-2/subject.md:118` | 복수 지역 추천과 결과 캐싱은 선택 과제이므로 현재 구현 범위에는 포함하지 않았습니다. |

## 11. README 요구사항 추적

| README 요구사항 | 구현 위치 | 설명 |
| --- | --- | --- |
| 프로그램 개요 | `A1-2/README.md:1`, `A1-2/README.md:5` | Gemini API와 Kakao Local API를 조합하는 CLI임을 설명합니다. |
| 실행 방법 | `A1-2/README.md:41`, `A1-2/README.md:53` | `-date`, `--date` 실행 예시를 제공합니다. |
| API 키 설정 방법 | `A1-2/README.md:14`, `A1-2/README.md:37` | `.env`와 환경변수 설정 예시를 제공합니다. |
| 결과물 확인 방법 | `A1-2/README.md:101`, `A1-2/README.md:111` | 저장 경로와 결과 파일명을 설명합니다. |
| API 키 유출 주의 사항 | `A1-2/README.md:39`, `A1-2/README.md:137`, `A1-2/README.md:141` | `.env`를 Git에 올리지 않고 키를 코드/README/로그/결과 파일에 포함하지 말라고 안내합니다. |
| 흐름 시퀀스 다이어그램 | `A1-2/README.md:55`, `A1-2/README.md:91` | CLI, 설정, Gemini, Kakao, 결과 저장소 사이의 흐름을 Mermaid 시퀀스 다이어그램으로 표현했습니다. |

## 12. 주요 실패 케이스 처리 방식

| 실패 케이스 | 구현 위치 | 처리 방식 |
| --- | --- | --- |
| `-date` 누락 | `A1-2/travel_planner.py:24`, `A1-2/travel_planner.py:28` | `required=True` 때문에 argparse가 사용법과 누락 오류를 출력하고 종료합니다. |
| 날짜 형식 오류 | `A1-2/travel_planner.py:13`, `A1-2/travel_planner.py:17` | `YYYY-MM-DD` 형식이 아니면 `ArgumentTypeError`로 처리되어 사용법과 오류 메시지가 출력됩니다. |
| Gemini/Kakao API 키 누락 | `A1-2/config.py:57`, `A1-2/config.py:70`, `A1-2/travel_planner.py:47`, `A1-2/travel_planner.py:51` | 누락 키 이름과 설정 방법을 출력한 뒤 종료 코드 `1`로 종료합니다. |
| 허용되지 않은 Gemini 모델 | `A1-2/config.py:72`, `A1-2/config.py:74` | 허용 모델 목록을 안내하는 `ConfigError`를 발생시키고 종료합니다. |
| Gemini HTTP/네트워크/타임아웃 오류 | `A1-2/gemini_client.py:57`, `A1-2/gemini_client.py:66` | `GeminiError`로 변환합니다. 1차 추천 단계의 Gemini 오류는 프로그램 종료, 최종 리포트 단계의 Gemini 오류는 fallback 리포트 저장으로 처리합니다. |
| Kakao HTTP 401/403 | `A1-2/kakao_client.py:83`, `A1-2/kakao_client.py:86`, `A1-2/kakao_client.py:103`, `A1-2/kakao_client.py:106` | `AUTH_ERROR`로 errors에 기록하고 빈 맛집 목록으로 계속 진행합니다. |
| Kakao HTTP 429 | `A1-2/kakao_client.py:87`, `A1-2/kakao_client.py:88` | `QUOTA_ERROR`로 errors에 기록하고 빈 맛집 목록으로 계속 진행합니다. |
| Kakao 검색 결과 0건 | `A1-2/kakao_client.py:117`, `A1-2/kakao_client.py:120` | `EMPTY_RESULT`를 errors에 기록하고 빈 맛집 목록으로 계속 진행합니다. |
| 최종 리포트 필수 섹션 누락 | `A1-2/gemini_client.py:271`, `A1-2/gemini_client.py:323`, `A1-2/gemini_client.py:326`, `A1-2/travel_planner.py:76`, `A1-2/travel_planner.py:85` | Gemini에 1회 재작성을 요청합니다. 그래도 누락되면 `GeminiError`로 처리하고 fallback Markdown을 저장합니다. |

