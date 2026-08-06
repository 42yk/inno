# 모듈 구조와 의존성

- 상태: 현재 구현 구조
- 아키텍처 개요: [`README.md`](README.md)
- 데이터 통신: [`data-communication.md`](data-communication.md)

## 1. CLI

사용자 입력을 Service 호출로 바꾸고 결과를 사람이 읽을 수 있는 형식으로 표시한다.

- argparse 파서와 9개 서브커맨드
- 문자열 옵션의 기본 문법과 상호 배타 조건 검증
- `argparse.Namespace`를 Request DTO로 변환
- Result DTO를 콘솔 메시지로 변환
- 오류를 종료 코드 `0`, `1`, `2`로 매핑

CLI는 Service 공개 함수, DTO·Models·순수 Rules, 설정, Composition 공개 함수만 사용한다. SQL, Repository·Client 구현, pandas, matplotlib을 직접 호출하지 않는다.

## 2. Services

명령 하나를 완료하는 처리 순서를 조정한다.

- `import`, `clean`, `analyze`, `extract`
- `list`, `show`, `stats`, `dashboard`, `export`
- 대상 선택, 배치 분할, 재시도, 부분 성공 판정
- Repository, Client, File I/O, Output 호출 순서 결정
- 파생 데이터 무효화와 stale 처리 요청

Services는 외부 라이브러리의 반환 객체를 직접 다루지 않는다. 구체 모듈을 호출할 수 있지만 내부 SQL, SDK 응답 형식, 렌더링 객체에는 의존하지 않는다.

## 3. Models와 Rules

프로젝트 전체가 공유하는 데이터 의미와 순수 계산을 담당한다.

- `RawReview`, `CleanReview`, `SentimentResult`, `InsightResult`
- 본문·제품명·날짜 정규화와 검증
- 중복 지문 계산
- 분석 완료율, 평균 신뢰도, 별점·감정 일치율 계산
- enum과 값 범위 검증

Models와 Rules는 DB, 네트워크, 파일, CLI에 접근하지 않으며 Python 표준 라이브러리만 사용한다.

## 4. Repositories

SQLite 데이터 접근과 짧은 쓰기 트랜잭션을 담당한다.

- 스키마 생성과 연결 관리
- raw, clean, 감정, 인사이트 조회·저장
- JOIN, 필터, 정렬, 페이지네이션
- `sqlite3.Row`를 내부 모델이나 Result DTO로 변환
- 여러 테이블을 함께 바꾸는 저장 동작의 commit/rollback

원자성이 필요한 동작은 하나의 공개 Repository 메서드로 제공한다. 별도 트랜잭션 조정 계층은 두지 않는다.

## 5. Clients

외부 API 호출과 응답 검증을 담당한다.

- Gemini 클라이언트 생성
- 감정 분석과 인사이트 추출 프롬프트
- 구조화 응답 파싱
- 리뷰 ID, 감정 enum, 신뢰도 범위 검증
- SDK 예외를 프로젝트 오류로 변환

Gemini SDK 응답과 원본 JSON은 Client 밖으로 반환하지 않는다.

## 6. File I/O와 Output

파일 형식과 표현 기술을 담당한다.

- CSV/XLSX를 `RawReviewInput`으로 변환
- 조회 결과를 CSV/XLSX로 기록
- `DashboardData`로 PNG 차트 생성
- 같은 `DashboardData`로 TXT/MD 리포트 생성

pandas `DataFrame`과 matplotlib `Figure`는 해당 모듈 안에서만 사용한다. Output은 DB나 Gemini를 다시 조회하지 않는다.

## 7. 실행 시작점과 로깅 설정

`main.py`는 CLI 실행을 시작한다. `composition.py`는 도움말 파싱 뒤 기본 Repository를 조립하고, 실제 첫 AI 호출 시에만 `.env`의 `GEMINI_API_KEY`와 Gemini Client를 구성한다. CLI는 주입된 의존성을 Service에 전달할 뿐 Repository나 Client 구현을 직접 import하지 않는다. `logging_config.py`는 애플리케이션 시작 시 공통 핸들러와 포맷을 한 번 설정하며 세부 기준은 [`../policies/logging.md`](../policies/logging.md)를 따른다.

## 8. 허용 의존성과 금지 의존성

| 출발 모듈 | 허용 | 금지 |
| --- | --- | --- |
| Models·Rules·DTO | Python 표준 라이브러리와 같은 영역의 타입 | CLI, Services, Repositories, Clients, pandas, matplotlib, Gemini SDK |
| CLI | Services 공개 API, DTO·Models·순수 Rules, 설정, Composition | Repository·Client·Output 구현 직접 import, SQL, Gemini SDK, pandas, matplotlib |
| Composition | 설정, Repository·Client 구현 | 업무 규칙, SQL row 처리, 사용자 출력 |
| Services | DTO, Models·Rules, 필요한 Repository·Client·File I/O·Output 공개 API | CLI, `sqlite3.Row`, Gemini SDK 응답, DataFrame, Figure |
| Repositories | DTO·Models, sqlite3 | CLI, Services, Clients, File I/O, Output |
| Clients | DTO·Models, 담당 SDK | CLI, Services, Repositories, File I/O, Output |
| File I/O·Output | DTO·Models, 담당 파일·렌더링 라이브러리 | CLI, Services, Repositories, Clients |
| `main.py` | 설정과 CLI 실행 시작 함수 | 업무 규칙, SQL, 데이터 변환 |

다음 호출이나 import는 구조 위반이다.

```text
cli -> repositories/clients/output
repositories -> services/clients/output
clients -> repositories/services/output
file_io/output -> repositories/clients/services
models/rules/dto -> 외부 라이브러리 또는 상위 모듈
```

Services가 구체 외부 연동 모듈을 아는 것은 허용한다. 공개 함수의 입출력을 내부 타입으로 제한하여 별도 추상 인터페이스 없이 결합 범위를 통제한다.

## 9. 목표 디렉터리 구조

```text
review_analytics/
├── cli.py
├── composition.py
├── config.py
├── dto.py
├── models.py
├── errors.py
├── rules/
│   ├── validation.py
│   ├── normalization.py
│   ├── duplicate_policy.py
│   └── metrics.py
├── services/
│   ├── ingestion.py
│   ├── cleaning.py
│   ├── sentiment.py
│   ├── extraction.py
│   ├── query.py
│   ├── reporting.py
│   └── exporting.py
├── repositories/
│   ├── database.py
│   ├── reviews.py
│   └── analyses.py
├── clients/
│   └── gemini.py
├── file_io/
│   ├── reader.py
│   └── exporter.py
├── output/
│   ├── charts.py
│   └── reports.py
└── logging_config.py
```

`main.py`는 저장소 루트의 실행 파일이고 `review_analytics.cli`를 호출한다. 구현이 작은 동안 관련 기능은 한 파일에 함께 둘 수 있으며 파일을 나누기 위해 비어 있는 추상 계층을 추가하지 않는다.

## 10. 구조 변경 규칙

- 새 외부 기술은 해당 Client, Repository, File I/O 또는 Output에만 추가한다.
- 동일 역할의 실제 구현이 두 개 이상 필요해질 때만 공통 인터페이스 도입을 검토한다.
- 새 서브커맨드는 Request DTO와 Service 공개 함수 하나에 연결한다.
- 모듈 간 새 데이터가 필요하면 [`data-communication.md`](data-communication.md)를 먼저 갱신한다.
