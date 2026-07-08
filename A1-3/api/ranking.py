from http.server import BaseHTTPRequestHandler

try:
    from api.lib.config import get_settings
    from api.lib.http import send_json, send_options
    from api.lib.ranking_store import RankingStore
except ModuleNotFoundError:
    from lib.config import get_settings
    from lib.http import send_json, send_options
    from lib.ranking_store import RankingStore


class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        send_options(self)

    def do_GET(self):
        settings = get_settings()
        items = RankingStore(settings).top10()
        send_json(self, 200, {"items": items, "profile": settings.app_profile})

    def do_POST(self):
        send_json(self, 405, {"message": "Method Not Allowed"})
