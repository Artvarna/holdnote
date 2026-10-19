"""Tests for scripts/fund_holdings.py: Holdings overlap and Look-through
from full issuer files.

Each fixture is built in the shape the issuer's live file had on 2026-10-09
(column names, date formats, units, non-equity rows), small enough that
every expected figure below is worked by hand.
"""

from __future__ import annotations

import argparse
import io
import json
import zipfile
from datetime import date
from decimal import Decimal
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))

import contract  # noqa: E402
import fund_holdings as fh  # noqa: E402

SPPW, EIMI, VUSA, MEUD = (fh.SOURCES[i] for i in
                          ("IE00BFY0GT14", "IE00BKM4GZ66", "IE00B3XXRP09", "LU0908500753"))

NVDA, AAPL, GOOGL, GOOG = "US67066G1040", "US0378331005", "US02079K3059", "US02079K1079"
ASML, PKO, ETE = "NL0010273215", "PLPKO0000016", "GRS003003035"


def filler(prefix: str, n: int) -> list[str]:
    return [f"{prefix}{i:08d}{i % 10}" for i in range(n)]  # XSA00000000 0 ...


# --- fixtures in each issuer's shape -----------------------------------------

def make_xlsx(rows: list[list[object]]) -> bytes:
    """A minimal xlsx: strings shared, numbers inline, one blank row kept."""
    shared: list[str] = []
    sheet = []
    for r, row in enumerate(rows, start=1):
        if not row:
            continue  # a blank row is absent from the XML, as in SSGA's file
        cells = []
        for c, value in enumerate(row):
            ref = f"{chr(65 + c)}{r}"
            if isinstance(value, (int, float, Decimal)):
                cells.append(f'<c r="{ref}"><v>{value}</v></c>')
            else:
                shared.append(str(value))
                cells.append(f'<c r="{ref}" t="s"><v>{len(shared) - 1}</v></c>')
        sheet.append(f'<row r="{r}">{"".join(cells)}</row>')
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/worksheets/sheet1.xml",
                   f'<worksheet {ns}><sheetData>{"".join(sheet)}</sheetData></worksheet>')
        z.writestr("xl/sharedStrings.xml",
                   f'<sst {ns}>' + "".join(f"<si><t>{escape(s)}</t></si>" for s in shared)
                   + "</sst>")
    return buf.getvalue()


SSGA_HEADER = ["ISIN", "SEDOL", "Security Name", "Currency", "Number of Shares",
               "Percent of Fund", "Trade Country Name", "Local Price",
               "Sector Classification", "Industry Classification", "Base Market Value"]


def ssga_bytes(isin: str = SPPW.isin, as_of: str = "08-Oct-2026", extra=()) -> bytes:
    def row(code, name, weight):
        return [code, "0000000", name, "USD", 1, weight, "United States", 1, "IT", "IT", 1]
    rows = [
        ["Fund Name:", "State Street SPDR MSCI World UCITS ETF (Acc)"],
        ["ISIN:", isin],
        ["Ticker Symbol:", "SPPW GY"],
        ["Holdings As Of:", as_of],
        [],
        SSGA_HEADER,
        row(NVDA, "NVIDIA Corporation", "5.000000"),
        row(AAPL, "Apple Inc.", "4.000000"),
        row(GOOGL, "Alphabet Inc. Class A", "1.500000"),
        row(GOOG, "Alphabet Inc. Class C", "1.300000"),
        row(ASML, "ASML Holding NV", "0.500000"),
        *[row(code, f"SPPW filler {i}", "4.385000") for i, code in enumerate(filler("XSA", 20))],
        *extra,
        row("Unassigned", "U.S. Dollar", "-"),
        [],
        ["Marketing communication. The performance data quoted represents past performance."],
    ]
    return make_xlsx(rows)


def ishares_bytes(first_line: str = 'Fund Holdings as of,"07/Oct/2026"') -> bytes:
    header = ("Ticker,Name,Sector,Asset Class,Market Value,Weight (%),Notional Value,"
              "Shares,Price,Location,Exchange,Market Currency")

    def row(t, name, cls, weight, loc, exch):
        return ",".join(f'"{v}"' for v in
                        (t, name, "IT", cls, "1.00", weight, "1.00", "1.00", "1.00", loc, exch, "USD"))
    lines = [
        first_line, "", header,
        row("2330", "TAIWAN SEMICONDUCTOR MANUFACTURING", "Equity", "14.00", "Taiwan",
            "Taiwan Stock Exchange"),
        row("PKO", "POWSZECHNA KASA OSZCZEDNOSCI BANK", "Equity", "0.19", "Poland",
            "Warsaw Stock Exchange/Equities/Main Market"),
        row("ETE", "NATIONAL BANK OF GREECE", "Equity", "0.11", "Greece",
            "Athens Exchange S.A. Cash Market"),
        *[row(f"{9000 + i}", f"EIMI FILLER {i} LTD", "Equity", "4.285", "Taiwan",
              "Taiwan Stock Exchange") for i in range(20)],
        row("USD", "USD/THB", "FX", "0.00", "Thailand", "-"),
        "",
    ]
    return "\r\n".join(lines).encode("utf-8-sig")


def vanguard_bytes(items_over=None, total=None, last=None) -> bytes:
    def item(isin, name, issuer, weight, kind="EQ.STOCK"):
        return {"issuerName": issuer, "securityLongDescription": name,
                "marketValuePercentage": weight, "isin": isin, "ticker": "",
                "securityType": kind, "effectiveDate": "2026-08-31",
                "bloombergIsoCountry": "US"}
    items = [
        item(NVDA, "NVIDIA Corp", "NVIDIA Corp", 8.0),
        item(AAPL, "Apple Inc", "Apple Inc", 7.0),
        item(GOOGL, "Alphabet Inc Class A", "Alphabet Inc", 2.0),
        item(GOOG, "Alphabet Inc Class C", "Alphabet Inc", 1.7),
        *[item(code, f"VUSA filler {i}", f"VUSA filler {i}", 4.065)
          for i, code in enumerate(filler("XSB", 20))],
        item(None, "S&P500 EMINI FUT  Sep26", "", 0.0, "DE.IND"),
    ]
    if items_over is not None:
        items = items_over(items)
    return json.dumps({"data": {"borHoldings": [{"holdings": {
        "items": items, "totalHoldings": len(items) if total is None else total,
        "lastItemKey": last}}]}}).encode()


def amundi_bytes(product_id: str = MEUD.isin) -> bytes:
    def row(isin, name, bbg, weight, kind="EQUITY_ORDINARY", country="United Kingdom"):
        c = {"bbg": bbg, "isin": isin, "name": name, "weight": weight, "type": kind,
             "date": "2026-10-07", "countryOfRisk": country}
        return {"compositionCharacteristics": c, "weight": weight}
    rows = [
        row(ASML, "ASML HOLDING NV", "ASML NA", 0.05, country="Netherlands"),
        row(PKO, "PKO BANK POLSKI", "PKO PW", 0.004, country="Poland"),
        row(ETE, "NATIONAL BANK OF GREECE SA NEW", "ETE GA", 0.003, country="Greece"),
        *[row(code, f"MEUD FILLER {i}", f"F{i} LN", 0.04715)
          for i, code in enumerate(filler("XSC", 20))],
        row(None, None, None, 0.0, "CASH", country=None),
    ]
    return json.dumps({"products": [{"productId": product_id, "composition": {
        "totalNumberOfInstruments": len(rows), "compositionData": rows}}]}).encode()


@pytest.fixture
def holdings_dir(tmp_path: Path) -> Path:
    d = tmp_path / "holdings"
    d.mkdir()
    (d / "SPPW-2026-10-09.xlsx").write_bytes(ssga_bytes())
    (d / "EIMI-2026-10-09.csv").write_bytes(ishares_bytes())
    (d / "VUSA-2026-10-09.json").write_bytes(vanguard_bytes())
    (d / "MEUD-2026-10-09.json").write_bytes(amundi_bytes())
    return d


def load_all(d: Path) -> dict[str, fh.Fund]:
    return {s.ticker: fh.load_fund(s, fh.latest_file(d, s.ticker)) for s in fh.SOURCES.values()}


# --- parsers ----------------------------------------------------------------

def test_ssga_reads_every_row_to_the_blank_line(holdings_dir):
    fund = load_all(holdings_dir)["SPPW"]
    assert fund.as_of == date(2026, 10, 8)
    assert len(fund.rows) == 26  # 25 securities + the cash row; disclaimer excluded
    assert sum(1 for r in fund.rows if r.equity) == 25
    assert sum(r.weight for r in fund.rows) == Decimal("100.000000")


def test_ssga_refuses_another_funds_file(tmp_path):
    path = tmp_path / "SPPW-2026-10-09.xlsx"
    path.write_bytes(ssga_bytes(isin="IE00B4L5Y983"))
    with pytest.raises(fh.Refused, match="not IE00BFY0GT14"):
        fh.load_fund(SPPW, path)


def test_ssga_reads_a_serial_date(tmp_path):
    path = tmp_path / "SPPW-2026-10-09.xlsx"
    path.write_bytes(ssga_bytes(as_of=46303))  # Excel serial for 2026-10-08
    assert fh.load_fund(SPPW, path).as_of == date(2026, 10, 8)


def test_ishares_maps_exchanges_to_bloomberg_codes(holdings_dir):
    fund = load_all(holdings_dir)["EIMI"]
    assert fund.as_of == date(2026, 10, 7)
    by_name = {r.name: r for r in fund.rows}
    assert by_name["POWSZECHNA KASA OSZCZEDNOSCI BANK"].bbg == "PKO PW"
    assert by_name["NATIONAL BANK OF GREECE"].bbg == "ETE GA"
    assert by_name["TAIWAN SEMICONDUCTOR MANUFACTURING"].bbg == ""
    assert fund.unmatched_exchanges == 21  # TSMC and the 20 Taiwan fillers
    assert not by_name["USD/THB"].equity


def test_ishares_refuses_the_german_file(tmp_path):
    path = tmp_path / "EIMI-2026-10-09.csv"
    path.write_bytes(ishares_bytes(first_line='Fondsposition per,"07.Okt.2026"'))
    with pytest.raises(fh.Refused, match="not the English file"):
        fh.load_fund(EIMI, path)


def test_vanguard_uses_issuer_names_and_month_end(holdings_dir):
    fund = load_all(holdings_dir)["VUSA"]
    assert fund.as_of == date(2026, 8, 31)
    assert not fund.rows[-1].equity  # the future
    assert fund.rows[2].issuer_name == "Alphabet Inc"


@pytest.mark.parametrize("kwargs, message", [
    ({"last": "abc"}, "one page of several"),
    ({"total": 999}, "against totalHoldings"),
])
def test_vanguard_refuses_a_partial_response(tmp_path, kwargs, message):
    path = tmp_path / "VUSA-2026-10-09.json"
    path.write_bytes(vanguard_bytes(**kwargs))
    with pytest.raises(fh.Refused, match=message):
        fh.load_fund(VUSA, path)


def test_vanguard_refuses_mixed_dates(tmp_path):
    def mix(items):
        items[0]["effectiveDate"] = "2026-07-31"
        return items
    path = tmp_path / "VUSA-2026-10-09.json"
    path.write_bytes(vanguard_bytes(items_over=mix))
    with pytest.raises(fh.Refused, match="effective dates"):
        fh.load_fund(VUSA, path)


def test_amundi_weights_are_fractions_read_as_percent(holdings_dir):
    fund = load_all(holdings_dir)["MEUD"]
    assert fund.rows[0].weight == Decimal("5.000")
    assert fund.rows[1].bbg == "PKO PW"
    assert sum(r.weight for r in fund.rows) == Decimal("100.00000")


def test_amundi_refuses_another_product(tmp_path):
    path = tmp_path / "MEUD-2026-10-09.json"
    path.write_bytes(amundi_bytes(product_id="LU1681043599"))
    with pytest.raises(fh.Refused, match="not LU0908500753"):
        fh.load_fund(MEUD, path)


def test_a_top_ten_is_not_a_full_file(tmp_path):
    def top(items):
        return items[:10]
    path = tmp_path / "VUSA-2026-10-09.json"
    path.write_bytes(vanguard_bytes(items_over=top))
    with pytest.raises(fh.Refused, match="equity rows"):
        fh.load_fund(VUSA, path)


def test_weights_outside_the_band_refuse(tmp_path):
    path = tmp_path / "SPPW-2026-10-09.xlsx"
    extra = [["XSZ000000001", "0", "Doubled", "USD", 1, "50.0", "x", 1, "x", "x", 1]]
    path.write_bytes(ssga_bytes(extra=extra))
    with pytest.raises(fh.Refused, match="weights sum to 150.00"):
        fh.load_fund(SPPW, path)


def test_latest_file_wins(tmp_path):
    (tmp_path / "SPPW-2026-10-01.xlsx").write_bytes(b"old")
    (tmp_path / "SPPW-2026-10-09.xlsx").write_bytes(b"new")
    assert fh.latest_file(tmp_path, "SPPW").name == "SPPW-2026-10-09.xlsx"


# --- matching ---------------------------------------------------------------

def test_share_classes_combine_by_cusip_issuer():
    assert fh.company_key(GOOGL) == fh.company_key(GOOG) == "cusip:02079K"
    assert fh.company_key(ASML) == f"isin:{ASML}"


def test_name_key_folds_one_issuers_lines():
    assert fh.name_key("SAMSUNG ELECTRONICS LTD") == fh.name_key("SAMSUNG ELECTRONICS")


def test_exposures(holdings_dir):
    exps = fh.exposures(list(load_all(holdings_dir).values()))
    alphabet = fh.company_key(GOOGL)
    assert exps["SPPW"].weights[alphabet] == Decimal("2.800000")
    assert exps["VUSA"].weights[alphabet] == Decimal("3.7")
    # EIMI's PKO row joins MEUD's through the Bloomberg ticker
    assert exps["EIMI"].weights[f"isin:{PKO}"] == Decimal("0.19")
    assert exps["EIMI"].weights[f"isin:{ETE}"] == Decimal("0.11")


def test_holdings_table_shared_weight_is_the_sum_of_minimums(holdings_dir):
    funds = load_all(holdings_dir)
    order = ["SPPW", "MEUD", "EIMI", "VUSA"]
    exps = fh.exposures(list(funds.values()))
    lines = fh.holdings_table(order, funds, {}, exps, ["VUSA", "SPPW", "MEUD", "EIMI"])
    rows = {line.split("|")[1].strip(): line.split("|")[2:4] for line in lines[2:]}
    # NVIDIA 5 + Apple 4 + Alphabet min(2.80, 3.70)
    assert rows["SPPW - VUSA"][1].strip() == "11.80"
    assert rows["SPPW - VUSA"][0].strip().startswith("3 (largest: NVIDIA Corp, Apple Inc, Alphabet Inc)")
    assert rows["SPPW - MEUD"][1].strip() == "0.50"
    # PKO min(0.40, 0.19) + National Bank of Greece min(0.30, 0.11)
    assert rows["MEUD - EIMI"][1].strip() == "0.30"
    assert rows["SPPW - EIMI"] == [" 0 ", " 0 "]
    assert rows["MEUD - VUSA"] == [" 0 ", " 0 "]


def test_holdings_table_names_a_missing_fund(holdings_dir):
    funds = load_all(holdings_dir)
    del funds["EIMI"]
    exps = fh.exposures(list(funds.values()))
    lines = fh.holdings_table(["SPPW", "EIMI"], funds, {"EIMI": "www.ishares.com returned 403"},
                              exps, ["VUSA"])
    assert lines[2] == ("| SPPW - EIMI | Not available - EIMI: www.ishares.com returned 403 "
                        "| Not available |")


# --- look-through -----------------------------------------------------------

FUND_W = {"SPPW": Decimal("40.00"), "MEUD": Decimal("15.00"),
          "EIMI": Decimal("11.00"), "VUSA": Decimal("8.00")}
DIRECT = {fh.company_key(AAPL): Decimal("13.00"), fh.company_key(NVDA): Decimal("8.00"),
          fh.company_key(GOOGL): Decimal("5.00")}
DIRECT_NAMES = {fh.company_key(AAPL): "AAPL", fh.company_key(NVDA): "NVDA",
                fh.company_key(GOOGL): "GOOGL"}


def lookthrough(holdings_dir, top=3):
    exps = fh.exposures(list(load_all(holdings_dir).values()))
    return fh.lookthrough_table(["SPPW", "MEUD", "EIMI", "VUSA"], exps, FUND_W, DIRECT,
                                DIRECT_NAMES, top, ["VUSA", "SPPW", "MEUD", "EIMI"])


def test_lookthrough_rows(holdings_dir):
    lines, stats = lookthrough(holdings_dir)
    assert lines[0] == "| Company | Direct | via SPPW | via MEUD | via EIMI | via VUSA | Total |"
    rows = [line for line in lines[2:]]
    # held directly first, by Total; then the three largest others
    assert rows[0] == "| Apple Inc | 13.00 | 1.60 | - | - | 0.56 | 15.16 |"
    assert rows[1] == "| NVIDIA Corp | 8.00 | 2.00 | - | - | 0.64 | 10.64 |"
    # 40 x 2.80 / 100 = 1.12; 8 x 3.70 / 100 = 0.296 -> 0.30
    assert rows[2] == "| Alphabet Inc | 5.00 | 1.12 | - | - | 0.30 | 6.42 |"
    # 11 x 14 / 100 = 1.54; the SPPW fillers 40 x 4.385 / 100 = 1.754 -> 1.75
    assert rows[3].endswith("| 1.75 | - | - | - | 1.75 |")
    assert len(rows) == 6
    assert stats["shown"] == 6


def test_lookthrough_passes_the_contract(holdings_dir):
    lines, _ = lookthrough(holdings_dir)
    result = "Look-through (market weights, as of 2026-10-09)\n" + "\n".join(lines) + "\n"
    assert contract.lookthrough_problems({"RESULT": result}) == []


def test_hidden_bets_are_the_companies_reached_through_two_or_more_holdings(holdings_dir):
    lines, stats = lookthrough(holdings_dir, top=1)
    bets = fh.hidden_bets(stats["reached"])
    # Read from every company the cells reach, not the printed rows (top=1)
    table = fh.hidden_bets_table(bets)
    assert table[0] == "| Company | Through | Largest part | Total | Added by the others |"
    assert table[2:] == [
        "| Apple Inc | Direct 13.00 · via SPPW 1.60 · via VUSA 0.56 | Direct 13.00 | 15.16 | 2.16 |",
        "| NVIDIA Corp | Direct 8.00 · via SPPW 2.00 · via VUSA 0.64 | Direct 8.00 | 10.64 | 2.64 |",
        "| Alphabet Inc | Direct 5.00 · via SPPW 1.12 · via VUSA 0.30 | Direct 5.00 | 6.42 | 1.42 |",
    ]
    # PKO is reached through MEUD and EIMI, but only 0.06 + 0.02: under 1.00
    assert all("PKO" not in row for row in table)
    assert fh.hidden_bets_method(bets).endswith("3 companies, 32.22 of the portfolio together")


def test_hidden_bets_count_fund_only_companies_and_say_so_when_none(holdings_dir):
    reached = [("Shell", [("Direct", None), ("via A", Decimal("0.70")), ("via B", Decimal("0.40"))],
                Decimal("1.10")),
               ("Tiny", [("Direct", None), ("via A", Decimal("0.50")), ("via B", Decimal("0.49"))],
                Decimal("0.99"))]
    assert fh.hidden_bets_table(fh.hidden_bets(reached))[2] == (
        "| Shell | via A 0.70 · via B 0.40 | via A 0.70 | 1.10 | 0.40 |")
    assert fh.hidden_bets_table([])[2] == (
        "| none | no company reaches 1.00 through two or more holdings | - | 0 | 0 |")


def test_hidden_bets_pass_the_contract_beside_lookthrough(holdings_dir):
    lines, stats = lookthrough(holdings_dir)
    result = ("Look-through (market weights, as of 2026-10-09)\n" + "\n".join(lines) + "\n\n"
              "Hidden bets (market weights, as of 2026-10-09)\n"
              + "\n".join(fh.hidden_bets_table(fh.hidden_bets(stats["reached"]))) + "\n")
    assert contract.hidden_bets_problems({"RESULT": result}) == []
    broken = result.replace("| Direct 13.00 | 15.16 | 2.16 |", "| Direct 13.00 | 15.16 | 2.00 |")
    assert contract.hidden_bets_problems({"RESULT": broken}) == [
        "Hidden bets Apple Inc: Added by the others 2.00 is not Total - Largest part (2.16)"]


def test_parse_lookthrough_round_trips_and_gives_its_floor(holdings_dir):
    lines, stats = lookthrough(holdings_dir)
    rows, floor = fh.parse_lookthrough(lines)
    assert [r[0] for r in rows] == [ln.split("|")[1].strip() for ln in lines[2:]]
    assert floor == Decimal("1.75")  # the smallest fund-only Total printed (the SPPW fillers)
    # Every bet over the floor comes out the same as from the full data
    full = fh.hidden_bets(stats["reached"])
    assert fh.hidden_bets(rows) == full


def test_holdings_table_passes_the_contract(holdings_dir):
    funds = load_all(holdings_dir)
    exps = fh.exposures(list(funds.values()))
    lines = fh.holdings_table(["SPPW", "MEUD", "EIMI", "VUSA"], funds, {}, exps, ["VUSA"])
    result = "Holdings (full issuer files)\n" + "\n".join(lines) + "\n"
    assert contract.holdings_problems({"RESULT": result}) == []


# --- the report command -----------------------------------------------------

def report_args(holdings_dir, prices=None, top=15):
    return argparse.Namespace(holdings_dir=holdings_dir, prices=prices,
                              data_dir=Path("data/t212"), pies=Path("pies.md"),
                              ownership=Path("ownership.md"), top=top,
                              min_country=Decimal("0.50"), min_currency=Decimal("0.50"))


def test_report_without_prices_prints_holdings_and_says_why_no_lookthrough(holdings_dir, capsys):
    assert fh.cmd_report(report_args(holdings_dir)) == 0
    out = capsys.readouterr().out
    assert "Holdings (full issuer files, as of SPPW 2026-10-08, MEUD 2026-10-07, EIMI 2026-10-07, VUSA 2026-08-31)" in out
    assert "| all | Not available - no --prices file, so no market weights |" in out
    assert "Holdings file VUSA:" in out and "as of 2026-08-31" in out
    assert "Holdings dates:" in out  # Vanguard's month-end differs from the daily files


def test_report_with_weights(holdings_dir, capsys, monkeypatch):
    weights = {SPPW.isin: Decimal("40.00"), MEUD.isin: Decimal("15.00"),
               EIMI.isin: Decimal("11.00"), VUSA.isin: Decimal("8.00"),
               AAPL: Decimal("13.00"), NVDA: Decimal("8.00"), GOOGL: Decimal("5.00")}
    tickers = {SPPW.isin: "SPPW", MEUD.isin: "MEUD", EIMI.isin: "EIMI", VUSA.isin: "VUSA",
               AAPL: "AAPL", NVDA: "NVDA", GOOGL: "GOOGL"}
    pies = {i: ("Stock" if i in (AAPL, NVDA, GOOGL) else "ETF") for i in weights}
    monkeypatch.setattr(fh, "market_weights",
                        lambda *a: (weights, tickers, pies, date(2026, 10, 9)))
    assert fh.cmd_report(report_args(holdings_dir, prices=Path("p.json"), top=3)) == 0
    out = capsys.readouterr().out
    assert "| Company | Direct | via SPPW | via MEUD | via EIMI | via VUSA | Total |" in out
    assert "| Apple Inc | 13.00 | 1.60 | - | - | 0.56 | 15.16 |" in out
    assert "Hidden bets (market weights, as of 2026-10-09)" in out
    assert "| NVIDIA Corp | Direct 8.00 · via SPPW 2.00 · via VUSA 0.64 | Direct 8.00 | 10.64 | 2.64 |" in out
    assert "Hidden bets: companies with a Look-through Total of 1.00 or more" in out
    assert "Fund weights consumed: SPPW 40.00, MEUD 15.00, EIMI 11.00, VUSA 8.00" in out
    assert "| United States | 26.00 | 40.00 | - | - | 8.00 | 74.00 |" in out
    assert "Countries direct stocks: the country the fund files give the same company" in out


def test_report_looks_through_the_rest_when_a_held_fund_has_no_file(holdings_dir, capsys, monkeypatch):
    (holdings_dir / "EIMI-2026-10-09.csv").unlink()
    weights = {SPPW.isin: Decimal("60"), MEUD.isin: Decimal("20"),
               EIMI.isin: Decimal("10"), VUSA.isin: Decimal("10")}
    tickers = {i: fh.SOURCES[i].ticker for i in weights}
    monkeypatch.setattr(fh, "market_weights",
                        lambda *a: (weights, tickers, {i: "ETF" for i in weights}, date(2026, 10, 9)))
    fh.cmd_report(report_args(holdings_dir, prices=Path("p.json")))
    out = capsys.readouterr().out
    assert "| SPPW - MEUD | 1 (largest: ASML Holding NV) | 0.50 |" in out
    assert ("Look-through (market weights, as of 2026-10-09; covers the funds worth 90.00% of "
            "the portfolio; not looked through: EIMI 10.00)") in out
    assert "via EIMI" not in out.split("Look-through (")[1].split("Hidden bets")[0]
    # The bucket tables still add up to the whole portfolio.
    countries = out.split("Countries (")[1].split("\n\n")[0]
    assert "| Not looked through | - | - | - | - | 10.00 | 10.00 |" in countries
    assert "Not looked through: EIMI 10.00% of the portfolio (EIMI-" not in out
    assert "Not looked through: EIMI 10.00% of the portfolio (no file in" in out


def test_report_withholds_lookthrough_when_no_fund_has_a_file(holdings_dir, capsys, monkeypatch):
    for f in holdings_dir.iterdir():
        f.unlink()
    weights = {SPPW.isin: Decimal("60"), MEUD.isin: Decimal("40")}
    tickers = {i: fh.SOURCES[i].ticker for i in weights}
    monkeypatch.setattr(fh, "market_weights",
                        lambda *a: (weights, tickers, {i: "ETF" for i in weights}, date(2026, 10, 9)))
    fh.cmd_report(report_args(holdings_dir, prices=Path("p.json")))
    out = capsys.readouterr().out
    assert "| all | Not available - no holdings file for any fund (SPPW 60.00% of the portfolio" in out


def test_a_catalogue_fund_needs_only_ticker_and_isin(tmp_path):
    funds = tmp_path / "funds.md"
    funds.write_text("# Funds\n\n## Funds\n\n| Ticker | ISIN | Issuer | Holdings file |\n"
                     "|---|---|---|---|\n"
                     "| CSPX | IE00B5BMR087 | | |\n"
                     "| VWRL | IE00B3RBWM25 | vanguard | |\n", encoding="utf-8")
    out = fh.load_funds(funds)
    cspx, vwrl = out["IE00B5BMR087"], out["IE00B3RBWM25"]
    assert (cspx.ticker, cspx.issuer) == ("CSPX", "ishares")
    assert "/products/253743/" in cspx.url and cspx.url.endswith("dataType=fund")
    assert cspx.alts and cspx.alts[0].endswith("/products/253743/fund/latest-holdings.csv")
    # VWRL is the distributing share class of VWCE: same holdings, its own ticker and ISIN.
    assert (vwrl.ticker, vwrl.isin, vwrl.issuer) == ("VWRL", "IE00B3RBWM25", "vanguard")
    assert vwrl.body["variables"]["portIds"] == ["9679"]


def test_the_catalogue_parses_and_names_only_supported_issuers():
    rows = fh.funds_table(fh.CATALOG_FILE)
    assert len(rows) >= 20
    assert {r[2] for r in rows} <= set(fh.ISSUERS)
    isins = [r[1] for r in rows] + [a for r in rows for a in r[4]]
    assert len(isins) == len(set(isins))
    for t, isin, issuer, holdings, _ in rows:
        fh.make_source(t, isin, issuer, holdings)  # every row makes a source


def test_fetch_tries_the_alternate_link(tmp_path, monkeypatch, capsys):
    tried = []

    def fake(source, timeout=60):
        tried.append(source.url)
        if "ajax" in source.url:
            raise fh.Refused("www.ishares.com returned 404")
        return ishares_bytes()
    monkeypatch.setattr(fh, "fetch", fake)
    url, alts = fh.ishares_urls("264659", "EIMI")
    monkeypatch.setattr(fh, "SOURCES", {"IE00BKM4GZ66": fh.Source(
        "EIMI", "IE00BKM4GZ66", "ishares", url, "csv", alts=alts)})
    assert fh.cmd_fetch(tmp_path, date(2026, 10, 9)) == 0
    assert len(tried) == 2 and tried[1].endswith("latest-holdings.csv")
    assert "EIMI: " in capsys.readouterr().out and (tmp_path / "EIMI-2026-10-09.csv").exists()


def test_fetch_names_the_host_when_refused(tmp_path, monkeypatch, capsys):
    def refuse(source, timeout=60):
        raise fh.Refused(f"{source.ticker.lower()}.example returned 403")
    monkeypatch.setattr(fh, "fetch", refuse)
    assert fh.cmd_fetch(tmp_path, date(2026, 10, 9)) == 1
    out = capsys.readouterr().out
    assert "SPPW: Not available - sppw.example returned 403" in out
    assert not list(tmp_path.iterdir())


def test_fetch_keeps_the_raw_bytes(tmp_path, monkeypatch, capsys):
    raw = {"SPPW": ssga_bytes(), "EIMI": ishares_bytes(), "VUSA": vanguard_bytes(),
           "MEUD": amundi_bytes()}
    monkeypatch.setattr(fh, "fetch", lambda source, timeout=60: raw[source.ticker])
    assert fh.cmd_fetch(tmp_path, date(2026, 10, 9)) == 0
    assert (tmp_path / "SPPW-2026-10-09.xlsx").read_bytes() == raw["SPPW"]
    assert "VUSA: " in capsys.readouterr().out


def test_name_key_keeps_holding_companies_apart():
    # Two companies each, seen in EIMI's live file on 2026-10-10
    assert fh.name_key("PSK INC") != fh.name_key("PSK HOLDINGS INC")
    assert fh.name_key("YOUNGONE") != fh.name_key("YOUNGONE HOLDINGS LTD")
    # ...while one company's share classes still fold
    assert fh.name_key("ITAU UNIBANCO HOLDING PREF SA") == fh.name_key("ITAU UNIBANCO HOLDING SA")


# --- countries ----------------------------------------------------------------

@pytest.mark.parametrize("raw, name", [
    ("Korea (South)", "South Korea"), ("UAE", "United Arab Emirates"), ("US", "United States"),
    ("XE", ""), ("European Union", ""), (None, ""), ("-", ""), ("Taiwan", "Taiwan"),
])
def test_canonical_country(raw, name):
    assert fh.canonical_country(raw) == name


def test_each_parser_reads_a_country(holdings_dir):
    funds = load_all(holdings_dir)
    assert {r.country for r in funds["SPPW"].rows if r.equity} == {"United States"}
    assert {r.country for r in funds["VUSA"].rows if r.equity} == {"United States"}
    by = {r.name: r.country for r in funds["EIMI"].rows}
    assert by["NATIONAL BANK OF GREECE"] == "Greece"
    assert fh.fund_countries(funds["MEUD"])["Poland"] == Decimal("0.400")


def test_fund_countries_put_non_equity_rows_in_cash(holdings_dir):
    split = fh.fund_countries(load_all(holdings_dir)["EIMI"])
    assert split["Taiwan"] == Decimal("14.00") + 20 * Decimal("4.285")
    assert split[fh.CASH] == Decimal("0.00")  # the FX row


def test_countries_table_re_adds(holdings_dir):
    funds = load_all(holdings_dir)
    order = ["SPPW", "MEUD", "EIMI", "VUSA"]
    direct = {"United States": Decimal("26.00")}
    lines, stats = fh.countries_table(order, funds, FUND_W, direct, Decimal("0.50"))
    assert lines[0] == "| Country | Direct | via SPPW | via MEUD | via EIMI | via VUSA | Total |"
    rows = {line.split("|")[1].strip(): line for line in lines[2:]}
    # 26 direct + 40 + 8 (both US funds, all US)
    assert rows["United States"] == "| United States | 26.00 | 40.00 | - | - | 8.00 | 74.00 |"
    # MEUD 15: 5% Netherlands (ASML) = 0.75
    assert rows["Netherlands"].endswith("| 0.75 | - | - | 0.75 |")
    # Poland (MEUD 0.40%, EIMI 0.19%) and Greece fold into Other: under 0.50 each
    assert "Poland" not in rows and "Other countries (2)" in rows
    assert rows["Other countries (2)"] == "| Other countries (2) | - | - | 0.11 | 0.03 | - | 0.14 |"
    # 26 + 40 + 15 + 11 + 8 = 100; MEUD's column is 15.01 because each cell is
    # rounded to the cent on its own (Netherlands 0.75, UK 14.145 -> 14.15, Other 0.11)
    assert rows["Total"] == "| Total | 26.00 | 40.00 | 15.01 | 11.00 | 8.00 | 100.01 |"
    result = "Countries (market weights, as of 2026-10-09)\n" + "\n".join(lines) + "\n"
    assert contract.countries_problems({"RESULT": result}) == []


def test_countries_contract_catches_a_wrong_total():
    result = ("Countries (market weights, as of 2026-10-09)\n"
              "| Country | Direct | via SPPW | Total |\n|---|---|---|---|\n"
              "| United States | 26.00 | 40.00 | 66.10 |\n"
              "| Total | 26.00 | 40.00 | 66.00 |\n")
    problems = contract.countries_problems({"RESULT": result})
    assert any("United States" in p and "66.10" in p for p in problems)
    assert any("Total row" in p for p in problems)


# --- sectors and currencies ---------------------------------------------------

@pytest.mark.parametrize("raw, name", [
    ("Communication", "Communication Services"), ("Information Technology", "Information Technology"),
    ("Unassigned", ""), ("Cash and/or Derivatives", ""), ("", ""), (None, ""),
])
def test_canonical_sector(raw, name):
    assert fh.canonical_sector(raw) == name


@pytest.mark.parametrize("raw, code", [
    ("usd", "USD"), ("GBX", "GBP"), ("GBp", "GBP"), ("CNH", "CNH"), ("-", ""), ("", ""), (None, ""),
])
def test_canonical_currency(raw, code):
    assert fh.canonical_currency(raw) == code


@pytest.mark.parametrize("bbg, code", [
    ("ASML NA", "EUR"), ("HSBA LN", "GBP"), ("ROP SE", "CHF"), ("PKO PW", "PLN"),
    ("XYZ ZZ", ""), ("SXOZ6", ""), ("", ""), (None, ""),
])
def test_exchange_currency(bbg, code):
    assert fh.exchange_currency(bbg) == code


def test_parsers_read_sector_and_currency(holdings_dir):
    funds = load_all(holdings_dir)
    assert {(r.sector, r.currency) for r in funds["SPPW"].rows if r.equity} == {("IT", "USD")}
    assert {(r.sector, r.currency) for r in funds["EIMI"].rows if r.equity} == {("IT", "USD")}
    meud = {r.bbg: (r.currency, r.currency_from) for r in funds["MEUD"].rows if r.equity}
    assert meud["ASML NA"] == ("EUR", "exchange") and meud["PKO PW"] == ("PLN", "exchange")
    assert {r.sector for r in funds["VUSA"].rows} == {""}  # Vanguard's file has none
    assert {r.local for r in funds["EIMI"].rows if r.name.startswith("NATIONAL")} == {
        "ETE @ Athens Exchange S.A. Cash Market"}


def test_fund_split_borrows_from_peers_and_says_how_much(holdings_dir):
    funds = load_all(holdings_dir)
    by_bbg = fh.bbg_keys(list(funds.values()))
    sectors = fh.peer_values(funds, "sector")
    split, basis = fh.fund_split(funds["VUSA"], "sector", sectors, by_bbg, fh.NO_SECTOR)
    # NVIDIA 8 + Apple 7 + Alphabet A 2 + C 1.7 are in SPPW's file; the fillers are not
    assert split["IT"] == Decimal("18.7") and basis["borrowed"] == Decimal("18.7")
    assert split[fh.NO_SECTOR] == 20 * Decimal("4.065") == basis["none"]
    assert split[fh.CASH] == Decimal("0.0")  # the futures row


def test_amundi_sector_and_currency_fields_win_over_the_exchange_code(tmp_path):
    payload = json.loads(amundi_bytes())
    rows = payload["products"][0]["composition"]["compositionData"]
    rows[0]["compositionCharacteristics"].update(sector="Information Technology", currency="EUR")
    # a London line that trades in dollars: the file says USD, the code would say GBP
    rows[3]["compositionCharacteristics"].update(sector="Energy", currency="USD")
    path = tmp_path / "MEUD-2026-10-09.json"
    path.write_text(json.dumps(payload))
    by = {r.bbg: r for r in fh.load_fund(MEUD, path).rows if r.equity}
    assert (by["ASML NA"].sector, by["ASML NA"].currency, by["ASML NA"].currency_from) == (
        "Information Technology", "EUR", "file")
    assert (by["F0 LN"].currency, by["F0 LN"].currency_from) == ("USD", "file")
    assert (by["F1 LN"].currency, by["F1 LN"].currency_from) == ("GBP", "exchange")
    assert by["F1 LN"].sector == ""
    assert "sector" in MEUD.body["composition"]["compositionFields"]
    assert "currency" in MEUD.body["composition"]["compositionFields"]


def test_meud_currency_comes_from_its_own_exchange_codes(holdings_dir):
    funds = load_all(holdings_dir)
    by_bbg = fh.bbg_keys(list(funds.values()))
    split, basis = fh.fund_split(funds["MEUD"], "currency", fh.peer_values(funds, "currency"),
                                 by_bbg, fh.NO_CURRENCY)
    assert split["EUR"] == Decimal("5.000") + Decimal("0.300")  # ASML NA, ETE GA
    assert split["PLN"] == Decimal("0.400")
    assert split["GBP"] == 20 * Decimal("4.71500")
    assert basis["exchange"] == sum((v for k, v in split.items() if k != fh.CASH), Decimal(0))


def test_report_prints_sectors_and_currencies_that_re_add(holdings_dir, capsys, monkeypatch):
    weights = {SPPW.isin: Decimal("40.00"), MEUD.isin: Decimal("15.00"),
               EIMI.isin: Decimal("11.00"), VUSA.isin: Decimal("8.00"),
               AAPL: Decimal("13.00"), NVDA: Decimal("8.00"), GOOGL: Decimal("5.00")}
    tickers = {SPPW.isin: "SPPW", MEUD.isin: "MEUD", EIMI.isin: "EIMI", VUSA.isin: "VUSA",
               AAPL: "AAPL", NVDA: "NVDA", GOOGL: "GOOGL"}
    pies = {i: ("Stock" if i in (AAPL, NVDA, GOOGL) else "ETF") for i in weights}
    monkeypatch.setattr(fh, "market_weights",
                        lambda *a: (weights, tickers, pies, date(2026, 10, 9)))
    assert fh.cmd_report(report_args(holdings_dir, prices=Path("p.json"), top=3)) == 0
    out = capsys.readouterr().out
    assert "Sectors (market weights, as of 2026-10-09)" in out
    assert "| Sector | Direct | via SPPW | via MEUD | via EIMI | via VUSA | Total |" in out
    assert "Currencies (market weights, as of 2026-10-09)" in out
    # 26 direct + 40 SPPW + EIMI's 11 (all USD in the fixture) + VUSA's borrowed 8 x 18.7%
    assert "| USD | 26.00 | 40.00 | - | 11.00 | 1.50 | 78.50 |" in out
    assert "Sectors direct stocks: AAPL IT (from SPPW)" in out
    assert "Currencies sources (% of each fund's equity): SPPW file 100.00; MEUD exchange" in out
    result = out.split("METHOD")[0]
    for name in ("Sectors", "Currencies"):
        assert contract.bucket_problems({"RESULT": result}, name) == []


# --- history: snapshots and changes ------------------------------------------

def test_snapshot_writes_weekly_and_skips_within_the_week(holdings_dir, tmp_path, capsys):
    hist = tmp_path / "history"
    assert fh.cmd_snapshot(holdings_dir, hist) == 0
    out = capsys.readouterr().out
    assert "SPPW: wrote" in out and (hist / "SPPW" / "2026-10-08.csv").exists()
    assert (hist / "VUSA" / "2026-08-31.csv").exists()  # the file's own as-of, not the fetch date
    fh.cmd_snapshot(holdings_dir, hist)
    assert "SPPW: skipped - newest snapshot 2026-10-08, file as of 2026-10-08" in capsys.readouterr().out


def test_snapshot_round_trips_and_sums_share_classes(holdings_dir, tmp_path):
    fund = load_all(holdings_dir)["SPPW"]
    snap = fh.take_snapshot(fund)
    alphabet = fh.company_key(GOOGL)
    assert snap.weight(alphabet) == Decimal("2.8")  # A 1.5 + C 1.3
    assert fh.CASH_KEY not in snap.rows  # SSGA's dollar row is 0
    path = tmp_path / "SPPW" / "2026-10-08.csv"
    fh.write_snapshot(snap, path, fund.path)
    back = fh.read_snapshot(path)
    assert back.as_of == date(2026, 10, 8) and back.ticker == "SPPW"
    assert back.rows == snap.rows


def test_eimi_snapshot_keys_do_not_depend_on_another_funds_file(holdings_dir):
    keys = fh.take_snapshot(load_all(holdings_dir)["EIMI"]).names
    assert "tkr:PKO @ Warsaw Stock Exchange/Equities/Main Market" in keys
    assert not any(k.startswith(("isin:", "cusip:", "bbg:")) for k in keys)


def _older(snap: fh.Snapshot, days: int, **edits) -> fh.Snapshot:
    rows = {k: dict(v) for k, v in snap.rows.items()}
    for key, weight in edits.items():
        if weight is None:
            rows.pop(key)
        else:
            rows.setdefault(key, {"name": key, "country": "", "sector": "", "currency": ""})
            rows[key]["weight"] = f"{Decimal(weight):.6f}"
    from datetime import timedelta
    return fh.Snapshot(snap.ticker, snap.as_of - timedelta(days=days), rows)


def test_changes_lists_added_dropped_and_moves_and_re_adds(holdings_dir, tmp_path):
    funds = load_all(holdings_dir)
    now = fh.take_snapshot(funds["SPPW"])
    nvda, asml = fh.company_key(NVDA), fh.company_key(ASML)
    week_ago = _older(now, 7, **{nvda: "4.75", asml: None, "isin:XX0000000001": "0.30"})
    hist = tmp_path / "history"
    fh.write_snapshot(week_ago, hist / "SPPW" / f"{week_ago.as_of}.csv", funds["SPPW"].path)
    lines, proof = fh.changes_table(["SPPW"], {"SPPW": funds["SPPW"]}, {}, hist)
    assert lines[2] == ("| SPPW | 2026-10-01 to 2026-10-08 | 24 to 24 | 1 (ASML Holding NV 0.50) | "
                        "1 (isin:XX0000000001 0.30) | NVIDIA Corporation +0.25 |")
    pr = proof["SPPW"]
    assert pr["now_eq"] - pr["base_eq"] == pr["moves"] + pr["added"] - pr["dropped"]


def test_changes_needs_a_snapshot_seven_days_older(holdings_dir, tmp_path):
    funds = load_all(holdings_dir)
    now = fh.take_snapshot(funds["SPPW"])
    hist = tmp_path / "history"
    six = _older(now, 6)
    fh.write_snapshot(six, hist / "SPPW" / f"{six.as_of}.csv", funds["SPPW"].path)
    lines, proof = fh.changes_table(["SPPW", "MEUD"], {"SPPW": funds["SPPW"]},
                                    {"MEUD": "MEUD-x.json: refused"}, hist)
    assert lines[2] == ("| SPPW | Not available - no snapshot 7+ days before 2026-10-08; "
                        "history starts 2026-10-02 | - | - | - | - |")
    assert lines[3] == "| MEUD | Not available - MEUD-x.json: refused | - | - | - | - |"
    assert proof == {}


def test_changes_with_nothing_changed_says_so(holdings_dir, tmp_path):
    funds = load_all(holdings_dir)
    same = _older(fh.take_snapshot(funds["SPPW"]), 14)
    hist = tmp_path / "history"
    fh.write_snapshot(same, hist / "SPPW" / f"{same.as_of}.csv", funds["SPPW"].path)
    lines, _ = fh.changes_table(["SPPW"], {"SPPW": funds["SPPW"]}, {}, hist)
    assert lines[2] == "| SPPW | 2026-09-24 to 2026-10-08 | 24 to 24 | 0 | 0 | none |"


def test_changes_command_prints_method_and_proof(holdings_dir, tmp_path, capsys):
    hist = tmp_path / "history"
    funds = load_all(holdings_dir)
    old = _older(fh.take_snapshot(funds["SPPW"]), 7, **{fh.company_key(NVDA): "4.00"})
    fh.write_snapshot(old, hist / "SPPW" / f"{old.as_of}.csv", funds["SPPW"].path)
    assert fh.cmd_changes(holdings_dir, hist) == 0
    out = capsys.readouterr().out
    assert out.startswith("Holdings changes (each fund's latest file against its snapshot 7+ days older)")
    assert "Holdings changes basis:" in out and "not attributed to either" in out
    assert "SPPW: equity" in out and out.rstrip().endswith("PASS")


# --- the funds file (me/funds.md) --------------------------------------------

FUNDS_MD = """# Funds

| Issuer | Holdings file |
|---|---|
| `ssga` | not this table |

## Funds

| Ticker | ISIN | Issuer | Holdings file |
|---|---|---|---|
| SWRD | IE00BFY0GT14 | ssga | https://www.ssga.com/x/holdings-daily-emea-en-swrd-ln.xlsx |
| MEUD | LU0908500753 | amundi | |
| VUAA | IE00BFMXXD54 | vanguard | 9679 |
"""


def test_load_funds_reads_only_the_funds_table(tmp_path):
    path = tmp_path / "funds.md"
    path.write_text(FUNDS_MD)
    funds = fh.load_funds(path)
    assert [s.ticker for s in funds.values()] == ["SWRD", "MEUD", "VUAA"]
    assert funds["IE00BFY0GT14"].url.endswith("swrd-ln.xlsx")
    assert funds["LU0908500753"].body["productIds"] == ["LU0908500753"]
    assert funds["IE00BFMXXD54"].body["variables"]["portIds"] == ["9679"]


@pytest.mark.parametrize("row, message", [
    ("| X | IE00BFY0GT14 | ssga | not-a-link |", "needs the holdings file's https:// link"),
    ("| X | IE00BFMXXD54 | vanguard | abc |", "port ID"),
    ("| X | IE00BFMXXD54 | xtrackers | 1 |", "is not one of"),
    ("| X | NOTANISIN | amundi | |", "valid ISIN"),
])
def test_load_funds_refuses_a_row_it_cannot_fetch(tmp_path, row, message):
    path = tmp_path / "funds.md"
    path.write_text("## Funds\n\n| Ticker | ISIN | Issuer | Holdings file |\n|---|---|---|---|\n" + row + "\n")
    with pytest.raises(fh.Refused, match=message):
        fh.load_funds(path)


def test_use_funds_swaps_the_set(tmp_path):
    path = tmp_path / "funds.md"
    path.write_text(FUNDS_MD)
    try:
        assert fh.use_funds(path).endswith("3 funds")
        assert set(fh.ISIN_OF) == {"SWRD", "MEUD", "VUAA"}
        assert fh.name_order() == ["VUAA", "SWRD", "MEUD"]  # Vanguard's issuer names first
        assert fh.peers() == ["SWRD", "MEUD"]  # no iShares fund in this set
    finally:
        assert fh.use_funds(None) == "built-in catalog, 4 funds"
    assert set(fh.ISIN_OF) == {"SPPW", "MEUD", "EIMI", "VUSA"}


def test_a_missing_or_empty_funds_file_is_no_funds_not_the_catalog(tmp_path):
    empty = tmp_path / "funds.md"
    empty.write_text((REPO / "templates" / "me" / "funds.md").read_text())
    try:
        note = fh.use_funds(tmp_path / "missing.md")
        assert fh.SOURCES == {} and "set up Holdnote" in note
        assert fh.use_funds(empty).endswith("lists no fund") and fh.SOURCES == {}
    finally:
        fh.use_funds(None)


def test_one_fund_reads_as_one_fund(tmp_path):
    path = tmp_path / "funds.md"
    path.write_text("## Funds\n\n| Ticker | ISIN | Issuer | Holdings file |\n|---|---|---|---|\n"
                    "| MEUD | LU0908500753 | amundi | |\n")
    try:
        assert fh.use_funds(path).endswith(", 1 fund")
    finally:
        fh.use_funds(None)


def test_holdings_table_with_one_fund_says_so(holdings_dir):
    funds = load_all(holdings_dir)
    exps = fh.exposures([funds["MEUD"]])
    lines = fh.holdings_table(["MEUD"], {"MEUD": funds["MEUD"]}, {}, exps, ["MEUD"])
    assert lines[2] == "| MEUD alone | none - overlap needs two funds | 0 |"
    result = "Holdings (full issuer files)\n" + "\n".join(lines) + "\n"
    assert contract.holdings_problems({"RESULT": result}) == []


@pytest.mark.parametrize("cmd", ["report", "fetch", "snapshot", "changes"])
def test_stocks_only_user_gets_none_not_an_error(tmp_path, capsys, cmd):
    funds = tmp_path / "funds.md"
    funds.write_text((REPO / "templates" / "me" / "funds.md").read_text())
    try:
        argv = [cmd, "--funds", str(funds)]
        if cmd in ("report", "fetch", "snapshot", "changes"):
            argv += ["--holdings-dir", str(tmp_path / "h")]
        if cmd in ("snapshot", "changes"):
            argv += ["--history-dir", str(tmp_path / "hh")]
        assert fh.main(argv) == 0
        out = capsys.readouterr().out
        assert "lists no fund" in out and "Not available" not in out
        assert not (tmp_path / "h").exists()  # nothing fetched or written
    finally:
        fh.use_funds(None)


def test_method_names_only_the_users_own_funds(holdings_dir):
    order = ["MEUD", "VUSA"]
    lines = [fh.countries_basis(order), fh.sectors_basis(order), fh.currencies_basis(order)]
    text = "\n".join(lines)
    assert "SPPW" not in text and "EIMI" not in text and "SSGA" not in text and "iShares" not in text
    assert "Amundi (MEUD)" in text and "Vanguard (VUSA)" in text
    full = fh.countries_basis(["SPPW", "MEUD", "EIMI", "VUSA"])
    assert "SSGA (SPPW) the country a security trades in" in full


def test_the_users_funds_file_parses():
    path = REPO / "me" / "funds.md"
    if path.is_file():
        assert {s.ticker for s in fh.load_funds(path).values()} == {"SPPW", "MEUD", "EIMI", "VUSA"}
    assert fh.load_funds(REPO / "templates" / "me" / "funds.md") == {}


def test_vanguard_pages_are_joined(monkeypatch):
    def item(n):
        return {"issuerName": f"Co {n}", "securityLongDescription": f"Co {n}",
                "marketValuePercentage": 0.5, "isin": "US0378331005", "ticker": "X",
                "securityType": "EQ.STOCK", "effectiveDate": "2026-09-30",
                "bloombergIsoCountry": "US"}
    pages = {None: ([item(i) for i in range(150)], "k1"), "k1": ([item(i) for i in range(50)], None)}
    seen = []

    def once(source, timeout=60):
        key = source.body["variables"]["lastItemKey"]
        seen.append(key)
        items, nxt = pages[key]
        return json.dumps({"data": {"borHoldings": [{"holdings": {
            "items": items, "totalHoldings": 200, "lastItemKey": nxt}}]}}).encode()
    monkeypatch.setattr(fh, "fetch_once", once)
    src = fh.make_source("VWCE", "IE00BK5BQT80", "vanguard", "9679")
    data = fh.fetch(src)
    assert seen == [None, "k1"]
    as_of, rows = fh.parse_vanguard(data, src)
    assert len(rows) == 200 and as_of == date(2026, 9, 30)
    assert src.body["variables"]["lastItemKey"] is None  # the catalogue's source is untouched
