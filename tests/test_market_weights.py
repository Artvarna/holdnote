"""Tests for scripts/market_weights.py: the Allocation table."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))

import contract  # noqa: E402
import market_weights as mw  # noqa: E402

AS_OF = date(2026, 10, 2)
DAY = AS_OF.isoformat()


def rows():
    return [
        mw.Row("ETF", "I1", "AAA", Decimal("2"), Decimal("60")),
        mw.Row("ETF", "I2", "BBB", Decimal("10"), Decimal("15")),
        mw.Row("Stock", "I3", "CCC", Decimal("1"), Decimal("25")),
    ]


def prices(**over):
    base = {
        "I1": {"price": "30", "currency": "EUR", "date": DAY},
        "I2": {"price": "850", "currency": "GBX", "date": DAY},
        "I3": {"price": "22", "currency": "USD", "date": DAY},
    }
    base.update(over)
    return base


FX = {"USD": {"per_eur": "1.1", "date": DAY}, "GBP": {"per_eur": "0.85", "date": DAY}}
PIES = {"ETF": Decimal("75"), "Stock": Decimal("25")}


def table(p=None, fx=FX, r=None):
    priced = mw.price_rows(r or rows(), AS_OF, p or prices(), fx)
    return priced, mw.allocation_table(priced, PIES)


def cells(lines, ticker):
    for line in lines:
        parts = [c.strip() for c in line.strip("|").split("|")]
        if parts[1] == ticker:
            return parts
    raise AssertionError(ticker)


# --------------------------------------------------------------------------
# Valuation
# --------------------------------------------------------------------------


def test_values_convert_to_eur_at_the_stated_rate():
    priced, _ = table()
    assert [p.value for p in priced] == [Decimal("60.00"), Decimal("100.00"), Decimal("20.00")]


def test_gbx_is_pence():
    priced, _ = table()
    assert priced[1].value == Decimal("100.00")  # 10 x 8.50 GBP / 0.85


def test_weights_come_from_the_printed_values():
    _, lines = table()
    assert cells(lines, "AAA")[5:] == ["33.33", "60.00", "-26.67"]
    assert cells(lines, "BBB")[5:] == ["55.56", "15.00", "+40.56"]
    assert cells(lines, "CCC")[5:] == ["11.11", "25.00", "-13.89"]


def test_pie_totals_and_portfolio_total():
    _, lines = table()
    assert [c for c in lines if c.startswith("| ETF pie")][0].split("|")[5:8] == [
        " 160.00 ", " 88.89 ", " 75.00 "]
    assert lines[-1] == "| Portfolio | total | | | 180.00 | 100.00 | 100.00 | 0.00 |"


def test_a_target_without_a_holding_is_zero_not_missing():
    r = rows() + [mw.Row("Stock", "I4", "DDD", Decimal(0), Decimal("0"))]
    priced, lines = table(r=r)
    assert priced[-1].value == Decimal("0.00")
    assert cells(lines, "DDD")[4] == "0.00"


# --------------------------------------------------------------------------
# One as-of date, or no weights
# --------------------------------------------------------------------------


@pytest.mark.parametrize("p, fx, reason", [
    (prices(I3={"price": "22", "currency": "USD", "date": "2026-10-01"}), FX,
     "priced only at 2026-10-01, table as-of is 2026-10-02"),
    (prices(I3=None), FX, "no price supplied"),
    (prices(), {"GBP": FX["GBP"]}, "no USD rate supplied"),
    (prices(), {"GBP": FX["GBP"], "USD": {"per_eur": "1.1", "date": "2026-10-01"}},
     "USD rate dated 2026-10-01, table as-of is 2026-10-02"),
])
def test_a_row_that_cannot_be_valued_at_the_as_of_withholds_every_weight(p, fx, reason):
    p = {k: v for k, v in p.items() if v is not None}
    priced, lines = table(p, fx)
    assert priced[2].reason == reason
    body = [line for line in lines[2:]]
    assert all("Not available" in line.split("|")[6] for line in body)
    assert cells(lines, "AAA")[4] == "60.00"  # values that can be computed still print


def test_a_floor_quantity_is_not_valued():
    r = rows()
    r[2] = mw.Row("Stock", "I3", "CCC", None, Decimal("25"))
    priced, lines = table(r=r)
    assert priced[2].reason.startswith("quantity is a floor")
    assert cells(lines, "CCC")[2] == "floor"


@pytest.mark.parametrize("bad", ["0", "-3", "abc", "NaN"])
def test_a_price_that_is_not_a_positive_number_is_refused(bad):
    with pytest.raises(mw.Refused):
        table(prices(I1={"price": bad, "currency": "EUR", "date": DAY}))


# --------------------------------------------------------------------------
# What the table may say
# --------------------------------------------------------------------------


def test_the_table_carries_numbers_only():
    _, lines = table()
    text = "\n".join(lines).lower()
    for word in ("over", "under", "rebalanc", "buy", "sell", "should"):
        assert word not in text


# --------------------------------------------------------------------------
# The real exports
# --------------------------------------------------------------------------

REAL = REPO / "data" / "t212"
REAL_PRICES = {
    "as_of": "2026-10-02",
    "prices": {
        "IE00BFY0GT14": {"price": "47.545", "currency": "EUR", "date": "2026-10-02"},
        "IE00B3XXRP09": {"price": "110.5075", "currency": "GBP", "date": "2026-10-02"},
        "IE00BKM4GZ66": {"price": "55.34", "currency": "USD", "date": "2026-10-02"},
        "LU0908500753": {"price": "26502.5", "currency": "GBX", "date": "2026-10-02"},
        "US0378331005": {"price": "333.69", "currency": "USD", "date": "2026-10-02"},
        "US67066G1040": {"price": "233.95", "currency": "USD", "date": "2026-10-02"},
        "US02079K3059": {"price": "343.50", "currency": "USD", "date": "2026-10-02"},
    },
    "fx": {
        "USD": {"per_eur": "1.1225", "date": "2026-10-02"},
        "GBP": {"per_eur": "0.85033", "date": "2026-10-02"},
    },
}

needs_real = pytest.mark.skipif(not any(REAL.glob("*.csv")), reason="no real exports in data/t212")


def run_cli(tmp_path, spec):
    f = tmp_path / "prices.json"
    f.write_text(json.dumps(spec), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(REPO / "scripts" / "market_weights.py"), "--prices", str(f),
         "--data-dir", str(REAL), "--pies", str(REPO / "me" / "pies.md"),
         "--ownership", str(REPO / "me" / "ownership.md")],
        capture_output=True, text=True, cwd=REPO,
    )


@needs_real
def test_real_exports_give_a_complete_table_that_passes_the_contract(tmp_path):
    proc = run_cli(tmp_path, REAL_PRICES)
    assert proc.returncode == 0, proc.stdout
    out = proc.stdout
    assert "| Portfolio | total |" in out and "Not available" not in out
    table_text = out.split("\n\n")[0]
    result = "RESULT\n\n" + table_text.replace(
        "Allocation (market weights, EUR, as of 2026-10-02)", "Allocation")
    assert contract.allocation_problems({"RESULT": result}) == []


@needs_real
def test_an_as_of_before_the_last_trade_is_refused(tmp_path):
    spec = dict(REAL_PRICES, as_of="2025-12-01")
    proc = run_cli(tmp_path, spec)
    assert proc.returncode == 1
    assert proc.stdout.startswith("Allocation: Not available - as-of 2025-12-01 precedes the last trade")


# --------------------------------------------------------------------------
# contract.allocation_problems
# --------------------------------------------------------------------------

GOOD = [
    "Allocation",
    "| Pie | Ticker | Quantity | Close | Value (EUR) | Weight (market) | Target | Diff (pp) |",
    "|---|---|---|---|---|---|---|---|",
    "| ETF | AAA | 2 | EUR 30 | 60.00 | 60.00 | 75.00 | -15.00 |",
    "| ETF pie | total | | | 60.00 | 60.00 | 75.00 | -15.00 |",
    "| Stock | CCC | 1 | USD 44 | 40.00 | 40.00 | 25.00 | +15.00 |",
    "| Stock pie | total | | | 40.00 | 40.00 | 25.00 | +15.00 |",
    "| Portfolio | total | | | 100.00 | 100.00 | 100.00 | 0.00 |",
    "",
]


def check(lines):
    return contract.allocation_problems({"RESULT": "\n".join(lines)})


def test_a_consistent_table_passes():
    assert check(GOOD) == []


def test_a_diff_that_is_not_weight_minus_target_is_caught():
    bad = list(GOOD)
    bad[3] = bad[3].replace("-15.00", "-14.00")
    assert check(bad) == ["AAA: Diff -14.00 is not Weight 60.00 - Target 75.00 (-15.00)"]


@pytest.mark.parametrize("cell", ["overweight", "-15.00 (under)", "rebalance"])
def test_words_in_the_diff_column_are_caught(cell):
    bad = list(GOOD)
    bad[3] = bad[3].replace("-15.00", cell)
    found = check(bad)
    assert len(found) == 1 and found[0].startswith("AAA: Diff")


def test_holding_weights_must_sum_to_100():
    bad = list(GOOD)
    bad[5] = bad[5].replace("| 40.00 | 40.00 |", "| 40.00 | 39.00 |").replace("+15.00", "+14.00")
    assert any("sum to 99.00" in p for p in check(bad))


def test_withheld_weights_pass():
    na = [line.replace("| 60.00 | 75.00 | -15.00 |", "| Not available | 75.00 | Not available |")
          for line in GOOD]
    assert check(na) == []


# --------------------------------------------------------------------------
# Units: pence, and the cost-basis guard (found in review, 2026-10-05)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("ccy", ["GBX", "GBp", "GBx"])
def test_every_pence_spelling_is_pence(ccy):
    priced, _ = table(prices(I2={"price": "850", "currency": ccy, "date": DAY}))
    assert priced[1].value == Decimal("100.00")


def test_upper_case_gbp_is_pounds():
    r = rows()
    priced, _ = table(prices(I2={"price": "8.50", "currency": "GBP", "date": DAY}), r=r)
    assert priced[1].value == Decimal("100.00")


def test_pence_read_as_pounds_is_withheld_by_the_cost_guard():
    r = rows()
    r[1] = mw.Row("ETF", "I2", "BBB", Decimal("10"), Decimal("15"), cost_eur=Decimal("95"))
    priced, lines = table(prices(I2={"price": "850", "currency": "GBP", "date": DAY}), r=r)
    assert priced[1].value is None
    assert priced[1].reason == "value EUR 10000.00 against cost basis EUR 95.00 - check the close's unit (GBP)"
    assert all("Not available" in line.split("|")[6] for line in lines[2:])


def test_an_ordinary_gain_passes_the_cost_guard():
    r = rows()
    r[0] = mw.Row("ETF", "I1", "AAA", Decimal("2"), Decimal("60"), cost_eur=Decimal("20"))
    priced, _ = table(r=r)
    assert priced[0].value == Decimal("60.00")  # 3x cost: plausible


@pytest.mark.parametrize("ccy", ["CHF", "", "pence"])
def test_an_unsupported_currency_is_named(ccy):
    priced, _ = table(prices(I1={"price": "30", "currency": ccy, "date": DAY}))
    assert priced[0].value is None and priced[0].reason.startswith("price currency")


@needs_real
def test_real_meud_in_gbp_by_mistake_is_caught(tmp_path):
    spec = json.loads(json.dumps(REAL_PRICES))
    spec["prices"]["LU0908500753"]["currency"] = "GBP"
    proc = run_cli(tmp_path, spec)
    meud = [line for line in proc.stdout.splitlines() if "| MEUD |" in line][0]
    assert "against cost basis EUR 46.63" in meud


@needs_real
def test_real_meud_in_yahoo_pence_matches_gbx(tmp_path):
    spec = json.loads(json.dumps(REAL_PRICES))
    spec["prices"]["LU0908500753"]["currency"] = "GBp"
    proc = run_cli(tmp_path, spec)
    meud = [line for line in proc.stdout.splitlines() if "| MEUD |" in line][0]
    assert "| 46.04 | 14.34 |" in meud


# --------------------------------------------------------------------------
# contract.lookthrough_problems
# --------------------------------------------------------------------------

LOOK = [
    "Look-through (top-10 depth, % of portfolio, as of 2026-10-02)",
    "| Company | Direct | via AAA | Total |",
    "|---|---|---|---|",
    "| Apple | 40.00 | 3.00 | 43.00 |",
    "| Microsoft | — | 2.50 | 2.50 |",
    "",
]


def look(lines):
    return contract.lookthrough_problems({"RESULT": "\n".join(GOOD + lines)})


def test_a_consistent_lookthrough_passes():
    assert look(LOOK) == []


def test_a_total_that_is_not_the_row_sum_is_caught():
    bad = list(LOOK)
    bad[3] = "| Apple | 40.00 | 3.00 | 44.00 |"
    assert look(bad) == ["Look-through Apple: Total 44.00 is not the sum of its cells (43.00)"]


def test_a_fund_cannot_contribute_more_than_its_own_weight():
    bad = list(LOOK)
    bad[4] = "| Microsoft | — | 61.00 | 61.00 |"
    assert look(bad) == ["Look-through Microsoft: via AAA 61.00 exceeds AAA's own weight 60.00"]


def test_lookthrough_not_available_passes():
    na = ["Look-through", "| Company | Total |", "|---|---|",
          "| all | Not available — no market weights |", ""]
    assert look(na) == []
