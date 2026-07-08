from http.server import BaseHTTPRequestHandler

try:
    from api.lib.ai_client import recommend_menu
    from api.lib.config import get_settings
    from api.lib.http import read_json, send_json, send_options
    from api.lib.ranking_store import RankingStore
    from api.lib.validation import validate_recommend_payload
except ModuleNotFoundError:
    from lib.ai_client import recommend_menu
    from lib.config import get_settings
    from lib.http import read_json, send_json, send_options
    from lib.ranking_store import RankingStore
    from lib.validation import validate_recommend_payload


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        send_options(self)

    def do_POST(self):
        try:
            payload = read_json(self)
        except Exception:
            send_json(self, 400, {"message": "필수 항목을 입력해주세요."})
            return

        data, error = validate_recommend_payload(payload)
        if error:
            send_json(self, 400, {"message": error})
            return

        settings = get_settings()

        try:
            result = recommend_menu(data, settings)
        except Exception:
            send_json(self, 502, {"message": "추천 결과를 가져오지 못했습니다. 잠시 후 다시 시도해주세요."})
            return

        try:
            RankingStore(settings).increment(result["menuName"])
        except Exception:
            pass

        send_json(self, 200, {"result": result, "profile": settings.app_profile})

    def do_GET(self):
        send_json(self, 405, {"message": "Method Not Allowed"})
