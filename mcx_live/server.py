"""HTTP surface for the live demo.

    GET /health          -> service liveness, no key needed
    GET /scan            -> fetch today's bhavcopy and run the bound
    GET /scan/cached     -> the last successful scan, from disk
    GET /circulars?from=01/10/2024&to=31/12/2024
                         -> date-filtered MCX circular archive

``/scan`` is deliberately expensive (it drives a real browser), so it is cached
to disk and served from there afterwards. That keeps a demo instant on the
second and later calls, and makes the fetch rate honest.

The API key never leaves the server: the front end fetches from this process,
which is the only place the credential is read.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from . import plane
from .cli import build_report

_CACHE_DIR = Path(os.environ.get("MCX_LIVE_CACHE", "cache"))
_LOCK = threading.Lock()


def _cache_path(name: str) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / f"{name}.json"


def run_scan(force: bool = False) -> dict:
    """Fetch today's bhavcopy and cache the result.

    Thread-safe, so two judges hitting refresh at once do not trigger two paid
    browser runs.
    """
    cached = _cache_path("latest")
    with _LOCK:
        if not force and cached.exists():
            payload = json.loads(cached.read_text())
            payload["from_cache"] = True
            return payload
        frame, source = plane.live_frame()
        report = build_report(frame, source)
        report["from_cache"] = False
        cached.write_text(json.dumps(report, indent=1, default=str))
        return report


def create_app():
    """Build the FastAPI app. Kept separate so tests can build it without uvicorn."""
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI(title="arb-bound-live", version="0.1.0")

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "arb-bound-live"}

    @app.get("/scan")
    def scan(force: bool = False):
        try:
            return run_scan(force=force)
        except plane.TinyFishUnavailable as exc:
            return JSONResponse({"error": str(exc)}, status_code=503)

    @app.get("/scan/cached")
    def scan_cached():
        cached = _cache_path("latest")
        if not cached.exists():
            return JSONResponse(
                {"error": "no scan yet - call /scan first"}, status_code=404
            )
        payload = json.loads(cached.read_text())
        payload["from_cache"] = True
        return payload

    @app.get("/circulars")
    def circulars(date_from: str, date_to: str):
        try:
            run = plane.archive_circulars(date_from, date_to)
        except plane.TinyFishUnavailable as exc:
            return JSONResponse({"error": str(exc)}, status_code=503)
        result = run.get("result") or {}
        return {
            "run_id": run.get("run_id"),
            "status": run.get("status"),
            "steps": run.get("num_of_steps"),
            "date_from": date_from,
            "date_to": date_to,
            "applied_date_filter": result.get("applied_date_filter"),
            "reason_if_failed": result.get("reason_if_failed"),
            "circulars": result.get("circulars") or [],
        }

    return app


# The module-level ASGI app. This is what ``uvicorn mcx_live.server:app`` and
# Vercel's Python runtime both look for, and it is the same object the test
# suite builds, so a local server, a deployed function and the tests cannot
# drift apart. Building it at import time costs a few milliseconds and needs
# FastAPI, which the ``server`` extra declares.
app = create_app()


def main() -> None:
    """Serve the app. ``uvicorn mcx_live.server:app`` is the shorter form."""
    try:
        import uvicorn
    except ImportError:  # pragma: no cover - optional runtime dep
        raise SystemExit(
            "uvicorn is not installed. Either: pip install -e '.[server]'  "
            "or run:  uvicorn mcx_live.server:app"
        )
    uvicorn.run(
        "mcx_live.server:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()
