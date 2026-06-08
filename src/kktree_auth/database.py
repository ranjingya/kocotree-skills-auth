import sqlite3
from contextlib import contextmanager

from .config import settings

# 后续增加账号等其他关联表
_SCHEMA = """\
CREATE TABLE IF NOT EXISTS api_keys (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自增主键
    key_hash    TEXT NOT NULL UNIQUE,               -- API Key 的 SHA-256 哈希
    short_id    TEXT NOT NULL,                      -- 前8位+后4位，用于识别和撤销
    name        TEXT NOT NULL DEFAULT '',           -- key 名称
    created_at  TEXT NOT NULL,                      -- 创建时间 ISO 8601
    expires_at  TEXT,                               -- 过期时间，NULL 表示永不过期
    revoked     INTEGER NOT NULL DEFAULT 0,         -- 0=有效 1=已撤销
    last_used   TEXT                                -- 最后使用时间
);
CREATE INDEX IF NOT EXISTS idx_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_short_id ON api_keys(short_id);
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def get_db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript(_SCHEMA)
