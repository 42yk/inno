# README 설치 안내 및 공개 결과 예시 설계

## 목표

README의 설치 절차를 현재 사용 방식에 맞추고, 실제 `output/` 생성물을 저장소에서 바로 확인할 수 있는 공개 예시로 제공한다.

## 승인된 결정

- 지원 Python 버전은 기존 기준인 `3.10 이상`으로 안내한다.
- 설치 전 `python3 --version`으로 버전을 확인하도록 안내한다.
- 의존성 설치 명령은 다음 한 줄을 사용한다.

  ```bash
  python3 -m pip install --user --break-system-packages -r requirements.txt
  ```

- 현재 셸에 `python` 명령이 없으므로 CLI 실행과 테스트 예시도 설치에 사용한 `python3`로 통일한다.
- `.venv` 생성·활성화 및 Windows PowerShell 가상환경 안내는 제거한다.
- `output/`은 실행 때마다 바뀌는 로컬 생성물로 계속 Git에서 제외한다.
- 공개 예시는 `public/examples/`에 별도 스냅샷으로 보관한다.
- PNG 세 개는 원래 이름을 유지하고 README에서 직접 표시한다.
- `output/test.csv`와 `output/test.xlsx`는 공개 목적이 드러나도록 각각 `reviews.csv`, `reviews.xlsx`로 복사하고 README에 다운로드 링크를 제공한다.
- 예시 파일은 재생성하거나 내용을 바꾸지 않고 현재 `output/` 파일을 그대로 복사한다.

## README 구성

`빠른 시작` 다음에 `완성 결과 예시` 절을 추가한다. 이 절은 예시 생성 명령을 설명하고 다음 결과를 제공한다.

1. 감정 분포 PNG
2. 일별 감정 비율 추이 PNG
3. 별점별 감정 건수 PNG
4. CSV 결과 링크
5. XLSX 결과 링크

공개 예시는 특정 실행 시점의 스냅샷이며, 사용자가 CLI를 실행하면 기본적으로 `output/`에 새 결과가 생성된다는 점을 함께 명시한다.

## 범위 제외

- Python 코드, CLI 계약, 설정 또는 테스트 동작은 변경하지 않는다.
- `output/review_sentiment_report.md`는 이번 요청의 이미지·CSV·XLSX 범위에 포함하지 않는다.
- 현재 결과를 다시 생성하기 위한 Gemini API 호출은 수행하지 않는다.

## 완료 조건

- README에서 Python `3.10 이상` 확인 방법과 승인된 설치 명령을 확인할 수 있다.
- README의 설치·실행·테스트 명령은 같은 `python3` 인터프리터를 사용한다.
- `public/examples/`의 다섯 파일이 원본과 바이트 단위로 일치한다.
- README의 이미지와 다운로드 상대 링크가 모두 실제 파일을 가리킨다.
- `.gitignore`의 `/output/` 제외 정책은 유지되고 `public/examples/` 파일은 제외되지 않는다.
