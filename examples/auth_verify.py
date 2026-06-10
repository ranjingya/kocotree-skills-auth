"""后端 Flask 装饰器：调 auth 服务验证飞书 token。

使用方式：
    from auth_verify import require_auth

    @app.route("/my-api")
    @require_auth
    def my_api():
        return jsonify({"code": 0, "data": "hello", "msg": "ok"})

环境变量：
    AUTH_SERVICE_URL  auth 服务地址，默认 http://kocotree-skills-auth:5050
"""

import os
from functools import wraps

import requests
from flask import jsonify, request

AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://kocotree-skills-auth:5050")
VERIFY_URL = f"{AUTH_SERVICE_URL}/api/v1/auth/verify"


def _verify_token(auth_header):
    """调 auth 服务校验 token，透传 Authorization header。"""
    try:
        resp = requests.get(VERIFY_URL, headers={"Authorization": auth_header}, timeout=5)
        return resp.json()
    except (requests.RequestException, ValueError):
        return None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")

        if not auth_header:
            return jsonify({"code": 401, "data": None, "msg": "Missing access token."}), 401

        result = _verify_token(auth_header)
        if not result or result.get("code") != 0:
            msg = result.get("msg", "Invalid or expired token.") if result else "Auth service unavailable."
            return jsonify({"code": 401, "data": None, "msg": msg}), 401

        return f(*args, **kwargs)

    return decorated
