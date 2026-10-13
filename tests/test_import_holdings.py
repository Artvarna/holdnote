"""import_holdings: any broker's export -> me/holdings.csv.

The exports below are synthetic, written in the shapes investment apps use
(semicolon + decimal comma, a "Symbol/ISIN" column, a preamble above the
header, Excel, buy/sell histories). Holdings and quantities are invented.
"""

from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import import_holdings as ih  # noqa: E402

WORLD = "IE00BFY0GT14"
SP500 = "IE00B3XXRP09"
APPLE = "US0378331005"
NVIDIA = "US67066G1040"


def write(tmp_path: Path, name: str, text: str) -> Path:
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def run(tmp_path: Path, *args: str) -> tuple[int, str]:
    out = tmp_path / "me" / "holdings.csv"
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = ih.main([*args, "-o", str(out)])
    return code, buf.getvalue()


def holdings(tmp_path: Path) -> dict[str, ih.Holding]:
    f = ih.load_holdings(tmp_path / "me" / "holdings.csv")
    return {h.isin: h for h in f.holdings}


# --- ISINs and numbers ------------------------------------------------------

def test_isin_check_digit():
    assert ih.isin_valid(APPLE)
    assert not ih.isin_valid("US0378331006")
    assert not ih.isin_valid("AAPL")


@pytest.mark.parametrize("raw,comma,want", [
    ("1.234,56", True, "1234.56"),
    ("1,234.56", False, "1234.56"),
    ("12,5", True, "12.5"),
    ("(3)", False, "-3"),
    ("−2", False, "-2"),
    ("1 250", False, "1250"),
    ("", False, None),
])
def test_parse_number(raw, comma, want):
    got = ih.parse_number(raw, comma)
    assert (str(got) if got is not None else None) == want


def test_decimal_comma_detection():
    assert ih.decimal_comma(["12,5", "3"], ",")
    assert not ih.decimal_comma(["1,234", "5"], ",")
    assert ih.decimal_comma(["10", "3"], ";")
    assert not ih.decimal_comma(["2.5"], ";")


# --- positions exports ------------------------------------------------------

def test_plain_positions_csv(tmp_path):
    f = write(tmp_path, "positions.csv",
              "Ticker,ISIN,Name,Quantity,Price,Value\n"
              f"SPPW,{WORLD},SPDR MSCI World UCITS ETF,12.5,40.1,501.25\n"
              f"AAPL,{APPLE},Apple Inc,3,230,690\n")
    code, out = run(tmp_path, str(f))
    assert code == 0, out
    h = holdings(tmp_path)
    assert h[WORLD].quantity == Decimal("12.5") and h[WORLD].kind == "fund"
    assert h[APPLE].quantity == Decimal("3") and h[APPLE].kind == "stock"
    assert "(guessed)" in out


def test_semicolon_decimal_comma_symbol_isin_column(tmp_path):
    f = write(tmp_path, "Portfolio.csv",
              "Product;Symbol/ISIN;Amount;Closing;Local value;Value in EUR\n"
              "CASH & CASH FUND & FTX CASH (EUR);;;;EUR 12,40;12,40\n"
              f"VANGUARD S&P500 UCITS ETF;{SP500};7;98,10;GBP 686,70;790,20\n"
              f"NVIDIA CORP;{NVIDIA};2,5;180,00;USD 450,00;385,10\n")
    code, out = run(tmp_path, str(f))
    assert code == 0, out
    h = holdings(tmp_path)
    assert set(h) == {SP500, NVIDIA}
    assert h[NVIDIA].quantity == Decimal("2.5")
    assert h[NVIDIA].ticker == ""  # the Symbol/ISIN cell was the ISIN
    assert 'confirm these are share counts' in out  # quantity came from "Amount"
    assert "Skipped: 1 rows" in out


def test_preamble_above_header_and_german_headers(tmp_path):
    f = write(tmp_path, "depot.csv",
              "Depotübersicht;Stand 13.10.2026\n"
              "\n"
              "Bezeichnung;ISIN;Stück;Kurs;Währung\n"
              f"Apple Inc.;{APPLE};4;210,5;EUR\n"
              "Summe;;;;\n")
    code, out = run(tmp_path, str(f))
    assert code == 0, out
    assert holdings(tmp_path)[APPLE].quantity == Decimal("4")
    assert "header on line 3" in out


def test_isin_found_inside_another_cell(tmp_path):
    f = write(tmp_path, "export.csv",
              "Instrument,Units\n"
              f"Apple Inc ({APPLE}),3\n")
    code, out = run(tmp_path, str(f))
    assert code == 0, out
    assert APPLE in holdings(tmp_path)


def test_same_isin_twice_is_summed(tmp_path):
    f = write(tmp_path, "two_accounts.csv",
              "Symbol,ISIN,Shares\n"
              f"AAPL,{APPLE},1\nAAPL,{APPLE},2.25\n")
    assert run(tmp_path, str(f))[0] == 0
    assert holdings(tmp_path)[APPLE].quantity == Decimal("3.25")


def test_two_brokers_in_one_run(tmp_path):
    a = write(tmp_path, "a.csv", f"ISIN,Quantity\n{APPLE},1\n")
    b = write(tmp_path, "b.csv", f"ISIN;Anzahl\n{APPLE};2\n{WORLD};5\n")
    code, out = run(tmp_path, str(a), str(b))
    assert code == 0, out
    h = holdings(tmp_path)
    assert h[APPLE].quantity == Decimal("3") and h[WORLD].quantity == Decimal("5")


def test_xlsx(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Open Positions"
    ws.append(["Account statement"])
    ws.append(["Name", "ISIN", "Units", "Open rate"])
    ws.append(["Apple", APPLE, 1.5, 200.0])
    p = tmp_path / "statement.xlsx"
    wb.save(p)
    code, out = run(tmp_path, str(p))
    assert code == 0, out
    assert holdings(tmp_path)[APPLE].quantity == Decimal("1.5")


# --- what stops a write ------------------------------------------------------

def test_missing_isin_needs_input_then_supplied(tmp_path):
    f = write(tmp_path, "revolut.csv", "Ticker,Quantity\nAAPL,2\n")
    code, out = run(tmp_path, str(f))
    assert code == 2 and "no ISIN for AAPL" in out
    assert not (tmp_path / "me" / "holdings.csv").exists()
    code, out = run(tmp_path, str(f), "--isin", f"AAPL={APPLE}")
    assert code == 0, out
    assert holdings(tmp_path)[APPLE].ticker == "AAPL"


def test_supplied_isin_with_bad_check_digit_is_refused(tmp_path):
    f = write(tmp_path, "t.csv", "Ticker,Quantity\nAAPL,2\n")
    code, out = run(tmp_path, str(f), "--isin", "AAPL=US0378331006")
    assert code == 1 and "check digit" in out


def test_no_quantity_column_needs_a_map(tmp_path):
    f = write(tmp_path, "odd.csv", f"ISIN,Name,Held\n{APPLE},Apple,3\n")
    code, out = run(tmp_path, str(f))
    assert code == 2 and '"Held"' in out
    code, out = run(tmp_path, str(f), "--map", "quantity=Held")
    assert code == 0, out
    assert holdings(tmp_path)[APPLE].quantity == Decimal("3")


def test_map_to_a_missing_column_lists_columns(tmp_path):
    f = write(tmp_path, "p.csv", f"ISIN,Quantity\n{APPLE},1\n")
    code, out = run(tmp_path, str(f), "--map", "quantity=Nope")
    assert code == 2 and '"Quantity"' in out


def test_trading212_history_is_sent_to_portfolio_sync(tmp_path):
    f = write(tmp_path, "t212.csv",
              "Action,Time,ISIN,Ticker,Name,No. of shares,Price / share\n"
              f"Market buy,2026-01-02 10:00:00,{APPLE},AAPL,Apple,1,200\n")
    code, out = run(tmp_path, str(f))
    assert code == 1 and "Trading 212 history export" in out


def test_negative_position_is_refused(tmp_path):
    f = write(tmp_path, "p.csv", f"ISIN,Quantity\n{APPLE},-1\n")
    code, out = run(tmp_path, str(f))
    assert code == 1 and "short positions" in out


# --- transaction histories --------------------------------------------------

def test_history_nets_buys_and_sells(tmp_path):
    f = write(tmp_path, "trades.csv",
              "Date,Type,ISIN,Name,Quantity,Price\n"
              f"2026-01-05,Buy,{APPLE},Apple,3,200\n"
              f"2026-02-05,Sell,{APPLE},Apple,-1,210\n"
              f"2026-03-01,Dividend,{APPLE},Apple,,1.2\n"
              f"2026-03-10,Buy,{WORLD},SPDR MSCI World UCITS ETF,4,40\n"
              ",Deposit,,,,500\n")
    code, out = run(tmp_path, str(f))
    assert code == 0, out
    h = holdings(tmp_path)
    assert h[APPLE].quantity == Decimal("2")  # a sell is subtracted whatever its sign
    assert h[WORLD].quantity == Decimal("4")
    assert "history" in out and "Dividend x1" in out
    assert ih.load_holdings(tmp_path / "me" / "holdings.csv").as_of.isoformat() == "2026-03-10"


def test_history_day_first_dates(tmp_path):
    f = write(tmp_path, "trades.csv",
              "Datum;Typ;ISIN;Anzahl\n"
              f"05.01.2026;Kauf;{APPLE};3\n"
              f"14.02.2026;Verkauf;{APPLE};1\n")
    assert run(tmp_path, str(f))[0] == 0
    f2 = ih.load_holdings(tmp_path / "me" / "holdings.csv")
    assert f2.as_of.isoformat() == "2026-02-14"
    assert f2.holdings[0].quantity == Decimal("2")


def test_history_fully_sold_holding_is_dropped(tmp_path):
    f = write(tmp_path, "trades.csv",
              "Date,Side,ISIN,Qty\n"
              f"2026-01-05,BUY,{APPLE},3\n2026-01-06,SELL,{APPLE},3\n"
              f"2026-01-07,BUY,{NVIDIA},1\n")
    assert run(tmp_path, str(f))[0] == 0
    assert set(holdings(tmp_path)) == {NVIDIA}


def test_history_with_a_split_is_refused(tmp_path):
    f = write(tmp_path, "trades.csv",
              "Date,Type,ISIN,Quantity\n"
              f"2026-01-05,Buy,{NVIDIA},1\n2026-06-10,Stock split,{NVIDIA},9\n")
    code, out = run(tmp_path, str(f))
    assert code == 1 and "export your current positions" in out


def test_history_selling_more_than_bought_is_refused(tmp_path):
    f = write(tmp_path, "trades.csv",
              f"Date,Type,ISIN,Quantity\n2026-01-05,Sell,{APPLE},2\n")
    code, out = run(tmp_path, str(f))
    assert code == 1 and "sells exceed buys" in out


# --- re-import keeps the user's decisions ----------------------------------

def test_reimport_keeps_kind_group_and_target(tmp_path):
    out_file = tmp_path / "me" / "holdings.csv"
    f = write(tmp_path, "p.csv", f"ISIN,Name,Quantity\n{APPLE},Apple,1\n{WORLD},World ETF,5\n")
    assert run(tmp_path, str(f))[0] == 0
    text = out_file.read_text().replace(f"{APPLE},,Apple,stock,1,Portfolio,",
                                        f"{APPLE},AAPL,Apple,stock,1,Stocks,20")
    out_file.write_text(text)
    f = write(tmp_path, "p.csv", f"ISIN,Quantity\n{APPLE},2\n")
    code, out = run(tmp_path, str(f))
    assert code == 0, out
    h = holdings(tmp_path)
    assert h[APPLE].quantity == Decimal("2")
    assert (h[APPLE].group, h[APPLE].target, h[APPLE].ticker) == ("Stocks", Decimal("20"), "AAPL")
    assert WORLD not in h and "removed: World ETF" in out
    assert "(guessed)" not in out


def test_kind_override(tmp_path):
    f = write(tmp_path, "p.csv", f"Name,ISIN,Quantity\nSomething Odd,{APPLE},1\n")
    assert run(tmp_path, str(f), "--kind", f"{APPLE}=fund")[0] == 0
    assert holdings(tmp_path)[APPLE].kind == "fund"


def test_dry_run_writes_nothing(tmp_path):
    f = write(tmp_path, "p.csv", f"ISIN,Quantity\n{APPLE},1\n")
    code, out = run(tmp_path, str(f), "--dry-run")
    assert code == 0 and "not written" in out
    assert not (tmp_path / "me" / "holdings.csv").exists()


# --- the holdings file itself ------------------------------------------------

def test_load_holdings_checks(tmp_path):
    p = tmp_path / "holdings.csv"
    good = f"# as_of: 2026-10-01\nisin,ticker,name,kind,quantity,group,target_pct\n{APPLE},AAPL,Apple,stock,1,,25\n"
    p.write_text(good)
    f = ih.load_holdings(p)
    assert f.as_of.isoformat() == "2026-10-01"
    assert f.holdings[0].group == "Portfolio" and f.holdings[0].target == Decimal("25")
    for bad, why in [
        (good.replace(APPLE, "US0378331006"), "not a valid ISIN"),
        (good.replace("stock", "crypto"), "fund or stock"),
        (good.replace(",25", ",125"), "outside 0-100"),
        (good + f"{APPLE},AAPL,Apple,stock,1,,\n", "appears twice"),
        (good.replace(",1,,25", ",-1,,25"), "zero or more"),
    ]:
        p.write_text(bad)
        with pytest.raises(ih.Refused, match=why):
            ih.load_holdings(p)


def test_holdings_csv_is_committed_but_raw_exports_are_not():
    import subprocess
    repo = Path(__file__).resolve().parents[1]

    def ignored(path: str) -> bool:
        return subprocess.run(["git", "check-ignore", "-q", "--no-index", path],
                              cwd=repo).returncode == 0

    assert not ignored("me/holdings.csv")  # setup commits it to the user's private copy
    assert ignored("Portfolio.csv") and ignored("data/export.csv") and ignored("me/export.csv")
