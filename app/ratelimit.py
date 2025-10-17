from __future__ import annotations

import time
from collections import deque
from threading import Lock

import redis
from redis.exceptions import RedisError

from .settings import settings

WINDOW = 60
LIMIT = 120

_redis = redis.from_url(settings.REDIS_URL)
_fallback_buckets: dict[str, deque[float]] = {}
_fallback_lock = Lock()


def _fallback_allow(ip: str, now: float) -> bool:
    with _fallback_lock:
        dq = _fallback_buckets.setdefault(ip, deque())
        while dq and now - dq[0] > WINDOW:
            dq.popleft()
        if len(dq) >= LIMIT:
            return False
        dq.append(now)
        return True


def allow(ip: str) -> bool:
    now = time.time()
    key = f"rl:{ip}"
    try:
        ts = f"{int(now)}-{int(now * 1_000_000)}"
        pipe = _redis.pipeline()
        pipe.zremrangebyscore(key, 0, now - WINDOW)
        pipe.zadd(key, {ts: now})
        pipe.zcard(key)
        pipe.expire(key, WINDOW)
        _, _, count, _ = pipe.execute()
        return count <= LIMIT
    except RedisError:
        return _fallback_allow(ip, now)


def reset(ip: str | None = None) -> None:
    pattern = f"rl:{ip}" if ip else None
    try:
        if ip:
            _redis.delete(pattern)
        else:
            for key in _redis.scan_iter("rl:*"):
                _redis.delete(key)
    except RedisError:
        pass

    with _fallback_lock:
        if ip:
            _fallback_buckets.pop(ip, None)
        else:
            _fallback_buckets.clear()
