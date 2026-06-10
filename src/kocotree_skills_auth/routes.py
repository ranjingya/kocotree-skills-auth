import time

from flask import Blueprint, jsonify, request

from .auth import (
    build_authorize_url,
    exchange_code_for_token,
    refresh_access_token,
    verify_access_token,
)
from .rate_limit import rate_limit

bp = Blueprint("api", __name__, url_prefix="/api/v1")

_pending_tokens: dict[str, dict] = {}
_PENDING_TTL = 300


def _cleanup_pending():
    now = time.time()
    expired = [k for k, v in _pending_tokens.items() if now - v["ts"] > _PENDING_TTL]
    for k in expired:
        _pending_tokens.pop(k, None)


@bp.route("/auth/login", methods=["GET"])
@rate_limit
def login():
    """返回飞书 OAuth 授权链接"""
    url, state = build_authorize_url()
    return jsonify({"code": 0, "data": {"authorize_url": url, "state": state}, "msg": "ok"})


@bp.route("/auth/redirect", methods=["GET"])
def redirect_callback():
    """飞书 OAuth 回调：接收 code，换 token，暂存供客户端轮询"""
    code = request.args.get("code")
    state = request.args.get("state", "")

    if not code:
        return "<h3>授权失败</h3><p>未收到授权码，请重试。</p>", 400

    token_data, err = exchange_code_for_token(code)
    if not token_data:
        return f"<h3>授权失败</h3><p>{err}</p>", 401

    _cleanup_pending()
    _pending_tokens[state] = {"data": token_data, "ts": time.time()}

    return "<h3>授权成功</h3><p>请返回终端，可以关闭此页面。</p>"


@bp.route("/auth/poll", methods=["GET"])
@rate_limit
def poll():
    """客户端轮询：用 state 获取已完成的 token"""
    state = request.args.get("state", "")
    if not state:
        return jsonify({"code": 400, "data": None, "msg": "Missing state."}), 400

    pending = _pending_tokens.pop(state, None)
    if not pending:
        return jsonify({"code": 202, "data": None, "msg": "Waiting for authorization."})

    return jsonify({"code": 0, "data": pending["data"], "msg": "ok"})


@bp.route("/auth/callback", methods=["POST"])
@rate_limit
def callback():
    """接收授权码，换取 access_token + refresh_token（备用）"""
    data = request.get_json(silent=True) or {}
    code = data.get("code")
    if not code:
        return jsonify({"code": 400, "data": None, "msg": "Missing code."}), 400

    token_data, err = exchange_code_for_token(code)
    if not token_data:
        return jsonify({"code": 401, "data": None, "msg": err}), 401

    return jsonify({"code": 0, "data": token_data, "msg": "ok"})


@bp.route("/auth/refresh", methods=["POST"])
@rate_limit
def refresh():
    """用 refresh_token 刷新 access_token"""
    data = request.get_json(silent=True) or {}
    refresh_token = data.get("refresh_token")
    if not refresh_token:
        return jsonify({"code": 400, "data": None, "msg": "Missing refresh_token."}), 400

    token_data, err = refresh_access_token(refresh_token)
    if not token_data:
        return jsonify({"code": 401, "data": None, "msg": err}), 401

    return jsonify({"code": 0, "data": token_data, "msg": "ok"})


@bp.route("/auth/verify", methods=["GET"])
@rate_limit
def verify():
    """验证飞书 access_token 是否有效"""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        access_token = auth_header[7:]
    elif auth_header:
        access_token = auth_header
    else:
        return jsonify({"code": 401, "data": None, "msg": "Missing access token."}), 401

    user_info = verify_access_token(access_token)
    if not user_info:
        return jsonify({"code": 401, "data": None, "msg": "Invalid or expired token."}), 401

    return jsonify({"code": 0, "data": user_info, "msg": "ok"})
