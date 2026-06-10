import os
from dataclasses import dataclass


@dataclass
class Settings:
    feishu_app_id: str = os.getenv("FEISHU_APP_ID", "")
    feishu_app_secret: str = os.getenv("FEISHU_APP_SECRET", "")
    feishu_redirect_uri: str = os.getenv("FEISHU_REDIRECT_URI", "http://localhost:5050/api/v1/auth/redirect")
    rate_limit_requests: int = int(os.getenv("RATE_LIMIT", "60"))
    rate_limit_window_seconds: int = int(os.getenv("RATE_WINDOW", "60"))


settings = Settings()
