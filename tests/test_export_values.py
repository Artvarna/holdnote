"""Weights from the export's own values: the portfolio view with no prices.

A user on the web or a phone has no desktop browser for closes, but most
positions exports state each holding's value. Those weights are the export's,
on its date; nothing is fetched and nothing guessed about the currency.
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fund_holdings as fh  # noqa: E402
import import_holdings as ih  # noqa: E402
import market_weights as mw  # noqa: E402

SP500 = "IE00B3XXRP09"
NVIDIA = "US67066G1040"
APPLE = "US0378331005"
WORLD = "IE00BFY0GT14"


def run(module, *args: str) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = module.main(list(args))
    return code, buf.getvalue()


def imported(tmp_path: Path, text: str, *extra: str) -> tuple[int, str, Path]:
    src = tmp_path / "export.csv"
    src.write_text(text, encoding="utf-8")
    out = tmp_path / "me" / "holdings.csv"
    code, printed = run(ih, str(src), "-o", str(out), "--as-of", "2026-10-16", *extra)
    return code, printed, out


DEGIRO = ("Product;Symbol/ISIN;Amount;Closing;Local value;Value in EUR\n"
          "CASH & CASH FUND & FTX CASH (EUR);;;;EUR 12,40;12,40\n"
          f"VANGUARD S&P500 UCITS ETF;{SP500};7;98,10;GBP 686,70;790,20\n"
          f"NVIDIA CORP;{NVIDIA};2,5;180,00;USD 450,00;385,10\n")


def test_import_keeps_the_account_currency_value_not_the_local_one(tmp_path):
    code, printed, out = imported(tmp_path, DEGIRO)
    assert code == 0, printed
    h = {x.isin: x for x in ih.load_holdings(out).holdings}
    assert (h[SP500].value, h[SP500].value_ccy) == (Decimal("790.2"), "EUR")
    assert (h[NVIDIA].value, h[NVIDIA].value_ccy) == (Decimal("385.1"), "EUR")
    assert 'value from "Value in EUR"' in printed
    assert "can weigh holdings from them" in printed


def test_value_currency_from_the_cells(tmp_path):
    code, printed, out = imported(
        tmp_path, "Name,ISIN,Shares,Market value\n"
                  f"Apple,{APPLE},3,$690.00\nSPDR World,{WORLD},12.5,$501.25\n")
    assert code == 0, printed
    assert {x.value_ccy for x in ih.load_holdings(out).holdings} == {"USD"}


def test_a_value_without_a_currency_is_asked_for_not_guessed(tmp_path):
    text = f"Ticker,ISIN,Name,Quantity,Price,Value\nAAPL,{APPLE},Apple Inc,3,230,690\n"
    code, printed, out = imported(tmp_path, text)
    assert code == 0 and "does not say in which currency" in printed
    assert run(mw, "--holdings", str(out))[1].startswith(
        "Allocation: Not available - the export's values do not say their currency")
    code, printed, out = imported(tmp_path, text, "--value-currency", "usd")
    assert ih.load_holdings(out).holdings[0].value_ccy == "USD"


def test_allocation_from_values(tmp_path):
    _code, _printed, out = imported(tmp_path, DEGIRO)
    code, printed = run(mw, "--holdings", str(out))
    assert code == 0, printed
    assert printed.startswith("Allocation (weights from the export's values, EUR, as of 2026-10-16)")
    assert "| Portfolio | NVIDIA CORP | 2.5 | - | 385.10 | 32.77 | - | - |" in printed
    assert "| Portfolio | total | | | 1175.30 | 100.00 | - | - |" in printed
    assert "Allocation prices: none read" in printed


def test_values_in_two_currencies_need_rates(tmp_path):
    text = ("Name,ISIN,Shares,Currency,Value\n"
            f"Apple,{APPLE},3,USD,690\nSPDR World,{WORLD},12.5,EUR,501.25\n")
    _code, _printed, out = imported(tmp_path, text)
    code, printed = run(mw, "--holdings", str(out))
    assert code == 1
    assert "values are in EUR and USD - weights need ECB rates" in printed


def test_a_missing_value_withholds_the_value_route(tmp_path):
    text = ("Name,ISIN,Shares,Value in EUR\n"
            f"Apple,{APPLE},3,640\nSPDR World,{WORLD},12.5,\n")
    _code, printed, out = imported(tmp_path, text)
    assert "no value for" in printed
    code, printed = run(mw, "--holdings", str(out))
    assert code == 1 and "gives no value for" in printed


def test_reimport_without_values_drops_old_ones(tmp_path):
    _code, _p, out = imported(tmp_path, DEGIRO)
    _code, _p, out = imported(tmp_path, f"isin,quantity\n{SP500},8\n{NVIDIA},2.5\n")
    assert all(h.value is None for h in ih.load_holdings(out).holdings)


def test_look_through_weights_come_from_values_without_prices(tmp_path):
    _code, _printed, out = imported(tmp_path, DEGIRO)
    weights, tickers, kinds, as_of = fh.market_weights(None, tmp_path, tmp_path, tmp_path, out)
    assert weights == {SP500: Decimal("67.23"), NVIDIA: Decimal("32.77")}
    assert kinds == {SP500: "fund", NVIDIA: "stock"} and as_of == date(2026, 10, 16)
