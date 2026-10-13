"""Server tests -- all offline, no real fetch and no real key.

The point of these is twofold: prove the caching works (so a demo is instant and
the fetch rate is honest), and prove the key never reaches the client.
"""

from __future__ import annotations

import json

import pytest

fastapi = pytest.importorskip("fastapi")


@pytest.fixture
def client(tmp_path, monkeypatch):
    from starlette.testclient import TestClient

    from mcx_live import server

    monkeypatch.setenv("TINYFISH_API_KEY", "sk-tinyfish-not-real")
    monkeypatch.setenv("MCX_LIVE_CACHE", str(tmp_path / "cache"))
    # Reset the module-level cache dir so each test starts clean.
    server._CACHE_DIR = tmp_path / "cache"
    return TestClient(server.create_app())


def _payload():
    return [
        {
            "sLTT": None, "Date": "10/12/2026", "DateDisplay": "12 Oct 2026",
            "Symbol": "GOLDM ", "ExpiryDate": "05OCT2026", "Open": 100000.0,
            "High": 100500.0, "Low": 99500.0, "Close": 100100.0,
            "PreviousClose": 99800.0, "Volume": 12000,
            "VolumeInThousands": "12.000 KGS ", "Value": 5000.0,
            "OpenInterest": 40000, "InstrumentName": "FUTCOM",
        },
        {
            "sLTT": None, "Date": "10/12/2026", "DateDisplay": "12 Oct 2026",
            "Symbol": "GOLDPETAL ", "ExpiryDate": "05OCT2026", "Open": 100000.0,
            "High": 100500.0, "Low": 99500.0, "Close": 100100.0,
            "PreviousClose": 99800.0, "Volume": 30000,
            "VolumeInThousands": "30.000 KGS ", "Value": 5000.0,
            "OpenInterest": 40000, "InstrumentName": "FUTCOM",
        },
    ]


def test_the_module_level_app_exists_for_uvicorn():
    """Regression: every instruction in the README says
    ``uvicorn mcx_live.server:app``, and that silently failed because ``server``
    exposed only a factory. An ASGI app must be importable by that path.
    """
    from mcx_live import server

    assert hasattr(server, "app"), "no module-level 'app'; uvicorn cannot start"
    # It must be the same object the tests build, not a second one.
    assert server.app is not None
    routes = {r.path for r in server.app.routes}
    for path in ("/health", "/scan", "/scan/cached", "/circulars"):
        assert path in routes, f"module-level app is missing {path}"


def test_health_needs_no_key(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_scan_caches_so_a_refresh_is_instant_and_free(client, monkeypatch):
    from mcx_live import server

    calls = {"n": 0}

    def fake_live(key=None):
        calls["n"] += 1
        frame, _ = None, None
        from mcx_live.ingest import normalise

        frame = normalise(_payload())
        return frame, "tinyfish-live:test"

    monkeypatch.setattr(server.plane, "live_frame", fake_live)

    first = client.get("/scan")
    assert first.status_code == 200
    body = first.json()
    assert body["from_cache"] is False
    assert body["verdict_summary"]["pairs_tested"] >= 1
    assert calls["n"] == 1

    second = client.get("/scan")
    assert second.json()["from_cache"] is True
    assert calls["n"] == 1, "a cached scan must not fetch again"

    forced = client.get("/scan?force=true")
    assert forced.json()["from_cache"] is False
    assert calls["n"] == 2


def test_cached_endpoint_serves_what_the_last_scan_produced(client, monkeypatch):
    from mcx_live import server

    monkeypatch.setattr(
        server.plane,
        "live_frame",
        lambda key=None: (normalise(_payload()), "tinyfish-live:test"),
    )
    from mcx_live.ingest import normalise

    client.get("/scan")
    r = client.get("/scan/cached")
    assert r.status_code == 200
    assert r.json()["source"].startswith("tinyfish-live:")


def test_cached_endpoint_is_an_actionable_404_before_any_scan(client):
    r = client.get("/scan/cached")
    assert r.status_code == 404
    assert "no scan yet" in r.json()["error"]


def test_scan_reports_unavailability_rather_than_crashing(client, monkeypatch):
    from mcx_live import plane, server

    def dead(key=None):
        raise plane.TinyFishUnavailable("TINYFISH_API_KEY is not set")

    monkeypatch.setattr(server.plane, "live_frame", dead)
    r = client.get("/scan")
    assert r.status_code == 503
    # The message names the variable but never a credential.
    assert "TINYFISH_API_KEY" in r.json()["error"]


def test_the_key_never_reaches_the_client(client, monkeypatch):
    from mcx_live import server
    from mcx_live.ingest import normalise

    monkeypatch.setattr(
        server.plane,
        "live_frame",
        lambda key=None: (normalise(_payload()), "tinyfish-live:test"),
    )
    r = client.get("/scan")
    body = r.text + str(dict(r.headers))
    assert "sk-tinyfish-" not in body, "the API key leaked to the client"
