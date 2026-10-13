"""MCX bhavcopy normalisation.

Everything in here is pure: page text in, tidy frame out. No network, no clock,
no market judgement. This is deliberately a smaller, self-contained version of
the same idea, because this repo must run without its parent project.

Two things here were learned the hard way, both recorded in
``docs/TINYFISH.md``:

1. **``DateDisplay`` is unambiguous and must win.** The API payload carries
   ``Date`` as ``MM/DD/YYYY`` and ``DateDisplay`` as ``12 Oct 2026``. Both
   readings of an ambiguous slash date parse cleanly, so a format-order guess
   silently moves rows by months.
2. **Options rows share the underlying future's ``Symbol``.** Unfiltered they
   corrupt every average downstream, so they are removed before any maths.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable

import pandas as pd

from .contracts import CONTRACTS

_ROW_MARKER = '{"sLTT"'
_MONTHS = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


class NotABhavcopy(ValueError):
    """Raised when the payload is not an MCX bhavcopy, with an actionable message."""


def extract_bhavcopy_array(page_text: str) -> list[dict]:
    """Pull the embedded JSON array out of an MCX page.

    Finds the array by its opening bracket and scans forward matching brackets,
    so it tolerates leading and trailing HTML. Raises ``NotABhavcopy`` with a
    message naming what was missing.
    """
    start = page_text.find(_ROW_MARKER)
    if start == -1:
        raise NotABhavcopy(
            "no bhavcopy rows found in the payload; expected a '"
            + _ROW_MARKER
            + "' marker"
        )
    opening = page_text.rfind("[", 0, start)
    if opening == -1:
        raise NotABhavcopy("bhavcopy rows found but not inside a JSON array")

    depth = 0
    for idx in range(opening, len(page_text)):
        ch = page_text[idx]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(page_text[opening : idx + 1])
                except json.JSONDecodeError as exc:
                    raise NotABhavcopy(f"bhavcopy JSON did not parse: {exc}") from exc
    raise NotABhavcopy("unterminated bhavcopy JSON array")


def parse_display_date(text: str) -> pd.Timestamp:
    """Parse an unambiguous rendered date such as ``12 Oct 2026``."""
    m = re.fullmatch(r"(\d{1,2}) ([A-Za-z]{3,}) (\d{4})", str(text).strip())
    if not m:
        raise ValueError(f"unrecognised display date: {text!r}")
    day, mon, year = m.groups()
    month = _MONTHS.index(mon.title()[:3]) + 1
    return pd.Timestamp(year=int(year), month=month, day=int(day))


def parse_slash_date(text: str) -> pd.Timestamp:
    """Parse a slash date, DD/MM/YYYY first.

    This remains a *guess* for ambiguous dates - both readings parse. Prefer
    ``DateDisplay`` whenever it is present; see ``trade_dates``.
    """
    text = str(text).strip()
    for fmt in ("%d/%m/%Y", "%m/%d/%Y"):
        try:
            return pd.Timestamp(pd.to_datetime(text, format=fmt))
        except (ValueError, TypeError):
            continue
    raise ValueError(f"unrecognised slash date: {text!r}")


def trade_dates(frame: pd.DataFrame) -> pd.Series:
    """Resolve the trade date, preferring the unambiguous ``DateDisplay``."""
    if "DateDisplay" not in frame.columns:
        return frame["Date"].map(parse_slash_date)
    parsed = pd.to_datetime(
        frame["DateDisplay"].astype(str).str.strip(),
        format="%d %b %Y",
        errors="coerce",
    )
    if parsed.isna().any():
        parsed = parsed.fillna(frame["Date"].map(parse_slash_date))
    return pd.Series(parsed.values, index=frame.index)


def _find(frame: pd.DataFrame, *names: str) -> str | None:
    """Locate a column by any of its tolerated spellings."""
    wanted = {n.lower() for n in names}
    for col in frame.columns:
        if col.lower() in wanted:
            return col
    return None


def normalise(rows: Iterable[dict]) -> pd.DataFrame:
    """Turn raw bhavcopy row dicts into the tidy frame the analysis consumes."""
    rows = list(rows)
    if not rows:
        raise NotABhavcopy("bhavcopy contained no rows")

    frame = pd.DataFrame(rows)

    symbol_col = _find(frame, "Symbol", "symbol")
    if symbol_col is None:
        raise NotABhavcopy(
            "not a bhavcopy: no 'Symbol' column. Found: "
            + ", ".join(map(str, frame.columns))
        )
    frame["symbol"] = frame[symbol_col].astype(str).str.strip().str.upper()

    # Options rows share the underlying future's Symbol; drop them first.
    instrument = _find(frame, "InstrumentName", "instrument")
    if instrument is not None:
        keep = frame[instrument].astype(str).str.strip().str.upper() == "FUTCOM"
        frame = frame[keep].copy()

    frame["date"] = trade_dates(frame)

    expiry = _find(frame, "ExpiryDate", "expiry")
    if expiry is None:
        raise NotABhavcopy("not a bhavcopy: no 'ExpiryDate' column")
    frame["expiry"] = frame[expiry].map(_parse_expiry)

    for name, col in (
        ("Close", ("Close", "close", "SettlementPrice")),
        ("High", ("High", "high")),
        ("Low", ("Low", "low")),
        ("Volume", ("Volume", "volume", "volume_lots")),
        ("OpenInterest", ("OpenInterest", "open_interest", "open_interest_lots")),
    ):
        src = _find(frame, *col)
        frame[name] = pd.to_numeric(frame[src] if src else None, errors="coerce")
    frame["Volume"] = frame["Volume"].fillna(0.0)
    frame["OpenInterest"] = frame["OpenInterest"].fillna(0.0)

    frame = frame[frame["symbol"].isin(CONTRACTS)].copy()
    if frame.empty:
        raise NotABhavcopy(
            "no rows for the modelled contracts ("
            + ", ".join(CONTRACTS)
            + ")"
        )

    frame["lot_grams"] = frame["symbol"].map(lambda s: CONTRACTS[s].lot_grams)
    frame["quote_grams"] = frame["symbol"].map(lambda s: CONTRACTS[s].quote_grams)
    frame["purity"] = frame["symbol"].map(lambda s: CONTRACTS[s].purity)
    # Rupees per gram of fine gold: the only unit that is comparable across
    # contracts with different quote bases and purities.
    frame["px_per_g_fine"] = frame["Close"] / frame["quote_grams"] / frame["purity"]

    frame["no_trade"] = (
        (frame["Volume"] <= 0)
        | frame["Close"].isna()
        | (frame["Close"] == 0)
        | (frame["High"].isna())
        | (frame["Low"].isna())
        | (frame["High"] == 0)
        | (frame["Low"] == 0)
    )

    frame = frame.sort_values(["symbol", "expiry", "date"]).reset_index(drop=True)
    return frame[
        [
            "date",
            "symbol",
            "expiry",
            "Close",
            "High",
            "Low",
            "Volume",
            "OpenInterest",
            "lot_grams",
            "quote_grams",
            "purity",
            "px_per_g_fine",
            "no_trade",
        ]
    ]


def _parse_expiry(text: Any) -> pd.Timestamp:
    """Expiries use a compact ``05OCT2026`` form."""
    m = re.fullmatch(r"(\d{2})([A-Z]{3})(\d{4})", str(text).strip())
    if not m:
        raise ValueError(f"unrecognised MCX expiry: {text!r}")
    day, mon, year = m.groups()
    month = _MONTHS.index(mon.title()) + 1
    return pd.Timestamp(year=int(year), month=month, day=int(day))
