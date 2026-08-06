# 용어집

- 대상: 데이터 처리와 Python CLI가 익숙하지 않은 학습자
- 프로젝트 흐름: [`../data-flow.md`](../data-flow.md)
- 아키텍처: [`../architecture/README.md`](../architecture/README.md)

용어를 한 파일에 계속 추가하지 않고 주제별 문서로 관리한다. 필요한 개념만 골라 읽는다.

## 문서 구조

```text
docs/glossary/
├── README.md
├── storage-formats.md
├── data-stages.md
├── pagination.md
├── matplotlib.md
└── project-terms.md
```

## 주제별 문서

| 문서 | 설명 |
| --- | --- |
| [`storage-formats.md`](storage-formats.md) | SQLite와 JSONL의 정의, 차이, 이 프로젝트의 선택 |
| [`data-stages.md`](data-stages.md) | 데이터 분석에서 Raw와 Clean의 정의와 차이 |
| [`pagination.md`](pagination.md) | 페이지네이션의 목적, 계산식, 안정된 정렬 |
| [`matplotlib.md`](matplotlib.md) | matplotlib의 역할과 이 프로젝트의 정적 차트 방식 |
| [`project-terms.md`](project-terms.md) | 서브커맨드, 분석 상태, 신뢰도, 지문, upsert, stale, DTO, Service, Repository, Client |

## 관리 원칙

- 하나의 용어가 길어지면 가장 가까운 주제 문서에 추가한다.
- 서로 다른 주제가 섞이면 새 파일을 만들고 이 색인에 연결한다.
- 프로젝트에서 사용하는 의미와 일반적인 의미가 다르면 둘을 구분해 적는다.
- CLI 예시와 파일 경로는 실제 설계 및 구현과 일치시킨다.
