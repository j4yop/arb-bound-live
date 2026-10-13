"""Serverless entry point for Vercel.

Exposes the *same* FastAPI application the local server and the tests use, so
there is one definition of "the verdict" on the laptop, in CI and on the
deployed URL. ``mcx_live.server.create_app`` builds it; this module only makes
sure it is importable from the repo root.

Credentials never leave the server: ``TINYFISH_API_KEY`` is read from the
environment and is not part of any response. An unconfigured deployment returns
an actionable 503 rather than a stack trace.

Local dev:  vercel dev        (or: uvicorn mcx_live.server:app)
Deploy:     vercel deploy --prod
"""

from __future__ import annotations

import sys
from pathlib import Path

# The deployed function must import the package from the repository root.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcx_live.server import create_app  # noqa: E402

# ``app`` is what Vercel's Python runtime detects, and it is ASGI, so the
# routing, caching and error handling are the ones the tests cover.
app = create_app()
