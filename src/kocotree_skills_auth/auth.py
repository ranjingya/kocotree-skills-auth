from functools import wraps
import time

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
            return jsonify({"code": 401, "data": None, "msg": "Missing API key."}), 401

        key_hash = hash_key(api_key)
        record = lookup_by_hash(key_hash)

        if not record:
            return jsonify({"code": 401, "data": None, "msg": "Invalid API key."}), 401

        if record.get("expires_ts") and time.time() > record["expires_ts"]:
            return jsonify({"code": 401, "data": None, "msg": "API key expired."}), 401

        update_last_used(key_hash)
        return f(*args, **kwargs)

    return decorated
