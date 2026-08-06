# Configuration policy

- Status: current implementation policy
- Related contracts: [`cli-commands.md`](cli-commands.md), [`../architecture/storage-schema.md`](../architecture/storage-schema.md), [`logging.md`](logging.md)

## Files and resolution

The JSON object at the explicitly selected configuration `Path` is required; the application does not silently fall back when it is absent, unreadable, malformed, or not an object. Relative `database_path`, `log_file`, and `output_directory` values resolve relative to the loaded `config.json` parent directory; absolute paths remain absolute. Loading never creates files or directories.

Unknown keys are rejected. Missing keys use defaults. JSON numeric values must be numbers, not strings or booleans. Paths and text settings are non-empty strings. `.env.sample` contains only `GEMINI_API_KEY=replace_with_your_key`; `.env` is Git-ignored. The key is required only by `analyze` and `extract`.

## `config.json`

| Key | JSON type | Default | Validation and use |
| --- | --- | --- | --- |
| `database_path` | string | `data/reviews.db` | Non-empty, resolved as above. |
| `gemini_model` | string | `gemini-3.1-flash-lite` | Non-empty model ID. |
| `duplicate_policy` | string | `skip` | Exactly `skip` or `upsert`; import CLI may override per run. |
| `minimum_review_length` | integer | `5` | Greater than zero. |
| `analysis_batch_size` | integer | `20` | Greater than zero. |
| `extraction_chunk_characters` | integer | `50000` | Greater than zero. |
| `ai_retry_count` | integer | `2` | Zero or greater; retries after initial request. |
| `default_page_size` | integer | `20` | Greater than zero and at most `maximum_page_size`. |
| `maximum_page_size` | integer | `100` | At least `default_page_size`. |
| `chart_font_candidates` | array of strings | `["AppleGothic", "Malgun Gothic", "NanumGothic"]` | Non-empty; all values are non-empty strings, used in order. |
| `log_level` | string | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. |
| `log_file` | string | `logs/app.log` | Non-empty, resolved as above. |
| `output_directory` | string | `output` | Non-empty, resolved as above. |

The committed [`../../config.json`](../../config.json) contains every default. `AppConfig` is frozen; resolved paths are `Path` instances and fonts are a tuple.

## Errors

`ConfigurationError` uses stable cause codes: `CONFIG_FILE_NOT_FOUND` (no file), `CONFIG_FILE_READ_ERROR` (unreadable), `INVALID_CONFIG_JSON` (invalid JSON/object), `UNKNOWN_CONFIG_KEY`, `INVALID_CONFIG_TYPE`, `INVALID_CONFIG_VALUE`, `DATABASE_DIRECTORY_FAILED` (database parent cannot be created), `LOG_SETUP_FAILED` (log file cannot be configured), and `GEMINI_API_KEY_REQUIRED` (AI command has no key). Messages include only a key path and cause code, never a key value or arbitrary file contents.
