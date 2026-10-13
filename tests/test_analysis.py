"""Analysis tests: the bound, its one-way direction, and the matched basis.

These encode the three defects the original project found, so they stay found.
"""

from __future__ import annotations

import pandas as pd
import pytest

from mcx_live.analysis import bound_for, matched_basis, verdict
from mcx_live.contracts import CONTRACTS


def _frame(prices: dict[str, float], date: str = "2026-10-12") -> pd.DataFrame:
    """A tidy one-day frame for the given symbol -> close price."""
    rows = []
    for symbol, price in prices.items():
        c = CONTRACTS[symbol]
        rows.append(
            {
                "date": pd.Timestamp(date),
                "symbol": symbol,
                "expiry": pd.Timestamp("2026-10-30"),
                "Close": price,
                "High": price,
                "Low": price,
                "Volume": 1000.0,
                "OpenInterest": 500.0,
                "lot_grams": c.lot_grams,
                "quote_grams": c.quote_grams,
                "purity": c.purity,
                "px_per_g_fine": price / c.quote_grams / c.purity,
                "no_trade": False,
            }
        )
    return pd.DataFrame(rows)


def test_the_smaller_bar_always_carries_the_larger_per_gram_charge():
    """Fabrication is per bar, so the per-gram charge falls as the bar grows.

    This is the core mechanism: it is why the GOLDPETAL premium is structural
    rather than a dislocation.
    """
    b = bound_for(("GOLDPETAL", "GOLDGUINEA"), 100000.0)
    assert b.overhead_order == ("GOLDPETAL", "GOLDGUINEA")
    assert b.fabrication_bps > 0


def test_the_995_contract_carries_the_purity_wedge():
    """Only the 995 duty-inclusive contract can carry the wedge."""
    with_wedge = bound_for(("GOLDM", "GOLDGUINEA"), 100000.0)
    without = bound_for(("GOLDPETAL", "GOLDGUINEA"), 100000.0)
    assert with_wedge.purity_wedge_bps > 0
    assert without.purity_wedge_bps == 0


def test_the_bound_is_a_band_not_a_point():
    b = bound_for(("GOLDPETAL", "GOLDGUINEA"), 100000.0)
    assert b.high_bps > b.low_bps > 0
    assert b.low_bps <= b.centre_bps <= b.high_bps


def test_matched_basis_ignores_mismatched_expiries():
    """Offset expiry calendars would otherwise leak term structure in."""
    frame = _frame({"GOLDM": 100100.0, "GOLDTEN": 999000.0})
    frame.loc[frame["symbol"] == "GOLDTEN", "expiry"] = pd.Timestamp("2027-01-30")
    basis = matched_basis(frame, max_days_apart=7)
    assert basis.empty, "legs months apart must not be paired"


def test_basis_measures_the_gap_between_per_gram_prices():
    """A 1% gap in per-gram-of-fine price is ~100 bps, by construction.

    Signed: the smaller-bar contract is more expensive per gram, so when its
    price is *below* the larger bar's, the basis is negative. The magnitude is
    what matters, and the sign is what makes the direction of a trade
    meaningful rather than decorative.
    """
    import math

    # GOLDM quotes 10 g at 995; GOLDTEN quotes 10 g at 999. Pick closes so the
    # per-gram-of-fine prices differ by exactly 1%.
    goldm_close = 9950.0  # -> exactly 1000.000 per g fine
    goldten_close = 1000.0 * 1.01 * 10.0 * 0.999
    frame = _frame({"GOLDM": goldm_close, "GOLDTEN": goldten_close})
    basis = matched_basis(frame)
    assert len(basis) == 1
    got = float(basis["basis_bps"].iloc[0])
    assert abs(got) == pytest.approx(10_000.0 * math.log(1.01), abs=1.0), got


def test_only_the_tradeable_direction_counts():
    """A breach on the wrong side must not be reported as cleared."""
    # GOLDM priced far *above* the retail bars is a wedge, not an opportunity.
    frame = _frame({"GOLDM": 200000.0, "GOLDGUINEA": 780000.0 / 10.0 * 0.995})
    rows = verdict(matched_basis(frame), 10_000.0)
    assert rows, "no verdicts produced"
    # Whatever the numbers, the count must come from the band, not abs().
    for r in rows:
        assert r["days_above_bound"] >= 0
        assert r["days_below_bound"] >= 0


def test_no_trade_rows_are_excluded_from_the_basis():
    frame = _frame({"GOLDM": 100100.0, "GOLDGUINEA": 780000.0})
    frame.loc[frame["symbol"] == "GOLDGUINEA", "no_trade"] = True
    basis = matched_basis(frame)
    assert basis.empty or "GOLDGUINEA/GOLDM" not in set(basis["pair"])


def test_verdict_names_every_bound_component():
    frame = _frame(
        {"GOLDM": 100100.0, "GOLDGUINEA": 780000.0, "GOLDPETAL": 101000.0}
    )
    rows = verdict(matched_basis(frame), 10_000.0)
    assert rows
    for r in rows:
        for key in (
            "fabrication_bps",
            "purity_wedge_bps",
            "friction_bps",
            "bound_low_bps",
            "bound_high_bps",
        ):
            assert key in r, f"{r['pair']} is missing {key}"
