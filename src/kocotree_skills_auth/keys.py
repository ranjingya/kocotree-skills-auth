import hashlib
import secrets


# 生成原始key，长度默认为32字节（256位），前缀 kk_
def generate_api_key(length_bytes: int = 32) -> str:
    raw = secrets.token_urlsafe(length_bytes)
    return f"kk_{raw}"


def hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def get_short_id(api_key: str) -> str:
    return f"{api_key[:8]}...{api_key[-4:]}"
