"""Serverless entry point for Vercel.

Serves `/api/health`, `/api/scan` and `/api/circulars` from the same
``mcx_live`` package the CLI uses, so there is one definition of "the verdict"
across the local server, the CLI and the deployed API.

Credentials never leave the server: ``TINYFISH_API_KEY`` is read from the
environment and is not part of any response. If it is absent the endpoint says so
rather than failing silently.

Local dev:  vercel dev
Deploy:     vercel deploy --prod
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# The deployed function must be able to import the package from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcx_live import plane  # noqa: E402
from mcx_live.cli import build_report  # noqa: E402


def _json(payload, status: int = 200):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Cache-Control": "no-store",
        },
        "body": _dumps(payload),
    }


def _dumps(payload) -> str:
    import json

    class _Enc(json.JSONEncoder):
        def default(self, o):
            try:
                return float(o)
            except Exception:
                return str(o)

    return json.dumps(payload, cls=_Enc)


def handler(event, context=None):
    """Single catch-all handler; routing is done on the path so one function
    covers all three endpoints."""
    path = event.get("rawUrl", "") or event.get("path", "/")
    path = path.split("?")[0].rstrip("/")

    # ---- /api/health : liveness, and whether a key is present
    if path.endswith("/api") or path.endswith("/api/health"):
        return _json(
            {
                "status": "ok",
                "service": "arb-bound-live",
                "key_configured": bool(os.environ.get("TINYFISH_API_KEY")),
                "endpoints": ["/api/health", "/api/scan", "/api/circulars"],
            }
        )

    # ---- /api/scan : fetch today's bhavcopy and run the bound
    if path.endswith("/api/scan"):
        if not os.environ.get("TINYFISH_API_KEY"):
            return _json(
                {
                    "error": "TINYFISH_API_KEY is not configured on this deployment.",
                    "how_to_fix": (
                        "vercel env add TINYFISH_API_KEY production, then "
                        "redeploy."
                    ),
                },
                status=503,
            )
        try:
            frame, source = plane.live_frame()
            report = build_report(frame, source)
        except plane.TinyFishUnavailable as exc:
            return _json({"error": str(exc)}, status=503)
        except Exception as exc:  # a scrape can fail in ways that are not ours
            return _json({"error": f"scan failed: {exc}"}, status=502)
        return _json(report)

    # ---- /api/circulars?from=DD/MM/YYYY&to=DD/MM/YYYY
    if path.endswith("/api/circulars"):
        if not os.environ.get("TINYFISH_API_KEY"):
            return _json(
                {
                    "error": "TINYFISH_API_KEY is not configured on this deployment.",
                    "how_to_fix": (
                        "vercel env add TINYFISH_API_KEY production, then "
                        "redeploy."
                    ),
                },
                status=503,
            )
        params = event.get("query") or {}
        date_from = params.get("from", "01/10/2024")
        date_to = params.get("to", "31/12/2024")
        try:
            run = plane.archive_circulars(date_from, date_to)
        except plane.TinyFishUnavailable as exc:
            return _json({"error": str(exc)}, status=503)
        except Exception as exc:
            return _json({"error": f"circulars failed: {exc}"}, status=502)
        result = run.get("result") or {}
        return _json(
            {
                "run_id": run.get("run_id"),
                "status": run.get("status"),
                "steps": run.get("num_of_steps"),
                "date_from": date_from,
                "date_to": date_to,
                "applied_date_filter": result.get("applied_date_filter"),
                "reason_if_failed": result.get("reason_if_failed"),
                "circulars": result.get("circulars") or [],
            }
        )

    return _json({"error": f"no route for {path}"}, status=404)
