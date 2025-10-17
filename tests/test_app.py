import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ratelimit import LIMIT, reset as reset_rate_limiter

c = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_rate_limit():
    reset_rate_limiter()
    yield
    reset_rate_limiter()

def test_health(): assert c.get("/health").json()["ok"] is True

def test_shorten_and_resolve():
    r = c.post("/shorten", json={"url":"https://example.com"})
    code = r.json()["code"]
    res = c.get(f"/{code}", follow_redirects=False)
    assert res.status_code == 307
    assert res.headers["location"].rstrip("/") == "https://example.com"

def test_not_found():
    assert c.get("/nope", follow_redirects=False).status_code == 404

def test_shorten_sets_location_header():
    r = c.post("/shorten", json={"url":"https://example.com"})
    assert r.status_code == 201
    assert r.headers["location"].endswith("/" + r.json()["code"])

def test_idempotent_same_url_same_code():
    r1 = c.post("/shorten", json={"url":"https://example.com"})
    r2 = c.post("/shorten", json={"url":"https://example.com"})
    assert r1.json()["code"] == r2.json()["code"]

def test_different_urls_different_codes():
    r1 = c.post("/shorten", json={"url":"https://example.com"})
    r2 = c.post("/shorten", json={"url":"https://example.org"})
    assert r1.json()["code"] != r2.json()["code"]

def test_rate_limit_trips_429_quickly():
    for _ in range(LIMIT):
        assert c.get("/health").status_code == 200
    assert c.get("/health").status_code == 429


def test_stats_tracks_visits():
    short = c.post("/shorten", json={"url": "https://example.com/stats"})
    code = short.json()["code"]
    headers = {"user-agent": "pytest-suite", "referer": "https://refer.example"}
    for _ in range(2):
        res = c.get(f"/{code}", headers=headers, follow_redirects=False)
        assert res.status_code == 307

    stats = c.get(f"/stats/{code}").json()
    assert stats["code"] == code
    assert stats["target"].rstrip("/") == "https://example.com/stats"
    assert stats["clicks_total"] >= 2
    assert stats["clicks_24h"] >= 2


def test_stats_unknown_code_404():
    assert c.get("/stats/nope").status_code == 404
