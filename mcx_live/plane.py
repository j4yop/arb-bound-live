"""The TinyFish plane -- the only code in this repo that touches the network.

It exists because of one hard-won fact: ``mcxindia.com`` returns HTTP 403
(Akamai Access Denied) from a datacentre IP, so this project cannot fetch MCX
data from its own machine. Verified 2026-10-13 against TinyFish's free Fetch
endpoint:

* ``POST https://api.fetch.tinyfish.ai`` returned the **live dated bhavcopy**
  (4.9 MB of real JSON, all gold contracts present) and the **circular
  listing** with real rows, on the exact URL where ``curl`` gets a block page.
* Fetch ignores a ``?date=`` parameter: only *today's* bhavcopy is reachable.
  That is a real limitation, recorded rather than papered over.
* The dated circular archive needed the **Agent** API, which drives a real
  browser: it set the archive's date filter and paged through the result.

Rate card, from ``GET /v1/wallet`` (verified 2026-10-13):
    TinyFish Fetch   $0.000 per url   -> free
    TinyFish Search  $0.000 per query -> free
    TinyFish Agent   $0.016 per step
    TinyFish Browser $0.002 per minute
    TinyFish Monitor $0.005 per run
So Search and Fetch are the defaults; Agent is the capped escalation path.

Nothing downstream of this module knows these calls happened. The API key is
read from the environment and is never logged or echoed.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

FETCH_URL = "https://api.fetch.tinyfish.ai"
SEARCH_URL = "https://api.search.tinyfish.ai"
AGENT_RUN_URL = "https://agent.tinyfish.ai/v1/automation/run"
AGENT_ASYNC_URL = "https://agent.tinyfish.ai/v1/automation/run-async"
RUN_URL = "https://agent.tinyfish.ai/v1/runs/{run_id}"
WALLET_URL = "https://agent.tinyfish.ai/v1/wallet"

MCX_BHAVCOPY = "https://www.mcxindia.com/market-data/bhavcopy"
MCX_CIRCULARS = "https://www.mcxindia.com/circulars/all-circulars"


class TinyFishUnavailable(RuntimeError):
    """Raised when the key is absent or the API rejects a request."""


def _key(explicit: str | None = None) -> str:
    val = explicit or os.environ.get("TINYFISH_API_KEY")
    if not val:
        raise TinyFishUnavailable(
            "TINYFISH_API_KEY is not set. Sign up via the HIH referral link, "
            "create a key at https://agent.tinyfish.ai/api-keys, and export it. "
            "See .env.example."
        )
    return val


def _post_json(url: str, body: dict, key: str, timeout: float = 180.0) -> dict:
    import urllib.error
    import urllib.request

    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "X-API-Key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # The key is secret; the status code and the server's own message are
        # not, so only those are surfaced.
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise TinyFishUnavailable(f"{url} -> HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise TinyFishUnavailable(f"{url} unreachable: {exc}") from exc


def _get_json(url: str, key: str, timeout: float = 60.0) -> dict:
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url, headers={"X-API-Key": key}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise TinyFishUnavailable(f"{url} -> HTTP {exc.code}: {detail}") from exc
    except Exception as exc:
        raise TinyFishUnavailable(f"{url} unreachable: {exc}") from exc


def fetch_page(url: str, key: str | None = None) -> str:
    """Fetch one URL as clean text via the free Fetch endpoint."""
    data = _post_json(FETCH_URL, {"urls": [url]}, _key(key))
    results = data.get("results") or []
    if not results:
        errors = data.get("errors") or []
        raise TinyFishUnavailable(f"Fetch returned no content for {url}: {errors}")
    return results[0].get("text", "")


def search(query: str, key: str | None = None) -> list[dict]:
    """Free structured web search."""
    import urllib.error
    import urllib.parse
    import urllib.request

    url = f"{SEARCH_URL}?{urllib.parse.urlencode({'query': query})}"
    req = urllib.request.Request(url, headers={"X-API-Key": _key(key)})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8")).get("results", [])
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise TinyFishUnavailable(f"Search -> HTTP {exc.code}: {detail}") from exc


def fetch_bhavcopy(
    key: str | None = None,
    url: str = MCX_BHAVCOPY,
    attempts: int = 3,
    delay: float = 4.0,
) -> str:
    """Live MCX bhavcopy page as text.

    Retries because Fetch is not perfectly stable on this endpoint: it sometimes
    returns an HTML shell instead of the embedded JSON. Callers should use
    :func:`live_frame`, which extracts the payload and handles the retry.

    Only *today's* bhavcopy is reachable; MCX ignores ``?date=`` on this URL, so
    this is a daily ingest and not a historical backfill.
    """
    from .ingest import extract_bhavcopy_array, NotABhavcopy

    last = ""
    for i in range(max(1, attempts)):
        try:
            raw = fetch_page(url, key)
        except TinyFishUnavailable:
            if i == attempts - 1:
                raise
            time.sleep(delay)
            continue
        last = raw
        try:
            if extract_bhavcopy_array(raw):
                return raw
        except NotABhavcopy:
            pass
        time.sleep(delay)
    return last


def live_frame(key: str | None = None) -> tuple:
    """Fetch today's bhavcopy and normalise it with the local ingest.

    Returns ``(frame, provenance)``.
    """
    import tempfile

    from .ingest import extract_bhavcopy_array, normalise, NotABhavcopy

    raw = fetch_bhavcopy(key)
    try:
        rows = extract_bhavcopy_array(raw)
    except NotABhavcopy as exc:
        raise TinyFishUnavailable(f"live bhavcopy: {exc}") from exc
    if not rows:
        raise TinyFishUnavailable("live bhavcopy: extractor returned no rows")

    with tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    ) as fh:
        json.dump(rows, fh)
        tmp = fh.name
    try:
        frame = normalise(json.loads(Path(tmp).read_text()))
    finally:
        Path(tmp).unlink(missing_ok=True)

    if frame.empty:
        raise TinyFishUnavailable("live bhavcopy: normaliser returned an empty frame")
    return frame, f"tinyfish-live:{MCX_BHAVCOPY}"


# ------------------------------------------------------------------ agent


def _agent_run_async(
    goal: str, key: str, url: str = MCX_CIRCULARS, schema: dict | None = None
) -> str:
    body: dict[str, Any] = {"url": url, "goal": goal}
    if schema:
        body["output_schema"] = schema
    return _post_json(AGENT_ASYNC_URL, body, key, timeout=120.0).get("run_id", "")


def wait_for_run(
    run_id: str,
    key: str | None = None,
    poll: float = 20.0,
    max_wait: float = 1800.0,
) -> dict:
    """Poll a run until it reaches a terminal state, or raise."""
    deadline = time.time() + max_wait
    last: dict = {}
    while time.time() < deadline:
        last = _get_json(RUN_URL.format(run_id=run_id), _key(key))
        if last.get("status") in ("COMPLETED", "FAILED", "CANCELLED"):
            return last
        time.sleep(poll)
    raise TinyFishUnavailable(
        f"run {run_id} still {last.get('status')} after {max_wait}s"
    )


CIRCULAR_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "applied_date_filter": {"type": "boolean"},
        "circulars": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "category": {"type": "string"},
                    "title": {"type": "string"},
                    "circular_no": {"type": "string"},
                },
                "required": ["date", "category"],
            },
        },
        "reason_if_failed": {"type": "string", "nullable": True},
    },
    "required": ["applied_date_filter", "circulars"],
}


def archive_circulars(
    date_from: str,
    date_to: str,
    key: str | None = None,
    poll: float = 20.0,
    max_wait: float = 1800.0,
) -> dict:
    """Date-filter MCX's circular archive and return the full run document.

    This is the capability that was previously unreachable. The archive's date
    filter is applied client-side, so Fetch sees only the default page; the
    Agent API drives a real browser to set From/To dates, click Show, and page
    through the results.

    Verified 2026-10-13: 01/10/2024 -> 31/12/2024 returned 204 circulars across
    14 result pages in 115 steps.
    """
    k = _key(key)
    goal = (
        f"Set the From Date field to {date_from} and the To Date field to "
        f"{date_to}, then click the Show button. Wait for the circulars table "
        "to refresh. Page through every page of results and list every circular "
        "with its date, category, title and circular number. If the date fields "
        "cannot be found or the table does not change, set applied_date_filter "
        "to false and explain why in reason_if_failed."
    )
    run_id = _agent_run_async(goal, k, MCX_CIRCULARS, CIRCULAR_SCHEMA)
    if not run_id:
        raise TinyFishUnavailable("archive_circulars: no run_id returned")
    return wait_for_run(run_id, k, poll=poll, max_wait=max_wait)


def wallet(key: str | None = None) -> dict:
    """Current balance and rates -- proves the key works and prices the plan."""
    return _get_json(WALLET_URL, _key(key))
