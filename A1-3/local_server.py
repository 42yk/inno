import mimetypes
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from api.lib.ai_client import recommend_menu
from api.lib.config import get_settings
from api.lib.http import read_json, send_json, send_options
from api.lib.ranking_store import RankingStore
from api.lib.validation import validate_recommend_payload

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / "frontend"


class LocalHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        send_options(self)

    def do_GET(self):
        if self.path.startswith("/api/ranking"):
            settings = get_settings()
            send_json(self, 200, {"items": RankingStore(settings).top10(), "profile": settings.app_profile})
            return

        self.serve_static()

    def do_POST(self):
        if not self.path.startswith("/api/recommend"):
            send_json(self, 404, {"message": "Not Found"})
            return

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

    def serve_static(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            file_path = FRONTEND / "index.html"
        else:
            file_path = FRONTEND / path.lstrip("/")

        try:
            resolved = file_path.resolve()
            if not str(resolved).startswith(str(FRONTEND.resolve())) or not resolved.is_file():
                self.send_error(404)
                return

            content = resolved.read_bytes()
            content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except OSError:
            self.send_error(500)


def main():
    port = 8000
    server = HTTPServer(("127.0.0.1", port), LocalHandler)
    print(f"Local server running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
