from __future__ import annotations

import json
from typing import Optional, Tuple

import redis

from .settings import settings

_r = redis.from_url(settings.REDIS_URL)


def get_target_cached(code: str) -> Optional[tuple[str, int]]:
    v = _r.get(f"c:{code}")
    if not v:
        return None
    try:
        data = json.loads(v)
        return data.get("target"), int(data.get("url_id"))
    except Exception:
        return None


def set_target_cached(code: str, target: str, url_id: int, ttl: int = 86400) -> None:
    payload = json.dumps({"target": target, "url_id": url_id})
    _r.setex(f"c:{code}", ttl, payload)


def del_target_cached(code: str) -> None:
    _r.delete(f"c:{code}")

