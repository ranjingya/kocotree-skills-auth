import json
import os
import re
import tempfile
import time
from functools import lru_cache

from flask import Blueprint, jsonify, request
from markupsafe import escape

from .auth import (
    build_authorize_url,
    exchange_code_for_token,
    refresh_access_token,
    verify_access_token,
)
from .rate_limit import rate_limit

bp = Blueprint("api", __name__, url_prefix="/api/v1")

_PENDING_DIR = os.path.join(tempfile.gettempdir(), "kocotree_auth_pending")
_PENDING_TTL = 300
os.makedirs(_PENDING_DIR, exist_ok=True)

_KK_BASE64_PATH = os.path.join(os.path.dirname(__file__), "assets", "base64.txt")


_STATE_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


def _validate_state(state: str) -> str:
    if not _STATE_RE.match(state):
        raise ValueError(f"Invalid state: {state!r}")
    return state


def _pending_path(state: str) -> str:
    return os.path.join(_PENDING_DIR, f"{_validate_state(state)}.json")


def _save_pending(state: str, token_data: dict):
    with open(_pending_path(state), "w", encoding="utf-8") as f:
        json.dump({"data": token_data, "ts": time.time()}, f)


def _pop_pending(state: str) -> dict | None:
    path = _pending_path(state)
    try:
        with open(path, "r", encoding="utf-8") as f:
            pending = json.load(f)
        if time.time() - pending.get("ts", 0) > _PENDING_TTL:
            os.remove(path)
            return None
        os.remove(path)
        return pending
    except (FileNotFoundError, json.JSONDecodeError, ValueError):
        return None


def _cleanup_pending():
    now = time.time()
    for name in os.listdir(_PENDING_DIR):
        path = os.path.join(_PENDING_DIR, name)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if now - data.get("ts", 0) > _PENDING_TTL:
                os.remove(path)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass


_LOGO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="40" height="32" viewBox="0 0 120 96">'
    '<ellipse cx="60" cy="28" rx="48" ry="26" fill="#2E9B3E"/>'
    '<ellipse cx="32" cy="32" rx="28" ry="22" fill="#2E9B3E"/>'
    '<ellipse cx="88" cy="32" rx="28" ry="22" fill="#2E9B3E"/>'
    '<rect x="16" y="28" width="88" height="8" fill="#2E9B3E"/>'
    '<g fill="#2D2117">'
    '<polygon points="18,58 30,58 42,76 36,76 27,63 18,76 12,76"/>'
    '<polygon points="30,58 36,58 36,76 30,76"/>'
    '<polygon points="60,58 72,58 84,76 78,76 69,63 60,76 54,76"/>'
    '<polygon points="72,58 78,58 78,76 72,76"/>'
    '</g></svg>'
)


@lru_cache(maxsize=1)
def _load_kk_logo_base64() -> str:
    try:
        with open(_KK_BASE64_PATH, "r", encoding="ascii") as f:
            return f.read().strip()
    except OSError:
        return ""


def _render_callback_page(success: bool, error: str = "", name: str = "") -> str:
    if success:
        icon, title = "&#10003;", "&#25480;&#26435;&#25104;&#21151;"
        msg = f"&#27426;&#36814;&#22238;&#26469;&#65292;{name}" if name else "&#24050;&#23436;&#25104;&#25480;&#26435;&#12290;"
        detail = "&#35831;&#36820;&#22238;&#24212;&#29992;&#65292;&#27492;&#39029;&#38754;&#21487;&#23433;&#20840;&#20851;&#38381;&#12290;"
        color = "#10b981"
    else:
        icon, title = "&#10007;", "&#25480;&#26435;&#22833;&#36133;"
        msg = error
        detail = "&#35831;&#20851;&#38381;&#39029;&#38754;&#21518;&#37325;&#35797;&#12290;"
        color = "#ef4444"
    logo_base64 = _load_kk_logo_base64()
    logo_html = (
        f'<img src="data:image/png;base64,{logo_base64}" width="40" height="40" alt="Kocotree">'
        if logo_base64
        else _LOGO_SVG
    )
    return f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Kocotree Auth</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{min-height:100vh;display:flex;align-items:center;justify-content:center;
       font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f0f2f5}}
  .card{{background:#fff;border-radius:8px;overflow:hidden;width:380px;
        box-shadow:0 2px 8px rgba(0,0,0,.08)}}
  .bar{{height:4px;background:{color}}}
  .body{{padding:40px 32px;text-align:center}}
  .badge{{width:56px;height:56px;border-radius:50%;background:{color};color:#fff;
         font-size:28px;display:inline-flex;align-items:center;justify-content:center;
         margin-bottom:16px;font-weight:bold}}
  h1{{font-size:20px;color:#1f2937;margin-bottom:8px}}
  .msg{{font-size:14px;color:#6b7280;margin-bottom:4px}}
  .detail{{font-size:13px;color:#9ca3af}}
  .logo{{margin-top:24px;opacity:.4;display:flex;justify-content:center}}
  .logo img{{display:block;border-radius:8px}}
</style></head>
<body><div class="card">
  <div class="bar"></div>
  <div class="body">
    <div class="badge">{icon}</div>
    <h1>{title}</h1>
    <p class="msg">{msg}</p>
    <p class="detail">{detail}</p>
    <div class="logo">{logo_html}</div>
  </div>
</div></body></html>"""


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
        return _render_callback_page(False, "未收到授权码，请重试。"), 400

    token_data, err = exchange_code_for_token(code)
    if not token_data:
        return _render_callback_page(False, str(escape(err))), 401

    user_info = verify_access_token(token_data["access_token"])
    if user_info:
        token_data["name"] = user_info.get("name", "")
        token_data["open_id"] = user_info.get("open_id", "")

    _cleanup_pending()
    _save_pending(state, token_data)

    name = token_data.get("name", "")
    return _render_callback_page(True, name=name)


@bp.route("/auth/poll", methods=["GET"])
@rate_limit
def poll():
    """客户端轮询：用 state 获取已完成的 token"""
    state = request.args.get("state", "")
    if not state:
        return jsonify({"code": 400, "data": None, "msg": "Missing state."}), 400

    try:
        pending = _pop_pending(state)
    except ValueError:
        return jsonify({"code": 400, "data": None, "msg": "Invalid state."}), 400
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
