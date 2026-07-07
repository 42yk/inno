from __future__ import annotations

import json
import urllib.error
import urllib.request

from config import Settings


GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions"
REQUIRED_REPORT_SECTIONS = [
    "# {date} 국내 여행 추천 리포트",
    "## 추천 지역",
    "## 추천 이유",
    "## 날씨 요약",
    "## 행사/축제",
    "## 맛집 추천",
    "## 1일 일정 제안",
    "## 오류 요약(errors)",
]


class GeminiError(Exception):
    pass


# Gemini API에 공통 POST 요청을 보내고 응답 텍스트를 반환합니다.
def call_gemini(
    prompt: str,
    system_instruction: str,
    settings: Settings,
    temperature: float = 0.2,
    response_format: dict | None = None,
    timeout: int = 30,
) -> str:
    payload = {
        "model": settings.gemini_model,
        "system_instruction": system_instruction,
        "input": prompt,
        "generation_config": {
            "temperature": temperature,
        },
    }
    if response_format:
        payload["response_format"] = response_format

    request = urllib.request.Request(
        GEMINI_ENDPOINT,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": settings.gemini_api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        raise GeminiError(f"Gemini API HTTP 오류({error.code}): {message}") from error
    except urllib.error.URLError as error:
        raise GeminiError(f"Gemini API 네트워크 오류: {error.reason}") from error
    except TimeoutError as error:
        raise GeminiError("Gemini API 요청 시간이 초과되었습니다.") from error

    try:
        response_data = json.loads(response_body)
    except json.JSONDecodeError as error:
        raise GeminiError("Gemini API 응답을 JSON으로 해석하지 못했습니다.") from error

    return extract_text_from_interaction_response(response_data)


# Gemini 응답 객체에서 출력 텍스트를 가능한 응답 형태별로 추출합니다.
def extract_text_from_interaction_response(response_data: dict) -> str:
    output_text = response_data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    text = response_data.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()

    steps = response_data.get("steps")
    if isinstance(steps, list):
        for step in reversed(steps):
            step_text = _extract_text_from_content(step)
            if step_text:
                return step_text

    candidates = response_data.get("candidates")
    if isinstance(candidates, list):
        for candidate in candidates:
            candidate_text = _extract_text_from_content(candidate)
            if candidate_text:
                return candidate_text

    raise GeminiError("Gemini API 응답에서 출력 텍스트를 찾지 못했습니다.")


# 중첩된 응답 구조에서 text 또는 output_text 값을 찾아 합칩니다.
def _extract_text_from_content(value: object) -> str:
    found: list[str] = []

    if isinstance(value, dict):
        for key in ("output_text", "text"):
            text = value.get(key)
            if isinstance(text, str) and text.strip():
                found.append(text.strip())

        for key in ("content", "parts", "output", "outputs", "messages"):
            nested = value.get(key)
            nested_text = _extract_text_from_content(nested)
            if nested_text:
                found.append(nested_text)

    elif isinstance(value, list):
        for item in value:
            item_text = _extract_text_from_content(item)
            if item_text:
                found.append(item_text)

    return "\n".join(found).strip()


# Markdown 코드블록으로 감싸진 JSON 응답을 순수 텍스트로 정리합니다.
def strip_markdown_code_fence(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


# Gemini structured output에 전달할 추천 JSON 스키마를 반환합니다.
def build_recommendation_response_format() -> dict:
    return {
        "type": "text",
        "mime_type": "application/json",
        "schema": {
            "type": "object",
            "properties": {
                "recommended_city": {
                    "type": "string",
                    "description": "국내 여행 추천 지역명. 예: 제주, 강릉, 부산",
                },
                "weather": {
                    "type": "string",
                    "description": "해당 시기의 일반적인 날씨 요약",
                },
                "events": {
                    "type": "array",
                    "description": "행사 또는 축제 후보 1~3개",
                    "items": {"type": "string"},
                    "minItems": 1,
                    "maxItems": 3,
                },
                "reason": {
                    "type": "string",
                    "description": "추천 근거 2~4문장",
                },
            },
            "required": ["recommended_city", "weather", "events", "reason"],
        },
    }


# 날짜를 바탕으로 1차 여행지 추천 프롬프트를 만듭니다.
def build_recommendation_prompt(date: str) -> str:
    return (
        f"여행 날짜: {date}\n"
        "이 날짜에 국내에서 여행하기 좋은 지역 1곳을 추천하고, "
        "일반적인 날씨 요약, 행사/축제 후보 1~3개, 추천 근거 2~4문장을 작성해줘."
    )


# 파싱 실패 후 재요청할 때 사용할 보정 프롬프트를 만듭니다.
def build_retry_prompt(date: str, previous_output: str) -> str:
    return (
        f"여행 날짜: {date}\n"
        "이전 응답은 JSON 파싱에 실패했습니다. 아래 필수 키만 포함한 JSON 객체 하나만 다시 출력해줘.\n"
        "- recommended_city: string\n"
        "- weather: string\n"
        "- events: array of string\n"
        "- reason: string\n\n"
        f"이전 응답:\n{previous_output}"
    )


# 1차 추천 JSON의 필수 키와 타입을 검증합니다.
def validate_recommendation(data: object) -> dict:
    if not isinstance(data, dict):
        raise ValueError("추천 결과는 JSON 객체여야 합니다.")

    required_string_keys = ("recommended_city", "weather", "reason")
    for key in required_string_keys:
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"추천 결과의 {key} 값이 비어 있거나 문자열이 아닙니다.")

    events = data.get("events")
    if not isinstance(events, list) or not all(isinstance(item, str) for item in events):
        raise ValueError("추천 결과의 events 값은 문자열 배열이어야 합니다.")
    cleaned_events = [event.strip() for event in events if event.strip()]
    if not 1 <= len(cleaned_events) <= 3:
        raise ValueError("추천 결과의 events 값은 1~3개의 비어 있지 않은 문자열이어야 합니다.")

    return {
        "recommended_city": data["recommended_city"].strip(),
        "weather": data["weather"].strip(),
        "events": cleaned_events,
        "reason": data["reason"].strip(),
    }


# Gemini로 여행지 추천 JSON을 생성하고 파싱 실패 시 1회 재시도합니다.
def generate_recommendation(date: str, settings: Settings) -> dict:
    system_instruction = (
        "너는 국내 여행 추천 도우미다. 반드시 response_format의 JSON 스키마를 만족하는 "
        "JSON만 출력한다. 실제 날씨/행사의 정확도보다 구조화된 출력과 다음 API 입력으로 "
        "사용할 수 있는 도시명이 중요하다."
    )
    response_format = build_recommendation_response_format()
    prompt = build_recommendation_prompt(date)
    previous_output = ""

    for attempt in range(2):
        if attempt == 1:
            prompt = build_retry_prompt(date, previous_output)

        raw_text = call_gemini(
            prompt=prompt,
            system_instruction=system_instruction,
            settings=settings,
            temperature=0.2,
            response_format=response_format,
        )
        previous_output = raw_text

        try:
            parsed = json.loads(strip_markdown_code_fence(raw_text))
            return validate_recommendation(parsed)
        except (json.JSONDecodeError, ValueError) as error:
            if attempt == 1:
                raise GeminiError(f"Gemini 추천 JSON 파싱 실패: {error}") from error

    raise GeminiError("Gemini 추천 JSON 파싱에 실패했습니다.")


# 리포트 생성에 전달할 입력 데이터를 문자열 프롬프트로 직렬화합니다.
def build_report_prompt(date: str, recommendation: dict, restaurants: list[dict], errors: list[dict]) -> str:
    payload = {
        "date": date,
        "recommendation": recommendation,
        "restaurants": restaurants,
        "errors": errors,
    }
    return (
        "아래 입력 데이터만 사용해서 여행 리포트를 Markdown으로 작성해줘.\n"
        "맛집 목록이 비어 있으면 맛집 추천 섹션에 데이터 없음이라고 써줘.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


# 최종 Markdown 리포트에 필수 섹션이 모두 있는지 확인합니다.
def find_missing_report_sections(date: str, markdown: str) -> list[str]:
    expected_sections = [
        section.format(date=date) if "{date}" in section else section
        for section in REQUIRED_REPORT_SECTIONS
    ]
    return [section for section in expected_sections if section not in markdown]


# 누락된 Markdown 섹션을 보완하도록 Gemini 재요청 프롬프트를 만듭니다.
def build_report_retry_prompt(original_prompt: str, previous_output: str, missing_sections: list[str]) -> str:
    missing_text = "\n".join(f"- {section}" for section in missing_sections)
    return (
        f"{original_prompt}\n\n"
        "이전 리포트에는 아래 필수 Markdown 섹션이 누락되었습니다.\n"
        f"{missing_text}\n\n"
        "위 섹션을 모두 포함한 Markdown 리포트 전체를 다시 작성해줘.\n"
        "이전 응답:\n"
        f"{previous_output}"
    )


# Gemini로 최종 Markdown 여행 리포트를 생성합니다.
def generate_report(
    date: str,
    recommendation: dict,
    restaurants: list[dict],
    errors: list[dict],
    settings: Settings,
) -> str:
    system_instruction = (
        "너는 국내 여행 리포트 작성자다. 입력된 추천 JSON, 맛집 목록, 오류 목록만 근거로 "
        "Markdown 리포트를 작성한다. 반드시 추천 지역, 추천 이유, 날씨 요약, 행사/축제, "
        "맛집 추천, 1일 일정 제안, 오류 요약(errors) 섹션을 포함한다."
    )
    prompt = build_report_prompt(date, recommendation, restaurants, errors)
    previous_output = ""
    missing_sections: list[str] = []

    for attempt in range(2):
        if attempt == 1:
            prompt = build_report_retry_prompt(prompt, previous_output, missing_sections)

        report = call_gemini(
            prompt=prompt,
            system_instruction=system_instruction,
            settings=settings,
            temperature=0.4,
        )
        missing_sections = find_missing_report_sections(date, report)
        if not missing_sections:
            return report
        previous_output = report

    missing_text = ", ".join(missing_sections)
    raise GeminiError(f"최종 리포트 필수 섹션 누락: {missing_text}")


# Gemini 리포트 생성 실패 시에도 결과물이 남도록 로컬 Markdown을 만듭니다.
def build_fallback_report(date: str, recommendation: dict, restaurants: list[dict], errors: list[dict]) -> str:
    events = recommendation.get("events") or []
    event_lines = "\n".join(f"- {event}" for event in events) if events else "- 데이터 없음"

    if restaurants:
        restaurant_lines = "\n".join(
            f"- {item.get('name', '이름 없음')} / {item.get('address', '주소 없음')} / "
            f"{item.get('category', '카테고리 없음')} / {item.get('url', 'URL 없음')}"
            for item in restaurants
        )
    else:
        restaurant_lines = "- 데이터 없음 (장소 검색 결과 0건 또는 검색 실패)"

    if errors:
        error_lines = "\n".join(
            f"- [{error.get('step', 'unknown')}] {error.get('type', 'ERROR')}: {error.get('message', '')}"
            for error in errors
        )
    else:
        error_lines = "- 없음"

    return f"""# {date} 국내 여행 추천 리포트

## 추천 지역
{recommendation.get("recommended_city", "데이터 없음")}

## 추천 이유
{recommendation.get("reason", "데이터 없음")}

## 날씨 요약
{recommendation.get("weather", "데이터 없음")}

## 행사/축제
{event_lines}

## 맛집 추천
{restaurant_lines}

## 1일 일정 제안
- 오전: 추천 지역의 대표 명소를 가볍게 둘러봅니다.
- 오후: 지역 행사나 축제 후보를 확인하고 방문합니다.
- 저녁: 맛집 추천 목록이 있으면 가까운 곳을 선택해 식사합니다.

## 오류 요약(errors)
{error_lines}
"""
