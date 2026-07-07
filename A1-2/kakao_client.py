from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

from config import Settings


KAKAO_KEYWORD_SEARCH_ENDPOINT = "https://dapi.kakao.com/v2/local/search/keyword.json"


# 오류 목록에 장소 검색 단계의 오류 정보를 추가합니다.
def add_place_error(errors: list[dict], error_type: str, message: str) -> None:
    errors.append(
        {
            "step": "place_search",
            "type": error_type,
            "message": message,
        }
    )


# Kakao Local 키워드 검색 요청 파라미터를 만듭니다.
def build_search_params(city: str, size: int) -> dict[str, str]:
    safe_size = max(1, min(size, 15))
    return {
        "query": f"{city} 맛집",
        "category_group_code": "FD6",
        "size": str(safe_size),
        "page": "1",
        "sort": "accuracy",
    }


# Kakao Local API에 GET 요청을 보내고 JSON 응답을 반환합니다.
def request_kakao_keyword_search(params: dict[str, str], settings: Settings, timeout: int = 10) -> dict:
    query = urllib.parse.urlencode(params)
    url = f"{KAKAO_KEYWORD_SEARCH_ENDPOINT}?{query}"
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"KakaoAK {settings.kakao_rest_api_key}",
        },
        method="GET",
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        response_body = response.read().decode("utf-8")
    return json.loads(response_body)


# 문자열 좌표를 float 좌표로 안전하게 변환합니다.
def parse_coordinate(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# Kakao 장소 문서를 과제 요구 필드로 정규화합니다.
def normalize_place(document: dict) -> dict:
    x = parse_coordinate(document.get("x"))
    y = parse_coordinate(document.get("y"))
    address = document.get("road_address_name") or document.get("address_name") or ""

    place = {
        "name": document.get("place_name", ""),
        "address": address,
        "category": document.get("category_name", ""),
        "url": document.get("place_url", ""),
    }

    if x is not None:
        place["x"] = x
    if y is not None:
        place["y"] = y

    return place


# HTTP 상태 코드에 따라 과제에서 요구한 오류 타입으로 분류합니다.
def map_http_error_type(status_code: int) -> str:
    if status_code in {401, 403}:
        return "AUTH_ERROR"
    if status_code == 429:
        return "QUOTA_ERROR"
    return "HTTP_ERROR"


# 추천 도시를 기준으로 Kakao Local에서 맛집을 검색합니다.
def search_restaurants(city: str, settings: Settings, errors: list[dict], size: int = 5) -> list[dict]:
    city = city.strip()
    if not city:
        add_place_error(errors, "INVALID_CITY", "recommended_city is empty")
        return []

    params = build_search_params(city, size)

    try:
        data = request_kakao_keyword_search(params, settings)
    except urllib.error.HTTPError as error:
        error_type = map_http_error_type(error.code)
        add_place_error(errors, error_type, f"HTTP {error.code}")
        return []
    except urllib.error.URLError as error:
        add_place_error(errors, "NETWORK_ERROR", str(error.reason))
        return []
    except TimeoutError:
        add_place_error(errors, "NETWORK_ERROR", "request timeout")
        return []
    except json.JSONDecodeError:
        add_place_error(errors, "PARSE_ERROR", "Kakao response is not valid JSON")
        return []

    documents = data.get("documents")
    if not isinstance(documents, list) or not documents:
        add_place_error(errors, "EMPTY_RESULT", f"0 results for query={params['query']}")
        return []

    return [normalize_place(document) for document in documents[:size]]
