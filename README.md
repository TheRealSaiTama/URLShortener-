# URL Shortener API (FastAPI)

A minimal, local URL shortener built with FastAPI and SQLAlchemy. It generates deterministic short codes for URLs and stores them in SQLite. No external shortening service is used.

## Features

- FastAPI REST API with simple JSON responses
- Deterministic 7‑character codes via BLAKE2b hash
- Idempotent shortening: same URL -> same code
- SQLite persistence with SQLAlchemy (table: `url_map`)
- Health check endpoint
- Resolve returns JSON target (no HTTP redirect by default)

## Requirements

- Python 3.10+
- Packages: `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`

## Install

```bash
python -m venv .venv
.\.venv\Scripts\activate   # Windows PowerShell
pip install fastapi uvicorn sqlalchemy pydantic
```

## Run

```bash
uvicorn app.main:app --reload
```

- The SQLite DB file `urlshorty.db` is created in the project root (see `app/db.py`).
- Default app metadata: title `url-shorty`, version `0.2`.

## Endpoints

1) Health

- Method/Path: `GET /health`
- Response: `200 OK` → `{ "ok": true }`

2) Shorten

- Method/Path: `POST /shorten`
- Body (JSON): `{ "url": "https://example.com" }`
- Success: `200 OK` → `{ "code": "<7chars>", "short_url": "/<code>" }`
- Validation error: `422` (invalid URL)

3) Resolve

- Method/Path: `GET /{code}`
- Success: `200 OK` → `{ "target": "https://example.com" }`
- Not found: `404` → `{ "detail": "code not found" }`

Notes:
- The `short_url` field is a path. Prepend your host to form a full URL (e.g., `http://localhost:8000/<code>`).
- Codes are deterministic for a given URL; the first call persists the mapping.

## Examples

PowerShell (Invoke-WebRequest):

```powershell
Invoke-WebRequest -Uri http://localhost:8000/shorten -Headers @{"Content-Type"="application/json"} -Body '{"url":"https://example.com"}' -Method POST
```

curl:

```bash
curl -sS -X POST http://localhost:8000/shorten \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}'
# => {"code":"c4681d7","short_url":"/c4681d7"}

curl -sS http://localhost:8000/c4681d7
# => {"target":"https://example.com"}
```

## Architecture

- API: `app/main.py` (FastAPI app, endpoints, hashing)
- DB: `app/db.py` (SQLAlchemy engine/session, SQLite URL)
- Model: `app/models.py` (table `url_map` with unique `code`)

Implementation details:
- Code generation uses BLAKE2b with `digest_size=5`, hex‑encoded, truncated to 7 chars.
- Schema is created at startup via `Base.metadata.create_all(engine)`.

## Upgrade: v1 → v2

This project evolved from a CLI-based shortener (v1) using `pyshorteners`/TinyURL into a self‑hosted API (v2).

What changed (breaking):
- CLI removed; replaced by an HTTP API (FastAPI)
- No TinyURL or third‑party network calls; all local
- Short codes are deterministic and locally generated (not TinyURL links)
- Resolve returns JSON (not an HTTP redirect)

How to upgrade:
- Stop using the old CLI script and `pyshorteners` dependency
- Install new deps and run the API with `uvicorn app.main:app --reload`
- If you need to preserve existing mappings, insert them into the `url_map` table. You can either:
  - Recreate codes using the new algorithm for each URL, or
  - Predefine your own `code` values (must be unique) when seeding the DB

Compatibility tips:
- Clients that expect a redirect should perform the redirect client‑side using the `target` returned by `GET /{code}`. If server‑side redirects are needed, add a redirect endpoint (e.g., using `starlette.responses.RedirectResponse`).

## License

MIT (see `LICENSE`).
