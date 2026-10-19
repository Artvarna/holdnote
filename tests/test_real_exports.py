"""Exports as twelve brokers write them (the pre-launch 'stranger test').

Each file is a positions or history export in the shape and language its
broker uses. The importer must read the ones it can without help, ask for
exactly what it cannot know (an ISIN a US export never states, the currency of
an unlabelled value), and never turn a cell that is not a number into one.
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import import_holdings as ih  # noqa: E402
import market_weights as mw  # noqa: E402

EXPORTS = ROOT / "tests" / "fixtures" / "exports"


def run(module, *args: str) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = module.main(list(args))
    return code, buf.getvalue()


def imported(tmp_path: Path, name: str, *extra: str):
    out = tmp_path / "holdings.csv"
    code, printed = run(ih, str(EXPORTS / name), "-o", str(out), "--as-of", "2026-10-16", *extra)
    held = {h.isin: h for h in ih.load_holdings(out).holdings} if code == 0 else {}
    return code, printed, held, out


# file, holdings expected (ISIN: quantity, value, currency), and whether the
# values alone give weights
READ_AS_IS = [
    ("degiro_nl.csv", {"IE00BK5BQT80": ("34", "4520.64", "EUR"), "US0378331005": ("5", "1083.45", "EUR"),
                       "IE00BKM4GZ66": ("40", "1364.80", "EUR")}, True),
    ("scalable_de.csv", {"IE00B4L5Y983": ("85.25", "9241.10", "EUR"), "DE0008404005": ("4", "1410", "EUR"),
                         "IE00BTJRMP35": ("60", "3789", "EUR")}, True),
    ("comdirect.csv", {"IE00BK5BQT80": ("120", "15955.20", "EUR"), "DE0007164600": ("10", "2413", "EUR")}, True),
    ("polish_xtb.csv", {"IE00B5BMR087": ("3", "7951.20", "PLN"), "PLPKN0000018": ("20", "1502", "PLN")}, True),
    ("spanish.csv", {"IE00B3XXRP09": ("40", "4112.80", "EUR"), "ES0144580Y14": ("100", "1650", "EUR")}, True),
    ("hl_uk.csv", {"IE00B3RBWM25": ("120", "12614.40", "GBP"), "IE0005042456": ("800", "6898.40", "GBP")}, True),
    ("ibkr_activity.csv", {"IE00B5BMR087": ("12", "7326.6", "EUR"), "IE00BK5BQT80": ("50", "6648", "EUR"),
                           "US5949181045": ("10", "5124", "USD")}, False),
    ("boursorama_fr.csv", {"IE0003XJA0J9": ("150", "5730", ""), "FR0000120271": ("12", "673.20", "")}, False),
]


@pytest.mark.parametrize("name, want, weighs", READ_AS_IS, ids=[r[0] for r in READ_AS_IS])
def test_export_reads_without_help(tmp_path, name, want, weighs):
    code, printed, held, out = imported(tmp_path, name)
    assert code == 0, printed
    assert set(held) == set(want)
    for isin, (qty, value, ccy) in want.items():
        h = held[isin]
        assert h.quantity == Decimal(qty), (isin, h.quantity)
        assert h.value == Decimal(value) and h.value_ccy == ccy, (isin, h.value, h.value_ccy)
    code, alloc = run(mw, "--holdings", str(out))
    assert (code == 0) == weighs, alloc


def test_ibkr_quantities_never_come_from_another_section(tmp_path):
    # The instrument section's ISIN cells sit under the Quantity column; read
    # as numbers they were 5,949,181,045 shares of Microsoft.
    _code, printed, held, _out = imported(tmp_path, "ibkr_activity.csv")
    assert held["US5949181045"].quantity == 10
    assert "MSFT US5949181045 (this export's instrument list)" in printed


def test_tickers_only_uk_export_gets_isins_from_the_catalogue(tmp_path):
    _code, printed, held, _out = imported(tmp_path, "hl_uk.csv")
    assert "VWRL IE00B3RBWM25 (Holdnote's fund catalogue)" in printed
    assert held["IE00B3RBWM25"].kind == "fund"


@pytest.mark.parametrize("name, tickers", [
    ("schwab_us.csv", "VOO, AAPL"), ("fidelity_us.csv", "QQQ, VTI"),
    ("revolut_trading.csv", "TSLA, NVDA")])
def test_us_exports_ask_for_the_isins_they_never_state(tmp_path, name, tickers):
    code, printed, _held, _out = imported(tmp_path, name)
    assert code == 2 and f"no ISIN for {tickers}" in printed


def test_us_export_reads_once_isins_are_given(tmp_path):
    code, printed, held, out = imported(tmp_path, "schwab_us.csv", "--isin", "VOO=US9229083632",
                                        "--isin", "AAPL=US0378331005")
    assert code == 0, printed
    assert held["US9229083632"].quantity == 20 and held["US9229083632"].value == Decimal("11202.40")
    assert held["US0378331005"].value_ccy == "USD"
    assert run(mw, "--holdings", str(out))[0] == 0


def test_an_isin_typo_in_the_export_is_shown_not_fixed(tmp_path):
    code, printed, _held, _out = imported(tmp_path, "bulgarian_isin_typo.csv")
    assert code == 2 and "BGSOFIX03002" in printed and "check digit" in printed


@pytest.mark.parametrize("raw", ["IE00B5BMR087", "US5949181045", "Apple Inc", "N/A 12"])
def test_text_is_not_a_number(raw):
    assert ih.parse_number(raw, False) is None


@pytest.mark.parametrize("raw, comma, want", [
    ("EUR 4520,64", True, "4520.64"), ("$11,202.40", False, "11202.40"), ("1 234,56 €", True, "1234.56"),
    ("USD 450.00", False, "450.00"), ("(12.50)", False, "-12.50")])
def test_numbers_with_currencies_still_parse(raw, comma, want):
    assert ih.parse_number(raw, comma) == Decimal(want)
