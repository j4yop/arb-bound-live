"""The structural bound, and the verdict.

This is the part that answers the question the repo exists to answer: *is this
cross-contract gap actually available, or is it the cost of closing it?*

The bound is **structural, not fitted**. It is built from:

* **per-bar fabrication cost** -- fixed per bar, so the per-gram charge scales
  *inversly* with bar size. An 8 g bar and a 1 g bar do not carry the same
  premium per gram, and that difference is a real cost, not a dislocation.
* **the purity/duty wedge** -- GOLDM settles 995 into 999 delivery, and its
  quote base is duty-inclusive; the retail bars are not.
* **statutory friction** -- brokerage, GST/CTT, stamp duty and exchange fees.

Fitting nothing to the price series is the whole point: a bound fitted to the
data cannot disagree with the data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from .contracts import CONTRACTS

# --- stated assumptions, carried as ranges and swept -----------------------
# MCX does not publish minting cost, so this is an assumption, not a
# measurement. The band is swept by the CLI and reported in the UI.
MINT_COST_PER_BAR_INR: tuple[float, float] = (20.0, 60.0)
DUTY_WEDGE_BPS: tuple[float, float] = (0.0, 400.0)
FRICTION_BPS_PER_LEG: tuple[float, float] = (4.0, 35.0)


@dataclass(frozen=True)
class Bound:
    """The tradeable band for one ordered pair of contracts."""

    pair: str
    centre_bps: float
    low_bps: float
    high_bps: float
    fabrication_bps: float
    purity_wedge_bps: float
    friction_bps: float
    overhead_order: tuple[str, str]

    @property
    def width_bps(self) -> float:
        return self.high_bps - self.low_bps


def _fabrication_penalty(
    small: str, large: str, mint_cost: float, reference_px: float
) -> float:
    """The per-gram fabrication cost of splitting the larger bar into the smaller.

    Reported in basis points *of the market price per gram of fine gold*.

    The mint cost is fixed per bar, so the charge per gram is ``mint / bar
    grams``. Splitting an 8 g bar into 1 g bars leaves each 1 g bar carrying
    ``mint / 1`` where the original carried ``mint / 8``; the difference is the
    real, structural, one-way cost of obtaining the smaller bar. Dividing by the
    *price* (not by the contract's gram count) is what makes it comparable
    across quote bases and purities -- getting this wrong produced a 175,000 bps
    bound on the first live run.
    """
    if reference_px <= 0:
        raise ValueError("reference price must be positive")
    small_grams = CONTRACTS[small].lot_grams
    large_grams = CONTRACTS[large].lot_grams
    per_gram = mint_cost * (1.0 / small_grams - 1.0 / large_grams)
    return per_gram / reference_px * 10_000.0


def bound_for(pair: tuple[str, str], reference_px: float) -> Bound:
    """Build the bound for ``pair`` in terms of the cheaper-per-gram side."""
    a, b = pair
    overhead_a = CONTRACTS[a].lot_grams
    overhead_b = CONTRACTS[b].lot_grams
    # The smaller bar always carries the higher per-gram fabrication charge.
    if overhead_a <= overhead_b:
        small, large = a, b
    else:
        small, large = b, a

    mint_low, mint_high = MINT_COST_PER_BAR_INR
    fab_low = _fabrication_penalty(small, large, mint_low, reference_px)
    fab_high = _fabrication_penalty(small, large, mint_high, reference_px)

    duty_low, duty_high = DUTY_WEDGE_BPS
    # Only the 995 purity, duty-inclusive contract can carry the wedge. The
    # 999 retail bars do not, so the test is 995 specifically, not "< 1.0".
    wedge = duty_high if 0.995 in (CONTRACTS[small].purity, CONTRACTS[large].purity) else 0.0

    fric_low, fric_high = FRICTION_BPS_PER_LEG

    low = fab_low + duty_low + 2 * fric_low
    high = fab_high + wedge + 2 * fric_high
    centre = (low + high) / 2.0

    return Bound(
        pair=f"{small}/{large}",
        centre_bps=centre,
        low_bps=low,
        high_bps=high,
        fabrication_bps=(fab_low + fab_high) / 2.0,
        purity_wedge_bps=wedge / 2.0,
        friction_bps=(fric_low + fric_high),
        overhead_order=(small, large),
    )


def matched_basis(
    frame: pd.DataFrame, max_days_apart: int = 7
) -> pd.DataFrame:
    """Maturity-matched per-gram basis for every ordered contract pair.

    A basis is only comparable when the two legs expire at roughly the same
    moment. Comparing across all listed expiries mixes term structure into the
    cross-contract spread, which is exactly the defect this repo was built to
    avoid.
    """
    traded = frame[~frame["no_trade"]]
    if traded.empty:
        return pd.DataFrame(
            columns=["date", "pair", "basis_bps", "days_apart", "small", "large"]
        )

    symbols = sorted(traded["symbol"].unique())
    out = []
    for i, small in enumerate(symbols):
        for large in symbols[i + 1 :]:
            left = traded[traded["symbol"] == small][
                ["date", "expiry", "px_per_g_fine"]
            ]
            right = traded[traded["symbol"] == large][
                ["date", "expiry", "px_per_g_fine"]
            ]
            merged = pd.merge(
                left,
                right,
                on="date",
                suffixes=("_small", "_large"),
                how="inner",
            )
            if merged.empty:
                continue
            days_apart = (
                (merged["expiry_small"] - merged["expiry_large"]).dt.days.abs()
            )
            merged["days_apart"] = days_apart
            merged = merged[days_apart <= max_days_apart]
            if merged.empty:
                continue
            ratio = merged["px_per_g_fine_small"] / merged["px_per_g_fine_large"]
            merged["basis_bps"] = 10_000.0 * ratio.apply(math.log)
            merged["pair"] = f"{small}/{large}"
            merged["small"] = small
            merged["large"] = large
            out.append(
                merged[["date", "pair", "basis_bps", "days_apart", "small", "large"]]
            )
    if not out:
        return pd.DataFrame(
            columns=["date", "pair", "basis_bps", "days_apart", "small", "large"]
        )
    return pd.concat(out, ignore_index=True)


def verdict(basis: pd.DataFrame, reference_px: float) -> list[dict]:
    """Compare each pair's basis against its own structural bound.

    Only the *dear-to-manufacture* direction is tradeable, because fabrication
    is one-way: small bars are always more expensive per gram, so the gap that
    means anything is the small bar being unusually cheap to *obtain* by
    splitting a larger one. Taking an absolute value would treat both
    directions as tradeable and manufacture hundreds of false breaches.
    """
    rows = []
    for pair, group in basis.groupby("pair"):
        if group.empty:
            continue
        small = group["small"].iloc[0]
        large = group["large"].iloc[0]
        b = bound_for((small, large), reference_px)
        level = float(group["basis_bps"].median())
        above = int((group["basis_bps"] > b.high_bps).sum())
        below = int((group["basis_bps"] < b.low_bps).sum())
        rows.append(
            {
                "pair": b.pair,
                "observations": int(len(group)),
                "median_basis_bps": round(level, 1),
                "bound_low_bps": round(b.low_bps, 1),
                "bound_high_bps": round(b.high_bps, 1),
                "bound_centre_bps": round(b.centre_bps, 1),
                "fabrication_bps": round(b.fabrication_bps, 1),
                "purity_wedge_bps": round(b.purity_wedge_bps, 1),
                "friction_bps": round(b.friction_bps, 1),
                "days_above_bound": above,
                "days_below_bound": below,
                "cleared": above > 0,
            }
        )
    rows.sort(key=lambda r: r["pair"])
    return rows
