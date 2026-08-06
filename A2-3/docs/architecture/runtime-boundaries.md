# 런타임 경계

- 상태: 현재 구현 계약
- 아키텍처 개요: [`README.md`](README.md)
- 데이터 통신: [`data-communication.md`](data-communication.md)
- 로깅 정책: [`../policies/logging.md`](../policies/logging.md)

## 1. 데이터 소유권

| 데이터 | 소유 모듈 | 다른 모듈에 전달하는 형태 |
| --- | --- | --- |
| CLI 옵션 | CLI | Request DTO로 즉시 변환 |
| `RawReview`, `CleanReview` | Models | 읽기 전용 내부 모델 |
| 감정 enum과 신뢰도 | Models | `SentimentResult` |
| SQL row와 connection | Repositories | 내부 모델 또는 Result DTO |
| Gemini SDK 응답 | Clients | 검증된 `SentimentResult` 또는 `InsightResult` |
| pandas `DataFrame` | File I/O | `RawReviewInput` 반복자 또는 `ExportRow` 입력 |
| matplotlib `Figure` | Output | 생성된 파일 경로 |

mutable dictionary는 외부 데이터를 처음 받는 모듈 안에서만 임시로 사용한다. 모듈 경계를 넘기기 전에 필드를 검증하고 이름이 있는 타입으로 바꾼다.

## 2. 트랜잭션 원칙

- Service는 DB 연결, cursor, 트랜잭션 객체를 받지 않는다.
- Repository 공개 저장 메서드가 필요한 SQL 작업을 짧은 트랜잭션으로 묶는다.
- 외부 API 호출과 파일 생성 중에는 SQLite 쓰기 트랜잭션을 열지 않는다.
- 여러 테이블 변경이 반드시 함께 성공해야 하면 하나의 Repository 공개 메서드로 만든다.
- 분석은 성공한 배치만 저장하며 실패 배치는 이전 성공 결과를 롤백하지 않는다.

### 2.1 원자적 저장 동작

| Repository 동작 | 한 트랜잭션에서 처리할 변경 |
| --- | --- |
| raw 저장 또는 upsert | 중복 확인, raw insert/update, 기존 clean·감정 무효화, 모든 집계 인사이트 stale 처리 |
| clean 저장 | clean upsert, raw 상태 갱신, 변경 시 감정 제거와 모든 집계 인사이트 stale 처리 |
| clean 거절 | 기존 clean·감정 제거, raw를 rejected로 변경, 모든 집계 인사이트 stale 처리 |
| 감정 배치 저장 | 검증된 성공 배치 전체 저장 또는 해당 배치 rollback |
| 인사이트 저장 | 범위와 결과, 모델·프롬프트 버전 저장 |

```text
Service
  1. Repository에서 분석 대상 조회
  2. DB 쓰기 트랜잭션 없이 Gemini 호출
  3. 검증된 결과를 Repository 저장 메서드에 전달

Repository.save_sentiment_batch
  1. transaction 시작
  2. 성공 배치 저장
  3. 정상 종료 시 commit, 예외 시 rollback
```

## 3. 오류 경계

외부 기술의 예외는 해당 기술을 소유한 모듈에서 프로젝트 오류로 바꾼다.

| 발생 모듈 | 프로젝트 오류 또는 결과 | Service 판단 | CLI 결과 |
| --- | --- | --- | --- |
| Models·Rules | `ValidationError` | 행 거절 또는 명령 오류 | 사유와 건수 |
| File I/O | `InputFileError` | import 전체 실패 | 종료 코드 `1` |
| Repository | `PersistenceError` | 해당 저장 동작 rollback | 종료 코드 `1` |
| Gemini Client | `AIServiceError` | 재시도 후 배치 스킵 | 일부 성공이면 `2`, 전부 실패면 `1` |
| Output | `OutputWriteError` | 다른 출력 성공 여부와 함께 부분 실패 | 종료 코드 `2` |
| Service | `NotFoundError` | 사용자가 지정한 ID나 범위 없음 | 종료 코드 `1` |
| Service | `StaleInsightError` | dashboard 중단, extract 안내 | 종료 코드 `1` |

프로젝트 오류에는 안전한 사용자 메시지와 원인 코드를 포함한다. SDK 응답, SQL 객체, 비밀정보를 CLI로 전달하지 않는다. 오류 로그는 [`../policies/logging.md`](../policies/logging.md)의 민감정보 규칙을 따른다.

## 4. 테스트 경계

- Models·Rules: 외부 의존성 없는 순수 단위 테스트
- Services: Repository와 Client를 fake 또는 mock으로 대체해 처리 순서와 실패 흐름 테스트
- Repositories: 임시 SQLite로 스키마, 쿼리, 트랜잭션 테스트
- Clients: 실제 네트워크 없이 가짜 Gemini SDK 응답으로 파싱·검증 테스트
- File I/O·Output: 임시 파일로 읽기, 내보내기, 렌더링 테스트
- CLI: Service 호출을 대체해 옵션 파싱, 출력, 종료 코드 테스트
- 종단 테스트: 임시 SQLite와 가짜 Gemini 응답으로 전체 명령 흐름 실행

fake는 공통 추상 클래스를 상속할 필요가 없다. Service가 사용하는 메서드 이름과 내부 데이터 타입만 맞춘다.

## 5. 필수 경계 검증

- CLI에서 `argparse.Namespace`가 Service로 전달되지 않는다.
- Repository 반환값에 `sqlite3.Row`, connection, cursor가 포함되지 않는다.
- Gemini Client가 요청 ID, enum, 신뢰도 범위, 잘못된 응답을 검증한다.
- Chart와 Report가 전달받은 `DashboardData`만 사용한다.
- Repository, Client, File I/O, Output 사이에 직접 import가 없다.
- Gemini 호출 중 SQLite 쓰기 트랜잭션이 열려 있지 않다.

## 6. 변경 규칙

- 원자적 저장 범위가 바뀌면 이 문서와 Repository 통합 테스트를 갱신한다.
- 새 프로젝트 오류를 추가하면 발생 모듈, Service 판단, CLI 종료 코드를 함께 기록한다.
- 계층 간 전달 타입이 바뀌면 [`data-communication.md`](data-communication.md)를 갱신한다.
- 로그 이벤트나 민감정보 처리가 바뀌면 [`../policies/logging.md`](../policies/logging.md)를 갱신한다.
