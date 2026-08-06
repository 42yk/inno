# 로깅 정책

- 상태: 현재 구현 정책
- 적용 범위: CLI, Services, Repositories, Clients, File I/O, Output
- 아키텍처 런타임 경계: [`../architecture/runtime-boundaries.md`](../architecture/runtime-boundaries.md)

## 1. 목적

로그는 명령의 진행 상태와 실패 원인을 운영자와 개발자가 확인할 수 있게 하되 API 키, 리뷰 원문, AI 요청·응답 같은 민감 데이터를 남기지 않는다. 사용자 출력과 진단 로그의 의미가 충돌하지 않도록 공통 레벨과 이벤트 이름을 사용한다.

## 2. 설정

| 항목 | 값 |
| --- | --- |
| 구현 | Python 표준 `logging` |
| 기본 레벨 | `INFO` |
| 설정 키 | `log_level`, `log_file` |
| 기본 파일 | `logs/app.log` |
| 인코딩 | UTF-8 |
| 파일 핸들러 | `RotatingFileHandler` |
| 회전 크기 | 5 MiB |
| 보관 파일 | 현재 파일 외 백업 3개 |

`logging_config.py`가 애플리케이션 시작 시 한 번만 설정한다. 로그 디렉터리가 없으면 생성하며 중복 핸들러를 추가하지 않는다. `logs/`와 회전 파일은 Git에 포함하지 않는다.

## 3. 출력 대상과 포맷

- 콘솔과 회전 파일에 같은 최소 레벨을 적용한다.
- 기본 포맷은 한 줄의 key-value 텍스트다.
- 시각은 타임존 오프셋을 포함한 ISO 8601 형식으로 기록한다.
- logger 이름은 `review_analytics.<module>` 형식을 사용한다.

```text
2026-08-06T14:23:10+09:00 INFO review_analytics.services.sentiment event=analysis.batch.completed command=analyze batch=2 succeeded=20 failed=0
```

필드 순서는 `timestamp`, `level`, `logger`, `event`, 공통 컨텍스트, 이벤트별 필드 순으로 유지한다.

## 4. 로그 레벨

| 레벨 | 사용 기준 | 예시 |
| --- | --- | --- |
| `INFO` | 정상 시작·완료·진행 집계와 예상된 분기 | 명령 시작/완료, 중복 skip, 출력 파일 생성 |
| `WARNING` | 명령은 계속되지만 확인이 필요한 항목 | clean 거절, AI 재시도, 최종 배치 스킵, 폰트 fallback |
| `ERROR` | 명령을 계속할 수 없는 오류 | 설정, 파일, DB, 전체 API, 출력 실패 |

중복 정책의 `skip`은 정상 동작이므로 `INFO`다. 개별 raw의 정제 거절은 원문을 보존한 채 계속하더라도 데이터 품질 확인이 필요하므로 `WARNING`이다.

## 5. 필수 이벤트

### 5.1 명령 공통

| 이벤트 | 레벨 | 필수 필드 |
| --- | --- | --- |
| `command.started` | INFO | `command` |
| `command.completed` | INFO | `command`, `processed`, `succeeded`, `skipped`, `failed`, `duration_ms` |
| `command.partial` | WARNING | 완료 필드와 `error_code` |
| `command.failed` | ERROR | `command`, `error_code`, `duration_ms` |

### 5.2 데이터와 AI

| 이벤트 | 레벨 | 필수 필드 |
| --- | --- | --- |
| `import.file.loaded` | INFO | `file_name`, `rows` |
| `duplicate.skipped` | INFO | `review_id` 또는 `fingerprint_prefix` |
| `import.row.failed` | WARNING | `error_code` |
| `clean.rejected` | WARNING | `review_id`, `reason_code` |
| `clean.row.failed` | WARNING | `review_id`, `error_code` |
| `analysis.batch.completed` | INFO | `batch`, `succeeded`, `failed` |
| `ai.retry` | WARNING | `operation`, `attempt`, `error_code` |
| `ai.batch.skipped` | WARNING | `operation`, `batch`, `error_code` |
| `insight.saved` | INFO | `scope_hash_prefix`, `review_count` |

### 5.3 출력

| 이벤트 | 레벨 | 필수 필드 |
| --- | --- | --- |
| `output.created` | INFO | `output_type`, `file_name` |
| `output.failed` | ERROR | `output_type`, `file_name`, `error_code` |

행별 성공을 모두 기록하지 않고 건수로 집계한다. 경고와 오류처럼 조치가 필요한 항목만 ID 단위로 기록한다.

## 6. 허용·금지 데이터

### 6.1 허용

- 명령 이름, 내부 리뷰 ID, 배치 번호
- 처리·성공·스킵·실패 건수
- 파일의 basename과 출력 형식
- 해시나 scope hash의 앞 8자
- 안전한 reason/error 코드
- 소요 시간

### 6.2 금지

- `GEMINI_API_KEY`와 모든 비밀정보
- 전체 리뷰 본문과 제품명 원문
- Gemini 프롬프트, 원본 요청, 원본 응답
- `.env` 내용과 전체 설정 덤프
- pandas 행, SQLite row, 전체 DTO 직렬화
- 사용자 입력이 포함될 수 있는 예외 객체의 무검증 `repr`

필요한 식별자는 내부 ID 또는 짧은 해시로 남긴다. 파일 경로는 전체 절대 경로 대신 basename을 기본으로 사용한다.

## 7. 오류 기록

- 외부 예외는 소유 모듈에서 프로젝트 오류 코드로 변환한 뒤 기록한다.
- 사용자 데이터가 포함될 가능성이 있는 원본 예외 메시지는 기록하지 않는다.
- 재시도 가능한 오류는 각 재시도를 `WARNING`으로 기록하고 최종 결과를 별도 이벤트로 남긴다.
- 부분 성공은 `command.partial`, 치명적 실패는 `command.failed`로 끝낸다.
- 동일 오류를 여러 계층에서 반복 기록하지 않는다. 오류를 프로젝트 오류로 처음 변환하는 모듈이 원인 이벤트를 남기고 CLI는 최종 명령 결과만 기록한다.

## 8. 테스트 기준

- 기본 설정에서 콘솔과 회전 파일 핸들러가 각각 하나만 생성된다.
- 로그 파일이 5 MiB를 넘으면 회전하고 백업을 최대 3개 유지한다.
- 설정된 레벨 아래 이벤트가 출력되지 않는다.
- 중복 skip은 INFO, clean 거절과 AI 재시도는 WARNING, 치명적 오류는 ERROR다.
- API 키, 전체 리뷰 본문, 프롬프트, Gemini 원본 응답이 로그에 포함되지 않는다.
- 같은 오류가 모듈과 CLI에서 중복 기록되지 않는다.
- 테스트는 임시 로그 디렉터리를 사용하고 실제 Gemini를 호출하지 않는다.

## 9. 변경 규칙

- 새 이벤트는 소유 모듈, 레벨, 필수 필드, 민감정보 여부를 이 문서에 추가한 뒤 구현한다.
- 포맷이나 회전 기준 변경은 `logging_config.py` 테스트와 함께 갱신한다.
- 오류 코드 변경은 [`../architecture/runtime-boundaries.md`](../architecture/runtime-boundaries.md)와 함께 검토한다.
- 설계 기록의 로깅 내용이 바뀌면 이 정책을 같은 작업에서 갱신한다.
