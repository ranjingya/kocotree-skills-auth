import time
from collections import defaultdict
from functools import wraps

from flask import jsonify, request

from .config import settings

_requests: dict[str, list[float]] = defaultdict(list)


def rate_limit(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            key = auth_header[7:]
        else:
            key = request.args.get("api_key") or request.remote_addr
        window = settings.rate_limit_window_seconds
        max_requests = settings.rate_limit_requests
        now = time.time()

        timestamps = [t for t in _requests[key] if now - t < window]
        if timestamps:
            _requests[key] = timestamps
        else:
            _requests.pop(key, None)

        if len(_requests.get(key, [])) >= max_requests:
            return jsonify({"error": f"Rate limit exceeded. Max {max_requests} requests per {window}s."}), 429

        _requests[key].append(now)
        return f(*args, **kwargs)

    return decorated
