# 설정 정책

- 상태: 현재 구현 정책
- 관련 계약: [`cli-commands.md`](cli-commands.md), [`../architecture/storage-schema.md`](../architecture/storage-schema.md), [`logging.md`](logging.md)

## 파일과 경로 해석

명시적으로 선택한 설정 `Path`에 JSON 객체가 반드시 존재해야 한다. 파일이 없거나 읽을 수 없거나, 형식이 잘못되었거나 JSON 객체가 아니어도 애플리케이션은 묵시적으로 다른 설정을 사용하지 않는다. 상대 경로인 `database_path`, `log_file`, `output_directory`는 불러온 `config.json`의 부모 디렉터리를 기준으로 해석하고, 절대 경로는 그대로 유지한다. 설정을 불러오는 과정에서는 파일이나 디렉터리를 생성하지 않는다.

알 수 없는 키는 거부하고, 누락된 키에는 기본값을 사용한다. JSON 숫자 값은 문자열이나 불리언이 아닌 숫자여야 한다. 경로와 텍스트 설정은 빈 문자열이 아니어야 한다. `.env.sample`에는 `GEMINI_API_KEY=replace_with_your_key`만 포함하고 `.env`는 Git에서 제외한다. API 키는 `analyze`와 `extract`에서만 필요하다.

## `config.json`

| 키 | JSON 타입 | 기본값 | 검증과 용도 |
| --- | --- | --- | --- |
| `database_path` | 문자열 | `data/reviews.db` | 빈 문자열이 아니어야 하며 위의 기준으로 경로를 해석한다. |
| `gemini_model` | 문자열 | `gemini-3.1-flash-lite` | 빈 문자열이 아닌 모델 ID여야 한다. |
| `duplicate_policy` | 문자열 | `skip` | `skip` 또는 `upsert`만 허용하며, `import` 명령에서 실행별로 덮어쓸 수 있다. |
| `minimum_review_length` | 정수 | `5` | 0보다 커야 한다. |
| `analysis_batch_size` | 정수 | `20` | 0보다 커야 한다. |
| `extraction_chunk_characters` | 정수 | `50000` | 0보다 커야 한다. |
| `ai_retry_count` | 정수 | `2` | 0 이상이어야 하며, 초기 요청 실패 후 재시도 횟수를 뜻한다. |
| `default_page_size` | 정수 | `20` | 0보다 크고 `maximum_page_size` 이하여야 한다. |
| `maximum_page_size` | 정수 | `100` | `default_page_size` 이상이어야 한다. |
| `chart_font_candidates` | 문자열 배열 | `["AppleGothic", "Malgun Gothic", "NanumGothic"]` | 빈 배열이 아니어야 하고 모든 값이 빈 문자열이 아니어야 하며, 주어진 순서대로 사용한다. |
| `log_level` | 문자열 | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` 중 하나여야 한다. |
| `log_file` | 문자열 | `logs/app.log` | 빈 문자열이 아니어야 하며 위의 기준으로 경로를 해석한다. |
| `output_directory` | 문자열 | `output` | 빈 문자열이 아니어야 하며 위의 기준으로 경로를 해석한다. |

저장소에 포함된 [`../../config.json`](../../config.json)에는 모든 기본값이 정의되어 있다. `AppConfig`는 불변 객체이며, 해석을 마친 경로는 `Path` 인스턴스이고 폰트 목록은 튜플이다.

## 오류

`ConfigurationError`는 다음의 안정적인 원인 코드를 사용한다. `CONFIG_FILE_NOT_FOUND`(파일 없음), `CONFIG_FILE_READ_ERROR`(파일을 읽을 수 없음), `INVALID_CONFIG_JSON`(잘못된 JSON 또는 객체), `UNKNOWN_CONFIG_KEY`, `INVALID_CONFIG_TYPE`, `INVALID_CONFIG_VALUE`, `DATABASE_DIRECTORY_FAILED`(데이터베이스 부모 디렉터리를 생성할 수 없음), `LOG_SETUP_FAILED`(로그 파일을 설정할 수 없음), `GEMINI_API_KEY_REQUIRED`(AI 명령에 필요한 키가 없음). 오류 메시지에는 키 경로와 원인 코드만 포함하며, 키 값이나 임의의 파일 내용은 절대 포함하지 않는다.
