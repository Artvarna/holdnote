#!/usr/bin/env python3
"""The BuffettBot demo: a full portfolio report with no setup and no fetch.

    python3 scripts/demo.py --draft <draft.md> [--tables Allocation,Stocks] [--proof]

Runs Mode C (references/etf-brief.md) on the synthetic demo portfolio in
demo/holdings.csv and the frozen snapshot of public data in demo/data/,
which scripts/demo_snapshot.py refreshes on GitHub's runners. The tables
come from the skill's own scripts, exactly as a real run pastes them:
market_weights runs here for Allocation; fund_holdings ran in the snapshot
job for Holdings, Look-through, Countries, Sectors and Currencies, because
the issuers' holdings files may not be redistributed and are not shipped
(demo/data/fund_report.txt is its output). The Stocks table is built from
the snapshot's EDGAR filings and company events pages.

It writes the full RULES.md Part IV draft to --draft, checks it with the
same contract as scripts/check_output.py, and prints the rendered report
(scripts/render.py) to stdout -- the demo's whole output. Nothing is fetched
and nothing is recalled: every figure is in demo/data/ with its source and
dates, and Data as of is the snapshot's date, never today's.

Exit codes: 0 printed; 1 the draft failed a contract check, or the fund
report was computed from a different demo/holdings.csv or prices.json than
the ones here (problems on stdout).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for folder in (HERE, ROOT / "tests"):
    if (folder / "contract.py").exists():
        sys.path.insert(0, str(folder))
        break
sys.path.insert(0, str(HERE))

import contract  # noqa: E402
import fund_holdings as fh  # noqa: E402
import import_holdings as ih  # noqa: E402
import render  # noqa: E402

DEMO = ROOT / "demo"
DATA = DEMO / "data"
# The order Mode C prints its tables in (etf-brief.md -> Mode C output).
ORDER = ["Allocation", "Holdings", "Look-through", "Hidden bets", "Countries", "Sectors",
         "Currencies", "Stocks"]
# "Show me a demo": everything but Currencies, which Countries mostly repeats
# for this portfolio and which a follow-up question can ask for.
DEFAULT = ["Allocation", "Holdings", "Look-through", "Hidden bets", "Countries", "Sectors", "Stocks"]
# Mode C tables the snapshot cannot fill, and why.
NOT_IN_DEMO = ("Performance, Comparison, Structural and Holdings changes "
               "(they need live closes, factsheets or a week of history)")


class Stale(Exception):
    """The shipped fund report does not match the shipped portfolio."""


def build_stamp() -> str:
    f = ROOT / "BUILD"
    if f.is_file():
        return f.read_text(encoding="utf-8").strip()
    try:
        return subprocess.run(["git", "log", "-1", "--format=%h %cs"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip() + " (repo)"
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run(script: str, *args: str) -> str:
    out = subprocess.run([sys.executable, str(HERE / script), *args], cwd=ROOT,
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"{script} refused the demo data:\n{out.stdout}{out.stderr}")
    return out.stdout


def blocks(text: str) -> tuple[dict[str, list[str]], list[str], list[str]]:
    """A script's printed tables by heading, then its METHOD and PROOF lines."""
    tables: dict[str, list[str]] = {}
    method: list[str] = []
    proof: list[str] = []
    part = "tables"
    current: list[str] = []
    for line in text.splitlines() + [""]:
        if line in ("METHOD", "PROOF"):
            part = line.lower()
            continue
        if part == "method":
            method += [line] if line.strip() else []
        elif part == "proof":
            proof += [line] if line.strip() else []
        elif line.strip():
            current.append(line)
        elif current:
            if len(current) > 1 and current[1].startswith("|"):
                heading = re.split(r"\s*[(—]", current[0], maxsplit=1)[0].strip()
                tables[heading] = current
            else:
                method += current  # market_weights prints its METHOD lines bare
            current = []
    return tables, method, proof


def hidden_bets_block(fund_tables: dict[str, list[str]], fund_method: list[str]) -> tuple[list[str], list[str]]:
    """Hidden bets, as fund_holdings prints it.

    A snapshot from before the table existed has none, so it is read back from
    the snapshot's Look-through table -- complete only when HIDDEN_MIN is above
    the smallest fund-only Total printed there, since every company the table
    leaves out is no larger than that. Otherwise it is Not available, never a
    partial list.
    """
    if "Hidden bets" in fund_tables:
        return fund_tables["Hidden bets"], []
    lt = fund_tables.get("Look-through", [])
    heading = lt[0].replace("Look-through", "Hidden bets", 1) if lt else "Hidden bets"
    rows, floor = fh.parse_lookthrough(lt)
    if not rows or floor is None or floor >= fh.HIDDEN_MIN:
        why = ("the snapshot's Look-through table does not print every company with a Total of "
               f"{fh.HIDDEN_MIN:.2f} or more")
        return ["Hidden bets", "| Company | Total |", "|---|---|", f"| all | Not available - {why} |"], []
    bets = fh.hidden_bets(rows)
    return ([heading, *fh.hidden_bets_table(bets)],
            [fh.hidden_bets_method(bets),
             f"Hidden bets source: read from the Look-through table above, which prints every "
             f"company with a Total over {floor:.2f}, so none of {fh.HIDDEN_MIN:.2f} or more is left out"])


def stocks_table(stocks: dict, holdings: list, as_of: date) -> tuple[list[str], list[str], list[str]]:
    start = as_of - timedelta(days=contract.STOCKS_WINDOW_DAYS)
    rows = ["Stocks", "| " + " | ".join(contract.STOCK_COLUMNS) + " |",
            "|" + "---|" * len(contract.STOCK_COLUMNS)]
    missing: list[str] = []
    proof: list[str] = []
    for h in holdings:
        s = stocks.get(h.isin)
        if h.kind != "stock" or s is None:
            continue
        if s["earnings"] and s["earnings"] >= as_of.isoformat():
            earnings = s["earnings"]
            proof.append(f"earnings date    {h.ticker} {earnings} >= data date {as_of}, "
                         f"from the company's events page ({s['earnings_basis']})  PASS")
        elif s["earnings_basis"].startswith("0 dated"):
            earnings = "Not available — company events page not readable without a browser"
            missing.append(f"{h.ticker} next earnings date")
        else:
            earnings = "Not available — not announced"
        filings = [f for f in s["filings"] if f["filed"] <= as_of.isoformat()]
        periodic = next((f for f in filings if f["form"] in ("10-K", "10-Q", "10-K/A", "10-Q/A")), None)
        eight_ks = sorted({f["filed"] for f in filings if f["form"] in ("8-K", "8-K/A")
                           and start.isoformat() <= f["filed"] <= as_of.isoformat()}, reverse=True)
        eight = f"{len(eight_ks)} ({', '.join(eight_ks)})" if eight_ks else "0"
        if periodic:
            latest, filed = f"{periodic['form']}, period {periodic['period']}", periodic["filed"]
        else:
            latest = filed = "Not available — no 10-K or 10-Q in the snapshot"
        rows.append(f"| {h.ticker} | {h.name} | {earnings} | {latest} | {filed} | {eight} |")
        proof.append(f"CIK match        {h.ticker} -> CIK {s['cik']}, \"{s['company']}\" ~ "
                     f"demo/holdings.csv \"{h.name}\"  PASS")
        proof.append(f"8-K window       {h.ticker}: {len(eight_ks)} listed, {len(eight_ks)} in the "
                     f"30 days to {as_of} per EDGAR  PASS")
    return rows, missing, proof


def confirmation(prices: dict, tickers: dict[str, str]) -> tuple[str, int]:
    """The Confirmation line: single-source closes first, so the rendered
    warning (cut at 140 characters) always shows them."""
    two, one = [], []
    for isin, p in prices.items():
        t = tickers.get(isin, isin)
        if p.get("confirmed_by"):
            two.append(f"{t} {p['confirmed_by']['diff_pct']}%")
        else:
            one.append((t, p.get("unconfirmed", "no second source")))
    parts = []
    if one:
        why = dict.fromkeys(re.sub(r"^Yahoo Finance chart, [^,]+, has", "Yahoo had", w) for _, w in one)
        parts.append(f"{', '.join(t for t, _ in one)} closes rest on one source, the exchange "
                     f"({'; '.join(why)})")
    if two:
        parts.append(f"{', '.join(t.split()[0] for t in two)} match Yahoo Finance "
                     f"({', '.join(two)})")
    return "; ".join(parts), len(one)


def sources_rows(sources: list[dict], as_of: date) -> list[str]:
    rows = ["| URL or path | Document | Published | Retrieved (UTC) |", "|---|---|---|---|"]
    for s in sources:
        rows.append(f"| {s['url']} | {s['document']} | {s['published']} | {s['retrieved']} |")
    for path, doc in (("demo/holdings.csv", "Demo portfolio quantities and targets (synthetic)"),
                      ("demo/funds.md", "Demo funds and their holdings-file sources")):
        rows.append(f"| {path} | {doc} | n/a — local file | n/a — packaged with the skill |")
    return rows


def summary_line(sources: list[dict], unverified: int) -> str:
    dates = sorted(s["published"] for s in sources if re.match(r"^\d{4}-\d{2}-\d{2}$", s["published"]))
    n = len(sources) + 2
    return (f"{n} documents · published {dates[0]} to {dates[-1]} · 0 stale · "
            f"{unverified} unverified · full list on \"show proof\"")


def build(tables_wanted: list[str], proof: bool) -> tuple[str, str]:
    """(draft with full SOURCES, report-ready text with SOURCES collapsed)."""
    prices_path = DATA / "prices.json"
    prices = json.loads(prices_path.read_text())
    as_of = date.fromisoformat(prices["as_of"])
    stocks = json.loads((DATA / "stocks.json").read_text())
    sources = json.loads((DATA / "sources.json").read_text())
    log = (DATA / "snapshot.log").read_text().splitlines()
    fetched = log[0].split("· run ", 1)[1] if log and "· run " in log[0] else "unknown"
    holdings = ih.load_holdings(DEMO / "holdings.csv").holdings

    alloc_tables, alloc_method, _ = blocks(run(
        "market_weights.py", "--prices", str(prices_path), "--holdings", "demo/holdings.csv"))
    meta = json.loads((DATA / "funds.json").read_text())
    stale = [p for p, h in meta["inputs"].items()
             if hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != h]
    if stale:
        raise Stale(f"demo/data/fund_report.txt was computed from a different {', '.join(stale)}; "
                    "run the Demo data workflow to rebuild it")
    fund_tables, fund_method, fund_proof = blocks((DATA / "fund_report.txt").read_text())
    bets_rows, bets_method = hidden_bets_block(fund_tables, fund_method)
    stock_rows, missing, stock_proof = stocks_table(stocks, holdings, as_of)
    printed = {**alloc_tables, **fund_tables, "Hidden bets": bets_rows, "Stocks": stock_rows}

    file_dates = ", ".join(f"{t} {m['as_of']}" for t, m in meta["funds"].items())
    tickers = {h.isin: h.ticker for h in holdings}
    confirm, unverified = confirmation(prices["prices"], tickers)
    funds = sum(1 for h in holdings if h.kind == "fund")

    result = ["RESULT", "Mode: Demo + Portfolio (Mode C)"]
    for name in [t for t in ORDER if t in tables_wanted]:
        result += [""] + printed[name]
    result.append("")

    asked = ("demo, default tables" if tables_wanted == DEFAULT
             else "demo, asked: " + ", ".join(tables_wanted))
    method = [
        "METHOD",
        f"Build: {build_stamp()}",
        f"Tables: {', '.join(t for t in ORDER if t in tables_wanted)} ({asked})",
        f"Demo: a synthetic portfolio (demo/holdings.csv) on a frozen snapshot of public data fetched "
        f"{fetched} by scripts/demo_snapshot.py; nothing was fetched in this run. Not in the demo: {NOT_IN_DEMO}",
        # market_weights words its prices for a live run, which also prints a
        # Performance table; the demo's closes come from the snapshot.
        *[ln.replace("the Performance closes of", "the snapshot's closes of")
          for ln in alloc_method if ln.startswith("Allocation")],
        *fund_method,
        *bets_method,
        f"Stocks window:     8-Ks filed in the 30 days to {as_of}, by EDGAR filing date",
        "Earnings dates:    company-announced only, never estimated",
        f"Confirmation: {confirm}",
        "Columns suppressed: none",
        "Next: attach your broker's export or a screenshot and ask \"what do I own?\" "
        "for your own portfolio, or say \"set up BuffettBot\"; say \"make a card\" for "
        "an image of this one to share",
        "",
    ]
    proof_block = ["PROOF", *fund_proof, *stock_proof,
                   *[f"close            {tickers.get(i, i)} {p['currency']} {p['price']} on {p['date']} "
                     f"({p['source']})" + (f" vs {p['confirmed_by']['price']} "
                                          f"({p['confirmed_by']['source']}), {p['confirmed_by']['diff_pct']}%  PASS"
                                          if p.get("confirmed_by") else "  one source")
                     for i, p in prices["prices"].items()],
                   ""]

    head = [
        "STATUS: Complete.",
        "",
        "CONTEXT",
        f"Data as of:       {as_of} · demo snapshot, frozen — not today's prices",
        f"Latest period:    fund holdings files as of {file_dates}; snapshot fetched {fetched}",
        "Currency / units: EUR · weights as % of the demo portfolio at market value",
        f"Not available:    {'; '.join(missing) if missing else 'none'}",
        f"Coverage:         {len(holdings)} of {len(holdings)} holdings · {funds} of {funds} funds "
        "with full holdings files",
        "",
    ]
    full_sources = ["SOURCES", *sources_rows(sources, as_of)]
    draft = "\n".join(head + result + method + proof_block + full_sources) + "\n"
    if proof:
        report = draft
    else:
        report = "\n".join(head + result + method + ["SOURCES", summary_line(sources, unverified)]) + "\n"
    return draft, report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--draft", type=Path, required=True, help="where to write the full draft")
    ap.add_argument("--tables", default="default",
                    help=f"comma-separated, from {', '.join(ORDER)}; 'all', or the default "
                         f"{', '.join(DEFAULT)}")
    ap.add_argument("--proof", action="store_true", help="print PROOF and the full SOURCES")
    args = ap.parse_args(argv)
    if args.tables == "default":
        wanted = DEFAULT
    elif args.tables == "all":
        wanted = ORDER
    else:
        wanted = [t.strip() for t in args.tables.split(",") if t.strip()]
        unknown = [t for t in wanted if t not in ORDER]
        if unknown:
            print(f"not a demo table: {', '.join(unknown)} (choose from {', '.join(ORDER)})")
            return 2
    try:
        draft, report = build(wanted, args.proof)
    except Stale as exc:
        print(exc)
        return 1
    args.draft.parent.mkdir(parents=True, exist_ok=True)
    args.draft.write_text(draft, encoding="utf-8")
    problems = contract.output_problems(draft) + contract.output_problems(report)
    if problems:
        print("\n".join(dict.fromkeys(problems)))
        return 1
    print(render.render(report), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
