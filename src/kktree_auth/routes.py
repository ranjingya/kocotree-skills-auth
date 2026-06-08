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
    expires_in_days = data.get("expires_in_days")
    result = storage.create_key(name=name, expires_in_days=expires_in_days)
    return jsonify(result), 201


@bp.route("/auth/verify", methods=["GET"])
@rate_limit
@require_api_key
def verify(current_key):
    """验证 API Key 是否有效，返回 key 元信息"""
    return jsonify({
        "valid": True,
        "name": current_key.get("name"),
        "short_id": current_key.get("short_id"),
        "created_at": current_key.get("created_at"),
        "expires_at": current_key.get("expires_at"),
    }), 200


@bp.route("/keys", methods=["GET"])
@rate_limit
@require_api_key
def list_keys():
    """列出所有 API Key 的基本信息（不含哈希和原始 key）"""
    keys = storage.list_keys()
    return jsonify(keys)


@bp.route("/keys/revoke", methods=["POST"])
@rate_limit
@require_api_key
def revoke_key():
    """通过 short_id 撤销指定 API Key"""
    data = request.get_json(silent=True) or {}
    short_id = data.get("short_id")
    if not short_id:
        return jsonify({"error": "Missing short_id field."}), 400
    if not storage.revoke_by_short_id(short_id):
        return jsonify({"error": "Key not found or already revoked."}), 404
    return jsonify({"detail": "Key revoked."})



