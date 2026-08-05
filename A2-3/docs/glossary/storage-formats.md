# SQLite와 JSONL

- 용어집 색인: [`README.md`](README.md)
- 관련 아키텍처: [`../../ARCHITECTURE.md`](../../ARCHITECTURE.md)

## SQLite란

SQLite는 애플리케이션 프로세스 안에서 동작하는 관계형 SQL 데이터베이스 엔진이다. 별도의 DB 서버를 설치하거나 실행하지 않아도 되고, 일반적으로 하나의 파일에 테이블·인덱스·데이터를 저장한다. 트랜잭션과 UNIQUE, FOREIGN KEY 같은 데이터 무결성 기능을 사용할 수 있다.

이 프로젝트에서는 하나의 `reviews.db` 파일 안에 다음 데이터를 서로 다른 테이블로 저장한다.

- `raw_reviews`: 입력 원본
- `clean_reviews`: 검증·정규화된 리뷰
- `sentiment_analyses`: 리뷰별 감정 결과
- `insight_extractions`: 필터 범위별 키워드·요약·개선 제안

참고: [SQLite 공식 소개](https://sqlite.org/about.html)

## JSONL이란

JSONL(JSON Lines, newline-delimited JSON)은 한 줄에 완전한 JSON 값 하나를 기록하는 UTF-8 텍스트 형식이다.

```jsonl
{"id": 1, "review_text": "배송이 빨라요", "rating": 5}
{"id": 2, "review_text": "포장이 손상됐어요", "rating": 2}
```

파일 전체를 한 번에 메모리에 올리지 않고 한 줄씩 읽고 쓸 수 있어 로그, 이벤트 스트림, 단순 데이터 교환에 편리하다. 하지만 JSONL 형식 자체는 SQL 질의, 인덱스, 외래 키, 여러 레코드를 묶는 트랜잭션을 제공하지 않는다. 이런 기능이 필요하면 애플리케이션 코드에서 별도로 구현해야 한다.

참고: [JSON Lines 형식 문서](https://jsonlines.org/)

## SQLite와 JSONL의 차이

| 비교 항목 | SQLite | JSONL |
| --- | --- | --- |
| 형태 | 관계형 데이터베이스 파일 | 줄 단위 JSON 텍스트 파일 |
| 조회 | SQL, WHERE, JOIN, GROUP BY | 파일을 순회하며 코드로 필터링 |
| 인덱스 | 지원 | 기본 지원 없음 |
| 갱신 | 특정 행 UPDATE/UPSERT 가능 | 보통 전체 재작성 또는 별도 병합 필요 |
| 트랜잭션 | ACID 트랜잭션 지원 | 형식 자체는 지원하지 않음 |
| 관계 | FOREIGN KEY로 표현 가능 | ID 연결을 애플리케이션이 관리 |
| 사람이 읽기 | 전용 도구가 있으면 편리 | 텍스트 편집기로 바로 읽기 쉬움 |
| 추가 서버 | 불필요 | 불필요 |
| 적합한 용도 | 필터, 정렬, 페이지네이션, 통계, upsert | 로그, append 중심 기록, 데이터 교환 |

## 이 프로젝트가 SQLite를 선택한 이유

이 과제는 감정·별점·기간 필터, 정렬, 페이지네이션, 중복 upsert, raw-clean 관계, 통계 집계를 요구한다. SQLite는 이런 작업을 SQL과 인덱스, 트랜잭션으로 직접 지원한다. JSONL로도 구현할 수 있지만 조회 때마다 많은 레코드를 순회하고, upsert와 파생 데이터 일관성을 애플리케이션에서 직접 관리해야 한다.

따라서 이 프로젝트에서는 SQLite를 영구 저장소로 사용하고 JSONL은 개념 비교 대상으로만 다룬다.
