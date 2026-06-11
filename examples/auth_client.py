"""Skill 客户端：飞书 OAuth 认证，管理本地 token，自动刷新。

使用方式：
    from auth_client import with_auth, get_headers

    @with_auth
    def fetch_data():
        return requests.get("http://other-service/api/data", headers=get_headers())

    result = fetch_data()
    # 首次：打开浏览器飞书授权 → 轮询获取 token → 保存
    # 后续：直接带 token 请求，过期自动刷新

环境变量：
    AUTH_SERVICE_URL  auth 服务地址，默认 http://localhost:5050
    AUTH_TOKEN_PATH   本地 token 存储路径，默认 ~/.kocotree-skills/auth.json
"""

import json
import os
import time
from functools import wraps
from pathlib import Path

import requests

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://121.40.167.37:5050")
_DEFAULT_TOKEN_PATH = os.path.join(Path.home(), ".kocotree-skills", "auth.json")
_token_path = os.getenv("AUTH_TOKEN_PATH", _DEFAULT_TOKEN_PATH)
_token_cache = None

POLL_INTERVAL = 5
POLL_TIMEOUT = 300


def _load_token():
    global _token_cache
    if _token_cache:
        return _token_cache
    try:
        with open(_token_path, "r", encoding="utf-8") as f:
            _token_cache = json.load(f)
            return _token_cache
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _save_token(token_data):
    global _token_cache
    os.makedirs(os.path.dirname(_token_path), exist_ok=True)
    now = int(time.time())
    token_data["access_token_expires_at"] = now + token_data.get("expires_in", 7200)
    token_data["refresh_token_expires_at"] = now + token_data.get("refresh_expires_in", 604800)
    with open(_token_path, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2, ensure_ascii=False)
    _token_cache = token_data


def _is_access_token_expired():
    data = _load_token()
    if not data or "access_token" not in data:
        return True
    return time.time() >= data.get("access_token_expires_at", 0)


def _is_refresh_token_expired():
    data = _load_token()
    if not data or "refresh_token" not in data:
        return True
    return time.time() >= data.get("refresh_token_expires_at", 0)


def _refresh():
    """用 refresh_token 刷新 access_token。"""
    data = _load_token()
    if not data:
        return False
    resp = requests.post(f"{AUTH_SERVICE_URL}/api/v1/auth/refresh", json={
        "refresh_token": data["refresh_token"],
    }, timeout=10)
    result = resp.json()
    if result.get("code") == 0:
        _save_token(result["data"])
        return True
    return False


def _oauth_login():
    """完整 OAuth 流程：打开浏览器授权，轮询 auth 服务获取 token。"""
    resp = requests.get(f"{AUTH_SERVICE_URL}/api/v1/auth/login", timeout=10)
    result = resp.json()
    if result.get("code") != 0:
        raise RuntimeError(f"Failed to get authorize URL: {result.get('msg')}")

    authorize_url = result["data"]["authorize_url"]
    state = result["data"]["state"]

    print("请完成飞书授权，手动在浏览器中打开以下链接：")
    print(authorize_url)

    start = time.time()
    while time.time() - start < POLL_TIMEOUT:
        time.sleep(POLL_INTERVAL)
        try:
            resp = requests.get(
                f"{AUTH_SERVICE_URL}/api/v1/auth/poll",
                params={"state": state},
                timeout=10,
            )
            result = resp.json()
            if result.get("code") == 0:
                _save_token(result["data"])
                print("授权成功。")
                return
        except requests.RequestException:
            pass

    raise RuntimeError("授权超时，请重试。")


def ensure_token():
    """确保本地有有效的 access_token，必要时刷新或重新登录。"""
    if not _is_access_token_expired():
        return

    if not _is_refresh_token_expired():
        if _refresh():
            return

    _oauth_login()


def get_headers():
    """返回带 Authorization 的 headers dict。"""
    ensure_token()
    data = _load_token()
    if data and data.get("access_token"):
        return {"Authorization": f"Bearer {data['access_token']}"}
    return {}


def with_auth(f):
    """装饰器：确保 token 有效后执行，401 时自动刷新重试。"""
    @wraps(f)
    def decorated(*args, **kwargs):
        ensure_token()
        resp = f(*args, **kwargs)
        try:
            data = resp.json()
        except (ValueError, AttributeError):
            return resp
        if resp.status_code == 401 or data.get("code") == 401:
            global _token_cache
            _token_cache = None
            ensure_token()
            resp = f(*args, **kwargs)
        return resp

    return decorated
