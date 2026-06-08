import os
from dataclasses import dataclass


@dataclass
class Settings:
    database_path: str = os.getenv("KKTREE_DB_PATH", "keys.db")
    rate_limit_requests: int = int(os.getenv("KKTREE_RATE_LIMIT", "60"))
    rate_limit_window_seconds: int = int(os.getenv("KKTREE_RATE_WINDOW", "60"))


settings = Settings()
