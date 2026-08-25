# 데이터 및 Firestore 설계

## 1. 원본 CSV

```csv
date,value,memo
2025-01-01,72.4,
2025-01-03,72.1,
```

가져오기 전 기준은 다음과 같다.

- 파일은 UTF-8과 헤더를 사용한다.
- 컬럼은 `date`, `value`, `memo` 순서로 준비한다.
- `date`는 `YYYY-MM-DD`, `value`는 kg 단위 숫자다.
- 날짜나 체중이 없는 행은 제외한다.
- 날짜별 기록을 하나로 확정한다.
- 날짜 오름차순으로 정렬한다.
- 정제 후 유효한 날짜·체중 기록이 100건 이상이어야 한다.

`scripts/import_csv.py`는 파일을 다시 검증하고 등록·건너뜀·실패 건수를 출력한다. 기본 동작은 기존 날짜를 덮어쓰지 않는 것이다.

## 2. `data` 컬렉션

날짜의 유일성을 단순하게 보장하기 위해 `YYYY-MM-DD` 문자열을 Firestore 문서 ID로 사용한다.

```text
data/{date}
```

문서 예시는 다음과 같다.

```json
{
  "date": "2025-01-01",
  "value": 72.4,
  "memo": "",
  "created_at": "Firestore server timestamp",
  "updated_at": "Firestore server timestamp"
}
```

### 필드 규칙

| 필드 | 형식 | 필수 | 규칙 |
|---|---|---:|---|
| `date` | 문자열 | 예 | `YYYY-MM-DD`, 미래 날짜 불가 |
| `value` | 숫자 | 예 | 20.0~300.0kg, 소수점 첫째 자리 |
| `memo` | 문자열 | 아니요 | 기본값 빈 문자열, 최대 200자 |
| `created_at` | timestamp | 예 | 생성 시 서버가 설정 |
| `updated_at` | timestamp | 예 | 생성·수정 시 서버가 설정 |

### 날짜 변경

문서 ID가 날짜이므로 수정 요청에서 날짜가 변경되면 트랜잭션을 사용한다.

1. 기존 문서의 존재를 확인한다.
2. 새 날짜 문서가 존재하지 않는지 확인한다.
3. 새 문서를 생성하면서 기존 `created_at`을 유지하고 `updated_at`을 갱신한다.
4. 기존 문서를 삭제한다.

## 3. `conversations` 컬렉션

Firestore 자동 ID를 사용한다.

```text
conversations/{conversation_id}
```

```json
{
  "title": "3월 평균 체중은?",
  "messages": [
    {
      "role": "user",
      "content": "3월 평균 체중은?",
      "created_at": "2026-08-25T10:00:00+09:00"
    },
    {
      "role": "assistant",
      "content": "3월 평균 체중은 72.1kg입니다.",
      "created_at": "2026-08-25T10:00:02+09:00"
    }
  ],
  "created_at": "Firestore server timestamp",
  "updated_at": "Firestore server timestamp"
}
```

`role`은 `user`와 `assistant`만 저장한다. 시스템 프롬프트와 도구 입출력은 저장하지 않는다. 제목은 첫 사용자 질문을 한 줄로 정규화하고 최대 길이로 잘라 생성한다.

## 4. 요약 계산

요약은 날짜 오름차순의 전체 유효 기록을 입력으로 받는다.

| 결과 | 계산 규칙 |
|---|---|
| `period.start` | 첫 기록 날짜 |
| `period.end` | 마지막 기록 날짜 |
| `count` | 유효 기록 개수 |
| `average` | 전체 체중 평균, 소수점 첫째 자리 반올림 |
| `max.value` | 최고 체중 |
| `max.dates` | 최고 체중이 기록된 모든 날짜 |
| `min.value` | 최저 체중 |
| `min.dates` | 최저 체중이 기록된 모든 날짜 |
| `first` | 첫 날짜와 체중 |
| `latest` | 마지막 날짜와 체중 |
| `change` | 최근 체중 - 최초 체중, 소수점 첫째 자리 반올림 |
| `trend` | 최근 10개와 이전 10개 평균 비교 |

### 추세 규칙

```text
difference = recent_10_average - previous_10_average
```

- `difference < -0.2`: `감소`
- `difference > +0.2`: `증가`
- `-0.2 <= difference <= +0.2`: `유지`
- 유효 기록이 20건 미만: `insufficient_data`

부동소수점 경계 오류를 피하기 위해 계산 내부에서는 `Decimal`을 사용하고 응답 직전에 숫자로 직렬화한다.

## 5. 기간 통계

`start_date`와 `end_date`를 포함하는 폐구간으로 조회한다.

- 시작일과 종료일 당일 기록을 포함한다.
- 기간 내 기록이 없으면 빈 목록 또는 `not_found` 상태를 반환한다.
- 기간 통계에는 기간 내 개수, 평균, 최고·최저와 날짜, 첫·마지막 기록, 변화량을 포함한다.
- 기간 내 20건 이상일 때만 동일한 추세 규칙을 적용하고, 미만이면 `insufficient_data`로 반환한다.

## 6. 인덱스

문서 ID가 날짜이므로 단일 날짜 조회는 문서 직접 조회를 사용한다. 날짜 범위는 문서 ID 또는 `date` 필드에 대한 범위 쿼리를 사용한다. 대화 목록은 `updated_at` 내림차순 쿼리를 사용하며, Firestore가 복합 인덱스를 요구하면 오류가 안내하는 인덱스만 추가한다.
