from flask import Blueprint, jsonify, request

from . import storage
from .auth import require_api_key
from .rate_limit import rate_limit

bp = Blueprint("api", __name__, url_prefix="/api/v1")


@bp.route("/keys", methods=["POST"])
@rate_limit
def create_key():
    """创建新的 API Key，原始 key 仅在此响应中出现一次"""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "")
    expires_in_days = data.get("expires_in_days", 30)
    result = storage.create_key(name=name, expires_in_days=expires_in_days)
    return jsonify({"code": 0, "data": result, "msg": "ok"}), 201


@bp.route("/auth/verify", methods=["GET"])
@rate_limit
@require_api_key
def verify():
    """验证 API Key 是否有效，通过返回 200，不通过由装饰器返回 401"""
    return jsonify({"code": 0, "data": None, "msg": "ok"})


@bp.route("/keys", methods=["GET"])
@rate_limit
@require_api_key
def list_keys():
    """列出所有 API Key 的基本信息（不含哈希和原始 key）"""
    keys = storage.list_keys()
    return jsonify({"code": 0, "data": keys, "msg": "ok"})


@bp.route("/keys/revoke", methods=["POST"])
@rate_limit
@require_api_key
def revoke_key():
    """通过 id 撤销指定 API Key"""
    data = request.get_json(silent=True) or {}
    key_id = data.get("id")
    if not key_id:
        return jsonify({"code": 400, "data": None, "msg": "Missing id field."}), 400
    if not storage.revoke_by_id(int(key_id)):
        return jsonify({"code": 404, "data": None, "msg": "Key not found or already revoked."}), 404
    return jsonify({"code": 0, "data": None, "msg": "ok"})
