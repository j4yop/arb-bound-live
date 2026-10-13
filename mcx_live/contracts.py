"""The gold contract master.

Every fact here is a property of the *contract*, not of a price series. They
come from MCX's published contract specifications and are cited in
``docs/TINYFISH.md``. Keeping them in one module means a downstream number is
only ever wrong for one reason.

Nothing in this module does arithmetic on market data; that separation is what
lets the ingest and analysis layers be tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Contract:
    """One MCX gold futures contract we model."""

    symbol: str
    lot_grams: float
    quote_grams: float
    purity: float
    delivery_unit_grams: float
    price_quote: str
    source: str

    @property
    def grams_of_fine_per_quote(self) -> float:
        return self.quote_grams * self.purity


CONTRACTS: dict[str, Contract] = {
    "GOLDM": Contract(
        symbol="GOLDM",
        lot_grams=100.0,
        quote_grams=10.0,
        purity=0.995,  # settles at Rate x 999/995 at delivery
        delivery_unit_grams=100.0,
        price_quote="Ex-Ahmedabad, inclusive of import duty",
        source="https://www.mcxindia.com/products/bullion/gold",
    ),
    "GOLDGUINEA": Contract(
        symbol="GOLDGUINEA",
        lot_grams=8.0,
        quote_grams=8.0,
        purity=0.999,
        delivery_unit_grams=8.0,
        price_quote="Ex-Mumbai, inclusive of import duty",
        source="https://www.mcxindia.com/products/bullion/gold",
    ),
    "GOLDPETAL": Contract(
        symbol="GOLDPETAL",
        lot_grams=1.0,
        quote_grams=1.0,
        purity=0.999,
        delivery_unit_grams=1.0,
        price_quote="Ex-Mumbai, inclusive of import duty",
        source="MCX/TRD/858/2024 annexure (31 Dec 2024)",
    ),
    "GOLDTEN": Contract(
        symbol="GOLDTEN",
        lot_grams=10.0,
        quote_grams=10.0,
        purity=0.999,
        delivery_unit_grams=10.0,
        price_quote="Ex-Mumbai, inclusive of import duty",
        source="MCX/TRD/134/2025 (18 Mar 2025)",
    ),
}


def symbols() -> list[str]:
    return list(CONTRACTS)


def spec(symbol: str) -> Contract:
    return CONTRACTS[symbol.strip().upper()]
