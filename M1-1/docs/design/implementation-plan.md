# 서울 장기 기온 분석 구현 설계와 실행 계획

## 1. 목표

기상청 ASOS 서울 지점 `108`의 1994~2024년 일자료를 원본 그대로 보존하고, 표준 CSV로 정규화한 뒤 장기 기온 추세와 통계적 이상 기온 후보를 재현 가능하게 분석한다. 구현은 `src/seoul_weather/` 패키지로 제공하며 패키지 실행과 콘솔 실행이 같은 코드를 사용한다.

## 2. 완료 정의

- 31개 연도의 원본 바깥 ZIP, 안쪽 ZIP, CSV와 SHA-256 manifest가 존재한다.
- 가공 CSV는 서울 지점, 기간, 날짜 완전성과 스키마 검증을 통과하며 누락 날짜가 하나라도 있으면 분석을 중단한다.
- 결측치를 0이나 보간값으로 대체하지 않고 통계적 이상 기온 후보를 삭제하지 않는다.
- 연평균·5년 이동평균·선형 추세·월별 편차·월내 z 점수를 계산한다.
- 고정 이름의 PNG 3개와 분석 요약 JSON을 생성한다.
- `download`, `analyze`, `run`을 패키지 명령과 콘솔 명령으로 모두 제공한다.
- 단위·통합·workflow·CLI·산출물 테스트와 새 Python 3.10 환경의 전체 실행을 통과한다.
- Git 커밋은 생성하지 않는다.

## 3. 기술 선택

| 항목 | 선택 |
| --- | --- |
| Python | 3.10 이상 |
| 구현 형식 | Python 패키지와 `.py` 모듈, 노트북 미사용 |
| 패키지 배치 | `src` layout |
| 빌드 백엔드 | setuptools |
| 데이터 처리 | pandas, numpy |
| 수집 | requests, BeautifulSoup |
| 시각화 | matplotlib, Pillow |
| 테스트 | pytest |
| 설치 메타데이터 | `pyproject.toml` |
| 직접 의존성 버전 | `requirements.txt` |

패키지 방식은 같은 함수를 CLI와 테스트가 공유해 전체 실행을 자동 검증하기 위해 선택했다. 회귀 기울기와 결정계수는 numpy로 계산한다. 미래 예측, 시계열 분해, 머신러닝 모델과 웹 서비스는 추가하지 않는다.

## 4. 데이터 계약

### 4.1 수집 범위

| 항목 | 값 |
| --- | --- |
| 제공기관 | 기상청 국가기후데이터센터 |
| 자료 | 종관기상관측(ASOS) 일자료 |
| 지점 | 서울 `108` |
| 기간 | 1994-01-01~2024-12-31 |
| 연도 수 | 31개 |
| 예상 달력 일수 | 11,323일 |

### 4.2 표준 CSV

`data/processed/seoul_weather_daily.csv`는 다음 8개 열을 가진다.

| 열 | 자료형 | 규칙 |
| --- | --- | --- |
| `station_id` | 정수 | 모두 `108` |
| `station_name` | 문자열 | 모두 `서울` |
| `date` | 날짜 | 하루 한 행, 오름차순 |
| `avg_temp_c` | 실수/결측 | 임의 대체 금지 |
| `min_temp_c` | 실수/결측 | 임의 대체 금지 |
| `max_temp_c` | 실수/결측 | 임의 대체 금지 |
| `precipitation_mm` | 실수/결측 | 공백을 자동으로 0 변환 금지 |
| `avg_humidity_pct` | 실수/결측 | 0~100 범위 검사 |

직접 준비한 표준 CSV도 [수동 데이터 입력 지침](../guides/manual-data-input.md)의 완전성·출처 기록 조건을 만족해야 한다.

## 5. 모듈 설계

### 5.1 수집과 원본 보존

`seoul_weather.collection`이 담당한다.

- `portal.py`: 검색 요청 payload, HTML 식별자 파싱, 재시도 세션과 다운로드
- `archives.py`: ZIP 매직 바이트·압축 유효성 검사, 중첩 압축 해제, 해시
- `manifest.py`: manifest 원자적 저장, 연도·지점·항목 수와 파일 크기·해시 재검증
- `pipeline.py`: 연도별 파일 재사용 또는 수집, 31개 연도 전체 조정

오류 HTML, 손상 ZIP, 검색 결과 0개·복수개, 기존 파일 해시 불일치는 명시적 오류로 중단한다. 자동 수집은 편의 기능이며 표준 CSV 직접 제공 시 생략할 수 있다.

### 5.2 정규화와 통합

`seoul_weather.processing`이 담당한다.

- `schema.py`: 원본 필수 컬럼과 표준 컬럼 정의
- `normalize.py`: CP949 CSV 해석, 숫자·날짜 변환, 지점·연도 확인
- `dataset.py`: manifest에 기록된 연도별 CSV 통합, 중복 원본 위치·제거 수 진단, 충돌 확인, 표준 CSV 입출력

동일한 중복 날짜는 하나로 합치고 원본 파일·CSV 행·제거 수를 manifest의 처리 진단에 기록한다. 값이 충돌하는 날짜는 양쪽 원본 위치와 함께 오류로 중단한다. 전체 검증 전에는 가공 결과를 최종 경로로 교체하지 않는다.

### 5.3 분석

`seoul_weather.analytics`가 담당한다.

- 기간·지점·날짜 완전성·결측·기온 `-50~50°C` 품질검사선·기온 순서 검증
- 연·월·계절과 일교차, 30일 후행 이동평균 파생
- 월 80%, 연 95% 관측률 적용
- 연평균, 전년 차이, 5년 후행 이동평균과 `°C/10년` 선형 추세
- 같은 달 전체를 모집단으로 한 z 점수와 `±2.5` 후보 분류
- 문서와 테스트가 공유하는 JSON 요약 생성

통계 함수는 파일 입출력과 분리한다. 후보 분류는 탐색 기준이며 공식 이상기후 판정이나 관측 오류 삭제 기준으로 사용하지 않는다.

### 5.4 시각화

`seoul_weather.visualization`이 담당한다.

- 쓰기 가능한 matplotlib·fontconfig 캐시 설정
- 한글 글꼴 선택
- 연평균 추세, 월별 편차 heatmap, 일별 이상 기온 후보 PNG 생성
- 임시 경로에서 세 PNG를 모두 완성한 뒤 workflow에 전달

### 5.5 workflow와 CLI

`seoul_weather.workflows`가 유스케이스를 조정한다.

| 명령 | workflow | 처리 순서 |
| --- | --- | --- |
| `download` | `run_download()` | 수집 또는 보존 원자료 재통합 → 표준 CSV |
| `analyze` | `run_analysis()` | 표준 CSV 검증 → 분석 → JSON·PNG |
| `run` | `run_pipeline()` | `run_download()` → `run_analysis()` |

`seoul_weather.cli.main()`은 `argparse` 인자를 workflow 호출로 변환하고 도메인 오류를 종료 코드 `1`로 바꾼다. `seoul_weather.__main__`과 `pyproject.toml`의 콘솔 진입점이 같은 `main()`을 호출한다.

`workflows/outputs.py`는 요약 JSON과 PNG가 staging에 모두 생성된 뒤 기존 최종 파일을 backup하고 일괄 승격한다. 다중 파일 승격 중 하나라도 실패하면 이미 교체한 파일을 제거하고 backup을 복구한다.

통합 `run`은 가공 CSV를 staging 경로에 만든 뒤 그 파일을 분석한다. 분석 결과도 별도 staging 경로에 만들고, 가공 CSV·요약 JSON·PNG 3개가 모두 완성된 경우에만 한 승격·복구 계층으로 최종 경로를 교체한다. 분석 실패뿐 아니라 최종 파일 교체 도중 실패해도 기존 가공 데이터와 분석 산출물이 서로 다른 실행 결과로 섞이지 않는다.

## 6. 실행 계약

### 패키지 실행

```bash
python -m seoul_weather download
python -m seoul_weather analyze
python -m seoul_weather run
```

### 콘솔 실행

```bash
seoul-weather download
seoul-weather analyze
seoul-weather run
```

`--rebuild-from-raw`는 네트워크 없이 보존 CSV와 manifest를 검증해 표준 CSV를 다시 만든다. 표준 CSV를 직접 준비했다면 `analyze`만 실행한다.

## 7. 테스트 전략

| 테스트 영역 | 검증 내용 |
| --- | --- |
| `tests/collection/` | 포털 파싱, ZIP 검사, 중첩 압축, manifest, 기존 파일 재사용 |
| `tests/analytics/` | 데이터 품질, 집계 경계, 이동평균, 추세, z 점수, 요약 |
| `tests/visualization/` | PNG 3개 유효성, 쓰기 가능한 글꼴 캐시 |
| `tests/workflows/` | analyze와 download→analyze 실행 순서·인자 전달 |
| `tests/deliverables/` | JSON과 README·REPORT 수치, 이미지 링크, 필수 섹션 |
| `tests/test_cli.py` | 하위 명령, 경로 옵션, 오류 종료 코드 |

네트워크 단위 테스트는 실제 서버에 연결하지 않고 fixture와 가짜 세션을 사용한다. 실데이터 수집은 별도 재현 검증으로 수행한다.

## 8. 구현 및 리뷰 순서

1. 패키지 설정과 경로·CLI 계약 테스트를 작성한다.
2. 기존 수집 기능을 `collection`과 `processing`으로 이동하고 관련 테스트를 통과시킨다.
3. 계산을 `analytics`, 렌더링을 `visualization`으로 이동하고 기존 결과와 비교한다.
4. `download`, `analyze`, `run` workflow와 두 실행 진입점을 구현한다.
5. 루트의 중복 실행 코드를 제거하고 전체 테스트를 실행한다.
6. README, REPORT와 `docs/` 문서를 실제 구조·명령에 맞춘다.
7. 새 Python 3.10 환경에서 editable 설치, 패키지·콘솔 실행, 전체 테스트와 산출물을 검증한다.
8. 요구사항·코드·문서·결과를 리뷰하고 발견 사항을 수정한 뒤 전체 검증을 반복한다.

각 단계는 `실패 테스트 → 구현 → 관련 테스트 → 전체 회귀 → 문서 대조 → 리뷰` 순환을 따른다.

## 9. 위험과 대응

| 위험 | 대응 |
| --- | --- |
| 포털 HTML 구조 변경 | 결과 0개·복수개를 실패시키고 fixture와 파서를 함께 갱신 |
| 오류 HTML을 ZIP으로 저장 | 매직 바이트와 `ZipFile` 검사 후 저장 |
| 일부 연도만 성공 | 전체 31개 연도 완료 전 가공 CSV 교체 금지 |
| 기존 원본 변경 | manifest 해시 불일치 시 덮어쓰지 않고 중단 |
| 결측으로 집계 왜곡 | 월·연 관측률 기준 미달 값을 NaN으로 유지 |
| 통계 후보를 오류로 오인 | 삭제하지 않고 원자료와 후보 기준을 함께 기록 |
| README와 결과 불일치 | 산출물 테스트에서 JSON 수치와 문서 비교 |
| 패키지·콘솔 동작 차이 | 동일한 `cli.main()`과 workflow 공유 |

## 10. 최종 검증 명령

```bash
python3.10 -m venv /tmp/m1-1-verification/venv
/tmp/m1-1-verification/venv/bin/python -m pip install -e .
/tmp/m1-1-verification/venv/bin/python -m seoul_weather run --rebuild-from-raw
/tmp/m1-1-verification/venv/bin/seoul-weather run --rebuild-from-raw
/tmp/m1-1-verification/venv/bin/python -m pytest -q
```

검증 결과에는 Python·라이브러리 버전, 행 수·기간, CSV SHA-256, 핵심 통계, PNG 유효성, 테스트 수와 종료 코드를 기록한다. 개인 임시 경로는 최종 사용자 안내에 고정값으로 요구하지 않는다.
