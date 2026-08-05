# AGENTS.md

이 파일은 저장소 작업의 짧은 진입점이다. 상세 규칙은 복제하지 않고 원본 문서에 연결한다.

## 프로젝트

CSV/Excel 고객 리뷰를 raw와 clean으로 분리 저장하고 Gemini 분석, CLI 조회·통계, 정적 대시보드, CSV/XLSX 내보내기를 제공한다. 사용자가 별도로 승인하지 않으면 보너스 기능은 구현하지 않는다.

## 작업 시작

1. 모든 작업 전에 [`docs/agent-guidelines.md`](docs/agent-guidelines.md)를 읽고 따른다.
2. [`docs/README.md`](docs/README.md)에서 현재 작업에 필요한 문서만 선택한다.
3. 범위 판단이 필요하면 [`subject.md`](subject.md)와 [승인된 설계](docs/superpowers/specs/2026-08-05-review-sentiment-cli-design.md)를 확인한다.

## 핵심 지도

- 계층과 의존성: [`ARCHITECTURE.md`](ARCHITECTURE.md)
- CLI와 데이터 흐름: [`docs/data-flow.md`](docs/data-flow.md)
- 계층 간 DTO·모듈 API·오류 계약: [`docs/layer-communication.md`](docs/layer-communication.md)
- 중복·upsert 정책: [`docs/policies/duplicate-review-policy.md`](docs/policies/duplicate-review-policy.md)

## 즉시 적용할 가드레일

- SQLite 행, Gemini 응답, pandas DataFrame, matplotlib Figure를 소유 모듈 밖으로 누출하지 않는다.
- `.env`, API 키, 생성 DB, 로그, output 파일을 커밋하지 않는다.
- 관련 없는 사용자 변경을 수정하거나 되돌리지 않는다.
- 사용자가 명시적으로 요청하지 않으면 커밋, 푸시, PR을 수행하지 않는다.
- 테스트와 관련 문서 검증 없이 완료라고 보고하지 않는다.
