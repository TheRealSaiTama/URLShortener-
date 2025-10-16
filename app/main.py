from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy import select
from .db import Base, engine, SessionLocal
from .models import UrlMap
import hashlib
from starlette.responses import RedirectResponse


app = FastAPI(title="url-shorty", version="0.2")
Base.metadata.create_all(engine)

class ShortenIn(BaseModel):
    url: HttpUrl

def mk_code(url: str) -> str:
    return hashlib.blake2b(url.encode(), digest_size=5).hexdigest()[:7]

@app.get("/health") 
def health(): return {"ok": True}

@app.post("/shorten")
def shorten(body: ShortenIn):
    code = mk_code(str(body.url))
    with SessionLocal() as s:
        row = s.execute(select(UrlMap).where(UrlMap.code == code)).scalar_one_or_none()
        if not row:
            s.add(UrlMap(code=code, target=str(body.url))); s.commit()
    return {"code": code, "short_url": f"/{code}"}

@app.get("/{code}")
def resolve(code: str):
    with SessionLocal() as s:
        row = s.execute(select(UrlMap).where(UrlMap.code == code)).scalar_one_or_none()
        if not row: raise HTTPException(404, "code not found")
        return {"target": row.target}

@app.get("/{code}")
def resolve(code: str):
    with SessionLocal() as s:
        row = s.execute(select(UrlMap).where(UrlMap.code == code)).scalar_one_or_none()
        if not row: raise HTTPException(404, "code not found")
        return RedirectResponse(row.target)