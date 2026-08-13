# 에이전트 작업 지침

- 적용 범위: 저장소의 코드, 테스트, 설정, 문서 변경
- 짧은 진입점: [`../AGENTS.md`](../AGENTS.md)
- 문서 지도: [`README.md`](README.md)

이 문서는 저장소에서 작업하는 에이전트와 개발자가 따라야 할 상세 실행 규칙의 단일 원본이다. 아키텍처나 정책의 상세 설명을 다시 정의하지 않고 해당 원본 문서에 연결한다.

## 1. 작업 전 준비

1. 현재 파일과 Git 상태를 확인하고 사용자 변경을 보존한다.
2. [`README.md`](README.md)에서 작업 종류에 맞는 문서를 선택해 읽는다.
3. 범위는 [`../subject.md`](../subject.md)와 [승인된 설계](superpowers/specs/2026-08-05-review-sentiment-cli-design.md)로 확인한다.
4. 보너스 기능은 사용자가 별도로 승인한 경우에만 범위에 넣는다.
5. 관련 문서에 정의되지 않은 결정이 필요하면 추측으로 범위를 넓히지 않는다.

모든 문서를 한꺼번에 읽지 않는다. 현재 작업에 필요한 문서만 점진적으로 확인한다.

## 2. 아키텍처 규칙

이 프로젝트는 단순 레이어드 모놀리스다. 상세 구조는 [`architecture/README.md`](architecture/README.md)와 연결된 아키텍처 문서를 따른다.

1. CLI는 Service 공개 API와 DTO만 호출한다.
2. Service는 처리 순서를 조정하며 필요한 Repository, Client, File I/O, Output의 공개 API를 호출할 수 있다.
3. Models·Rules·DTO는 상위 모듈과 외부 라이브러리를 import하지 않는다.
4. Repository, Client, File I/O, Output은 서로 직접 호출하거나 Service와 CLI를 import하지 않는다.
5. `sqlite3.Row`, Gemini SDK 응답, pandas DataFrame, matplotlib Figure는 이를 만든 모듈 안에서 내부 타입으로 변환한다.
6. 같은 역할의 실제 구현이 하나뿐이면 별도 추상 인터페이스를 만들지 않는다.
7. 원자성이 필요한 여러 DB 변경은 하나의 Repository 공개 메서드와 내부 트랜잭션으로 처리한다.
8. 새 외부 기술은 담당 Repository, Client, File I/O 또는 Output 모듈에만 추가한다.

## 3. 계층 간 데이터 규칙

상세 타입과 모듈 API는 [`architecture/data-communication.md`](architecture/data-communication.md), 오류와 트랜잭션은 [`architecture/runtime-boundaries.md`](architecture/runtime-boundaries.md)를 따른다.

- 계층 경계는 이름이 있는 Request DTO, Result DTO, 내부 모델로 통과한다.
- `argparse.Namespace`, `sqlite3.Row`, Gemini SDK 응답, pandas DataFrame, matplotlib Figure를 소유 모듈 밖으로 반환하지 않는다.
- CLI 입력은 즉시 Request DTO로 변환한다.
- 외부 응답은 해당 Repository, Client, File I/O, Output에서 검증된 내부 타입으로 변환한다.
- SQL 열 이름과 정렬 방향은 허용 목록의 enum으로 매핑한다.
- mutable dictionary는 외부 경계 내부에서만 임시로 사용한다.
- 계층 간 새 필드는 생성·검증 책임을 정하고 통신 계약을 먼저 갱신한 뒤 구현한다.

## 4. 데이터 불변 조건

- `import`는 raw만 저장하고 자동 정제하지 않는다.
- `clean`만 clean 데이터를 생성한다.
- raw 입력 원문은 보존하고 파생 데이터는 다시 만들 수 있어야 한다.
- 중복 지문은 정규화 본문·제품명·작성일로 계산한다.
- upsert는 raw ID를 유지하고 clean·감정 결과를 무효화하며 인사이트를 stale 처리한다.
- Gemini 감정은 `positive|negative|neutral`, 신뢰도는 `0.0..1.0`이다.
- 성공한 dashboard에는 같은 필터 범위의 최신 유효 인사이트가 반드시 포함된다.
- Gemini 호출 중에는 SQLite 쓰기 트랜잭션을 열지 않는다.

중복 세부 규칙은 [`policies/duplicate-review-policy.md`](policies/duplicate-review-policy.md), 명령별 상태 변화는 [`data-flow.md`](data-flow.md)를 따른다.
필드별 raw 보존 범위와 clean 정제·거절·재처리 계약은 [`policies/raw-clean-data.md`](policies/raw-clean-data.md)를 따른다.

## 5. 설정과 비밀정보

- 모델 기본값은 `gemini-3.1-flash-lite`이며 `config.json`에서 읽는다.
- API 키는 `.env`의 `GEMINI_API_KEY`에서 읽는다.
- `.env`, 생성 DB, 로그, output 파일을 커밋하지 않는다.
- `.env.sample`에는 실제 키를 넣지 않는다.
- API 키와 전체 리뷰 본문을 로그에 기록하지 않는다.
- 로그 레벨, 이벤트, 회전, 허용 필드는 [`policies/logging.md`](policies/logging.md)를 따른다.
- AI를 호출하지 않는 명령은 API 키 없이 동작해야 한다.
- 외부 경계 입력과 Gemini 구조화 응답을 검증한 뒤 사용한다.
- SQL은 매개변수화하고 정렬 필드는 허용 목록으로 제한한다.

## 6. 구현 순서

1. 관련 문서에서 범위, 경계, 완료 조건을 확인한다.
2. 변경을 검증하는 테스트를 먼저 추가하거나 갱신한다.
3. DTO·Models·Rules → Repository·Client·File I/O·Output → Service → CLI 순으로 구현한다.
4. Service의 fake/mock과 실제 외부 연동 모듈이 같은 내부 데이터 모양을 사용하게 한다.
5. 코드 동작이 바뀌면 관련 문서를 같은 변경에서 갱신한다.
6. 단위, 통합, 네트워크 없는 종단 테스트를 실행한다.
7. diff를 자체 검토하고 검증 결과를 근거와 함께 보고한다.

구현 후 실제 설치·실행 명령은 `README.md`를 단일 기준으로 유지한다. 아직 존재하지 않는 명령을 실행했다고 보고하지 않는다.

## 7. 테스트 기준

- Models·Rules 테스트는 외부 의존성 없이 실행한다.
- Service 테스트는 간단한 fake 또는 mock을 사용한다.
- Repository와 File I/O·Output 테스트는 임시 SQLite와 임시 파일을 사용한다.
- Gemini Client 테스트는 가짜 SDK 응답을 사용한다.
- 기본 테스트는 실제 Gemini와 네트워크를 사용하지 않는다.
- CLI 테스트는 옵션 파싱, 출력, 종료 코드 `0/1/2`를 확인한다.
- 전체 흐름은 30건 이상의 샘플 CSV로 import → clean → analyze(fake) → extract(fake) → dashboard → export를 검증한다.
- 테스트가 실패하면 원인을 해결하기 전 완료라고 보고하지 않는다.

## 8. 문서 동기화

| 변경 내용 | 함께 갱신할 문서 |
| --- | --- |
| 서브커맨드·옵션·기본값·종료 코드 | `policies/cli-commands.md`, `data-flow.md`, `../README.md` |
| 계층·패키지·의존성 | `architecture/README.md`, `architecture/modules.md` |
| DTO·모듈 API | `architecture/data-communication.md` |
| 데이터 소유권·트랜잭션·오류·테스트 경계 | `architecture/runtime-boundaries.md` |
| 로그 레벨·이벤트·민감정보·회전 | `policies/logging.md` |
| 중복·정규화·upsert | `policies/duplicate-review-policy.md` |
| raw/clean 필드·보존 범위·정제·거절 | `policies/raw-clean-data.md`, `data-flow.md`, `architecture/storage-schema.md` |
| AI 프롬프트·라벨·출력 스키마·confidence·버전 | `analysis/prompt-design.md`, `quality/sentiment-validation-plan.md` |
| 범위·데이터 모델·인수 기준 | 승인된 설계 문서 |
| 용어 의미·학습 설명 | `glossary/README.md`와 해당 주제 문서 |
| 작업 지침이나 문서 경로 | 이 문서, `../AGENTS.md`, `README.md` |

- 루트 `AGENTS.md`에 상세 규칙을 다시 복제하지 않는다.
- `superpowers/`의 설계 기록만으로 현재 기준을 대신하지 않고 관련 독립 문서를 함께 유지한다.
- 문서를 이동하면 `README.md`, `../AGENTS.md`, 상대 링크를 함께 수정한다.
- 문서와 구현이 다르면 차이를 숨기지 말고 요구사항과 사용자 결정을 확인해 함께 정렬한다.
- 완료된 문서에 미완료 표식이나 모호한 처리 지침을 남기지 않는다.

## 9. 검증과 안전

- 파일 탐색은 `rg --files`, 텍스트 검색은 `rg`를 우선한다.
- 관련 없는 사용자 변경을 수정하거나 되돌리지 않는다.
- 파괴적인 Git 명령을 사용하지 않는다.
- DB 스키마 변경은 마이그레이션과 기존 데이터 영향을 문서화한다.
- 완료 전 관련 테스트, 문서 링크, 미완료 표식, diff 공백 오류를 확인한다.
- 사용자가 명시적으로 요청하지 않으면 커밋, 푸시, PR을 수행하지 않는다.

## 10. 완료 보고

- 변경한 파일과 동작을 결과 중심으로 요약한다.
- 실행한 검증 명령과 결과를 함께 보고한다.
- 실행하지 못한 검증이나 남은 위험을 숨기지 않는다.
- 문서만 변경했다면 코드 테스트를 실행한 것처럼 표현하지 않는다.
