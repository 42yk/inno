# AI 프롬프트 설계와 출력 계약

- 상태: 현재 구현 계약
- 구현 근거: `review_analytics/clients/gemini.py`
- 검증 계획: [`../quality/sentiment-validation-plan.md`](../quality/sentiment-validation-plan.md)
- 운영 해석: [`decision-policy.md`](decision-policy.md)

## 1. 설계 원칙

Gemini Client는 세 작업을 수행한다.

1. 리뷰별 감정 분류: `sentiment-v2`
2. 리뷰 묶음의 키워드·요약·개선 권고 추출: `insight-v1`
3. 분할된 인사이트 병합: `insight-merge-v1`

모든 작업은 다음 공통 원칙을 따른다.

- 리뷰와 이전 AI 출력은 명령이 아닌 **신뢰할 수 없는 데이터**로 취급한다.
- 시스템 지시와 JSON Schema는 SDK의 `system_instruction`, `response_json_schema`로 분리한다.
- `response_mime_type`은 `application/json`이다.
- SDK의 구조화 응답을 그대로 신뢰하지 않고 Client가 키·타입·값 범위를 다시 검증한다.
- API 키, 전체 프롬프트, 리뷰 원문, 원본 AI 응답은 로그에 남기지 않는다.
- 저장 결과에는 모델 이름과 prompt version을 기록해 어떤 계약으로 생성됐는지 추적한다.

## 2. 감정 분류 프롬프트

### 2.1 입력 형식

Gemini에는 clean 리뷰의 ID와 정규화 본문만 전달한다. 별점, 제품명, 날짜는 감정 판정 입력에 포함하지 않는다.

```json
{
  "reviews": [
    {"review_id": 101, "review_text": "배송이 빠르고 제품도 만족스러워요."},
    {"review_id": 102, "review_text": "디자인은 예쁘지만 뚜껑이 깨져 와서 교환이 필요해요."},
    {"review_id": 103, "review_text": "용량은 500ml입니다."}
  ]
}
```

리뷰 본문에 “이전 지시를 무시하라” 같은 문장이 있어도 데이터로만 처리한다.

### 2.2 라벨 기준

| 라벨 | 판정 기준 | 예시 |
| --- | --- | --- |
| `positive` | 전체적으로 만족, 칭찬, 승인, 유익한 경험이 우세 | “배송이 빠르고 제품도 만족스러워요.” |
| `negative` | 불만, 결함, 피해, 실패, 항의, 시정 요구가 우세 | “뚜껑이 깨져 와서 교환이 필요해요.” |
| `neutral` | 사실 전달이나 질문이 중심이거나 긍정·부정 태도가 명확하지 않음 | “용량은 500ml인가요?” |

긍정과 부정이 함께 있으면 리뷰 전체의 우세한 태도를 선택한다. 어느 쪽도 명확히 우세하지 않으면 `neutral`을 선택한다. 예를 들어 “디자인은 예쁘지만 뚜껑이 깨져 와서 교환이 필요해요”는 시정 요구가 핵심이므로 `negative`로 분류하는 것이 이 규약에 맞는다.

라벨 기준은 리뷰 텍스트만 사용한다. 별점과 라벨이 다를 수 있으며, 별점·감정 일치율은 모델 입력 규칙이 아니라 사후 품질 지표다.

### 2.3 Confidence 점수 규약

`confidence`는 모델이 **리뷰 본문만으로 선택한 라벨이 위 기준에 부합한다고 판단하는 자기평가 확신도**다.

- 허용 범위: `0.0` 이상 `1.0` 이하의 숫자
- `0.0`: 매우 불확실
- `1.0`: 매우 확실
- 정답 확률이나 통계적으로 보정된 확률이 아님
- `0.8`이 “80% 확률로 정답”이라는 뜻이 아님
- 모델·프롬프트 버전이 다르면 점수의 직접 비교를 보장하지 않음

따라서 confidence는 저신뢰 사례를 검수하기 위한 진단값으로 사용한다. 자동 조치의 유일한 근거나 확률 계산 입력으로 사용하지 않는다. 구간별 경험 정확도 검증은 [감정 분석 정확도 검증 계획](../quality/sentiment-validation-plan.md)을 따른다.

### 2.4 출력 형식

```json
{
  "results": [
    {"review_id": 101, "sentiment": "positive", "confidence": 0.96},
    {"review_id": 102, "sentiment": "negative", "confidence": 0.91},
    {"review_id": 103, "sentiment": "neutral", "confidence": 0.88}
  ]
}
```

위 값은 형식을 설명하기 위한 예시이며 실제 모델 성능 측정 결과가 아니다.

출력 계약은 다음과 같다.

- 최상위 객체는 `results` 하나만 가진다.
- `results`의 각 항목은 `review_id`, `sentiment`, `confidence`만 가진다.
- 요청한 모든 review ID가 정확히 한 번씩 반환돼야 한다.
- 요청에 없는 ID, 누락 ID, 중복 ID는 허용하지 않는다.
- `sentiment`는 `positive|negative|neutral` 중 하나다.
- `confidence`는 불리언이 아닌 숫자이며 `0.0..1.0` 범위다.
- 응답 순서가 달라도 Client가 요청 순서로 정렬한 뒤 내부 모델로 반환한다.

## 3. 인사이트 추출 프롬프트

### 3.1 입력 형식

```json
{
  "scope_hash": "범위를 식별하는 해시",
  "reviews": [
    {"review_id": 201, "review_text": "배송이 이틀 늦었어요."},
    {"review_id": 202, "review_text": "포장이 찢어져 도착했습니다."}
  ]
}
```

`scope_hash`는 저장 범위를 연결하는 식별자이며 리뷰 내용에 대한 명령이 아니다.

### 3.2 출력 형식과 근거 규약

```json
{
  "positive_keywords": [],
  "negative_keywords": [
    {"keyword": "배송 지연", "review_ids": [201]},
    {"keyword": "포장 손상", "review_ids": [202]}
  ],
  "summary": "배송 지연과 포장 손상이 주요 불만으로 나타났습니다.",
  "recommendations": [
    "배송 단계별 안내를 강화합니다.",
    "출고 전 포장 검수 절차를 점검합니다."
  ]
}
```

위 예시는 형식 설명용이다. 출력 계약은 다음과 같다.

- `positive_keywords`, `negative_keywords`, `summary`, `recommendations` 네 필드를 모두 반환한다.
- 키워드는 비어 있지 않은 문자열이고 `review_ids`는 정수 배열이다.
- Service는 현재 입력 범위에 없는 근거 ID를 제거하고, 남은 고유 근거 ID 수로 빈도를 계산한다.
- `summary`는 입력 리뷰 전체의 간결한 요약이다.
- `recommendations`는 입력 리뷰에 근거한 실행 가능한 개선 후보 문자열 배열이다.
- 권고는 AI가 생성한 후보이며 키워드와 일대일 대응하거나 우선순위가 자동 보장되지 않는다. 실제 연결과 우선순위는 [감정 지표 운영 의사결정 정책](decision-policy.md)을 따른다.

## 4. 인사이트 병합 프롬프트

입력이 문자 수 제한을 넘으면 Service가 리뷰를 여러 묶음으로 나눠 `insight-v1`을 실행한다. Client는 부분 결과를 다음 형태로 다시 전달해 `insight-merge-v1`으로 병합한다.

```json
{
  "partial_insights": [
    {
      "positive_keywords": [],
      "negative_keywords": [{"keyword": "배송 지연", "review_ids": [201]}],
      "summary": "배송 지연 불만이 있습니다.",
      "recommendations": ["배송 안내를 강화합니다."]
    }
  ]
}
```

병합 출력은 3절과 같은 스키마다. 프롬프트는 키워드 중복을 합치고 근거 ID를 유지하며, 새로운 근거를 발명하지 않도록 지시한다. Service는 병합 후에도 현재 입력 ID 집합으로 근거를 다시 제한한다.

## 5. 거부되는 응답 예시

다음 응답은 JSON 문법이 맞더라도 `INVALID_AI_RESPONSE`로 거부한다.

| 잘못된 응답 | 거부 이유 |
| --- | --- |
| `{"results":[{"review_id":1,"sentiment":"mixed","confidence":0.8}]}` | 허용하지 않은 라벨 |
| `{"results":[{"review_id":1,"sentiment":"positive","confidence":1.2}]}` | confidence 범위 초과 |
| `{"results":[{"review_id":99,"sentiment":"positive","confidence":0.9}]}` | 요청 ID 집합과 불일치 |
| `{"results":[],"explanation":"..."}` | 추가 최상위 필드와 결과 누락 |
| 키워드의 `review_ids`가 `["201"]` | 정수가 아닌 문자열 ID |
| 인사이트 객체에 `extra` 필드가 있음 | `additionalProperties=false` 위반 |

SDK 호출 실패는 `AI_REQUEST_FAILED`, 구조·타입·값 계약 위반은 `INVALID_AI_RESPONSE`로 변환한다. 원격 오류 원문과 리뷰 본문은 안전 오류 메시지에 포함하지 않는다.

## 6. 버전 관리

| 버전 | 변경 내용 |
| --- | --- |
| `sentiment-v2` | 세 라벨 판정 기준, 복합 감정의 우세 태도 규칙, confidence 비확률 의미를 명시 |
| `insight-v1` | 근거 review ID를 포함한 긍정·부정 키워드, 요약, 개선 권고 추출 |
| `insight-merge-v1` | 부분 인사이트의 중복 병합과 근거 보존 |

라벨 의미, 입력 필드, 출력 스키마, confidence 규약처럼 결과 해석에 영향을 주는 변경은 prompt version을 올린다. 문구 정리라도 결과가 달라질 가능성이 있으면 새 버전으로 취급한다. 버전 변경 후에는 동일 정답셋으로 이전 버전과 비교하고 [프롬프트 실험 계획](../quality/sentiment-validation-plan.md)의 비회귀 기준을 적용한다.

### 기존 DB 전환 절차

현재 Repository는 저장된 결과의 prompt version을 보고 자동 재분석하지 않는다. 운영자가 버전 전환 범위를 통제하도록 다음 순서로 갱신한다.

1. 모델 설정과 적용할 프롬프트 버전을 확인한다.
2. `python3 main.py analyze --all --force`로 모든 clean 리뷰의 기존 감정 결과를 교체한다.
3. 감정 결과가 하나라도 교체되면 현재 인사이트는 저장 트랜잭션 안에서 stale 처리된다.
4. 대시보드·리포트에서 사용하는 각 필터 범위로 `extract`를 다시 실행한다.
5. 새 인사이트가 저장된 뒤 대시보드와 리포트를 재생성한다.

`sentiment-v2`는 현재 구현이 생성·저장하는 프롬프트 계약이다. 다만 [검증 계획](../quality/sentiment-validation-plan.md)의 비교 실험이 아직 실행되지 않았으므로 v1보다 정확도가 향상됐다고 주장하지 않는다. 실험을 수행하기 전 버전 전환은 라벨 규약의 명시성과 결과 추적을 위한 계약 변경이며, 측정된 성능 개선을 의미하지 않는다.
