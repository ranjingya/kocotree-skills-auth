from datetime import datetime, timezone
from functools import wraps
import inspect

from flask import jsonify, request

from .keys import hash_key
from .storage import lookup_by_hash, update_last_used


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
        else:
            api_key = request.args.get("api_key")

        if not api_key:
            return jsonify({"error": "Missing API key. Provide via Authorization: Bearer <key> header or api_key query param."}), 401

        key_hash = hash_key(api_key)
        record = lookup_by_hash(key_hash)

        if not record:
            return jsonify({"error": "Invalid API key."}), 401

        if record.get("expires_at"):
            expires = datetime.fromisoformat(record["expires_at"])
            if datetime.now(timezone.utc) > expires:
                return jsonify({"error": "API key expired."}), 401

        update_last_used(key_hash)

        # 如果视图函数声明了 current_key 参数，则注入
        if "current_key" in inspect.signature(f).parameters:
            kwargs["current_key"] = record
        return f(*args, **kwargs)

    return decorated
