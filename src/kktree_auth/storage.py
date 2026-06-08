from datetime import datetime, timedelta, timezone

from .database import get_db
from .keys import generate_api_key, get_short_id, hash_key


def create_key(name: str = "", expires_in_days: int | None = None) -> dict:
    # 生成原始key，计算hash和前缀，设置过期时间
    raw_key = generate_api_key()
    key_hash = hash_key(raw_key)
    short_id = get_short_id(raw_key)
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=expires_in_days)) if expires_in_days else None

    with get_db() as conn:
        conn.execute(
            "INSERT INTO api_keys (key_hash, short_id, name, created_at, expires_at) VALUES (?, ?, ?, ?, ?)",
            (key_hash, short_id, name, now.isoformat(), expires_at.isoformat() if expires_at else None),
        )

    return {
        "api_key": raw_key,
        "short_id": short_id,
        "name": name,
        "created_at": now.isoformat(),
        "expires_at": expires_at.isoformat() if expires_at else None,
    }


def lookup_by_hash(key_hash: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM api_keys WHERE key_hash = ? AND revoked = 0",
            (key_hash,),
        ).fetchone()
        return dict(row) if row else None


def update_last_used(key_hash: str):
    with get_db() as conn:
        conn.execute(
            "UPDATE api_keys SET last_used = ? WHERE key_hash = ?",
            (datetime.now(timezone.utc).isoformat(), key_hash),
        )


def revoke_by_short_id(short_id: str) -> bool:
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE api_keys SET revoked = 1 WHERE short_id = ? AND revoked = 0",
            (short_id,),
        )
        return cur.rowcount > 0


def list_keys() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, short_id, name, created_at, expires_at, revoked, last_used FROM api_keys ORDER BY created_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]
