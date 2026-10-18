"""The demo: references/demo.md, scripts/demo.py, RULES.md v13.

Runs on the committed snapshot in demo/data/, so it also guards each monthly
refresh: .github/workflows/demo-data.yml runs this file before committing a
new snapshot. The portfolio is synthetic; the snapshot's figures are public
data with their sources, read here only to check their shape.
"""

from __future__ import annotations

import csv
import io
import json
import re
import subprocess
import sys
import zipfile
from decimal import Decimal
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO / "scripts"))

import contract  # noqa: E402
import demo  # noqa: E402
import fund_holdings as fh  # noqa: E402

DATA = REPO / "demo" / "data"


def holdings_rows() -> tuple[str, list[dict]]:
    text = (REPO / "demo" / "holdings.csv").read_text()
    as_of = re.search(r"^# as_of: (\S+)$", text, re.MULTILINE).group(1)
    body = [ln for ln in text.splitlines() if ln and not ln.startswith("#")]
    return as_of, list(csv.DictReader(body))


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    folder = tmp_path_factory.mktemp("demo")

    def _run(*args: str) -> tuple[int, str, str]:
        draft = folder / f"draft-{len(list(folder.iterdir()))}.md"
        out = subprocess.run([sys.executable, str(REPO / "scripts" / "demo.py"),
                              "--draft", str(draft), *args],
                             capture_output=True, text=True, cwd=folder)
        return out.returncode, out.stdout, draft.read_text() if draft.exists() else ""
    return _run


# --- the snapshot -------------------------------------------------------------

def test_portfolio_is_synthetic_and_targets_sum_to_100():
    _, rows = holdings_rows()
    assert sum(Decimal(r["target_pct"]) for r in rows) == 100
    assert "synthetic" in (REPO / "demo" / "holdings.csv").read_text().splitlines()[1]


def test_snapshot_is_one_session_date_throughout():
    as_of, rows = holdings_rows()
    prices = json.loads((DATA / "prices.json").read_text())
    assert prices["as_of"] == as_of, "demo/holdings.csv as_of must move with the snapshot"
    assert {r["isin"] for r in rows} == set(prices["prices"])
    assert {p["date"] for p in prices["prices"].values()} == {as_of}
    assert {f["date"] for f in prices["fx"].values()} == {as_of}


def test_fund_report_covers_every_fund_from_its_full_file():
    funds = fh.load_funds(REPO / "demo" / "funds.md")  # not use_funds: no global state
    meta = json.loads((DATA / "funds.json").read_text())["funds"]
    report = (DATA / "fund_report.txt").read_text()
    assert set(meta) == {s.ticker for s in funds.values()}
    for ticker, m in meta.items():
        assert m["equity_rows"] >= 100, f"{ticker}: not a full holdings file"
        assert f"Holdings file {ticker}: SSGA daily holdings file (read by the snapshot job, not kept)" in report
    for table in ("Holdings", "Look-through", "Countries", "Sectors", "Currencies"):
        assert re.search(rf"^{table} \(", report, re.MULTILINE), f"no {table} table in the fund report"


def test_no_issuer_holdings_file_is_shipped_or_tracked():
    # SSGA's files may not be reproduced or passed on (DECISIONS.md, 2026-10-15).
    tracked = subprocess.run(["git", "ls-files", "demo"], cwd=REPO, capture_output=True,
                             text=True, check=True).stdout.split()
    assert not [t for t in tracked if t.endswith((".xlsx", ".xls")) or "/holdings/" in t]
    assert not list(DATA.rglob("*.xlsx"))


def test_fund_report_was_computed_from_the_shipped_portfolio_and_prices():
    import hashlib
    inputs = json.loads((DATA / "funds.json").read_text())["inputs"]
    for path, digest in inputs.items():
        assert hashlib.sha256((REPO / path).read_bytes()).hexdigest() == digest, (
            f"{path} changed after the fund report was computed: run the Demo data workflow")


def test_every_close_names_its_source_and_any_second_source():
    for p in json.loads((DATA / "prices.json").read_text())["prices"].values():
        assert p["source"]
        if p.get("confirmed_by"):
            assert abs(Decimal(p["confirmed_by"]["diff_pct"])) <= Decimal("0.10")
        else:
            assert p.get("unconfirmed"), "a single-source close says why"


def test_every_source_has_a_url_and_both_dates():
    for s in json.loads((DATA / "sources.json").read_text()):
        assert s["url"].startswith("https://")
        assert s["published"] and re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC$", s["retrieved"])


def test_stocks_have_edgar_filings():
    _, rows = holdings_rows()
    stocks = json.loads((DATA / "stocks.json").read_text())
    for r in rows:
        if r["kind"] == "stock":
            s = stocks[r["isin"]]
            assert s["cik"] and any(f["form"] in ("10-K", "10-Q") for f in s["filings"])


# --- the report ---------------------------------------------------------------

def test_demo_prints_a_report_that_passes_the_contract(run):
    code, out, draft = run()
    assert code == 0, out
    assert contract.output_problems(draft) == []
    assert out.startswith("## Demo portfolio\n")
    assert "demo snapshot, frozen — not today's prices" in out
    for table in demo.DEFAULT:
        assert f" {table}\n" in out
    assert "Currencies" not in out
    assert "Not financial advice." in out
    assert 'say "set up Holdnote"' in out


def test_mode_line_and_data_as_of_are_the_snapshots(run):
    _, _, draft = run()
    sections = contract.split_sections(draft)
    assert "Mode: Demo + Portfolio (Mode C)" in sections["RESULT"]
    as_of, _ = holdings_rows()
    assert contract._data_as_of(sections).isoformat() == as_of
    assert re.search(r"^Demo: .*nothing was fetched in this run", sections["METHOD"], re.MULTILINE)


def test_lookthrough_counts_a_stock_held_directly_and_through_funds(run):
    _, _, draft = run()
    tables = contract.result_tables(contract.split_sections(draft)["RESULT"])
    rows = next(v for k, v in tables.items() if k.startswith("Look-through"))
    amazon = next(r for r in rows if r[0].startswith("Amazon"))
    direct, *via, total = amazon[1:]
    assert direct != "-" and all(v != "-" for v in via)
    assert Decimal(total) > Decimal(direct)


def test_draft_keeps_full_sources_and_proof_while_report_shows_one_line(run):
    _, out, draft = run()
    sections = contract.split_sections(draft)
    assert "PROOF" in sections
    n = len(json.loads((DATA / "sources.json").read_text())) + 2
    assert len([ln for ln in sections["SOURCES"].splitlines() if ln.startswith("| ")]) == n + 1
    assert re.search(rf"\b{n} documents · published ", out)


def test_tables_can_be_picked_and_proof_shown(run):
    code, out, draft = run("--tables", "Holdings", "--proof")
    assert code == 0, out
    assert "### 🔗 Holdings" in out and "Allocation" not in out.split("---")[0].split("Holdings", 1)[0]
    assert "Tables: Holdings (demo, asked: Holdings)" in draft


def test_all_tables(run):
    code, out, _ = run("--tables", "all")
    assert code == 0, out
    assert "### 💱 Currencies" in out


def test_a_report_for_another_portfolio_is_refused(run, tmp_path, monkeypatch):
    holdings = REPO / "demo" / "holdings.csv"
    original = holdings.read_text()
    try:
        holdings.write_text(original.replace(",8,Portfolio,7", ",9,Portfolio,7"))
        code, out, _ = run()
    finally:
        holdings.write_text(original)
    assert code == 1 and "computed from a different demo/holdings.csv" in out


def test_unknown_table_is_refused(run):
    code, out, _ = run("--tables", "Performance")
    assert code == 2 and "not a demo table: Performance" in out


def test_single_source_closes_are_said_on_the_confirmation_line(run):
    prices = json.loads((DATA / "prices.json").read_text())["prices"]
    single = [p for p in prices.values() if not p.get("confirmed_by")]
    _, out, draft = run()
    line = re.search(r"^Confirmation: (.*)$", draft, re.MULTILINE).group(1)
    if single:
        assert "rest on one source" in line and "⚠️" in out
        assert f"· {len(single)} unverified ·" in out
    else:
        assert "one source" not in line


# --- shipping -------------------------------------------------------------------

def test_zip_ships_the_demo(tmp_path):
    import build_zip
    names = set(build_zip.demo_files())
    assert {"demo/data/prices.json", "demo/data/stocks.json", "demo/data/sources.json"} <= names
    assert {"demo/data/fund_report.txt", "demo/data/funds.json"} <= names
    assert not [n for n in names if n.endswith(".xlsx")]
    for path in ("scripts/demo.py", "demo/holdings.csv", "demo/funds.md", "references/demo.md"):
        assert path in build_zip.FILES
    target = build_zip.build(tmp_path / "b.zip")
    with zipfile.ZipFile(target) as z:
        listed = set(z.namelist())
    assert "holdnote/demo/data/prices.json" in listed
    assert "holdnote/scripts/demo.py" in listed
    assert not [n for n in listed if n.endswith((".xlsx", ".xls"))]
