# M1-1 문서 인덱스

이 디렉터리는 서울 장기 기온 분석 프로젝트의 요구사항, 설계, 사용 지침과 학습 자료를 생명주기별로 관리한다. 프로젝트 개요와 실제 결과는 [프로젝트 소개](../README.md)와 [분석 리포트](../REPORT.md)에서 확인한다.

## 디렉터리 구조

```text
docs/
├── README.md
├── requirements/
│   └── README.md
├── design/
│   ├── data-source.md
│   ├── analysis-design.md
│   ├── architecture.md
│   └── implementation-plan.md
├── guides/
│   ├── manual-data-input.md
│   └── verification-plan.md
└── learning/
    ├── guide.md
    ├── objectives.md
    └── glossary.md
```

## `requirements/` — 요구사항

| 문서 | 설명 |
| --- | --- |
| [서울 장기 기온 분석 요구사항](requirements/README.md) | 승인된 범위, 기능·비기능 요구사항, 산출물과 완료 조건을 정의한다. |

## `design/` — 설계와 구현 계획

| 문서 | 설명 |
| --- | --- |
| [데이터 출처와 수집 정책](design/data-source.md) | 데이터 선정 근거, 수집·보관 방식, 컬럼 대응과 출처표시 정책을 정의한다. |
| [분석 설계](design/analysis-design.md) | 분석 질문, 정제 기준, 통계 기법, 시각화와 해석 기준을 정의한다. |
| [과제 아키텍처](design/architecture.md) | 패키지 구조, 구성요소 책임, 데이터 흐름과 오류 처리 원칙을 설명한다. |
| [구현 설계와 실행 계획](design/implementation-plan.md) | 모듈 계약, 구현 순서, 테스트 전략과 기술적 위험 대응을 정리한다. |

## `guides/` — 실행과 검증 지침

| 문서 | 설명 |
| --- | --- |
| [수동 데이터 입력 지침](guides/manual-data-input.md) | 자동 수집 없이 표준 CSV를 제공할 때 지켜야 하는 입력 계약과 실행 방법을 안내한다. |
| [검증 계획](guides/verification-plan.md) | 자동 테스트, 실제 데이터 재현, 산출물 검수와 실패 판정 기준을 정의한다. |

## `learning/` — 학습 자료

| 문서 | 설명 |
| --- | --- |
| [데이터 분석 개념 학습 가이드](learning/guide.md) | 데이터 구조부터 품질, 기초 통계, 시계열 분석과 결과 해석까지 개념 흐름을 설명한다. |
| [과제 목표](learning/objectives.md) | 데이터 분석 사고, 시계열 이해와 AI 활용 역량이 프로젝트에 적용된 과정과 근거를 설명한다. |
| [데이터 분석 용어집](learning/glossary.md) | 기상 데이터, 데이터 품질, 기초 통계, 시계열과 해석 용어의 짧은 정의를 제공한다. |

## 권장 읽기 순서

### 프로젝트 전체 이해

1. [프로젝트 소개](../README.md)
2. [분석 리포트](../REPORT.md)
3. [요구사항](requirements/README.md)
4. [분석 설계](design/analysis-design.md)
5. [과제 아키텍처](design/architecture.md)

### 데이터 준비와 재현

1. [데이터 출처와 수집 정책](design/data-source.md)
2. [수동 데이터 입력 지침](guides/manual-data-input.md)
3. [검증 계획](guides/verification-plan.md)

### 데이터 분석 학습

1. [데이터 분석 개념 학습 가이드](learning/guide.md)
2. [과제 목표](learning/objectives.md)
3. [데이터 분석 용어집](learning/glossary.md)
4. [분석 설계](design/analysis-design.md)

## 문서 기준 우선순위

문서 내용이 충돌하면 다음 순서로 판단한다.

1. `requirements/README.md`의 승인된 범위와 완료 조건
2. `design/data-source.md`와 `design/analysis-design.md`의 데이터·분석 정책
3. `design/architecture.md`와 `guides/verification-plan.md`의 구현·검증 세부사항
4. `design/implementation-plan.md`의 구현 순서와 기술적 참고사항

원자료 특성이나 구현 제약으로 기준을 변경해야 하면 관련 문서에 이유와 영향을 먼저 기록한다.
