# SQLite storage schema

- Status: current implementation contract
- Related contracts: [`data-communication.md`](data-communication.md), [`runtime-boundaries.md`](runtime-boundaries.md), [`../policies/duplicate-review-policy.md`](../policies/duplicate-review-policy.md)

## General rules

All data is stored in the configured single SQLite database. Each connection enables `PRAGMA foreign_keys = ON`, schema initialization is idempotent, and non-null timestamps are UTC ISO-8601 text. SQLite booleans are `0` or `1`. Raw input is preserved except for the documented duplicate-policy upsert.

`clean_status` is one of `pending`, `cleaned`, `rejected`; `sentiment` is one of `positive`, `negative`, `neutral`.

## `raw_reviews`

| Column | Type and constraints | Meaning |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY` | Internal raw-review ID. |
| `fingerprint` | `TEXT NOT NULL UNIQUE` | SHA-256 of normalized body, product, and date. |
| `review_text_raw` | `TEXT NOT NULL` | Source review text without cleaning. |
| `rating_raw` | `TEXT` | Optional source rating without cleaning. |
| `review_date_raw` | `TEXT` | Optional source date without cleaning. |
| `product_name_raw` | `TEXT` | Optional source product without cleaning. |
| `source_type` | `TEXT NOT NULL CHECK (source_type IN ('csv', 'xlsx'))` | Source format. |
| `source_ref` | `TEXT NOT NULL` | Source file name/reference. |
| `source_row` | `INTEGER` | Optional one-based source row. |
| `clean_status` | `TEXT NOT NULL CHECK (clean_status IN ('pending', 'cleaned', 'rejected'))` | Current cleaning state. |
| `rejection_reason` | `TEXT` | Stable clean rejection code, if rejected. |
| `created_at` | `TEXT NOT NULL` | Initial import time. |
| `updated_at` | `TEXT NOT NULL` | Most recent upsert time. |

The automatic unique index on `fingerprint` is required. Add `idx_raw_reviews_clean_status_id(clean_status, id)` and `idx_raw_reviews_source_ref(source_ref)`.

## `clean_reviews`

| Column | Type and constraints | Meaning |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY` | Internal clean-review ID. |
| `raw_review_id` | `INTEGER NOT NULL UNIQUE REFERENCES raw_reviews(id) ON DELETE CASCADE` | The one source raw review. |
| `review_text` | `TEXT NOT NULL` | NFKC and whitespace-normalized body. |
| `rating` | `INTEGER CHECK (rating BETWEEN 1 AND 5)` | Optional validated rating. |
| `review_date` | `TEXT` | Optional ISO `YYYY-MM-DD` date. |
| `product_name` | `TEXT` | Optional normalized product name. |
| `cleaning_version` | `TEXT NOT NULL` | Version of the cleaning rules. |
| `cleaned_at` | `TEXT NOT NULL` | Successful cleaning time. |

The automatic unique index on `raw_review_id` enforces a one-to-one relation. Add `idx_clean_reviews_review_date(review_date)`, `idx_clean_reviews_rating(rating)`, and `idx_clean_reviews_product_name(product_name)`.

## `sentiment_analyses`

| Column | Type and constraints | Meaning |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY` | Internal analysis ID. |
| `clean_review_id` | `INTEGER NOT NULL UNIQUE REFERENCES clean_reviews(id) ON DELETE CASCADE` | The one analyzed clean review. |
| `sentiment` | `TEXT NOT NULL CHECK (sentiment IN ('positive', 'negative', 'neutral'))` | Validated model classification. |
| `confidence` | `REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0)` | Validated confidence. |
| `model_name` | `TEXT NOT NULL` | Model identifier. |
| `prompt_version` | `TEXT NOT NULL` | Prompt version. |
| `analyzed_at` | `TEXT NOT NULL` | Completion time. |

The automatic unique index on `clean_review_id` enforces one current analysis. Add `idx_sentiment_analyses_sentiment(sentiment)` and `idx_sentiment_analyses_confidence(confidence)`.

## `insight_extractions`

| Column | Type and constraints | Meaning |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY` | Internal extraction ID. |
| `scope_json` | `TEXT NOT NULL` | Canonical filters, limit application, and sorted conditions. |
| `scope_hash` | `TEXT NOT NULL` | Identifier for equivalent scopes. |
| `review_count` | `INTEGER NOT NULL CHECK (review_count >= 0)` | Input review count. |
| `positive_keywords_json` | `TEXT NOT NULL` | Keywords and validated evidence IDs. |
| `negative_keywords_json` | `TEXT NOT NULL` | Keywords and validated evidence IDs. |
| `summary` | `TEXT NOT NULL` | Overall summary. |
| `recommendations_json` | `TEXT NOT NULL` | Recommendation list. |
| `model_name` | `TEXT NOT NULL` | Model identifier. |
| `prompt_version` | `TEXT NOT NULL` | Prompt version. |
| `is_stale` | `INTEGER NOT NULL DEFAULT 0 CHECK (is_stale IN (0, 1))` | Derived data must be regenerated when `1`. |
| `created_at` | `TEXT NOT NULL` | Creation time. |

Add `idx_insight_extractions_scope_current(scope_hash, is_stale, created_at DESC)` to select the newest valid exact-scope insight. Historical extractions can share a scope hash.

## Referential and invalidation rules

Deleting a clean row cascades to its analysis; deleting a raw row cascades through clean to analysis. The application normally preserves raw rows. In one upsert transaction, the repository resets the matched raw row to `pending`, clears `rejection_reason`, deletes its clean row (cascading analysis), and sets every `insight_extractions.is_stale` to `1`. A changed or rejected cleaning result performs the same derivative invalidation.
