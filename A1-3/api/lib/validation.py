ALLOWED_MEAL_TIMES = {"아침", "점심", "저녁", "야식"}
ALLOWED_FOOD_TYPES = {"한식", "중식", "일식", "양식", "분식", "패스트푸드", "상관없음"}
ALLOWED_SPICY_LEVELS = {"안 매움", "보통", "매움"}


def parse_integer(value):
    if isinstance(value, bool):
        raise ValueError

    if isinstance(value, int):
        return value

    if isinstance(value, str):
        text = value.strip()
        if text.isdecimal():
            return int(text)

    raise ValueError


def validate_recommend_payload(payload):
    meal_time = str(payload.get("mealTime", "")).strip()
    budget_value = payload.get("budget")
    people_value = payload.get("people")
    food_type = str(payload.get("foodType", "")).strip()
    spicy_level = str(payload.get("spicyLevel", "")).strip()

    if not meal_time or budget_value in (None, "") or people_value in (None, "") or not food_type or not spicy_level:
        return None, "필수 항목을 입력해주세요."

    if meal_time not in ALLOWED_MEAL_TIMES or food_type not in ALLOWED_FOOD_TYPES or spicy_level not in ALLOWED_SPICY_LEVELS:
        return None, "필수 항목을 입력해주세요."

    try:
        budget = parse_integer(budget_value)
    except ValueError:
        return None, "예산은 숫자로 입력해주세요."

    try:
        people = parse_integer(people_value)
    except ValueError:
        return None, "인원은 1명 이상 입력해주세요."

    if budget < 1000:
        return None, "예산은 1,000원 이상 입력해주세요."

    if budget > 100000:
        return None, "예산은 100,000원 이하로 입력해주세요."

    if people < 1:
        return None, "인원은 1명 이상 입력해주세요."

    if people > 20:
        return None, "인원은 20명 이하로 입력해주세요."

    return {
        "mealTime": meal_time,
        "budget": budget,
        "people": people,
        "foodType": food_type,
        "spicyLevel": spicy_level,
    }, ""
