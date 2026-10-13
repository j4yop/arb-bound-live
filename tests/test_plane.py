"""Plane tests -- all offline.

The network calls are replaced, so the suite costs nothing and runs in CI. The
live capabilities themselves are evidenced by the archived runs in
``docs/TINYFISH.md`` and ``data/mcx_circulars_oct_dec_2024.json``.
"""

from __future__ import annotations

import json

import pytest

from mcx_live import plane

_REAL_POST = plane._post_json
_REAL_GET = plane._get_json


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    """Fail loudly if a test reaches for the network, and let the key resolve
    without touching a real credential."""
    monkeypatch.setenv("TINYFISH_API_KEY", "sk-tinyfish-not-real")

    def boom(*a, **k):
        raise AssertionError("a test attempted a real network call")

    monkeypatch.setattr(plane, "_post_json", boom)
    monkeypatch.setattr(plane, "_get_json", boom)


# ------------------------------------------------------------------- the key


def test_missing_key_is_an_actionable_error(monkeypatch):
    monkeypatch.delenv("TINYFISH_API_KEY", raising=False)
    with pytest.raises(plane.TinyFishUnavailable) as exc:
        plane.fetch_page("https://example.com")
    assert "TINYFISH_API_KEY" in str(exc.value)


def test_key_can_be_passed_explicitly():
    assert plane._key("sk-tinyfish-not-real") == "sk-tinyfish-not-real"


def test_fetch_error_surfaces_status_not_credentials(monkeypatch):
    """A 401 must surface the status code, never the key."""
    import io
    import urllib.error
    import urllib.request

    def fake_urlopen(req, timeout=None):
        raise urllib.error.HTTPError(
            req.full_url, 401, "Unauthorized", None, io.BytesIO(b'{"error":"nope"}')
        )

    # Restore the real _post_json so its own handler is what we exercise.
    monkeypatch.setattr(plane, "_post_json", _REAL_POST)
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(plane.TinyFishUnavailable) as exc:
        plane.fetch_page("https://example.com", key="sk-tinyfish-not-real")
    assert "401" in str(exc.value)
    assert "sk-tinyfish-not-real" not in str(exc.value)


# ------------------------------------------------------------- retries


def test_fetch_bhavcopy_retries_when_fetch_returns_a_shell(monkeypatch):
    """Fetch sometimes returns HTML instead of the JSON; retry, then give up."""
    calls = {"n": 0}

    def shell_then_json(url, key=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return "<html>a partially rendered shell</html>"
        return '[{"sLTT":null,"Date":"10/12/2026","Symbol":"GOLDM "}]'

    monkeypatch.setattr(plane, "fetch_page", shell_then_json)
    monkeypatch.setattr(plane.time, "sleep", lambda s: None)
    out = plane.fetch_bhavcopy("sk-tinyfish-not-real", attempts=3, delay=0.0)
    assert calls["n"] == 2, "the retry path must actually retry"
    assert "sLTT" in out


def test_fetch_bhavcopy_gives_up_and_returns_the_last_response(monkeypatch):
    monkeypatch.setattr(plane, "fetch_page", lambda url, key=None: "<html>shell</html>")
    monkeypatch.setattr(plane.time, "sleep", lambda s: None)
    out = plane.fetch_bhavcopy("sk-tinyfish-not-real", attempts=2, delay=0.0)
    assert out == "<html>shell</html>"


# --------------------------------------------------------- the live frame


def test_live_frame_normalises_through_the_local_ingest(monkeypatch):
    """The plane must not reimplement parsing."""
    from mcx_live import cli as _cli  # noqa: F401  (import proves no cycle)

    payload = json.dumps(
        [
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
                "Symbol": "GOLDGUINEA ", "ExpiryDate": "05NOV2026", "Open": 78000.0,
                "High": 78500.0, "Low": 77500.0, "Close": 78100.0,
                "PreviousClose": 77900.0, "Volume": 3000,
                "VolumeInThousands": "3.000 KGS ", "Value": 1000.0,
                "OpenInterest": 9000, "InstrumentName": "FUTCOM",
            },
        ]
    )
    monkeypatch.setattr(plane, "fetch_bhavcopy", lambda key=None, **k: payload)

    frame, source = plane.live_frame("sk-tinyfish-not-real")
    assert source.startswith("tinyfish-live:")
    assert set(frame["symbol"]) == {"GOLDM", "GOLDGUINEA"}
    # The date fix, live: 12 October, not 10 December.
    assert set(frame["date"].dt.strftime("%Y-%m-%d")) == {"2026-10-12"}


# --------------------------------------------------------- the archive path


def test_archive_circulars_is_submit_then_poll(monkeypatch):
    seen: dict = {}

    def fake_submit(goal, key, url=plane.MCX_CIRCULARS, schema=None):
        seen["goal"], seen["url"], seen["schema"] = goal, url, schema
        return "run-123"

    def fake_wait(run_id, key=None, poll=20.0, max_wait=1800.0):
        seen["run_id"] = run_id
        return {
            "run_id": "run-123", "status": "COMPLETED", "num_of_steps": 115,
            "result": {"applied_date_filter": True, "circulars": [
                {"date": "31 Dec 2024", "category": "T&S",
                 "title": "Commencement Of Futures Trading In Gold Petal "
                          "April 2025 Contract",
                 "circular_no": "858"}]},
        }

    monkeypatch.setattr(plane, "_agent_run_async", fake_submit)
    monkeypatch.setattr(plane, "wait_for_run", fake_wait)

    run = plane.archive_circulars("01/10/2024", "31/12/2024")
    assert "01/10/2024" in seen["goal"] and "31/12/2024" in seen["goal"]
    assert seen["run_id"] == "run-123"
    assert seen["schema"]["required"] == ["applied_date_filter", "circulars"]
    assert run["result"]["circulars"][0]["circular_no"] == "858"


def test_wait_for_run_raises_rather_than_looping_forever(monkeypatch):
    monkeypatch.setattr(plane, "_get_json", lambda url, key: {"status": "RUNNING"})
    monkeypatch.setattr(plane.time, "sleep", lambda s: None)
    with pytest.raises(plane.TinyFishUnavailable) as exc:
        plane.wait_for_run("run-x", max_wait=1.0, poll=0.0)
    assert "still RUNNING" in str(exc.value)


def test_search_returns_results(monkeypatch):
    def fake_urlopen(req, timeout=None):
        import io
        from contextlib import closing

        class _R:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            @staticmethod
            def read():
                return json.dumps(
                    {"results": [{"title": "x", "url": "https://example.com"}]}
                ).encode()

        return _R()

    monkeypatch.setattr(plane, "_post_json", _REAL_POST)
    monkeypatch.setattr(plane, "_get_json", _REAL_GET)
    import urllib.request

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    out = plane.search("anything", key="sk-tinyfish-not-real")
    assert out and out[0]["url"] == "https://example.com"
