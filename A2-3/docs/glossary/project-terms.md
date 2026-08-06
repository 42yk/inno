# 프로젝트 용어

- 용어집 색인: [`README.md`](README.md)
- 데이터 통신 계약: [`../architecture/data-communication.md`](../architecture/data-communication.md)

## 서브커맨드

하나의 CLI 프로그램 아래에 있는 개별 명령이다. `python main.py import`에서 `import`가 서브커맨드다. 각 서브커맨드는 독립된 옵션과 책임을 갖는다. 전체 명령 계약은 [`../policies/cli-commands.md`](../policies/cli-commands.md)를 참고한다.

## 감정 신뢰도

Gemini가 분류한 감정 결과를 얼마나 확신하는지를 `0.0`~`1.0`으로 표현한 값이다. 긍정·부정의 강도를 의미하지 않는다. 예를 들어 `negative (0.91)`은 강한 부정이 아니라 부정 분류에 대한 높은 신뢰를 뜻한다.

## 분석 상태

조회 대상 리뷰에 연결된 감정 결과가 없으면 `unanalyzed`, 검증된 감정 결과가 저장되어 있으면 `analyzed`다. CLI는 각각 `미분석`, `완료`로 표시한다. `미분석`과 분석 필드의 `N/A`는 화면 표시값이며 감정 데이터로 저장하지 않는다.

## 지문(Fingerprint)

리뷰 중복을 빠르게 확인하기 위해 정규화된 본문·제품명·작성일을 SHA-256으로 해시한 값이다. 상세 규칙은 [`../policies/duplicate-review-policy.md`](../policies/duplicate-review-policy.md)를 참고한다.

## upsert

대상이 없으면 insert하고 이미 있으면 update하는 동작이다. 이 프로젝트에서 raw 리뷰를 upsert하면 clean·감정 결과를 무효화하고 모든 집계 인사이트를 stale 처리한다.

## stale

저장된 결과가 존재하지만 원본이나 파생 데이터가 바뀌어 더 이상 최신이라고 신뢰할 수 없는 상태다. stale 인사이트는 dashboard에 사용하지 않고 `extract`로 다시 생성한다.

## DTO

Data Transfer Object의 약자로, 계층 사이에서 정해진 데이터를 전달하는 목적의 타입이다. 업무 로직이나 DB 연결을 담지 않고 이름이 있는 필드만 제공한다.

이 프로젝트에서는 다음 두 종류로 구분한다.

- Request DTO: CLI가 Service에 전달하는 명령과 조회 조건
- Result DTO: Service가 CLI나 출력 단계에 반환하는 처리 결과

## Service

하나의 서브커맨드를 완료하는 처리 순서를 담당하는 모듈이다. 검증 규칙, Repository, Gemini Client, 파일·출력 모듈을 필요한 순서로 호출하고 부분 성공 여부를 결정한다. SQL이나 Gemini SDK 응답을 직접 해석하지 않는다.

## Repository

SQLite의 조회와 저장을 담당하는 모듈이다. SQL, JOIN, row 변환, 트랜잭션을 내부에서 처리하고 내부 모델이나 Result DTO만 반환한다.

## Client

Gemini처럼 외부 API를 호출하는 모듈이다. SDK 사용법, 프롬프트, 응답 파싱, 외부 오류 변환을 맡고 검증된 내부 결과만 Service에 반환한다.
