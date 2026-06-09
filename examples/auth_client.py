"""Skill 客户端装饰器：管理本地 key，自动处理 code=100 响应并重试。

使用方式：
    from auth_client import with_auth, get_headers

    @with_auth
    def fetch_data():
        return requests.get("http://other-service/api/data", headers=get_headers())

    result = fetch_data()
    # 首次：后端返回 code=100 → 自动保存 key → 重试 → 返回正常响应
    # 后续：直接带 key 请求 → 返回正常响应

环境变量：
    AUTH_KEY_PATH  本地 key 存储路径，默认 ~/.kocotree-skills/auth.json
"""

import json
import os
from functools import wraps
from pathlib import Path

_DEFAULT_KEY_PATH = os.path.join(Path.home(), ".kocotree-skills", "auth.json")
_key_path = os.getenv("AUTH_KEY_PATH", _DEFAULT_KEY_PATH)
_key_cache = None


def _load_key():
    global _key_cache
    if _key_cache:
        return _key_cache
    try:
        with open(_key_path, "r", encoding="utf-8") as f:
            _key_cache = json.load(f)
            return _key_cache
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _save_key(key_data):
    global _key_cache
    os.makedirs(os.path.dirname(_key_path), exist_ok=True)
    with open(_key_path, "w", encoding="utf-8") as f:
        json.dump(key_data, f, indent=2, ensure_ascii=False)
    _key_cache = key_data


def get_headers():
    """返回带 Authorization 的 headers dict，没有 key 则返回空 dict。"""
    data = _load_key()
    api_key = data.get("api_key") if data else None
    if api_key:
        return {"Authorization": f"Bearer {api_key}"}
    return {}


def with_auth(f):
    """装饰器：自动处理 code=100（key 创建）响应，保存 key 后重试。"""
    @wraps(f)
    def decorated(*args, **kwargs):
        resp = f(*args, **kwargs)
        try:
            data = resp.json()
        except (ValueError, AttributeError):
            return resp
        if data.get("code") == 100 and data.get("msg") == "key_created":
            _save_key(data["data"])
            resp = f(*args, **kwargs)
        return resp

    return decorated
