# SQLite 저장 스키마

- 상태: 현재 구현 계약
- 관련 계약: [`data-communication.md`](data-communication.md), [`runtime-boundaries.md`](runtime-boundaries.md), [`../policies/raw-clean-data.md`](../policies/raw-clean-data.md), [`../policies/duplicate-review-policy.md`](../policies/duplicate-review-policy.md)

## 공통 규칙

모든 데이터는 설정된 하나의 SQLite 데이터베이스에 저장한다. 각 연결은 `PRAGMA foreign_keys = ON`을 활성화하고, 스키마 초기화는 멱등으로 수행한다. `NULL`이 아닌 시각은 UTC ISO-8601 텍스트로 저장한다. SQLite의 불리언 값은 `0` 또는 `1`을 사용한다. 원본 입력은 문서화된 중복 정책의 upsert를 제외하고 그대로 보존한다.

`clean_status`는 `pending`, `cleaned`, `rejected` 중 하나이며, `sentiment`는 `positive`, `negative`, `neutral` 중 하나다.

## `raw_reviews`

| 컬럼 | 타입 및 제약조건 | 의미 |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY` | 내부 raw 리뷰 ID다. |
| `fingerprint` | `TEXT NOT NULL UNIQUE` | 정규화한 본문, 제품명, 작성일의 SHA-256 값이다. |
| `review_text_raw` | `TEXT NOT NULL` | 정제하지 않은 원본 리뷰 본문이다. |
| `rating_raw` | `TEXT` | 정제하지 않은 선택 원본 별점이다. |
| `review_date_raw` | `TEXT` | 정제하지 않은 선택 원본 작성일이다. |
| `product_name_raw` | `TEXT` | 정제하지 않은 선택 원본 제품명이다. |
| `source_type` | `TEXT NOT NULL CHECK (source_type IN ('csv', 'xlsx'))` | 원본 파일 형식이다. |
| `source_ref` | `TEXT NOT NULL` | 원본 파일 이름 또는 참조값이다. |
| `source_row` | `INTEGER` | 1부터 시작하는 선택 원본 행 번호다. |
| `clean_status` | `TEXT NOT NULL CHECK (clean_status IN ('pending', 'cleaned', 'rejected'))` | 현재 정제 상태다. |
| `rejection_reason` | `TEXT` | 정제가 거절됐을 때 사용하는 안정적인 거절 코드다. |
| `created_at` | `TEXT NOT NULL` | 최초 가져오기 시각이다. |
| `updated_at` | `TEXT NOT NULL` | 가장 최근 upsert 시각이다. |

`fingerprint`의 자동 고유 인덱스가 필요하다. `idx_raw_reviews_clean_status_id(clean_status, id)`와 `idx_raw_reviews_source_ref(source_ref)`를 추가한다.

## `clean_reviews`

| 컬럼 | 타입 및 제약조건 | 의미 |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY` | 내부 clean 리뷰 ID다. |
| `raw_review_id` | `INTEGER NOT NULL UNIQUE REFERENCES raw_reviews(id) ON DELETE CASCADE` | 연결된 하나의 원본 raw 리뷰다. |
| `review_text` | `TEXT NOT NULL` | NFKC와 공백 규칙으로 정규화한 본문이다. |
| `rating` | `INTEGER CHECK (rating BETWEEN 1 AND 5)` | 검증된 선택 별점이다. |
| `review_date` | `TEXT` | ISO `YYYY-MM-DD` 형식의 선택 작성일이다. |
| `product_name` | `TEXT` | 정규화한 선택 제품명이다. |
| `cleaning_version` | `TEXT NOT NULL` | 정제 규칙 버전이다. |
| `cleaned_at` | `TEXT NOT NULL` | 정제 성공 시각이다. |

`raw_review_id`의 자동 고유 인덱스가 일대일 관계를 보장한다. `idx_clean_reviews_review_date(review_date)`, `idx_clean_reviews_rating(rating)`, `idx_clean_reviews_product_name(product_name)`을 추가한다.

## `sentiment_analyses`

| 컬럼 | 타입 및 제약조건 | 의미 |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY` | 내부 분석 ID다. |
| `clean_review_id` | `INTEGER NOT NULL UNIQUE REFERENCES clean_reviews(id) ON DELETE CASCADE` | 분석된 하나의 clean 리뷰다. |
| `sentiment` | `TEXT NOT NULL CHECK (sentiment IN ('positive', 'negative', 'neutral'))` | 검증된 모델 분류값이다. |
| `confidence` | `REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0)` | 범위가 검증된 모델 자기평가 확신도다. 정답 확률은 아니다. |
| `model_name` | `TEXT NOT NULL` | 모델 식별자다. |
| `prompt_version` | `TEXT NOT NULL` | 프롬프트 버전이다. |
| `analyzed_at` | `TEXT NOT NULL` | 분석 완료 시각이다. |

`clean_review_id`의 자동 고유 인덱스가 현재 분석 결과 하나만 존재하도록 보장한다. `idx_sentiment_analyses_sentiment(sentiment)`와 `idx_sentiment_analyses_confidence(confidence)`를 추가한다.

감정 라벨과 confidence의 의미·출력 계약은 [`../analysis/prompt-design.md`](../analysis/prompt-design.md)를 따른다.

## `insight_extractions`

| 컬럼 | 타입 및 제약조건 | 의미 |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY` | 내부 추출 ID다. |
| `scope_json` | `TEXT NOT NULL` | 정규 형식의 필터, limit 적용 여부, 정렬된 조건이다. |
| `scope_hash` | `TEXT NOT NULL` | 동등한 범위를 식별하는 값이다. |
| `review_count` | `INTEGER NOT NULL CHECK (review_count >= 0)` | 입력 리뷰 건수다. |
| `positive_keywords_json` | `TEXT NOT NULL` | 긍정 키워드와 검증된 근거 ID다. |
| `negative_keywords_json` | `TEXT NOT NULL` | 부정 키워드와 검증된 근거 ID다. |
| `summary` | `TEXT NOT NULL` | 전체 요약이다. |
| `recommendations_json` | `TEXT NOT NULL` | 개선 제안 목록이다. |
| `model_name` | `TEXT NOT NULL` | 모델 식별자다. |
| `prompt_version` | `TEXT NOT NULL` | 프롬프트 버전이다. |
| `is_stale` | `INTEGER NOT NULL DEFAULT 0 CHECK (is_stale IN (0, 1))` | 값이 `1`이면 파생 데이터를 다시 생성해야 한다. |
| `created_at` | `TEXT NOT NULL` | 생성 시각이다. |

가장 최근의 유효한 정확 범위 인사이트를 선택하기 위해 `idx_insight_extractions_scope_current(scope_hash, is_stale, created_at DESC)`를 추가한다. 과거 추출 결과는 같은 범위 해시를 공유할 수 있다.

## 참조 및 무효화 규칙

clean 행을 삭제하면 연결된 분석 결과가 연쇄 삭제되고, raw 행을 삭제하면 clean을 거쳐 분석 결과까지 연쇄 삭제된다. 애플리케이션은 일반적으로 raw 행을 보존한다. Repository는 하나의 upsert 트랜잭션에서 일치하는 raw 행을 `pending`으로 되돌리고, `rejection_reason`을 비우고, clean 행을 삭제하여 분석 결과를 연쇄 삭제한 뒤, 모든 `insight_extractions.is_stale`을 `1`로 설정한다. 정제 결과가 변경되거나 거절된 경우에도 같은 방식으로 파생 데이터를 무효화한다.
