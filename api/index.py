"""Serverless entry point for Vercel.

Exposes the same FastAPI application the local server and the tests use, so there
is one definition of "the verdict" on the laptop, in CI and on a deployed URL.

Status: kept for local parity (`uvicorn mcx_live.server:app` is the tested
path). The current Vercel deployment serves only the static site — see
``vercel.json``. If you want the API on Vercel, ``vercel env add`` the key and
re-add the ``/api`` route; the runtime needs ``pandas`` and ``fastapi`` in
``requirements.txt`` and a cold-start budget to install them.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mcx_live.server import create_app  # noqa: E402

# ``app`` is ASGI, so routing, caching and error handling are the ones the
# tests cover rather than a second implementation.
app = create_app()
