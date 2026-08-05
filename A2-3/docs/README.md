# 프로젝트 문서 지도

이 디렉터리는 고객 리뷰 감정 분석 CLI의 기록 시스템이다. 처음부터 모든 문서를 읽지 말고 현재 작업에 필요한 문서부터 확인한다.

## 권장 읽기 순서

1. 상세 작업 지침: [`agent-guidelines.md`](agent-guidelines.md)
2. 과제 범위: [`../subject.md`](../subject.md)
3. 전체 설계 결정: [`superpowers/specs/2026-08-05-review-sentiment-cli-design.md`](superpowers/specs/2026-08-05-review-sentiment-cli-design.md)
4. 최상위 아키텍처: [`../ARCHITECTURE.md`](../ARCHITECTURE.md)
5. 작업별 상세 문서: 아래 문서 목록에서 선택

## 문서 목록

| 문서 | 대상 | 내용 | 언제 갱신하는가 |
| --- | --- | --- | --- |
| [`../AGENTS.md`](../AGENTS.md) | 에이전트·개발자 | 짧은 작업 진입점과 핵심 가드레일 | 문서 경로나 필수 진입 규칙 변경 시 |
| [`agent-guidelines.md`](agent-guidelines.md) | 에이전트·개발자 | 구현, 테스트, 보안, 문서 동기화, 검증 상세 지침 | 작업 절차나 공통 지침 변경 시 |
| [`../ARCHITECTURE.md`](../ARCHITECTURE.md) | 개발자·에이전트 | 계층, 책임, 허용 의존성, 데이터 소유권 | 패키지 경계나 의존성 방향 변경 시 |
| [`data-flow.md`](data-flow.md) | 사용자·개발자 | 전체 파이프라인과 서브커맨드별 입력·처리·결과 예시 | CLI 동작이나 저장 흐름 변경 시 |
| [`layer-communication.md`](layer-communication.md) | 개발자·테스터 | 계층 간 DTO, 모듈 API, 오류, 트랜잭션 계약 | 계층 간 전달 데이터나 공개 함수 변경 시 |
| [`glossary/README.md`](glossary/README.md) | 입문자·사용자 | 주제별 용어 문서 색인 | 용어 문서를 추가·이동할 때 |
| [`policies/duplicate-review-policy.md`](policies/duplicate-review-policy.md) | 개발자·테스터 | 중복 지문과 skip/upsert 정책 | 중복 판정 또는 무효화 규칙 변경 시 |
| [`superpowers/specs/2026-08-05-review-sentiment-cli-design.md`](superpowers/specs/2026-08-05-review-sentiment-cli-design.md) | 기획·개발 | 승인된 범위, CLI 계약, 데이터 모델, 인수 기준 | 제품 범위나 승인된 설계 변경 시 |

### 용어집 구성

| 문서 | 주요 용어 |
| --- | --- |
| [`glossary/storage-formats.md`](glossary/storage-formats.md) | SQLite, JSONL |
| [`glossary/data-stages.md`](glossary/data-stages.md) | Raw, Clean |
| [`glossary/pagination.md`](glossary/pagination.md) | 페이지네이션 |
| [`glossary/matplotlib.md`](glossary/matplotlib.md) | matplotlib |
| [`glossary/project-terms.md`](glossary/project-terms.md) | DTO, Service, Repository, Client와 프로젝트 공통 용어 |

## 작업별 문서 선택

- 구현 순서·테스트·보안·완료 보고 기준을 확인하려면 `agent-guidelines.md`
- 입력·정제·분석 순서를 이해하려면 `data-flow.md`
- 파일을 어느 패키지에 둘지 결정하려면 `ARCHITECTURE.md`
- 계층 사이에서 어떤 타입을 주고받을지 결정하려면 `layer-communication.md`
- 중복 버그를 수정하려면 `policies/duplicate-review-policy.md`
- 낯선 용어를 확인하려면 `glossary/README.md`에서 주제 문서를 선택한다.
- 기능이 과제 범위에 포함되는지 판단하려면 설계 문서와 `subject.md`

## 문서 간 우선순위

`subject.md`는 필수 범위를 정의하고, 승인된 설계 문서는 그 범위를 구현 가능한 결정으로 구체화한다. 아키텍처와 정책 문서는 구현 불변 조건을 정의하며, 데이터 흐름과 용어집은 그 결정을 설명한다.

문서가 서로 충돌하면 임의로 하나를 선택하지 않는다. 요구사항과 사용자 결정을 먼저 확인한 뒤 영향을 받는 문서를 같은 변경에서 함께 수정한다.

## 문서 작성 원칙

- `AGENTS.md`에는 상세 내용을 복제하지 않고 `agent-guidelines.md`와 이 지도에 링크한다.
- 예시는 실제 CLI 계약과 일치시킨다.
- 구현 전 문서는 목표 동작임을 명시하고, 구현 후에는 실제 검증 결과와 맞춘다.
- 계층 간에 전달되는 데이터는 이름, 필드, 검증 책임을 문서화한다.
- 완료된 문서에 미완료 표식이나 소유자 없는 결정을 남기지 않는다.
- 파일을 이동하거나 이름을 바꾸면 모든 상대 링크를 함께 수정한다.

이 문서 구조는 `AGENTS.md`를 백과사전이 아닌 짧은 목차로 사용하고 상세 지식을 구조화된 `docs/`에 두는 [OpenAI Harness Engineering](https://openai.com/ko-KR/index/harness-engineering/)의 원칙을 참고했다.
