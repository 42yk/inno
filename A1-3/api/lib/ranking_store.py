from .config import Settings

RANKING_KEY = "menu:ranking"

SAMPLE_RANKING = [
    {"menuName": "제육볶음", "count": 12},
    {"menuName": "김치찌개", "count": 9},
    {"menuName": "돈까스", "count": 7},
    {"menuName": "떡볶이", "count": 6},
    {"menuName": "짬뽕", "count": 5},
    {"menuName": "비빔밥", "count": 4},
    {"menuName": "우동", "count": 4},
    {"menuName": "토마토 파스타", "count": 3},
    {"menuName": "치킨버거 세트", "count": 3},
    {"menuName": "김밥", "count": 2},
]


class RankingStore:
    def __init__(self, settings: Settings):
        self.settings = settings

    def increment(self, menu_name):
        if not menu_name:
            return

        if self.settings.is_prod:
            self._upstash_command(["ZINCRBY", RANKING_KEY, 1, menu_name])
            return

        redis_client = self._dev_redis_client()
        redis_client.zincrby(RANKING_KEY, 1, menu_name)

    def top10(self):
        try:
            if self.settings.is_prod:
                result = self._upstash_command(["ZRANGE", RANKING_KEY, 0, 9, "REV", "WITHSCORES"])
                return self._normalize_pairs(result)

            redis_client = self._dev_redis_client()
            rows = redis_client.zrevrange(RANKING_KEY, 0, 9, withscores=True)
            return [
                {"menuName": self._decode(menu), "count": int(score)}
                for menu, score in rows
            ]
        except Exception:
            return SAMPLE_RANKING

    def _dev_redis_client(self):
        import redis

        return redis.Redis.from_url(self.settings.redis_url, socket_connect_timeout=1, socket_timeout=1)

    def _upstash_command(self, command):
        import requests

        if not self.settings.upstash_redis_rest_url or not self.settings.upstash_redis_rest_token:
            raise RuntimeError("Upstash Redis environment variables are required in prod profile.")

        response = requests.post(
            self.settings.upstash_redis_rest_url,
            headers={
                "Authorization": f"Bearer {self.settings.upstash_redis_rest_token}",
                "Content-Type": "application/json",
            },
            json=command,
            timeout=5,
        )
        response.raise_for_status()
        payload = response.json()
        if "error" in payload and payload["error"]:
            raise RuntimeError(str(payload["error"]))
        return payload.get("result", [])

    def _normalize_pairs(self, rows):
        items = []
        for index in range(0, len(rows), 2):
            try:
                menu_name = self._decode(rows[index])
                count = int(float(rows[index + 1]))
            except (IndexError, TypeError, ValueError):
                continue
            items.append({"menuName": menu_name, "count": count})
        return items or SAMPLE_RANKING

    def _decode(self, value):
        if isinstance(value, bytes):
            return value.decode("utf-8")
        return str(value)
