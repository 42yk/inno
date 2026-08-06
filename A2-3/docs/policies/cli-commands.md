# CLI 서브커맨드 정책

- 상태: 현재 구현 정책
- 적용 범위: `main.py`의 argparse 명령, 옵션, 기본값, 출력, 종료 코드
- 처리 흐름과 예시: [`../data-flow.md`](../data-flow.md)
- 내부 데이터 계약: [`../architecture/data-communication.md`](../architecture/data-communication.md)

## 1. 문서 역할

이 문서는 9개 필수 서브커맨드의 사용자 입력 계약을 정의하는 단일 정책이다. 명령 이름, 위치 인수, 옵션, 허용값, 기본값, 상호 배타 조건, 종료 코드를 변경할 때 이 문서를 먼저 갱신한다.

문서별 책임은 다음과 같다.

| 문서 | 책임 |
| --- | --- |
| 이 문서 | 명령 문법, 옵션, 기본값, 검증, 종료 코드 |
| [`../data-flow.md`](../data-flow.md) | 명령별 데이터 처리 순서, 상태 변화, 실행·결과 예시 |
| [`../architecture/data-communication.md`](../architecture/data-communication.md) | Request/Result DTO와 모듈 간 전달 데이터 |
| [`../../subject.md`](../../subject.md) | 과제의 필수 기능 범위 |
| [`../superpowers/specs/2026-08-05-review-sentiment-cli-design.md`](../superpowers/specs/2026-08-05-review-sentiment-cli-design.md) | 승인 당시 설계 결정 기록 |

## 2. 공통 실행 계약

모든 명령은 다음 형식으로 실행한다.

```bash
python main.py <command> [arguments] [options]
```

다음 도움말은 DB와 Gemini를 호출하지 않고 종료 코드 `0`을 반환한다.

```bash
python main.py --help
python main.py <command> --help
```

### 2.1 공통 값 규칙

| 값 | 허용 규칙 |
| --- | --- |
| 감정 | `positive`, `negative`, `neutral` |
| 별점 | 정수 `1`~`5` |
| 날짜 | ISO `YYYY-MM-DD` |
| 날짜 범위 | `date_from <= date_to` |
| ID | `1` 이상의 정수 |
| 개수·페이지 값 | `1` 이상의 정수 |
| 정렬 방향 | `asc`, `desc` |
| 중복 정책 | `skip`, `upsert` |
| 내보내기 형식 | `csv`, `xlsx` |
| 리포트 형식 | `txt`, `md` |

CLI는 위 형식과 옵션 조합을 검증한 뒤 Request DTO를 만든다. 파일 존재 여부, DB 대상 존재 여부, 데이터 상태처럼 실행이 필요한 검증은 Service와 해당 외부 연동 모듈이 담당한다.

### 2.2 공통 기본값

| 항목 | 기본값 | 출처 |
| --- | --- | --- |
| 중복 정책 | `config.json`의 `duplicate_policy`, 초기값 `skip` | 설정 |
| Gemini 모델 | `gemini-3.1-flash-lite` | 설정 |
| Gemini 분석 배치 | 20건 | `analysis_batch_size` |
| 목록 페이지 | 1 | CLI 정책 |
| 목록 페이지 크기 | 20건 | `default_page_size` |
| 최대 페이지 크기 | 100건 | `maximum_page_size` |
| 목록 정렬 | `id asc` | CLI 정책 |
| 대시보드 TOP N | 5 | CLI 정책 |
| 대시보드 리포트 형식 | `md` | CLI 정책 |
| 출력 디렉터리 | `output` | `output_directory` |

`config.json`에 정의된 설정은 명령행 옵션이 있으면 해당 실행에서만 덮어쓴다.

### 2.3 종료 코드

| 코드 | 의미 |
| --- | --- |
| `0` | 완전 성공, 도움말 출력, 정상적인 처리 대상 0건 |
| `1` | 잘못된 사용법, 설정·입력·DB·API 오류, 대상 없음 등 명령 실패 |
| `2` | 일부 항목은 성공하고 일부 항목은 실패한 부분 성공 |

argparse 사용법 오류도 `1`로 변환한다. `2`는 실행을 시작한 뒤 발생한 부분 성공에만 사용한다.

### 2.4 API 키

- `analyze`, `extract`는 `.env`의 `GEMINI_API_KEY`가 필요하다.
- 나머지 명령과 모든 도움말은 API 키 없이 동작한다.
- 키가 없으면 AI를 호출하기 전에 오류를 출력하고 종료 코드 `1`을 반환한다.

## 3. 명령 요약

| 명령 | 목적 | DB 쓰기 | 파일 쓰기 | Gemini |
| --- | --- | --- | --- | --- |
| `import` | CSV/XLSX 리뷰 수집 | raw | 없음 | 없음 |
| `clean` | raw 검증·정제 | raw 상태, clean | 없음 | 없음 |
| `analyze` | 리뷰별 감정 분석 | 감정 결과 | 없음 | 호출 |
| `extract` | 범위별 키워드·요약·제안 추출 | 인사이트 | 없음 | 호출 |
| `list` | 필터·정렬·페이지 목록 조회 | 없음 | 없음 | 없음 |
| `show` | 리뷰 한 건 상세 조회 | 없음 | 없음 | 없음 |
| `stats` | 통계와 품질 지표 조회 | 없음 | 없음 | 없음 |
| `dashboard` | 리포트와 PNG 차트 생성 | 없음 | TXT/MD, PNG | 없음 |
| `export` | clean·감정 결과 내보내기 | 없음 | CSV/XLSX | 없음 |

## 4. `import`

```bash
python main.py import --file <path> [--duplicate-policy skip|upsert]
```

| 인수·옵션 | 필수 | 기본값 | 의미와 검증 |
| --- | --- | --- | --- |
| `--file PATH` | 예 | 없음 | 존재하는 `.csv` 또는 `.xlsx` 파일 |
| `--duplicate-policy` | 아니요 | 설정값 | 이번 실행의 중복 처리 정책 |

- 필수 열은 `review_text`이고 선택 열은 `rating`, `review_date`, `product_name`이다.
- 파일을 읽을 수 없거나 필수 열이 없으면 어떤 행도 저장하지 않고 종료 코드 `1`을 반환한다.
- 각 입력 행은 raw에만 저장하며 자동으로 clean을 만들지 않는다.
- 개별 행의 DB 실패가 있어 다른 행은 저장되면 종료 코드 `2`를 반환한다.

## 5. `clean`

```bash
python main.py clean [--pending | --all | --id <raw-id>]
```

| 인수·옵션 | 필수 | 기본값 | 의미와 검증 |
| --- | --- | --- | --- |
| `--pending` | 아니요 | 선택 옵션이 없을 때 적용 | `clean_status=pending`인 raw 처리 |
| `--all` | 아니요 | 없음 | 거절된 행을 포함한 모든 raw 재평가 |
| `--id ID` | 아니요 | 없음 | 지정한 raw ID 한 건 처리 |

- 세 대상 옵션은 상호 배타적이다.
- `--id` 대상이 없으면 종료 코드 `1`을 반환한다.
- 여러 건 중 일부만 거절되는 것은 정상적인 정제 결과이므로 명령 자체가 정상 완료되면 종료 코드 `0`이다.
- 재정제로 기존 clean이 달라지거나 거절되면 기존 감정을 제거하고 모든 집계 인사이트를 stale 처리한다.

## 6. `analyze`

```bash
python main.py analyze [--unanalyzed | --all | --id <clean-id>]
                       [--limit <count>] [--force]
```

| 인수·옵션 | 필수 | 기본값 | 의미와 검증 |
| --- | --- | --- | --- |
| `--unanalyzed` | 아니요 | 선택 옵션이 없을 때 적용 | 감정 결과가 없는 clean만 분석 |
| `--all` | 아니요 | 없음 | 모든 clean을 대상으로 선택 |
| `--id ID` | 아니요 | 없음 | 지정한 clean ID 한 건 선택 |
| `--limit COUNT` | 아니요 | 제한 없음 | 선택된 대상 중 최대 처리 건수 |
| `--force` | 아니요 | `false` | 기존 감정 결과가 있어도 다시 분석하고 교체 |

- 세 대상 옵션은 상호 배타적이다.
- `--all`도 `--force`가 없으면 이미 분석된 리뷰를 건너뛴다.
- 선택된 대상은 설정의 `analysis_batch_size`, 초기값 20건으로 나눠 호출한다.
- 대상이 0건이면 Gemini를 호출하지 않고 종료 코드 `0`을 반환한다.
- 일부 배치가 최종 실패하고 다른 배치가 저장되면 종료 코드 `2`, 모든 배치가 실패하면 `1`이다.

## 7. `extract`

```bash
python main.py extract [--sentiment positive|negative|neutral]
                       [--product <name>]
                       [--date-from YYYY-MM-DD] [--date-to YYYY-MM-DD]
                       [--limit <count>]
```

| 인수·옵션 | 필수 | 기본값 | 의미와 검증 |
| --- | --- | --- | --- |
| `--sentiment` | 아니요 | 전체 감정 | 감정 결과가 해당 값인 리뷰만 선택 |
| `--product NAME` | 아니요 | 전체 제품 | 정규화된 제품명이 일치하는 리뷰 선택 |
| `--date-from DATE` | 아니요 | 시작 제한 없음 | 작성일 하한, 포함 |
| `--date-to DATE` | 아니요 | 종료 제한 없음 | 작성일 상한, 포함 |
| `--limit COUNT` | 아니요 | 제한 없음 | 필터 결과 중 최대 입력 건수 |

- 필터가 없으면 전체 clean 리뷰가 대상이다.
- 대상이 없으면 Gemini를 호출하지 않고 종료 코드 `1`을 반환한다.
- 결과의 범위 정보에는 필터와 limit 적용 여부를 함께 기록한다.
- `--limit`으로 일부만 추출한 결과는 전체 범위의 `dashboard`를 충족하지 않는다.

## 8. `list`

```bash
python main.py list [--sentiment positive|negative|neutral] [--rating 1..5]
                    [--date-from YYYY-MM-DD] [--date-to YYYY-MM-DD]
                    [--page <number>] [--size <count>]
                    [--sort-by id|review_date|rating|sentiment|confidence]
                    [--order asc|desc]
```

| 인수·옵션 | 필수 | 기본값 | 의미와 검증 |
| --- | --- | --- | --- |
| `--sentiment` | 아니요 | 전체 감정 | 감정 필터 |
| `--rating INT` | 아니요 | 전체 별점 | 정확히 일치하는 별점 `1`~`5` |
| `--date-from DATE` | 아니요 | 시작 제한 없음 | 작성일 하한, 포함 |
| `--date-to DATE` | 아니요 | 종료 제한 없음 | 작성일 상한, 포함 |
| `--page INT` | 아니요 | `1` | 1부터 시작하는 페이지 번호 |
| `--size INT` | 아니요 | `20` | 페이지 크기; 최대 `100` |
| `--sort-by FIELD` | 아니요 | `id` | 허용 목록의 정렬 필드 |
| `--order` | 아니요 | `asc` | 정렬 방향 |

- 같은 정렬값이 있으면 `id`를 마지막 정렬 기준으로 사용한다.
- 감정 필터가 없으면 감정 분석 여부와 관계없이 모든 clean 리뷰를 포함한다.
- 분석 완료 행은 `negative (0.91)`처럼 `감정 (신뢰도)`로, 미분석 행은 `미분석`으로 표시한다.
- `--sentiment`를 지정하면 해당 감정 결과가 있는 분석 완료 리뷰만 포함하고 미분석 리뷰는 제외한다.
- `--sort-by sentiment|confidence`에서는 분석 완료 리뷰를 요청 방향으로 정렬하고 미분석 리뷰를 항상 마지막에 둔다.
- 결과가 없거나 요청 페이지가 전체 범위를 벗어나도 빈 목록과 페이지 정보를 출력하고 종료 코드 `0`을 반환한다.
- 정렬 필드는 Repository에서 허용된 SQL 열 이름으로 매핑하며 입력 문자열을 SQL에 직접 넣지 않는다.

## 9. `show`

```bash
python main.py show <id>
```

| 인수 | 필수 | 의미와 검증 |
| --- | --- | --- |
| `id` | 예 | `1` 이상의 raw 리뷰 ID |

- raw 원문, 정제 상태, clean, 감정 결과를 하나의 상세 결과로 출력한다.
- 출력에는 항상 `분석 상태`, `감정`, `신뢰도`, `분석 모델`, `분석 시각` 필드를 둔다.
- 감정 결과가 없으면 `분석 상태: 미분석`으로 표시하고 나머지 분석 필드는 `N/A`로 표시한다.
- 감정 결과가 있으면 `분석 상태: 완료`와 저장된 감정·신뢰도·모델·분석 시각을 표시한다.
- 정제 전 `pending` raw는 정제문을 `N/A`, 분석 상태를 `미분석`, 나머지 분석 필드를 `N/A`로 표시한다.
- 정제에 실패한 raw는 `rejection_reason`을 표시하고 정제문을 `N/A`, 분석 상태를 `미분석`, 나머지 분석 필드를 `N/A`로 표시한다.
- `N/A`와 `미분석`은 CLI 표시값이며 DB에 감정 결과로 저장하지 않는다.
- ID가 없으면 종료 코드 `1`을 반환한다.

## 10. `stats`

```bash
python main.py stats [--sentiment positive|negative|neutral]
                     [--product <name>]
                     [--date-from YYYY-MM-DD] [--date-to YYYY-MM-DD]
```

| 인수·옵션 | 필수 | 기본값 | 의미와 검증 |
| --- | --- | --- | --- |
| `--sentiment` | 아니요 | 전체 감정 | 감정 필터 |
| `--product NAME` | 아니요 | 전체 제품 | 제품 필터 |
| `--date-from DATE` | 아니요 | 시작 제한 없음 | 작성일 하한, 포함 |
| `--date-to DATE` | 아니요 | 종료 제한 없음 | 작성일 상한, 포함 |

- 감정 필터가 없으면 전체 clean 리뷰가 통계 범위이며 미분석 리뷰도 clean 리뷰 수와 평균 별점에 포함한다.
- `--sentiment`를 지정하면 해당 감정으로 분석된 리뷰만 범위에 포함하며 미분석 리뷰는 제외한다.
- 분석 완료율의 분모는 통계 범위의 clean 리뷰 수, 분자는 감정 결과가 있는 리뷰 수다.
- 감정별 건수·비율과 평균 신뢰도는 분석 완료 리뷰만으로 계산한다.
- 평균 별점은 통계 범위에서 별점이 있는 모든 clean 리뷰로 계산한다.
- 별점·감정 일치율은 별점과 감정 결과가 모두 있는 리뷰만으로 계산한다.
- clean 리뷰는 있지만 분석 완료 리뷰가 없으면 분석 완료율은 `0.0%`, 감정별 건수는 각각 `0건`, 평균 신뢰도와 일치율은 `N/A`다.
- 통계 범위에 clean 리뷰가 없으면 건수는 `0건`, 분모가 없는 비율과 평균은 `N/A`로 출력하고 종료 코드 `0`을 반환한다.

## 11. `dashboard`

```bash
python main.py dashboard [--product <name>]
                         [--date-from YYYY-MM-DD] [--date-to YYYY-MM-DD]
                         [--top <count>] [--output-dir <path>]
                         [--report-format txt|md]
```

| 인수·옵션 | 필수 | 기본값 | 의미와 검증 |
| --- | --- | --- | --- |
| `--product NAME` | 아니요 | 전체 제품 | 제품 필터 |
| `--date-from DATE` | 아니요 | 시작 제한 없음 | 작성일 하한, 포함 |
| `--date-to DATE` | 아니요 | 종료 제한 없음 | 작성일 상한, 포함 |
| `--top COUNT` | 아니요 | `5` | 긍정·부정 키워드 각각의 최대 개수 |
| `--output-dir PATH` | 아니요 | 설정의 `output` | 출력 디렉터리; 없으면 생성 |
| `--report-format` | 아니요 | `md` | 파일 리포트 형식 |

- 같은 제품·기간 필터이고 limit가 적용되지 않은 최신 유효 인사이트가 있어야 한다.
- 감정 필터나 limit가 적용된 extract 결과는 전체 범위 dashboard에 사용하지 않는다.
- 유효한 인사이트가 없거나 stale이면 파일을 만들지 않고 같은 필터의 `extract` 실행법을 안내한 뒤 종료 코드 `1`을 반환한다.
- 성공 시 콘솔 리포트, TXT/MD 리포트 하나, PNG 차트 3종을 생성한다.
- 날짜나 별점 데이터가 없어도 해당 PNG를 생략하지 않고 “표시할 데이터 없음”을 기록한다.

## 12. `export`

```bash
python main.py export --format csv|xlsx --output <path>
                      [--sentiment positive|negative|neutral]
                      [--rating-min 1..5]
```

| 인수·옵션 | 필수 | 기본값 | 의미와 검증 |
| --- | --- | --- | --- |
| `--format` | 예 | 없음 | `csv` 또는 `xlsx` |
| `--output PATH` | 예 | 없음 | 생성할 파일 경로; 부모 디렉터리가 없으면 생성 |
| `--sentiment` | 아니요 | 전체 감정 | 감정 필터 |
| `--rating-min INT` | 아니요 | 제한 없음 | 최소 별점 `1`~`5`, 포함 |

- 출력 확장자는 `--format`과 일치해야 한다.
- CSV는 UTF-8 BOM으로 기록한다.
- CSV/XLSX에는 clean 필드와 감정, 신뢰도, 분석 시각을 한 행으로 합쳐 기록한다.
- 필터 결과가 없으면 헤더만 있는 파일을 만들고 종료 코드 `0`을 반환한다.

## 13. 변경과 검증 규칙

명령 계약을 변경할 때 다음 문서를 같은 변경에서 검토한다.

1. 이 문서의 문법, 옵션, 기본값, 종료 코드
2. [`../data-flow.md`](../data-flow.md)의 처리 흐름과 예시
3. [`../architecture/data-communication.md`](../architecture/data-communication.md)의 Request/Result DTO
4. [`../README.md`](../README.md)의 문서 지도
5. 구현 후에는 루트 `README.md`의 실제 사용법과 `--help` 출력

CLI 테스트는 다음을 확인한다.

- 9개 명령과 각 `--help`
- 필수·선택 인수와 상호 배타 옵션
- enum, 날짜, ID, 숫자 범위 검증
- 기본값과 config 덮어쓰기
- 결과 출력과 종료 코드 `0`, `1`, `2`
- AI가 필요하지 않은 명령이 API 키 없이 동작함
- `list`가 기본 조회에서 미분석 리뷰를 포함하고 감정 필터에서는 제외함
- 감정·신뢰도 정렬에서 미분석 리뷰가 항상 마지막에 위치함
- `show`가 pending, rejected, 미분석 clean, 분석 완료 상태를 고정된 필드로 표시함
- `stats`가 분석 전·부분 분석·완료 상태에서 정의된 분모와 `N/A` 규칙을 적용함
