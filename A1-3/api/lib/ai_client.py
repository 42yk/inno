import json
import re

from .config import Settings


GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"

MENU_CATALOG = {
    "한식": [
        ("제육볶음", 10000, "계란찜"),
        ("김치찌개", 9000, "공깃밥"),
        ("비빔밥", 9500, "된장국"),
    ],
    "중식": [
        ("짬뽕", 10000, "군만두"),
        ("짜장면", 8000, "탕수육 소"),
        ("마파두부덮밥", 9500, "오이무침"),
    ],
    "일식": [
        ("돈까스", 11000, "미소국"),
        ("우동", 8500, "유부초밥"),
        ("연어덮밥", 14000, "녹차"),
    ],
    "양식": [
        ("토마토 파스타", 13000, "마늘빵"),
        ("치킨 샐러드", 12000, "아이스티"),
        ("리조또", 13500, "탄산수"),
    ],
    "분식": [
        ("떡볶이", 7000, "순대"),
        ("김밥", 4500, "어묵국"),
        ("라면", 5000, "참치김밥"),
    ],
    "패스트푸드": [
        ("치킨버거 세트", 9000, "제로콜라"),
        ("불고기버거 세트", 8500, "감자튀김"),
        ("치킨랩", 8000, "아이스 아메리카노"),
    ],
}


def recommend_menu(data, settings: Settings):
    if settings.is_dev and not settings.gemini_api_key:
        return mock_recommendation(data)

    try:
        return request_gemini_recommendation(data, settings)
    except Exception:
        if settings.is_dev:
            return mock_recommendation(data)
        raise


def request_gemini_recommendation(data, settings: Settings):
    import requests

    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is required in prod profile.")

    prompt = build_prompt(data)
    response = requests.post(
        GEMINI_INTERACTIONS_URL,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": settings.gemini_api_key,
        },
        json={
            "model": settings.gemini_model,
            "input": prompt,
            "system_instruction": "사용자의 조건에 맞는 한국어 메뉴 추천을 JSON으로만 반환한다.",
            "response_format": {
                "type": "text",
                "mime_type": "application/json",
                "schema": recommendation_schema(),
            },
            "generation_config": {
                "max_output_tokens": 400,
            },
            "store": False,
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    text = extract_gemini_text(payload)
    parsed = parse_json_object(text)

    return normalize_recommendation(parsed, data)


def recommendation_schema():
    return {
        "type": "object",
        "properties": {
            "menuName": {"type": "string"},
            "reason": {"type": "string"},
            "estimatedPrice": {"type": "integer"},
            "sideMenu": {"type": "string"},
        },
        "required": ["menuName", "reason", "estimatedPrice", "sideMenu"],
    }


def build_prompt(data):
    return (
        "아래 조건으로 점심/식사 메뉴 하나를 추천해줘.\n"
        f"- 식사 시간: {data['mealTime']}\n"
        f"- 총 예산: {data['budget']}원\n"
        f"- 인원: {data['people']}명\n"
        f"- 음식 종류: {data['foodType']}\n"
        f"- 맵기: {data['spicyLevel']}\n\n"
        "반드시 아래 JSON 형식으로만 답해줘. 마크다운 코드블록은 쓰지 마.\n"
        '{"menuName":"메뉴명","reason":"추천 이유","estimatedPrice":12000,"sideMenu":"사이드 메뉴 또는 음료"}'
    )


def extract_gemini_text(payload):
    chunks = []
    for step in payload.get("steps", []):
        if step.get("type") != "model_output":
            continue
        for item in step.get("content", []):
            if isinstance(item.get("text"), str):
                chunks.append(item["text"])

    for candidate in payload.get("candidates", []):
        content = candidate.get("content", {})
        for part in content.get("parts", []):
            if isinstance(part.get("text"), str):
                chunks.append(part["text"])

    if not chunks:
        raise ValueError("Gemini response did not include output text.")

    return "\n".join(chunks)


def parse_json_object(text):
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def normalize_recommendation(result, data):
    menu_name = str(result.get("menuName", "")).strip()
    reason = str(result.get("reason", "")).strip()
    side_menu = str(result.get("sideMenu", "")).strip()

    try:
        estimated_price = int(result.get("estimatedPrice"))
    except (TypeError, ValueError):
        estimated_price = min(data["budget"], 10000 * data["people"])

    if not menu_name or not reason or not side_menu:
        raise ValueError("Gemini recommendation is missing required fields.")

    estimated_price = max(1000, min(estimated_price, data["budget"]))

    return {
        "menuName": menu_name,
        "reason": reason,
        "estimatedPrice": estimated_price,
        "sideMenu": side_menu,
    }


def mock_recommendation(data):
    food_type = data["foodType"]
    candidates = []

    if food_type == "상관없음":
        for items in MENU_CATALOG.values():
            candidates.extend(items)
    else:
        candidates = MENU_CATALOG.get(food_type, MENU_CATALOG["한식"])

    budget_per_person = max(1000, data["budget"] // data["people"])
    affordable = [item for item in candidates if item[1] <= budget_per_person]
    menu_name, price, side_menu = affordable[0] if affordable else min(candidates, key=lambda item: item[1])
    total_price = min(price * data["people"], data["budget"])

    spicy_note = {
        "안 매움": "자극적이지 않아 부담 없이 먹기 좋습니다.",
        "보통": "무난한 간으로 함께 먹기 좋습니다.",
        "매움": "매콤한 맛이 식사 만족감을 높여줍니다.",
    }[data["spicyLevel"]]

    return {
        "menuName": menu_name,
        "reason": f"{data['mealTime']}에 어울리고 {data['people']}명이 예산 안에서 먹기 좋습니다. {spicy_note}",
        "estimatedPrice": total_price,
        "sideMenu": side_menu,
    }
