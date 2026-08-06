# 고객 리뷰 감정 분석 CLI

CSV/XLSX 고객 리뷰를 SQLite에 raw/clean으로 나누어 저장하고, Gemini로 감정과 인사이트를 분석한 뒤 조회·통계·PNG 차트·TXT/MD 리포트·CSV/XLSX 내보내기를 제공하는 Python CLI입니다.

## 요구 환경과 설치

- Python 3.10 이상
- 실제 AI 분석 시 Gemini API 키

프로젝트 루트에서 다음을 실행합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Windows PowerShell에서는 가상환경 활성화 명령으로 `.venv\Scripts\Activate.ps1`을 사용합니다.

`analyze` 또는 `extract`에서 실제 AI 호출이 필요하면 예시 파일을 복사하고 키를 입력합니다.

```bash
cp .env.sample .env
```

```dotenv
GEMINI_API_KEY=your_actual_key
```

`.env`는 Git에서 제외됩니다. 도움말과 `import`, `clean`, `list`, `show`, `stats`, `dashboard`, `export`는 API 키가 없어도 동작합니다. `analyze`도 처리 대상이 0건이면 키나 네트워크를 사용하지 않습니다.

## 입력 파일

지원 확장자는 `.csv`, `.xlsx`입니다. 첫 행에 다음 열 이름을 사용합니다.

| 열 | 필수 | 의미 |
| --- | --- | --- |
| `review_text` | 예 | 리뷰 원문 |
| `rating` | 아니요 | 1~5 정수 |
| `review_date` | 아니요 | 정제 후 `YYYY-MM-DD`로 통일할 날짜 |
| `product_name` | 아니요 | 제품명 |

제출용 [샘플 데이터](data/sample_reviews.csv)는 34행이며 세 제품, 여러 날짜와 별점, 선택값 누락, 중복, 정제 거절 사례를 포함합니다.

## 빠른 시작

권장 순서입니다.

```bash
python main.py import --file data/sample_reviews.csv
python main.py clean --pending
python main.py analyze --unanalyzed
python main.py extract
python main.py stats
python main.py dashboard --output-dir output --report-format md
python main.py export --format xlsx --output output/reviews.xlsx
```

`dashboard`는 같은 제품·기간 필터로 생성된 최신 `extract` 결과가 필요합니다. 인사이트가 없거나 원천 리뷰가 바뀌어 stale 상태라면 안내된 필터로 `extract`를 다시 실행합니다. 대시보드는 Gemini를 암묵적으로 호출하지 않습니다.

## 아홉 개 명령

전체 옵션은 `python main.py --help`와 `python main.py <command> --help`에서 확인할 수 있습니다.

### 1. `import`

```bash
python main.py import --file reviews.csv [--duplicate-policy skip|upsert]
```

파일 전체 구조를 먼저 검증한 뒤 raw 리뷰를 저장합니다. 기본 중복 정책은 `config.json`에서 읽습니다.

### 2. `clean`

```bash
python main.py clean [--pending | --all | --id RAW_ID]
```

기본 대상은 `pending`입니다. 본문·별점·날짜·최소 길이를 검증하고 clean 저장 또는 사유가 있는 정상 거절로 기록합니다.

### 3. `analyze`

```bash
python main.py analyze [--unanalyzed | --all | --id CLEAN_ID] [--limit COUNT] [--force]
```

기본 대상은 미분석 clean 리뷰입니다. 실제 대상이 있을 때 `.env`의 키로 Gemini를 호출하며, 성공 배치는 저장하고 최종 실패 배치는 안전한 코드로 집계합니다.

### 4. `extract`

```bash
python main.py extract [--sentiment positive|negative|neutral] [--product NAME] \
  [--date-from YYYY-MM-DD] [--date-to YYYY-MM-DD] [--limit COUNT]
```

필터 범위의 긍정·부정 키워드와 근거 리뷰 ID, 요약, 개선 제안을 저장합니다. `--limit`을 사용한 결과는 limit 없는 대시보드 범위와 일치하지 않습니다.

### 5. `list`

```bash
python main.py list [--sentiment positive|negative|neutral] [--rating 1..5] \
  [--date-from YYYY-MM-DD] [--date-to YYYY-MM-DD] [--page N] [--size N] \
  [--sort-by id|review_date|rating|sentiment|confidence] [--order asc|desc]
```

미분석 리뷰도 기본 목록에 포함됩니다. 감정 또는 신뢰도 정렬에서도 미분석 행은 마지막에 위치합니다.

### 6. `show`

```bash
python main.py show RAW_ID
```

raw 원문, 정제 상태와 거절 사유, nullable clean 필드, 감정·신뢰도·모델·분석 시각을 표시합니다.

### 7. `stats`

```bash
python main.py stats [--sentiment positive|negative|neutral] [--product NAME] \
  [--date-from YYYY-MM-DD] [--date-to YYYY-MM-DD]
```

clean 리뷰 수, 분석 완료율, 감정 분포, 평균 별점, 평균 신뢰도, 별점·감정 일치율을 출력합니다. 분모가 없으면 `N/A`로 표시합니다.

### 8. `dashboard`

```bash
python main.py dashboard [--product NAME] [--date-from YYYY-MM-DD] \
  [--date-to YYYY-MM-DD] [--top COUNT] [--output-dir PATH] \
  [--report-format txt|md]
```

콘솔 종합 리포트와 파일 리포트 하나, 다음 PNG 세 개를 생성합니다.

- `sentiment_distribution.png`
- `sentiment_trend.png`
- `rating_sentiment_matrix.png`

날짜나 별점 데이터가 없어도 해당 PNG 안에 `표시할 데이터 없음`을 기록합니다. 파일 리포트 이름은 `review_sentiment_report.md` 또는 `review_sentiment_report.txt`입니다.

### 9. `export`

```bash
python main.py export --format csv|xlsx --output PATH \
  [--sentiment positive|negative|neutral] [--rating-min 1..5]
```

CSV는 UTF-8 BOM을 사용합니다. `--output` 확장자는 선택한 형식과 일치해야 하며, 결과가 없어도 헤더 파일을 생성합니다.

## 설정과 생성 파일

애플리케이션은 프로젝트 루트의 `config.json`을 읽습니다. 상대 `database_path`, `log_file`, `output_directory`는 이 파일의 디렉터리를 기준으로 해석합니다. 주요 기본값은 다음과 같습니다.

| 항목 | 기본값 |
| --- | --- |
| SQLite | `data/reviews.db` |
| Gemini 모델 | `gemini-3.1-flash-lite` |
| 중복 정책 | `skip` |
| 분석 배치 | 20건 |
| 목록 크기 / 최대 크기 | 20 / 100 |
| 로그 | `logs/app.log`, INFO, 5 MiB, 백업 3개 |
| 대시보드 출력 | `output` |

API 키, 리뷰 원문, AI 프롬프트와 원본 응답은 로그에 기록하지 않습니다. DB, 로그, `.env`, 기본 output 파일은 Git에서 제외됩니다. 전체 설정 계약은 [configuration policy](docs/policies/configuration.md), 명령 계약은 [CLI policy](docs/policies/cli-commands.md)를 참고합니다.

## 종료 코드

| 코드 | 의미 |
| --- | --- |
| `0` | 성공, 도움말, 정상적인 대상 0건 |
| `1` | 사용법·설정·입력·DB·API·전체 출력 실패 |
| `2` | 일부 결과를 보존한 부분 성공 |

## 테스트

전체 테스트는 실제 Gemini 호출 없이 실행됩니다.

```bash
python -m pytest -q
python -m pytest tests/e2e/test_offline_pipeline.py -q
```

E2E 테스트는 `tests/fakes.py`의 DTO 호환 Fake Gemini를 주입해 아홉 명령, SQLite 상태, PNG/MD, CSV/XLSX를 검증합니다. 일반 CLI의 `analyze`와 `extract`는 처리 대상이 있으면 공식 `google-genai` SDK와 실제 API 키를 사용합니다.

## 개발 문서

현재 기준 문서의 지도는 [docs/README.md](docs/README.md), 승인된 설계 기록은 [2026-08-05 design](docs/superpowers/specs/2026-08-05-review-sentiment-cli-design.md)에 있습니다.
