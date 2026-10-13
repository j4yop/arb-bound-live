"""Ingest tests: parsing, normalisation, and the date bug.

All offline. A fixed payload captured from the live API on 2026-10-12 is used
so the tests exercise the real shape rather than a synthetic one.
"""

from __future__ import annotations

import pandas as pd
import pytest

from mcx_live.ingest import (
    NotABhavcopy,
    extract_bhavcopy_array,
    normalise,
    parse_display_date,
    parse_slash_date,
    trade_dates,
)


def _row(**over):
    row = {
        "sLTT": None,
        "Date": "10/12/2026",  # MM/DD/YYYY per MCX's API payload
        "DateDisplay": "12 Oct 2026",  # unambiguous
        "Symbol": "GOLDM ",
        "ExpiryDate": "05OCT2026",
        "Open": 100000.0,
        "High": 100500.0,
        "Low": 99500.0,
        "Close": 100100.0,
        "PreviousClose": 99800.0,
        "Volume": 12000,
        "VolumeInThousands": "12.000 KGS ",
        "Value": 5000.0,
        "OpenInterest": 40000,
        "InstrumentName": "FUTCOM",
    }
    row.update(over)
    return row


def _gold_rows():
    return [
        _row(Symbol="GOLDM ", ExpiryDate="05OCT2026"),
        _row(Symbol="GOLDPETAL ", ExpiryDate="05OCT2026", Close=100100.0),
        _row(Symbol="GOLDGUINEA ", ExpiryDate="05OCT2026", Close=780000.0),
        _row(Symbol="GOLDTEN ", ExpiryDate="05OCT2026", Close=999000.0),
    ]


# ------------------------------------------------------- date handling


def test_display_date_is_unambiguous():
    assert parse_display_date("12 Oct 2026") == pd.Timestamp("2026-10-12")


def test_ambiguous_slash_date_is_not_silently_shifted():
    """The regression this repo exists partly to hold.

    ``Date`` is MM/DD/YYYY. Both readings of ``10/12/2026`` parse, so a
    format-order guess moves every row by two months. ``DateDisplay`` resolves
    it. Verified against the live payload on 2026-10-12.
    """
    frame = pd.DataFrame(_gold_rows())
    resolved = set(trade_dates(frame).dt.strftime("%Y-%m-%d"))
    assert resolved == {"2026-10-12"}, resolved


def test_slash_fallback_still_works_without_display():
    """CSV exports carry no DateDisplay, so the fallback must still parse."""
    assert parse_slash_date("12/10/2026") == pd.Timestamp("2026-10-12")


def test_slash_date_still_rejects_rubbish():
    with pytest.raises(ValueError):
        parse_slash_date("not a date")


# ------------------------------------------------------------- extraction


def test_extractor_finds_the_array_in_real_page_text():
    page = (
        'garbage before [{"sLTT":null,"Date":"10/12/2026"},'
        '{"sLTT":null,"Date":"11/12/2026"}]  trailing junk'
    )
    rows = extract_bhavcopy_array(page)
    assert [r["Date"] for r in rows] == ["10/12/2026", "11/12/2026"]


def test_extractor_rejects_a_page_with_no_rows():
    with pytest.raises(NotABhavcopy) as exc:
        extract_bhavcopy_array("<html>no bhavcopy here</html>")
    assert "no bhavcopy rows" in str(exc.value)


# -------------------------------------------------------------- normalise


def test_options_rows_are_dropped():
    """OPTFUT rows share the underlying's Symbol and would corrupt every average."""
    rows = _gold_rows()
    rows.append(
        _row(Symbol="GOLDM ", ExpiryDate="05OCT2026", InstrumentName="OPTFUT",
             StrikePrice=240000.0, OptionType="CE", Volume=0)
    )
    frame = normalise(rows)
    assert len(frame) == 4
    assert set(frame["symbol"]) == {"GOLDM", "GOLDPETAL", "GOLDGUINEA", "GOLDTEN"}


def test_symbols_are_stripped_and_matched():
    frame = normalise(_gold_rows())
    assert set(frame["symbol"]) == set(
        ["GOLDM", "GOLDPETAL", "GOLDGUINEA", "GOLDTEN"]
    )


def test_per_gram_of_fine_is_comparable_across_contracts():
    """100100 for 10g at 995 must exceed the same nominal price for 10g at 999."""
    a = normalise([_row(Symbol="GOLDM ", Close=100100.0)])["px_per_g_fine"].iloc[0]
    b = normalise([_row(Symbol="GOLDTEN ", Close=100100.0)])["px_per_g_fine"].iloc[0]
    assert a > b, "purity must raise rupees-per-gram-of-fine, not lower it"


def test_non_gold_rows_are_discarded():
    rows = _gold_rows()
    rows.append(_row(Symbol="ZINC ", ExpiryDate="30OCT2026"))
    frame = normalise(rows)
    assert "ZINC" not in set(frame["symbol"])


def test_empty_input_is_an_actionable_error():
    with pytest.raises(NotABhavcopy):
        normalise([])


def test_missing_symbol_column_is_an_actionable_error():
    bad = [{"Date": "10/12/2026", "ExpiryDate": "05OCT2026"}]
    with pytest.raises(NotABhavcopy) as exc:
        normalise(bad)
    assert "Symbol" in str(exc.value)
