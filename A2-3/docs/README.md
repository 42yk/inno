# 프로젝트 문서 지도

이 디렉터리는 고객 리뷰 감정 분석 CLI의 현재 기준 문서를 보관한다. 모든 문서를 한꺼번에 읽지 말고 작업에 필요한 문서만 선택한다.

## 작업 시작 순서

1. 상세 작업 지침: [`agent-guidelines.md`](agent-guidelines.md)
2. 과제 범위: [`../subject.md`](../subject.md)
3. 현재 작업에 해당하는 아키텍처·정책·흐름 문서
4. 결정 배경이 필요할 때만 [`superpowers/`](superpowers/)의 설계 기록

## 핵심 문서

| 문서 | 내용 | 갱신 시점 |
| --- | --- | --- |
| [`agent-guidelines.md`](agent-guidelines.md) | 구현, 테스트, 보안, 문서 동기화, 완료 보고 지침 | 공통 작업 절차 변경 시 |
| [`data-flow.md`](data-flow.md) | 전체 파이프라인과 명령별 처리·결과 예시 | 사용자 동작이나 저장 흐름 변경 시 |
| [`architecture/README.md`](architecture/README.md) | 시스템 컨텍스트, 전체 구조, 아키텍처 문서 색인 | 전체 구조나 문서 경계 변경 시 |

## 아키텍처 문서

| 문서 | 내용 | 갱신 시점 |
| --- | --- | --- |
| [`architecture/modules.md`](architecture/modules.md) | 모듈 책임, 허용 의존성, 목표 디렉터리 구조 | 계층·패키지·의존성 변경 시 |
| [`architecture/data-communication.md`](architecture/data-communication.md) | Request/Result DTO, 내부 모델, 모듈 간 송수신 | 계층 간 전달 데이터나 공개 함수 변경 시 |
| [`architecture/runtime-boundaries.md`](architecture/runtime-boundaries.md) | 데이터 소유권, 트랜잭션, 오류, 테스트 경계 | 원자성·오류·테스트 경계 변경 시 |
| [`architecture/storage-schema.md`](architecture/storage-schema.md) | SQLite 테이블, 열, 인덱스, 외래 키, 무효화 규칙 | 저장 구조나 인덱스 변경 시 |

## 정책 문서

| 문서 | 내용 | 갱신 시점 |
| --- | --- | --- |
| [`policies/cli-commands.md`](policies/cli-commands.md) | 9개 서브커맨드의 문법, 옵션, 기본값, 종료 코드 | 명령 계약이나 도움말 변경 시 |
| [`policies/duplicate-review-policy.md`](policies/duplicate-review-policy.md) | 중복 지문과 skip/upsert, 파생 데이터 무효화 | 중복 판정이나 upsert 변경 시 |
| [`policies/logging.md`](policies/logging.md) | 로그 레벨, 이벤트, 출력, 회전, 민감정보 | 로깅 동작이나 이벤트 변경 시 |
| [`policies/configuration.md`](policies/configuration.md) | `config.json` 키, 기본값, 검증, 경로 해석, `.env` | 설정이나 비밀정보 정책 변경 시 |
| [`policies/raw-clean-data.md`](policies/raw-clean-data.md) | raw/clean 분리 이유, 필드별 보존·정제·거절, 재처리 정책 | 입력 필드·정제 규칙·보존 범위·무효화 변경 시 |

## 분석과 운영 의사결정

| 문서 | 내용 | 갱신 시점 |
| --- | --- | --- |
| [`analysis/decision-policy.md`](analysis/decision-policy.md) | 부정률 임계치, 알림→조치, 부정 키워드 우선순위, 급증 원인 가설 | 운영 임계치·우선순위 산식·조사 절차 변경 시 |
| [`analysis/visualization-methodology.md`](analysis/visualization-methodology.md) | 별점×감정 누적 막대 선택 근거, 통계적 한계, 대안 비교 | 차트 집계·표현 방식 또는 해석 기준 변경 시 |
| [`analysis/prompt-design.md`](analysis/prompt-design.md) | 감정·인사이트 프롬프트 입력·출력, 라벨 기준, confidence 규약과 예시 | 프롬프트·JSON Schema·응답 검증·버전 변경 시 |

## 품질 검증

| 문서 | 내용 | 갱신 시점 |
| --- | --- | --- |
| [`quality/sentiment-validation-plan.md`](quality/sentiment-validation-plan.md) | 층화 샘플링, 이중 검수, 정확도 메트릭, 프롬프트 A/B 실험 | 라벨 기준·합격선·실험 절차 변경 시 |

## 장애 시나리오

| 문서 | 내용 | 갱신 시점 |
| --- | --- | --- |
| [`failure-scenarios/spreadsheet-formula-input.md`](failure-scenarios/spreadsheet-formula-input.md) | 스프레드시트 수식 형태 입력의 현재 미정의 동작과 운영 지침 | 내보내기 입력 처리 범위를 결정하거나 구현할 때 |

## 용어집

| 문서 | 주요 용어 |
| --- | --- |
| [`glossary/README.md`](glossary/README.md) | 주제별 용어 문서 색인 |
| [`glossary/storage-formats.md`](glossary/storage-formats.md) | SQLite, JSONL |
| [`glossary/data-stages.md`](glossary/data-stages.md) | Raw, Clean |
| [`glossary/pagination.md`](glossary/pagination.md) | 페이지네이션 |
| [`glossary/matplotlib.md`](glossary/matplotlib.md) | matplotlib |
| [`glossary/project-terms.md`](glossary/project-terms.md) | DTO, Service, Repository, Client와 공통 용어 |

## 설계 기록

[`superpowers/specs/2026-08-05-review-sentiment-cli-design.md`](superpowers/specs/2026-08-05-review-sentiment-cli-design.md)는 승인된 설계 과정과 결정 배경을 보존한다. 이 파일은 현재 기준 문서를 대체하지 않는다.

설계 기록에만 존재하는 요구사항은 구현 기준으로 충분하지 않다. 아키텍처, 데이터 흐름, 명령, 로깅, 중복 처리처럼 구현에 직접 영향을 주는 내용은 위의 독립 문서에도 기록하고 같은 변경에서 동기화한다.

## 작업별 선택

- 명령 문법과 종료 코드: `policies/cli-commands.md`
- 명령 실행 순서와 저장 결과: `data-flow.md`
- 파일을 둘 위치와 import 방향: `architecture/modules.md`
- 모듈 사이 데이터 타입: `architecture/data-communication.md`
- 트랜잭션과 오류 처리: `architecture/runtime-boundaries.md`
- SQLite 스키마·인덱스·외래 키: `architecture/storage-schema.md`
- 로그 이벤트와 비밀정보 보호: `policies/logging.md`
- 설정 키·기본값·경로 해석: `policies/configuration.md`
- 중복과 upsert: `policies/duplicate-review-policy.md`
- raw/clean 보존·정제·거절: `policies/raw-clean-data.md`
- 감정 임계치·개선 우선순위·급증 조사: `analysis/decision-policy.md`
- 시각화 선택과 통계적 해석: `analysis/visualization-methodology.md`
- AI 라벨·출력·confidence 규약: `analysis/prompt-design.md`
- 감정 정확도와 프롬프트 실험: `quality/sentiment-validation-plan.md`
- 낯선 용어: `glossary/README.md`

## 문서 운영 규칙

- 루트 [`../AGENTS.md`](../AGENTS.md)는 시작 지침만 유지한다.
- 현재 구현 기준은 `superpowers/` 밖의 독립 문서에 둔다.
- 문서를 이동하면 이 지도와 모든 상대 링크를 함께 수정한다.
- 예시는 실제 CLI 계약과 일치시킨다.
- 완료된 문서에 미완료 표식이나 소유자 없는 결정을 남기지 않는다.

이 구조는 `AGENTS.md`를 짧은 진입점으로 사용하고 상세 지식을 저장소 문서에 두는 [OpenAI Harness Engineering](https://openai.com/ko-KR/index/harness-engineering/) 원칙을 참고한다.
