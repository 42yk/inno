import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_profile: str
    gemini_api_key: str
    gemini_model: str
    redis_url: str
    upstash_redis_rest_url: str
    upstash_redis_rest_token: str

    @property
    def is_dev(self) -> bool:
        return self.app_profile == "dev"

    @property
    def is_prod(self) -> bool:
        return self.app_profile == "prod"


def get_settings() -> Settings:
    profile = os.getenv("APP_PROFILE", "dev").strip().lower()
    if profile not in {"dev", "prod"}:
        profile = "dev"

    return Settings(
        app_profile=profile,
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite").strip(),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6380/0").strip(),
        upstash_redis_rest_url=os.getenv("UPSTASH_REDIS_REST_URL", "").strip().rstrip("/"),
        upstash_redis_rest_token=os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip(),
    )
