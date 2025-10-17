from datetime import datetime, timedelta, timezone
import hashlib
import secrets

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel, HttpUrl, Field
from sqlalchemy import func, select
from starlette.responses import RedirectResponse, PlainTextResponse

from .db import Base, SessionLocal, engine
from .models import UrlMap, Visit
from .ratelimit import LIMIT, allow
from .settings import settings
from .validation import validate_target
from .cache import get_target_cached, set_target_cached, del_target_cached
from prometheus_client import Counter, Histogram, generate_latest


BASE_URL = settings.BASE_URL.rstrip("/")
RESERVED_CODES = {"health", "_healthz", "_readyz", "docs", "openapi.json", "metrics", "stats"}

app = FastAPI(title="url-shorty", version="0.3")

@app.middleware("http")
async def rate_limit(request, call_next):
    ip = request.client.host if request.client else "unknown"
    if not allow(ip):
        from starlette.responses import JSONResponse

        return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
    return await call_next(request)


# Prometheus metrics
REQS = Counter("http_requests_total", "", ["path", "method", "status"])
LAT = Histogram("http_request_latency_seconds", "", ["path", "method"])


@app.middleware("http")
async def metrics_mw(request, call_next):
    import time as _t

    st = _t.perf_counter()
    resp = await call_next(request)
    LAT.labels(request.url.path, request.method).observe(_t.perf_counter() - st)
    REQS.labels(request.url.path, request.method, str(resp.status_code)).inc()
    return resp


class ShortenIn(BaseModel):
    url: HttpUrl
    alias: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]{4,32}$")


class ExpireIn(BaseModel):
    expires_at: datetime | None = None


def mk_code(url: str, salt: str = "") -> str:
    h = hashlib.blake2b((url + salt).encode(), digest_size=5).hexdigest()
    return h[:7]


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/shorten", status_code=201)
def shorten(body: ShortenIn, response: Response):
    # Guardrails: avoid self-shortening to prevent redirect loops
    from urllib.parse import urlparse

    def is_own(short: str) -> bool:
        return urlparse(short).netloc == urlparse(settings.BASE_URL).netloc

    target = str(body.url)
    if is_own(target):
        raise HTTPException(status_code=400, detail="refusing to shorten own short URL")

    # validate scheme and host (SSRF guard)
    try:
        target = validate_target(target)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # choose code
    if body.alias:
        if body.alias in RESERVED_CODES:
            raise HTTPException(status_code=409, detail="alias is reserved")
        code = body.alias
    else:
        code = mk_code(target)

    with SessionLocal() as s:
        row = s.execute(select(UrlMap).where(UrlMap.code == code)).scalar_one_or_none()
        if row:
            if row.target == target:
                short = f"{BASE_URL}/{code}"
                response.headers["Location"] = short
                return {"code": code, "short_url": short}
            if body.alias:
                # alias exists but points to another target
                raise HTTPException(status_code=409, detail="alias already in use")
            # collision: rehash with a tiny salt until unique
            while row:
                code = mk_code(target, salt=secrets.token_hex(2))
                row = s.execute(select(UrlMap).where(UrlMap.code == code)).scalar_one_or_none()
        s.add(UrlMap(code=code, target=target))
        s.commit()
        # best-effort cache fill
        created = s.execute(select(UrlMap).where(UrlMap.code == code)).scalar_one()
        set_target_cached(code, created.target, created.id)
    short = f"{BASE_URL}/{code}"
    response.headers["Location"] = short
    return {"code": code, "short_url": short}


@app.get("/{code}")
def resolve(code: str, request: Request):
    with SessionLocal() as s:
        cached = get_target_cached(code)
        url_id: int | None = None
        target: str | None = None
        if cached:
            target, url_id = cached
        else:
            row = s.execute(select(UrlMap).where(UrlMap.code == code)).scalar_one_or_none()
            if not row:
                raise HTTPException(status_code=404, detail="code not found")
            # expiry/disabled checks
            now = datetime.now(timezone.utc)
            if (row.expires_at and row.expires_at <= now) or row.disabled:
                raise HTTPException(status_code=410, detail="link expired or disabled")
            url_id = row.id
            target = row.target
            set_target_cached(code, target, url_id)

        # log visit
        s.add(
            Visit(
                url_id=url_id,
                ip=request.client.host if request.client else "unknown",
                ua=request.headers.get("user-agent", ""),
                ref=request.headers.get("referer", ""),
            )
        )
        s.commit()
        return RedirectResponse(url=target, status_code=307)


@app.get("/stats/{code}")
def stats(code: str):
    with SessionLocal() as s:
        url = s.execute(select(UrlMap).where(UrlMap.code == code)).scalar_one_or_none()
        if not url:
            raise HTTPException(status_code=404, detail="code not found")

        total = s.scalar(
            select(func.count(Visit.id)).where(Visit.url_id == url.id)
        ) or 0

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        recent = s.scalar(
            select(func.count(Visit.id)).where(
                Visit.url_id == url.id, Visit.ts > cutoff
            )
        ) or 0

        return {
            "code": code,
            "target": url.target,
            "clicks_total": int(total),
            "clicks_24h": int(recent),
        }


@app.patch("/expire/{code}")
def expire(code: str, body: ExpireIn):
    with SessionLocal() as s:
        row = s.execute(select(UrlMap).where(UrlMap.code == code)).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="code not found")
        row.expires_at = body.expires_at
        s.add(row)
        s.commit()
        del_target_cached(code)
        return {"code": code, "expires_at": row.expires_at.isoformat() if row.expires_at else None}


@app.get("/_healthz")
def liveness():
    return {"ok": True}


@app.get("/_readyz")
def readiness():
    import redis

    try:
        with SessionLocal() as s:
            s.execute(select(UrlMap).limit(1))
        redis.from_url(settings.REDIS_URL).ping()
        return {"ready": True}
    except Exception:
        raise HTTPException(status_code=503, detail="not ready")


@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type="text/plain")
