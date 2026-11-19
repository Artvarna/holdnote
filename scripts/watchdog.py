#!/usr/bin/env python3
"""Thesis Watchdog: check the conditions the user wrote, every week.

Follow RULES.md. The module is references/thesis-watchdog.md.

Every tripwire is one row of ``me/watch.md``: the user's own words, verbatim,
and the measurable check they confirmed for them -- a metric, its exact
definition, a test, and the value it had on the day it was written. The run
fetches each metric's newest value into a JSON file; this script, not the
model, compares. A model asked "did this thesis break?" will find a way to
say yes or no; a comparison of two numbers with the same definition cannot.

    python3 scripts/watchdog.py add --watch me/watch.md --holding AAPL ...
    python3 scripts/watchdog.py check --watch me/watch.md --values values.json --write
    python3 scripts/watchdog.py list --watch me/watch.md

The values file the run writes:

    {"as_of": "2026-11-21",
     "values": {"AAPL-1": {"value": "68.4", "unit": "%",
                           "definition": "gross margin, quarter, GrossProfit / Revenues",
                           "date": "2026-10-31", "source": "Apple 10-Q, filed 2026-10-31",
                           "evidence": "0000320193-26-000101",
                           "quote": "optional: the passage a filing-read value came from"}}}

States: ``armed`` (watching), ``met YYYY-MM-DD`` (crossed on that day),
``not watchable`` (the user's words name nothing a document can show; kept,
because that is worth knowing too). A met tripwire alerts once, says "still
met" quietly after that, and re-arms when the value crosses back.

What it prints is the user's words, the figure, its source and its date. It
never says what to do about it (rules 6, 11): "a condition you wrote has been
met", then stop.

Exit codes: 0 printed, 1 refused (the reason on stdout), 2 usage.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


class Refused(Exception):
    """The file or the values cannot be read correctly; the message says why."""


# --------------------------------------------------------------------------
# What can be watched
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Metric:
    unit: str  # "%", "x", "EUR m", "USD m", "pp" or "text"
    applies: str  # "stock" or "fund"
    where: str  # where the run reads it, in references/thesis-watchdog.md terms


METRICS: dict[str, Metric] = {
    # Stocks: SEC companyfacts, the tags references/stock-brief.md uses
    "revenue_growth": Metric("%", "stock", "sec"),
    "gross_margin": Metric("%", "stock", "sec"),
    "operating_margin": Metric("%", "stock", "sec"),
    "net_margin": Metric("%", "stock", "sec"),
    "fcf_margin": Metric("%", "stock", "sec"),
    "free_cash_flow": Metric("USD m", "stock", "sec"),
    "net_debt_to_ebitda": Metric("x", "stock", "sec"),
    "share_count_change": Metric("%", "stock", "sec"),
    "return_on_equity": Metric("%", "stock", "sec"),
    "pe_ratio": Metric("x", "stock", "sec"),
    # Stocks: a figure the filing states but companyfacts does not carry
    # (a segment's revenue or margin, a customer count): read from the filing,
    # with the passage quoted
    "filing_figure": Metric("as stated", "stock", "filing"),
    # Funds: factsheet, KID, prospectus notices, the full holdings file
    "ter": Metric("%", "fund", "factsheet"),
    "top10_weight": Metric("%", "fund", "holdings"),
    "largest_holding_weight": Metric("%", "fund", "holdings"),
    "holdings_count": Metric("x", "fund", "holdings"),
    "tracking_difference": Metric("pp", "fund", "factsheet"),
    "fund_size": Metric("EUR m", "fund", "factsheet"),
    "index": Metric("text", "fund", "factsheet"),
    "distribution_policy": Metric("text", "fund", "factsheet"),
    "domicile": Metric("text", "fund", "factsheet"),
    "fund_status": Metric("text", "fund", "notice"),
}

# Price on its own is not here on purpose: "tell me when it drops below 100"
# is an order, not a thesis (rule 11). A valuation multiple is a fact about
# the business against its price; the price alone is a trigger.

TEST = re.compile(r"^\s*(<=|>=|<|>)\s*(-?\d+(?:\.\d+)?)\s*$|^\s*(changes)\s*$", re.I)

# A new value this many times the baseline, or this fraction of it, is a unit
# error (0.684 against 68.4: a fraction read as a percentage) until shown
# otherwise. Margins and weights do not move 50x between two filings.
UNIT_JUMP = Decimal(50)


def parse_test(text: str) -> tuple[str, Decimal | None]:
    m = TEST.match(text)
    if not m:
        raise Refused(f"test {text!r} is not one of '< n', '<= n', '> n', '>= n', 'changes'")
    if m.group(3):
        return "changes", None
    return m.group(1), Decimal(m.group(2))


def holds(op: str, value, threshold, baseline) -> bool:
    if op == "changes":
        return str(value).strip().casefold() != str(baseline).strip().casefold()
    return {"<": value < threshold, "<=": value <= threshold,
            ">": value > threshold, ">=": value >= threshold}[op]


def number(raw: object, where: str) -> Decimal:
    try:
        value = Decimal(str(raw).strip().replace(",", "").rstrip("%"))
    except (InvalidOperation, ValueError):
        raise Refused(f"{where}: {raw!r} is not a number")
    if not value.is_finite():
        raise Refused(f"{where}: {raw!r} is not a number")
    return value


# --------------------------------------------------------------------------
# me/watch.md
# --------------------------------------------------------------------------

COLUMNS = ["ID", "Holding", "ISIN", "From", "Your words", "Metric", "Definition", "Test",
           "Baseline", "Baseline date", "Baseline source", "State", "Last evidence"]

HEADER = """# Watch

Tripwires Holdnote checks every week (references/thesis-watchdog.md). Your
words stay exactly as you wrote them. Add or change a row by asking Holdnote,
so the check stays one a document can answer.

"""


@dataclass
class Wire:
    id: str
    holding: str
    isin: str
    origin: str  # a thesis file name, or "quick"
    words: str
    metric: str
    definition: str
    test: str
    baseline: str
    baseline_date: str
    baseline_source: str
    state: str = "armed"
    last: str = ""

    def cells(self) -> list[str]:
        return [self.id, self.holding, self.isin, self.origin, self.words, self.metric,
                self.definition, self.test, self.baseline, self.baseline_date,
                self.baseline_source, self.state, self.last]

    @property
    def met_on(self) -> str:
        return self.state[4:] if self.state.startswith("met ") else ""


def _escape(cell: str) -> str:
    return cell.replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").strip()


def _split(line: str) -> list[str]:
    cells, cur, i = [], "", 0
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body) and body[i + 1] in "|\\":
            cur += body[i + 1]
            i += 2
            continue
        if ch == "|":
            cells.append(cur.strip())
            cur = ""
        else:
            cur += ch
        i += 1
    cells.append(cur.strip())
    return cells


def load(path: Path) -> list[Wire]:
    if not path.is_file():
        return []
    wires: list[Wire] = []
    header_seen = False
    for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip().startswith("|"):
            continue
        cells = _split(line)
        if cells[0] == "ID":
            if cells != COLUMNS:
                raise Refused(f"{path.name}:{n}: the header is not {' | '.join(COLUMNS)}")
            header_seen = True
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        if not header_seen:
            raise Refused(f"{path.name}:{n}: a row before the header")
        if len(cells) != len(COLUMNS):
            raise Refused(f"{path.name}:{n}: {len(cells)} cells, not {len(COLUMNS)}")
        wire = Wire(*cells)
        validate(wire, f"{path.name}:{n}")
        wires.append(wire)
    ids = [w.id for w in wires]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise Refused(f"{path.name}: ID used twice: {', '.join(sorted(dupes))}")
    return wires


def validate(wire: Wire, where: str) -> None:
    if not wire.words:
        raise Refused(f"{where}: no words - a tripwire is always the user's own")
    if wire.state == "not watchable":
        return
    if wire.metric not in METRICS:
        raise Refused(f"{where}: metric {wire.metric!r} is not one Holdnote can watch")
    if not wire.definition:
        raise Refused(f"{where}: no definition - without one a later value may not be "
                      "the same figure")
    op, _ = parse_test(wire.test)
    metric = METRICS[wire.metric]
    if (op == "changes") != (metric.unit == "text"):
        raise Refused(f"{where}: {wire.metric} takes "
                      + ("'changes'" if metric.unit == "text" else "a number test"))
    if not (wire.state == "armed" or re.fullmatch(r"met \d{4}-\d{2}-\d{2}", wire.state)):
        raise Refused(f"{where}: state {wire.state!r} is not armed, met YYYY-MM-DD or "
                      "not watchable")
    if not wire.baseline or not wire.baseline_date or not wire.baseline_source:
        raise Refused(f"{where}: a baseline needs its value, date and source")
    if metric.unit != "text":
        number(wire.baseline, f"{where} baseline")


def save(path: Path, wires: list[Wire]) -> None:
    lines = [HEADER.rstrip("\n"), "",
             "| " + " | ".join(COLUMNS) + " |",
             "|" + "|".join("---" for _ in COLUMNS) + "|"]
    lines += ["| " + " | ".join(_escape(c) for c in w.cells()) + " |" for w in wires]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def holding_status(path: Path) -> dict[str, str]:
    """Ticker and ISIN -> "tripwire met <date>" or "watched", for the Mirror."""
    out: dict[str, str] = {}
    for w in load(path):
        state = (f"tripwire met {w.met_on}" if w.met_on else
                 "watched" if w.state == "armed" else "noted, not watchable")
        for key in (w.holding.upper(), w.isin.upper()):
            rank = {"tripwire": 3, "watched": 2, "noted, not watchable": 1}
            now = out.get(key, "")
            if key and rank.get(state.split(" met")[0], 0) > rank.get(now.split(" met")[0], 0):
                out[key] = state
    return out


# --------------------------------------------------------------------------
# Checking
# --------------------------------------------------------------------------


@dataclass
class Result:
    wire: Wire
    outcome: str  # met | still met | no longer met | not met | no new information | not available | not compared
    value: str = ""
    date: str = ""
    source: str = ""
    quote: str = ""
    why: str = ""


def check(wires: list[Wire], values: dict, as_of: date, theses: Path | None = None
          ) -> tuple[list[Result], list[Wire]]:
    results: list[Result] = []
    updated: list[Wire] = []
    newer = newer_theses(theses)
    for w in wires:
        if w.state == "not watchable":
            updated.append(w)
            continue
        got = values.get(w.id)
        if not got:
            results.append(Result(w, "not available", why="no value fetched this run"))
            updated.append(w)
            continue
        evidence = str(got.get("evidence") or "").strip()
        if not evidence:
            raise Refused(f"{w.id}: the value has no evidence id (a filing accession, a "
                          "document's date): without one, last week's figure is checked again")
        if evidence == w.last:
            results.append(Result(w, "no new information", got.get("value", ""),
                                  got.get("date", ""), got.get("source", "")))
            updated.append(w)
            continue
        metric = METRICS[w.metric]
        unit = str(got.get("unit") or "").strip()
        if metric.unit != "as stated" and unit != metric.unit:
            results.append(Result(w, "not compared", why=f"unit {unit or 'none'!r}, the "
                                  f"tripwire's is {metric.unit!r}"))
            updated.append(w)
            continue
        definition = str(got.get("definition") or "").strip()
        if definition.casefold() != w.definition.casefold():
            results.append(Result(w, "not compared",
                                  why=f"defined as {definition!r}, the tripwire as "
                                      f"{w.definition!r} - not the same figure"))
            updated.append(w)
            continue
        for key in ("date", "source"):
            if not str(got.get(key) or "").strip():
                raise Refused(f"{w.id}: the value has no {key}")
        try:
            date.fromisoformat(str(got["date"]).strip())
        except ValueError:
            raise Refused(f"{w.id}: date {got['date']!r} is not YYYY-MM-DD - the document's own "
                          "date, not its period")
        if metric.where == "filing" and not str(got.get("quote") or "").strip():
            raise Refused(f"{w.id}: a figure read from a filing needs its passage quoted")
        op, threshold = parse_test(w.test)
        raw = got.get("value")
        if op == "changes":
            value, base = str(raw).strip(), w.baseline
        else:
            value = number(raw, f"{w.id} value")
            base = number(w.baseline, f"{w.id} baseline")
            if base and value and (abs(value / base) > UNIT_JUMP or abs(base / value) > UNIT_JUMP):
                results.append(Result(w, "not compared", str(raw), why=(
                    f"{raw} against a baseline of {w.baseline} is a {UNIT_JUMP}x jump - "
                    "a fraction read as a percentage, or the wrong figure")))
                updated.append(w)
                continue
        now = holds(op, value, threshold, base)
        when = str(got["date"])
        if now and not w.met_on:
            outcome, state = "met", f"met {when}"
        elif now:
            outcome, state = "still met", w.state
        elif w.met_on:
            outcome, state = "no longer met", "armed"
        else:
            outcome, state = "not met", "armed"
        res = Result(w, outcome, str(raw), when, str(got["source"]),
                     str(got.get("quote") or "").strip())
        if outcome in ("met", "still met"):
            later = [d for d in newer.get(w.holding.upper(), []) if d > (w.met_on or when)]
            if later:
                res.why = f"a newer thesis was written on {later[-1]}, after this was met"
        results.append(res)
        updated.append(replace(w, state=state, last=evidence))
    return results, updated


def newer_theses(theses: Path | None) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    if theses and theses.is_dir():
        for p in sorted(theses.glob("*.md")):
            m = re.fullmatch(r"(.+)-(\d{4}-\d{2}-\d{2})\.md", p.name)
            if m:
                out.setdefault(m.group(1).upper(), []).append(m.group(2))
    return out


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join(":---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(_escape(c) for c in r) + " |" for r in rows]
    return lines


def render(results: list[Result], wires: list[Wire], as_of: date) -> list[str]:
    met = [r for r in results if r.outcome == "met"]
    out = [f"Thesis Watchdog ({as_of})", ""]
    if met:
        n = len(met)
        out.append(f"{n} condition{'s' if n > 1 else ''} you wrote "
                   f"{'have' if n > 1 else 'has'} been met.")
        out.append("")
        for r in met:
            w = r.wire
            out.append(f"{w.holding} ({w.id}). You wrote: \"{w.words}\"")
            out.append(f"  Check: {w.definition} {w.test}. Baseline {w.baseline} "
                       f"({w.baseline_date}, {w.baseline_source}).")
            out.append(f"  Now: {r.value} ({r.date}, {r.source}).")
            if r.quote:
                out.append(f"  Passage: \"{r.quote}\"")
            if r.why:
                out.append(f"  Note: {r.why}.")
            out.append("")
    elif results and all(r.outcome in UNCHECKED for r in results):
        out.append(f"None of your {len(results)} tripwires could be checked this week - "
                   "this is not an all-clear. The table says why for each.")
        out.append("")
    else:
        out.append("No condition you wrote was met this week.")
        out.append("")
    rows = []
    for r in results:
        w = r.wire
        rows.append([w.id, w.holding, f"\"{w.words}\"", f"{w.metric} {w.test}",
                     w.baseline, r.value or "Not available", r.date, r.outcome
                     + (f" ({r.why})" if r.why and r.outcome != "met" else "")])
    if rows:
        out += _table(["ID", "Holding", "Your words", "Check", "Baseline", "Now", "As of",
                       "Result"], rows)
        out.append("")
    idle = [w for w in wires if w.state == "not watchable"]
    if idle:
        out.append("Not watchable (no document can show these): "
                   + "; ".join(f"{w.holding} \"{w.words}\"" for w in idle) + ".")
    out.append(f"Subject: {subject(results)}")
    return out


UNCHECKED = ("not available", "not compared")


def subject(results: list[Result]) -> str:
    """The email subject. It never reads as an all-clear when nothing was checked."""
    n = sum(r.outcome == "met" for r in results)
    gaps = sum(r.outcome in UNCHECKED for r in results)
    tail = f" ({gaps} of {len(results)} not checked)" if gaps else ""
    if n:
        return f"Holdnote weekly: {n} condition{'s' if n > 1 else ''} you wrote met{tail}"
    if results and gaps == len(results):
        return f"Holdnote weekly: Watchdog could not check any of your {len(results)} tripwires"
    return f"Holdnote weekly: no condition you wrote was met{tail}"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def cmd_add(args) -> int:
    if "\n" in args.words or "\r" in args.words:
        raise Refused("the words are more than one line; a tripwire is one sentence of yours, "
                      "kept exactly - split it into two tripwires")
    wires = load(args.watch)
    prefix = args.holding.upper()
    taken = {w.id for w in wires}
    n = 1
    while f"{prefix}-{n}" in taken:
        n += 1
    state = "not watchable" if args.not_watchable else "armed"
    wire = Wire(f"{prefix}-{n}", prefix, (args.isin or "").upper(), args.origin, args.words,
                args.metric or "", args.definition or "", args.test or "",
                args.baseline or "", args.baseline_date or "", args.baseline_source or "",
                state, "")
    if not args.not_watchable:
        metric = METRICS.get(args.metric or "")
        if metric and args.kind and metric.applies != args.kind:
            raise Refused(f"{args.metric} is a {metric.applies} metric; {prefix} is a {args.kind}")
    validate(wire, "the new tripwire")
    wires.append(wire)
    save(args.watch, wires)
    print(f"Added {wire.id}: \"{wire.words}\" -> "
          + ("not watchable" if args.not_watchable else
             f"{wire.metric} {wire.test} (baseline {wire.baseline}, {wire.baseline_date})"))
    return 0


def cmd_check(args) -> int:
    wires = load(args.watch)
    if not wires:
        print("Thesis Watchdog: Not available - no tripwires in "
              f"{args.watch.name} yet (say \"watch\" plus a holding to add one)")
        return 1
    spec = json.loads(args.values.read_text(encoding="utf-8"))
    try:
        as_of = date.fromisoformat(spec["as_of"])
    except (KeyError, TypeError, ValueError):
        raise Refused(f"{args.values.name}: 'as_of' must be a YYYY-MM-DD date")
    values = spec.get("values", {})
    results, updated = check(wires, values, as_of, args.theses)
    lines = render(results, updated, as_of)
    stray = sorted(set(values) - {w.id for w in wires})
    if stray:
        lines.insert(-1, "Values for no tripwire on file (a mistyped ID?): " + ", ".join(stray) + ".")
    print("\n".join(lines))
    if args.write:
        save(args.watch, updated)
    return 0


def cmd_list(args) -> int:
    wires = load(args.watch)
    if not wires:
        print(f"No tripwires in {args.watch.name}.")
        return 0
    print("\n".join(_table(["ID", "Holding", "Your words", "Check", "Baseline", "State"], [
        [w.id, w.holding, f"\"{w.words}\"", f"{w.metric} {w.test}".strip(),
         f"{w.baseline} ({w.baseline_date})" if w.baseline else "", w.state] for w in wires])))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="add one tripwire")
    a.add_argument("--watch", type=Path, default=Path("me/watch.md"))
    a.add_argument("--holding", required=True)
    a.add_argument("--isin", default="")
    a.add_argument("--kind", choices=["stock", "fund"], default=None)
    a.add_argument("--origin", default="quick", help="the thesis file, or 'quick'")
    a.add_argument("--words", required=True, help="the user's own words, verbatim")
    a.add_argument("--metric")
    a.add_argument("--definition")
    a.add_argument("--test")
    a.add_argument("--baseline")
    a.add_argument("--baseline-date")
    a.add_argument("--baseline-source")
    a.add_argument("--not-watchable", action="store_true")

    c = sub.add_parser("check", help="compare this run's values with every tripwire")
    c.add_argument("--watch", type=Path, default=Path("me/watch.md"))
    c.add_argument("--values", type=Path, required=True)
    c.add_argument("--theses", type=Path, default=None)
    c.add_argument("--write", action="store_true", help="save the new states to the watch file")

    li = sub.add_parser("list", help="the tripwires on file")
    li.add_argument("--watch", type=Path, default=Path("me/watch.md"))

    args = parser.parse_args(argv)
    try:
        return {"add": cmd_add, "check": cmd_check, "list": cmd_list}[args.cmd](args)
    except Refused as exc:
        print(f"Thesis Watchdog: Not available - {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
