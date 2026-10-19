"""Look-through without GitHub: each fund's factsheet top 10.

A user on the web or a phone has no copy of the issuers' full holdings files.
The run copies each fund's factsheet top 10 into a small CSV, and the report
looks through at that depth: labelled partial, weights as floors, and no
Countries, Sectors or Currencies, which need every company. The companies
and weights below are made up; no issuer's data is kept in this repo.
"""

from __future__ import annotations

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import card  # noqa: E402
import contract  # noqa: E402
import fund_holdings as fh  # noqa: E402

VWCE, EIMI, APPLE = "IE00BK5BQT80", "IE00BKM4GZ66", "US0378331005"
URL = "https://example.com/factsheet.pdf"

HOLDINGS = f"""# as_of: 2026-10-19
# source: export.csv (positions)
isin,ticker,name,kind,quantity,group,target_pct,value,value_ccy
{VWCE},VWCE,VANGUARD FTSE AW,fund,34,Portfolio,,6500,EUR
{EIMI},EIMI,ISHARES CORE MSCI EM IMI,fund,40,Portfolio,,2000,EUR
{APPLE},,APPLE INC. - COMMON ST,stock,5,Portfolio,,1500,EUR
"""

SHEETS = f"""fund,isin,as_of,source,company,weight
VWCE,{VWCE},2026-09-30,{URL},Example Chips Corp.,5.0
VWCE,{VWCE},2026-09-30,{URL},Apple Inc.,4.0
VWCE,{VWCE},2026-09-30,{URL},Sample Software Inc,3.0
EIMI,{EIMI},2026-09-30,{URL},EXAMPLE CHIPS CORP,10.0
EIMI,{EIMI},2026-09-30,{URL},Demo Bank Ltd Class A,2.0
EIMI,{EIMI},2026-09-30,{URL},Demo Bank Ltd Class B,1.0
"""


@pytest.fixture(autouse=True)
def keep_sources(monkeypatch):
    # main() points the module at this test's (empty) funds list; put it back.
    monkeypatch.setattr(fh, "SOURCES", dict(fh.SOURCES))
    monkeypatch.setattr(fh, "ISIN_OF", dict(fh.ISIN_OF))


def report(tmp_path: Path, sheets: str = SHEETS, holdings: str = HOLDINGS) -> tuple[int, str]:
    (tmp_path / "holdings.csv").write_text(holdings, encoding="utf-8")
    (tmp_path / "factsheets.csv").write_text(sheets, encoding="utf-8")
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = fh.main(["report", "--funds", str(tmp_path / "no-funds.md"),
                        "--holdings", str(tmp_path / "holdings.csv"),
                        "--holdings-dir", str(tmp_path / "none"),
                        "--factsheets", str(tmp_path / "factsheets.csv")])
    return code, buf.getvalue()


def rows(out: str, title: str) -> dict[str, list[str]]:
    block = out.split(f"\n{title}", 1)[1].split("\n\n", 1)[0]
    return {r.strip("|").split("|")[0].strip(): [c.strip() for c in r.strip("|").split("|")[1:]]
            for r in block.splitlines() if r.startswith("|") and not r.startswith("|---")}


def test_funds_with_no_file_are_looked_through_at_top_10_depth(tmp_path):
    code, out = report(tmp_path)
    assert code == 0, out
    assert "top-10 depth, partial for VWCE, EIMI" in out
    lt = rows(out, "Look-through")
    # Weights 65 / 20 / 15 from the export's values
    assert lt["Apple Inc."] == ["15.00", "2.60", "-", "17.60"]           # the direct stock joined by name
    assert lt["Example Chips Corp."] == ["-", "3.25", "2.00", "5.25"]   # two spellings, one company
    assert lt["Demo Bank Ltd"] == ["-", "-", "0.60", "0.60"]            # share classes combined
    bets = rows(out, "Hidden bets")
    assert set(bets) >= {"Apple Inc.", "Example Chips Corp."}
    assert "Holdings VWCE: factsheet top 3, https://example.com/factsheet.pdf, as of 2026-09-30" in out
    assert "they sum to 12.00% of the fund" in out


def test_countries_and_sectors_need_a_full_file(tmp_path):
    _code, out = report(tmp_path)
    for title in ("Countries", "Sectors", "Currencies"):
        assert "Not available - no fund's full holdings file read" in out.split(f"\n{title}", 1)[1]


def test_a_factsheet_that_fails_a_check_is_not_used(tmp_path):
    bad = SHEETS.replace("Sample Software Inc,3.0", "Sample Software Inc,300")
    code, out = report(tmp_path, bad)
    assert "Factsheet IE00BK5BQT80: not used - row Sample Software Inc 300" in out
    assert "top-10 depth, partial for EIMI" in out
    assert "not looked through: VWCE" in out


def test_a_factsheet_for_a_fund_not_held_is_left_out(tmp_path):
    held = "\n".join(ln for ln in HOLDINGS.splitlines() if EIMI not in ln) + "\n"
    _code, out = report(tmp_path, holdings=held)
    assert "Factsheet IE00BKM4GZ66: not used - not in the holdings" in out
    assert "via EIMI" not in out


def test_the_factsheet_file_needs_its_header(tmp_path):
    code, out = report(tmp_path, "ticker,weight\nVWCE,1\n")
    assert "Factsheets: Not available" in out and "header must be" in out


def test_match_key_reads_one_company_however_it_is_spelled():
    assert fh.match_key("APPLE INC. - COMMON ST") == fh.match_key("Apple Inc.") == "APPLE"
    assert (fh.match_key("TAIWAN SEMICONDUCTOR MANUFACTURING")
            == fh.match_key("Taiwan Semiconductor Manufacturing Co. Ltd."))
    assert fh.match_key("SAMSUNG ELECTRONICS NON VOTING PRE") == fh.match_key("SAMSUNG ELECTRONICS LTD")


def draft(out: str) -> str:
    result, method = out.split("\nMETHOD\n", 1)
    method = method.split("\nPROOF\n", 1)[0]
    return f"""STATUS: Complete.

CONTEXT
Data as of:       2026-10-19 · the export's own values
Latest period:    factsheets as of 2026-09-30
Currency / units: EUR · weights as % of the portfolio
Not available:    countries and sectors (factsheet top 10s only)
Coverage:         3 of 3 holdings · 2 funds at factsheet top-10 depth

RESULT
Mode: Any broker + Portfolio (Mode C)

{result.strip()}

METHOD
Build: test
Tables: Allocation, Holdings, Look-through, Hidden bets, Countries, Sectors
{method.strip()}

SOURCES
| URL or path | Document | Published | Retrieved (UTC) |
|---|---|---|---|
| {URL} | Example factsheet | 2026-09-30 | 2026-10-19 17:30 UTC |
"""


def test_a_top_10_card_says_so_and_skips_what_it_cannot_show(tmp_path):
    _code, out = report(tmp_path)
    text = draft(out)
    assert contract.output_problems(text) == []
    c = card.read(text)
    assert c.partial and c.partial_label == "PARTIAL · TOP-10 DEPTH"
    assert c.countries == [] and c.sectors == [] and c.companies is None
    assert c.hero[0] == "Apple Inc."
    svg = card.svg(card.layout(c, card.Fonts()))
    assert "factsheet top 10 only" in svg
    assert "shared weight" not in svg  # two funds share more than their top 10s show
