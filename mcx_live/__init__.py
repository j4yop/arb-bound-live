"""mcx_live -- live MCX gold data through TinyFish, and the bound that judges it.

TinyFish Builder Challenge (Hack in Hills '26).

The repo answers one question: is a cross-contract MCX gold gap an opportunity,
or the cost of closing it? The bound is structural and fitted to nothing, so it
can disagree with the data -- and it does.
"""

from .contracts import CONTRACTS, Contract
from .ingest import (
    NotABhavcopy,
    extract_bhavcopy_array,
    normalise,
    parse_display_date,
    parse_slash_date,
    trade_dates,
)
from .plane import (
    MCX_BHAVCOPY,
    MCX_CIRCULARS,
    TinyFishUnavailable,
    archive_circulars,
    fetch_bhavcopy,
    fetch_page,
    live_frame,
    search,
    wait_for_run,
    wallet,
)

__all__ = [
    "CONTRACTS", "Contract", "NotABhavcopy", "TinyFishUnavailable",
    "MCX_BHAVCOPY", "MCX_CIRCULARS",
    "archive_circulars", "extract_bhavcopy_array", "fetch_bhavcopy",
    "fetch_page", "live_frame", "normalise", "parse_display_date",
    "parse_slash_date", "search", "trade_dates", "wait_for_run", "wallet",
]

__version__ = "0.1.0"
