"""Runner and output-contract parser.

The only file that knows how to invoke the script under test. If the CLI
changes, change ``run()`` here and nothing else.

The contract it parses is RULES.md Part IV: six sections in a fixed order,
STATUS first, RESULT absent on a halt, and no recommendation language
anywhere.
"""

from __future__ import annotations

import datetime as _dt
import re
import subprocess
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "t212_holdings.py"

# The importer reports a halt on stdout like any other run, and distinguishes
# it by exit code alone.
EXIT_COMPLETE = 0
EXIT_HALT = 1

# Fixed section order mandated by RULES.md Part IV.
SECTIONS = ["STATUS", "CONTEXT", "RESULT", "METHOD", "PROOF", "SOURCES"]

# The STATUS line, exactly as RULES.md Part IV fixes it: the check that
# fired, an ASCII hyphen-minus between single spaces, then the figure. The
# separator is asserted rather than tolerated -- the code and the rules
# disagreed on it once and nothing caught it, because every parser here
# searched for "HALTED" and read the rest as free text.
STATUS_COMPLETE = "Complete."  # RULES.md Part IV: "STATUS: Complete."
HALT_STATUS = re.compile(
    r"^HALTED - (?P<check>[A-Za-z_][A-Za-z0-9_]*), (?P<figure>\S.*)$"
)

# The CONTEXT fields this module prints, as it labels them. A halt prints the
# same fields; the ones it could not populate read "not reached".
#
# There is no "Sources used" line: every file this module reads is local, and
# all of them are listed in SOURCES with their dates. What CONTEXT carries of
# them is the two values a reader needs to read the numbers -- the ownership
# cutoff and the date the policy files were last updated -- and both ride on
# "Latest period", which they bound.
CONTEXT_FIELDS = [
    "Data as of",
    "Latest period",
    "Currency/units",
    "Not available",
    "Coverage",
]

# Rule 6 -- describe and compare, never recommend.
#
# This module uses both verbs as nouns, and none of those uses is advice:
# "Market sell" is an Action copied out of the export, "Buy cost" and "Sell
# proceeds" are columns, and "buy: 1 divide" is a row kind in the
# exchange-rate tally. Those contexts are excluded rather than the verbs, so
# a bare "buy" or "sell" addressed to the reader still fails.
#
# Each exclusion is anchored to the position the noun is printed in, not to
# the words around it. An order type exempts the verb only at the start of a
# table cell or after a list dash, because "market sell" with nothing in
# front of it is also a clause -- and exempting "in a falling market sell
# into strength" is the recommendation rule 6 exists to stop. A colon
# exempts only when a count follows: "buy: 1 divide" is a tally row,
# "Verdict: buy: take the position" is advice.
_ACTION_CELL = (
    r"(?<!\| market )(?<!- market )"
    r"(?<!\| limit )(?<!- limit )"
    r"(?<!\| stop )(?<!- stop )"
    r"(?<!\| stop limit )(?<!- stop limit )"
)
_AS_NOUN = r"(?!\s*(?:\(|:\s*\d|price|rows?|side|cost|proceeds))"
BANNED = [
    _ACTION_CELL + r"\bbuy\b" + _AS_NOUN,
    _ACTION_CELL + r"\bsell\b" + _AS_NOUN,
    r"\bhold\b(?!ing|er)",
    r"\bundervalued\b",
    r"\bovervalued\b",
    r"\battractive\b",
    r"\bstrong fundamentals\b",
    r"\bentry point\b",
    r"\byou should\b",
    r"\bI (?:would |'d )?recommend\b",
    r"\bprice target\b",
    r"\bwe expect\b",
    r"\blikely to (?:rise|fall|outperform)\b",
    # His name never vouches for a result (references/buffett.md)
    r"\bBuffett[- ]approved\b",
    r"\bBuffett would\b",
    r"\bBuffett'?s (?:pick|favou?rite)\b",
    r"\ba Buffett stock\b",
]


@dataclass
class Run:
    """One execution of the script under test."""

    fixture: str
    exit_code: int
    stdout: str
    stderr: str
    sections: dict[str, str] = field(default_factory=dict)

    @property
    def halted(self) -> bool:
        return self.stdout.lstrip().upper().startswith("STATUS") and (
            "HALTED" in self.status_line.upper()
        )

    @property
    def status_line(self) -> str:
        body = self.sections.get("STATUS", "")
        return body.strip().splitlines()[0] if body.strip() else ""

    @property
    def halt_check(self) -> str | None:
        """The check named on the STATUS line, or None if it is not a halt.

        Returns None on a malformed halt line too, which is the point: a
        status that says HALTED in some other shape names no check as far as
        anything reading the output is concerned.
        """
        match = HALT_STATUS.match(self.status_line)
        return match.group("check") if match else None

    @property
    def halt_figure(self) -> str | None:
        """The figure named on the STATUS line, under the same rule."""
        match = HALT_STATUS.match(self.status_line)
        return match.group("figure") if match else None

    def context(self) -> dict[str, str]:
        out = {}
        for line in self.sections.get("CONTEXT", "").splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                out[k.strip()] = v.strip()
        return out

    def numbers(self) -> list[float]:
        return [float(m) for m in re.findall(r"-?\d+\.\d+", self.stdout)]

    def percentages(self) -> list[float]:
        return [float(m) for m in re.findall(r"(-?\d+(?:\.\d+)?)\s*%", self.stdout)]


def run(
    data_dir: Path,
    pies: Path,
    ownership: Path,
    *,
    cutoff: str | None = None,
    attribute: str | None = None,
    label: str = "",
    proof: bool = False,
) -> Run:
    """Invoke the script over a prepared workspace and split its output."""
    if not SCRIPT.exists():
        raise FileNotFoundError(
            f"{SCRIPT} not found. The harness tests the code, not the spec -- "
            "point SCRIPT at the real implementation."
        )
    argv = [
        sys.executable,
        str(SCRIPT),
        "--data-dir",
        str(data_dir),
        "--pies",
        str(pies),
        "--ownership",
        str(ownership),
    ]
    if cutoff:
        argv += ["--cutoff", cutoff]
    if attribute:
        argv += ["--attribute", attribute]
    if proof:
        argv.append("--proof")
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    result = Run(
        label or data_dir.parent.parent.name, proc.returncode, proc.stdout, proc.stderr
    )
    result.sections = split_sections(proc.stdout)
    return result


# A section header on its own line, or STATUS with its line after a colon --
# RULES.md Part IV allows both: `STATUS` over `Complete.`, and
# `STATUS: Complete.` on one line. For the second, the match ends where the
# status text starts, so the section body begins with it either way.
_HEADER = re.compile(
    rf"^[ \t]*(?:(?P<inline>STATUS):[ \t]*(?=\S)|(?P<name>{'|'.join(SECTIONS)})[ \t]*$)",
    re.MULTILINE,
)


def _header_name(m: re.Match) -> str:
    return m.group("inline") or m.group("name")


def split_sections(text: str) -> dict[str, str]:
    """Split rendered output on the six Part IV section headers."""
    marks = list(_HEADER.finditer(text))
    out: dict[str, str] = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        out[_header_name(m)] = text[m.end() : end]
    return out


def section_order(text: str) -> list[str]:
    return [_header_name(m) for m in _HEADER.finditer(text)]


_STATUS_COMPLETE = re.compile(r"^complete\.?$", re.IGNORECASE)
_STATUS_HALT = re.compile(r"^halted - \S", re.IGNORECASE)


def status_problems(sections: dict[str, str]) -> list[str]:
    """STATUS against RULES.md Part IV: `Complete.` alone, or a named halt.

    A complete run's line is `Complete.` and nothing more. Single-source rows
    go on METHOD's `Confirmation:` line and gaps in CONTEXT; a status that
    repeats them is a second copy that can disagree with the first. A halt
    line may wrap -- RULES.md's own example does -- so only it may run on.
    """
    if "STATUS" not in sections:
        return ["no STATUS: it is the first line of every output"]
    lines = [line.strip() for line in sections["STATUS"].splitlines() if line.strip()]
    if not lines:
        return ["STATUS is empty"]
    first = lines[0]
    if _STATUS_HALT.match(first):
        return []
    if _STATUS_COMPLETE.match(first):
        if len(lines) > 1:
            return [f"a complete STATUS is one line; it runs on: {lines[1]!r}"]
        return []
    if first.lower().startswith("complete"):
        return [
            "a complete STATUS is `Complete.` and nothing more -- single-source "
            f"rows belong on METHOD's Confirmation line, gaps in CONTEXT: {first!r}"
        ]
    return [f"STATUS is neither `Complete.` nor `Halted - ` and its check: {first!r}"]


def banned_hits(text: str) -> list[str]:
    hits = []
    for pat in BANNED:
        for m in re.finditer(pat, text, re.IGNORECASE):
            hits.append(f"{pat} -> {text[max(0, m.start() - 40) : m.end() + 40]!r}")
    return hits


# --------------------------------------------------------------------------
# Market-wide output (references/market-context.md -> Market-wide mode)
#
# That mode has no script behind it: the agent composes the output. These
# checks are the parts of its contract a parser can hold it to, so a saved
# run -- a journal entry, a pasted transcript -- can be read against them.
# --------------------------------------------------------------------------

# A clock time, including the shapes a time takes when a digit was never
# recorded: "13:1x", "1?:05", "HH:MM". Between a "T" and a "Z" it is the
# time half of an ISO timestamp and still counts.
_TIME = re.compile(
    r"(?:(?<=T)|(?<![\w:]))([0-9xX?#_hH]{1,2}):([0-9xX?#_mM]{2})(?=Z\b|(?![\w:]))"
)


def placeholder_times(text: str) -> list[str]:
    """Every time printed with a placeholder in it, or out of range.

    RULES.md Part IV: a time is an exact HH:MM or it is left off. "13:1x"
    is the defect this exists for -- five runs in a row printed it.
    """
    hits = []
    for m in _TIME.finditer(text):
        hour, minute = m.groups()
        if hour.isdigit() and minute.isdigit() and int(hour) < 24 and int(minute) < 60:
            continue
        hits.append(m.group(0))
    return hits


_SUBJECT_LINE = re.compile(r"^=== .+ ===$")
# What a SOURCES row looks like: a table row, a list item, the export-only
# form RULES.md Part IV gives, the v11 summary line, or "none".
_SOURCES_SUMMARY = re.compile(
    r"^(?P<n>\d+) documents? · published (?P<first>\d{4}-\d{2}-\d{2}) to "
    r"(?P<last>\d{4}-\d{2}-\d{2}) · (?P<stale>\d+) stale · "
    r"(?P<unverified>\d+) unverified · full list on \"show proof\"$"
)
_SOURCE_ROW = re.compile(r"^(?:\||- |```|SOURCES: |none$|\d+ documents? · )")


def text_outside_sections(text: str, *, subject_line: bool = False) -> list[str]:
    """Lines that belong to no section.

    Before the first header nothing may print, except a subject line where
    the module's reference specifies one (etf-brief Mode A). After SOURCES
    every line must be a source row: a loose note there is text outside the
    six sections even though a naive split files it under SOURCES.
    """
    marks = list(_HEADER.finditer(text))
    if not marks:
        return [line for line in text.splitlines() if line.strip()]
    stray = [line for line in text[: marks[0].start()].splitlines() if line.strip()]
    if subject_line and len(stray) == 1 and _SUBJECT_LINE.match(stray[0].strip()):
        stray = []
    seen = [_header_name(m) for m in marks]
    stray += [f"repeated header {h}" for h in SECTIONS if seen.count(h) > 1]
    body = [line.strip() for line in split_sections(text).get("SOURCES", "").splitlines()]
    stray += [line for line in body if line and not _SOURCE_ROW.match(line)]
    # One listing. A table followed by a list of links is the section and
    # then a second, undated copy of it -- text after SOURCES, not in it.
    if any(line.startswith("|") for line in body):
        stray += [f"separate link list: {line}" for line in body if line.startswith("- ")]
    return stray


_URL = re.compile(r"https?://\S+")


def sources_without_url(text: str) -> list[str]:
    """SOURCES rows that do not carry their own URL.

    RULES.md Part IV: every row carries its URL, or its path for a local
    file. The column-header row and the separator are not rows.
    """
    body = split_sections(text).get("SOURCES", "")
    rows = [line.strip() for line in body.splitlines() if line.strip().startswith(("|", "- "))]
    table = [r for r in rows if r.startswith("|")]
    if table:
        rows = [r for r in table[1:] if not set(r) <= set("|-: ")]
    return [r for r in rows if not _URL.search(r) and "local file" not in r]


def coverage_problems(sections: dict[str, str]) -> list[str]:
    """Coverage counts that describe a table which did not run.

    market-context.md -> Output: Coverage counts per table that ran, and a
    `0 of 0` reads as a fetch that found nothing. The v9 live run printed
    `0 of 0 indexes` and `0 of 0 rates & FX rows` on a sectors-only request.
    """
    context = sections.get("CONTEXT", "")
    line = next((l for l in context.splitlines() if l.strip().startswith("Coverage")), "")
    return [f"not run, still counted: {m.group(0)}"
            for m in re.finditer(r"\b0 of 0 [^,;]+", line)]


def result_tables(result: str) -> dict[str, list[list[str]]]:
    """RESULT's tables by heading: the line above a pipe table names it.

    Rows exclude the column-header row and the separator.
    """
    tables: dict[str, list[list[str]]] = {}
    lines = result.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if line and not line.startswith("|") and nxt.startswith("|"):
            rows = []
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("|"):
                cells = lines[j].strip().strip("|").split("|")
                rows.append([c.strip() for c in cells])
                j += 1
            tables[line] = [r for r in rows[1:] if not set("".join(r)) <= set("-: ")]
            i = j
        else:
            i += 1
    return tables


_CLOSE_ROW = re.compile(r"\bend \d{4}-\d{2}-\d{2}\b")
_BASE_DATE = re.compile(r"\bbase \d{4}-\d{2}-\d{2}\b")
_SOURCE_LIST = re.compile(r"\[([^\]]*)\]")
_VERDICT = re.compile(r"(PASS|single source|CONFLICT)\s*$")


def close_row_problems(proof: str) -> list[str]:
    """PROOF close rows that break market-context.md -> Closes.

    A close row is any PROOF line with an end date. Each must carry its base
    date -- Rates & FX included -- name the sources of both closes in
    brackets, and end in a verdict; a close with one source is never PASS.
    """
    problems = []
    for line in proof.splitlines():
        if not _CLOSE_ROW.search(line):
            continue
        row = line.strip()
        if not _BASE_DATE.search(line):
            problems.append(f"no base date: {row}")
        lists = _SOURCE_LIST.findall(line)
        if len(lists) < 2:
            problems.append(f"a close without its sources: {row}")
        verdict = _VERDICT.search(line)
        if not verdict:
            problems.append(f"no verdict: {row}")
            continue
        instrument = line.strip().split("  ", 1)[0]
        single = any(_matching_sources(instrument, lst) < 2 for lst in lists)
        if single and verdict.group(1) == "PASS":
            problems.append(f"single source marked PASS: {row}")
        if not single and verdict.group(1) == "single source":
            problems.append(f"two sources marked single source: {row}")
    return problems


_INSTRUMENT = re.compile(r"\((?P<variant>[^,()]+), (?P<ccy>[A-Z]{3})\)$")

# market-context.md -> Closes, headline convention: the four indexes whose
# unlabelled level is taken as the price index. MSCI is left off on purpose
# -- its price and net levels are both quoted without a label -- and so is
# every sector index.
HEADLINE_PRICE = {
    "S&P 500",
    "Dow Jones Industrial Average",
    "Nasdaq Composite",
    "STOXX Europe 600",
}
_UNSTATED = "variant not stated"


def _variant(instrument: str, stated: str) -> str | None:
    """The variant a stated label counts as for this row, or None if none.

    A label that names a variant is that variant. An unlabelled one counts
    as price for a headline index and matches nothing anywhere else.
    """
    if stated != _UNSTATED:
        return stated
    name = _INSTRUMENT.sub("", instrument).strip()
    return "price" if name in HEADLINE_PRICE else None


def _matching_sources(instrument: str, source_list: str) -> int:
    """How many sources in one bracketed list confirm the row's variant."""
    own = _INSTRUMENT.search(instrument)
    own_variant = _variant(instrument, own.group("variant")) if own else None
    count = 0
    for source in (s.strip() for s in source_list.split(";")):
        if not source:
            continue
        if source.endswith(f"({_UNSTATED})"):
            if own is None or _variant(instrument, _UNSTATED) != own_variant:
                continue
        count += 1
    return count


def variant_problems(sections: dict[str, str]) -> list[str]:
    """Index rows whose Instrument cell does not state variant and currency.

    "variant not stated" is a valid variant, but only when CONTEXT's
    Not available line lists it.
    """
    problems = []
    tables = result_tables(sections.get("RESULT", ""))
    not_available = ""
    for line in sections.get("CONTEXT", "").splitlines():
        if line.strip().startswith("Not available"):
            not_available = line
    for name in ("Indexes", "Sectors"):
        for row in tables.get(name, []):
            m = _INSTRUMENT.search(row[0])
            if not m:
                problems.append(f"{name}: no variant and currency in {row[0]!r}")
            elif m.group("variant") == "variant not stated":
                index = row[0][: m.start()].strip()
                if f"{index} variant" not in not_available:
                    problems.append(f"{name}: {index} variant not listed as Not available")
    return problems


def scope_problems(sections: dict[str, str], named: list[str] | None) -> list[str]:
    """RESULT and METHOD against the scope rule.

    ``named`` is the indexes the request named, or None when it named none.
    A named run prints those indexes and nothing else, with no Sectors or
    Rates & FX table; a default run says so.
    """
    problems = []
    method = re.sub(r"[ \t]+", " ", sections.get("METHOD", ""))  # labels are padded
    tables = result_tables(sections.get("RESULT", ""))
    if "Breadth" in tables:
        problems.append("Breadth table printed; it is not part of Market-wide")
    if named is None:
        if "Scope: default set" not in method:
            problems.append("METHOD does not say Scope: default set")
        return problems
    if "Scope: named indexes only" not in method:
        problems.append("METHOD does not say Scope: named indexes only")
    printed = [re.sub(r"\s*\([^()]*\)$", "", r[0]) for r in tables.get("Indexes", [])]
    for extra in sorted(set(printed) - set(named)):
        problems.append(f"index not named in the request: {extra}")
    for missing in sorted(set(named) - set(printed)):
        problems.append(f"named index has no row: {missing}")
    for table in ("Sectors", "Rates & FX"):
        if table in tables:
            problems.append(f"{table} printed on a named-index run")
    return problems


# The phrasings market-context.md -> Contribution (opt-in) gives for asking
# what moved an index. Anything else leaves the table off.
_CONTRIBUTION_ASK = [
    r"\bwhich (?:stocks|names|constituents|companies) "
    r"(?:drove|moved|are driving|were driving)\b",
    r"\bwhat (?:moved|drove|is driving|was driving) the\b",
    r"\b(?:biggest|top|largest) contributors?\b",
]


def contribution_requested(request: str) -> bool:
    return any(re.search(p, request, re.IGNORECASE) for p in _CONTRIBUTION_ASK)


_FIGURE = (
    r"(?P<date{n}>\d{{4}}-\d{{2}}-\d{{2}}) (?P<value{n}>-?[\d,]+(?:\.\d+)?) "
    r"\((?P<variant{n}>[^()]+)\) \[(?P<source{n}>[^\]]+)\]"
)
_CONFLICT = re.compile(
    _FIGURE.format(n=1) + r" vs " + _FIGURE.format(n=2) + r" gap (?P<gap>[\d.]+)%"
)
_WITHHELD = "Not available — sources conflict"


def conflict_problems(sections: dict[str, str]) -> list[str]:
    """Conflicts against market-context.md -> Closes.

    A conflict compares two figures for the row's own variant and currency,
    and only when they are more than 0.5% apart. A row RESULT withholds for
    a conflict still has both figures, their sources and dates printed --
    withheld from the answer is not withheld from the output (rule 5). On a
    run without PROOF that is a `Conflict:` line in METHOD (RULES.md Part
    IV v9); with PROOF, the row's own line there counts too.
    """
    problems = []
    conflicts = {}
    candidates = sections.get("PROOF", "").splitlines() + [
        line.strip().removeprefix("Conflict:")
        for line in sections.get("METHOD", "").splitlines()
        if line.strip().startswith("Conflict:")
    ]
    for line in candidates:
        if not line.rstrip().endswith("CONFLICT"):
            continue
        instrument = line.strip().split("  ", 1)[0]
        conflicts[instrument] = line
        m = _CONFLICT.search(line)
        if not m:
            problems.append(f"{instrument}: CONFLICT without both dated, sourced figures")
            continue
        own = _INSTRUMENT.search(instrument)

        def counts_as(label: str) -> str | None:
            variant, _, ccy = label.rpartition(", ")
            matched = _variant(instrument, variant)
            return f"{matched}, {ccy}" if matched else None

        own_variant = counts_as(f"{own.group('variant')}, {own.group('ccy')}") if own else None
        v1, v2 = counts_as(m.group("variant1")), counts_as(m.group("variant2"))
        if own_variant is None or not v1 == v2 == own_variant:
            problems.append(
                f"{instrument}: compared ({m.group('variant1')}) with "
                f"({m.group('variant2')}) -- two instruments, not a conflict"
            )
            continue
        b = float(m.group("value1").replace(",", ""))
        a = float(m.group("value2").replace(",", ""))
        gap = abs(a - b) / b * 100
        if gap <= 0.5:
            problems.append(f"{instrument}: gap {gap:.2f}% is not over 0.5%")
    for name, table in result_tables(sections.get("RESULT", "")).items():
        for row in table:
            if any(_WITHHELD in cell for cell in row) and row[0] not in conflicts:
                problems.append(f"{name}: {row[0]} withheld with no CONFLICT line in METHOD or PROOF")
    return problems


_MULTI_DAY = "contribution for multi-day periods; last session shown"


def _not_available(sections: dict[str, str]) -> str:
    """CONTEXT's Not available field, continuation lines joined."""
    context = sections.get("CONTEXT", "")
    start = context.find("Not available:")
    if start < 0:
        return ""
    end = context.find("Coverage:", start)
    field = context[start : end if end >= 0 else len(context)]
    return re.sub(r"\s+", " ", field)


def contribution_problems(
    sections: dict[str, str], requested: bool, *, multi_day: bool = False
) -> list[str]:
    """The Contribution table prints exactly when it was asked for.

    Over a period longer than one session it shows the last session only,
    and CONTEXT's Not available field has to say so, not METHOD alone.
    """
    problems = []
    method = re.sub(r"[ \t]+", " ", sections.get("METHOD", ""))  # labels are padded
    printed = "Contribution" in result_tables(sections.get("RESULT", ""))
    if requested:
        if not printed:
            problems.append("Contribution requested and not printed")
        if "Contribution: on (requested)" not in method:
            problems.append("METHOD does not say Contribution: on (requested)")
        if multi_day and _MULTI_DAY not in _not_available(sections):
            problems.append(f"CONTEXT Not available does not say: {_MULTI_DAY}")
    else:
        if printed:
            problems.append("Contribution printed without being requested")
        if "Contribution: off (not requested)" not in method:
            problems.append("METHOD does not say Contribution: off (not requested)")
    return problems

_SIGNED = re.compile(r"^(?:[+-]\d+(?:\.\d+)?|0(?:\.0+)?)$")


def period_cell_problems(sections: dict[str, str]) -> list[str]:
    """Period % and Incl. dist % cells that are not a bare signed number.

    market-context.md -> Performance row: the header carries the unit, so
    the cell is "+1.21", never "1.21%" or "+1.21 %". A withheld cell reads
    Not available and is not a number to check; an Incl. dist % cell may
    also be "—", for a row with no ex-date in its period.
    """
    problems = []
    result = sections.get("RESULT", "")
    for name, table in result_tables(result).items():
        header = _table_header(result, name)
        for label in ("Period %", "Incl. dist %"):
            if label not in header:
                continue
            col = header.index(label)
            for row in table:
                cell = row[col] if col < len(row) else ""
                if cell.startswith("Not available"):
                    continue
                if label == "Incl. dist %" and cell == "—":
                    continue
                if not _SIGNED.match(cell):
                    problems.append(f"{name}: {row[0]} {label} cell {cell!r}")
    return problems


def _table_header(result: str, name: str) -> list[str]:
    lines = [line.strip() for line in result.splitlines()]
    i = lines.index(name)
    return [c.strip() for c in lines[i + 1].strip("|").split("|")]


# --------------------------------------------------------------------------
# Mode C Stocks table (references/etf-brief.md -> Mode C -> Stocks table)
#
# The agent composes this table, so these are the parts of its contract a
# parser can hold a saved run to: cell shapes, the date windows, and that the
# table is present in Mode C at all. Whether a date was really company-
# announced is a sourcing fact no parser can see; PROOF carries that line.
# --------------------------------------------------------------------------

STOCK_COLUMNS = ["Ticker", "Company", "Next earnings", "Latest periodic", "Filed", "8-Ks, 30 days"]
STOCKS_WINDOW_DAYS = 30
_ISO = r"\d{4}-\d{2}-\d{2}"
_ISO_DATE = re.compile(rf"^{_ISO}$")
_PERIODIC = re.compile(rf"^10-[KQ](?:/A)?, period {_ISO}$")
_EIGHT_K = re.compile(rf"^(?P<n>\d+)(?: \((?P<dates>{_ISO}(?:, {_ISO})*)\))?$")
_NA_REASON = re.compile(r"^Not available — \S.*$")


def _date(text: str) -> _dt.date | None:
    try:
        return _dt.date.fromisoformat(text)
    except ValueError:
        return None


def _data_as_of(sections: dict[str, str]) -> _dt.date | None:
    for line in sections.get("CONTEXT", "").splitlines():
        if line.strip().startswith("Data as of"):
            m = re.search(_ISO, line)
            return _date(m.group(0)) if m else None
    return None


def stocks_table_problems(sections: dict[str, str]) -> list[str]:
    """The Stocks table against etf-brief.md -> Mode C -> Stocks table.

    Only a Mode C run has one. A set with no stocks prints the heading and
    ``none``; METHOD then reads ``Stocks window: none``. Every cell is a
    bare fact: a date, a form and period, a count with its dates. A
    withheld cell is ``Not available — `` and its reason.
    """
    result = sections.get("RESULT", "")
    if "(Mode C)" not in result:
        return []
    problems = []
    method = re.sub(r"[ \t]+", " ", sections.get("METHOD", ""))
    lines = [line.strip() for line in result.splitlines()]
    if "Stocks" not in lines:
        # A question-scoped run leaves Stocks out when nobody asked, and says so
        # on METHOD's Tables: line (etf-brief.md -> Which tables a question gets).
        tables_line = re.search(r"^\s*Tables:\s*(.+)$", sections.get("METHOD", ""), re.MULTILINE)
        if tables_line and "Stocks" not in tables_line.group(1).split("(")[0]:
            return []
        return ["Mode C printed no Stocks table and METHOD's Tables: line does not leave it out"]
    tables = result_tables(result)
    rows = tables.get("Stocks")
    if rows is None:
        following = lines[lines.index("Stocks") + 1 : lines.index("Stocks") + 3]
        if "none" not in following:
            problems.append("Stocks heading with neither a table nor `none`")
        if "Stocks window: none" not in method:
            problems.append("METHOD does not say Stocks window: none")
        return problems

    header = _table_header(result, "Stocks")
    if header != STOCK_COLUMNS:
        return [f"Stocks columns {header!r} are not {STOCK_COLUMNS!r}"]
    as_of = _data_as_of(sections)
    if as_of is None:
        problems.append("Stocks table printed but CONTEXT has no Data as of date")
        return problems
    if "Stocks window: 8-Ks filed in the 30 days to" not in method:
        problems.append("METHOD does not state the Stocks window")
    if "Earnings dates: company-announced only" not in method:
        problems.append("METHOD does not say Earnings dates: company-announced only")

    for row in rows:
        who = row[0]
        if len(row) != len(STOCK_COLUMNS):
            problems.append(f"{who}: {len(row)} cells, expected {len(STOCK_COLUMNS)}")
            continue
        _, _, earnings, periodic, filed, eight_k = row

        if earnings.startswith("Not available"):
            if not _NA_REASON.match(earnings):
                problems.append(f"{who}: withheld earnings date has no reason: {earnings!r}")
        elif not _ISO_DATE.match(earnings) or _date(earnings) is None:
            problems.append(f"{who}: earnings date is not an ISO date: {earnings!r}")
        elif _date(earnings) < as_of:
            problems.append(
                f"{who}: earnings date {earnings} is before Data as of {as_of} -- "
                "that is the last report, not the next"
            )

        if periodic.startswith("Not available"):
            if not _NA_REASON.match(periodic):
                problems.append(f"{who}: withheld filing has no reason: {periodic!r}")
        elif not _PERIODIC.match(periodic):
            problems.append(f"{who}: latest periodic is not `10-K|10-Q, period YYYY-MM-DD`: {periodic!r}")
        if not periodic.startswith("Not available"):
            if not _ISO_DATE.match(filed) or _date(filed) is None:
                problems.append(f"{who}: filed is not an ISO date: {filed!r}")
            elif _date(filed) > as_of:
                problems.append(f"{who}: filed {filed} is after Data as of {as_of}")

        if eight_k.startswith("Not available"):
            if not _NA_REASON.match(eight_k):
                problems.append(f"{who}: withheld 8-K cell has no reason: {eight_k!r}")
            continue
        m = _EIGHT_K.match(eight_k)
        if not m:
            problems.append(f"{who}: 8-K cell is not `0` or `n (dates)`: {eight_k!r}")
            continue
        n = int(m.group("n"))
        dates = m.group("dates").split(", ") if m.group("dates") else []
        if n != len(dates):
            problems.append(f"{who}: 8-K count {n} but {len(dates)} dates listed")
        parsed = [_date(d) for d in dates]
        if None in parsed:
            problems.append(f"{who}: an 8-K date is not a real date: {eight_k!r}")
            continue
        if parsed != sorted(parsed, reverse=True):
            problems.append(f"{who}: 8-K dates are not newest first: {eight_k!r}")
        start = as_of - _dt.timedelta(days=STOCKS_WINDOW_DAYS)
        for d in parsed:
            if not start <= d <= as_of:
                problems.append(f"{who}: 8-K {d} is outside the 30 days to {as_of}")
    return problems


# --------------------------------------------------------------------------
# Mode C overlap tables -- etf-brief.md -> Overlap analysis
# --------------------------------------------------------------------------

_PAIR_SPLIT = re.compile(r"\s+[–—·/x×-]\s+")


def _table(result: str, prefix: str) -> tuple[list[str], list[list[str]]] | None:
    """The first RESULT table whose heading starts with `prefix`: header, rows."""
    for name, rows in result_tables(result).items():
        if name.startswith(prefix):
            return _table_header(result, name), rows
    return None


def _provider(index_name: str) -> str:
    return index_name.strip().split()[0].upper() if index_name.strip() else ""


def structural_problems(sections: dict[str, str]) -> list[str]:
    """Cross-provider pairs called disjoint without a country-list fact,
    and `Not available` rows that do not say why.

    A DM index and an EM index from one provider never intersect. From two
    providers they can -- STOXX Europe 600 includes Poland, which MSCI
    classifies as emerging -- so a cross-provider `disjoint` must rest on
    the country lists, and its Index fact must say so.
    """
    result = sections.get("RESULT", "")
    structural = _table(result, "Structural")
    comparison = _table(result, "Comparison")
    if not structural or not comparison:
        return []
    c_header, c_rows = comparison
    if "Ticker" not in c_header or "Index" not in c_header:
        return []
    index_of = {
        row[c_header.index("Ticker")]: row[c_header.index("Index")]
        for row in c_rows if len(row) == len(c_header)
    }
    problems = []
    for row in structural[1]:
        if len(row) < 3:
            continue
        pair, verdict, fact = row[0], row[1].lower(), row[2]
        if verdict.startswith("not available") or fact.lower().startswith("not available"):
            said = f"{row[1]} {fact}".lower()
            if "browser route down" not in said and "returned" not in said:
                problems.append(
                    f"{pair}: Not available without a reason -- say `(browser route down)` "
                    f"or which document returned which status, not {fact!r}"
                )
            continue
        tickers = _PAIR_SPLIT.split(pair)
        if verdict != "disjoint" or len(tickers) != 2:
            continue
        providers = {_provider(index_of.get(t.strip(), "")) for t in tickers}
        if "" in providers or len(providers) < 2:
            continue
        if "countr" not in fact.lower():
            problems.append(
                f"{pair}: indexes from different providers called disjoint without "
                f"the country lists -- {fact!r}"
            )
    return problems


_ONE_FIGURE = re.compile(r"^\d+(?:\.\d+)?%?$")


def holdings_problems(sections: dict[str, str]) -> list[str]:
    """Shared weight is one figure per pair: sum of the smaller weights."""
    table = _table(sections.get("RESULT", ""), "Holdings")
    if not table:
        return []
    header, rows = table
    if not header or "weight" not in header[-1].lower():
        return []
    return [
        f"{row[0]}: shared weight is one figure, not {row[-1]!r}"
        for row in rows
        if row and not _ONE_FIGURE.match(row[-1].strip())
    ]


_PP = re.compile(r"^(?:[+-]\d+\.\d{2}|0\.00)$")
_PCT = re.compile(r"^\d+(?:\.\d+)?$")


def allocation_problems(sections: dict[str, str]) -> list[str]:
    """Allocation: Diff is Weight - Target, as a signed number and nothing else.

    A Target of ``-`` (no target set) carries a Diff of ``-``.

    The difference column is arithmetic; a word in it ("overweight",
    "rebalance") is a reading of the number, which is the user's to make.
    Holding weights, when all are printed, sum to 100 within rounding.
    """
    table = _table(sections.get("RESULT", ""), "Allocation")
    if not table:
        return []
    header, rows = table
    try:
        w, tg, d = (header.index(c) for c in ("Weight (market)", "Target", "Diff (pp)"))
    except ValueError:
        return ["Allocation: needs the columns Weight (market), Target and Diff (pp)"]
    problems: list[str] = []
    held: list[Decimal | None] = []
    for row in rows:
        if len(row) <= d:
            continue
        is_total = len(row) > 1 and row[1] == "total"
        name = row[0] if is_total else row[1]
        weight, target, diff = row[w], row[tg], row[d]
        if weight.startswith("Not available"):
            if not diff.startswith("Not available"):
                problems.append(f"{name}: Diff {diff!r} printed without a weight")
            if not is_total:
                held.append(None)
            continue
        if not is_total:
            held.append(Decimal(weight) if _PCT.match(weight) else None)
        if target == "-":  # no target set (holdings.csv): nothing to subtract
            if diff != "-":
                problems.append(f"{name}: Diff {diff!r} printed without a target")
            continue
        if not (_PP.match(diff) and _PCT.match(weight) and _PCT.match(target)):
            problems.append(f"{name}: Diff {diff!r} is not a signed number of pp")
            continue
        expect = Decimal(weight) - Decimal(target)
        if abs(Decimal(diff) - expect) > Decimal("0.005"):
            problems.append(
                f"{name}: Diff {diff} is not Weight {weight} - Target {target} ({expect:+.2f})"
            )
    if held and None not in held:
        total = sum(held, Decimal(0))
        if abs(total - 100) > Decimal("0.05"):
            problems.append(f"Allocation: holding weights sum to {total:.2f}, not 100")
    return problems


_NUMBER = re.compile(r"^\d+(?:\.\d+)?$")


def lookthrough_problems(sections: dict[str, str]) -> list[str]:
    """Look-through: each Total is the sum of its row's printed cells, and no
    `via <fund>` cell exceeds that fund's own Weight (market) in Allocation --
    a fund cannot put more of a company in the portfolio than the fund is.
    """
    result = sections.get("RESULT", "")
    table = _table(result, "Look-through")
    if not table:
        return []
    header, rows = table
    if not header or header[-1] != "Total":
        return []
    weights: dict[str, Decimal] = {}
    alloc = _table(result, "Allocation")
    if alloc and "Ticker" in alloc[0] and "Weight (market)" in alloc[0]:
        ti, wi = alloc[0].index("Ticker"), alloc[0].index("Weight (market)")
        for row in alloc[1]:
            if len(row) > wi and _NUMBER.match(row[wi]):
                weights[row[ti]] = Decimal(row[wi])
    problems = []
    for row in rows:
        if len(row) != len(header) or not _NUMBER.match(row[-1]):
            continue
        cells = row[1:-1]
        numbers = [Decimal(c) for c in cells if _NUMBER.match(c)]
        total = sum(numbers, Decimal(0))
        if abs(total - Decimal(row[-1])) > Decimal("0.01"):
            problems.append(f"Look-through {row[0]}: Total {row[-1]} is not the sum of its cells ({total})")
        for name, cell in zip(header[1:-1], cells):
            fund = name.split()[1] if name.startswith("via ") and len(name.split()) > 1 else ""
            if fund in weights and _NUMBER.match(cell) and Decimal(cell) > weights[fund]:
                problems.append(
                    f"Look-through {row[0]}: {name} {cell} exceeds {fund}'s own weight {weights[fund]}"
                )
    return problems


def countries_problems(sections: dict[str, str]) -> list[str]:
    """Countries: each row's Total is the sum of its cells, the Total row is the
    column sums, and no country is more than the whole portfolio."""
    return bucket_problems(sections, "Countries")


def sectors_problems(sections: dict[str, str]) -> list[str]:
    return bucket_problems(sections, "Sectors")


def currencies_problems(sections: dict[str, str]) -> list[str]:
    return bucket_problems(sections, "Currencies")


def bucket_problems(sections: dict[str, str], title: str) -> list[str]:
    """A Countries, Sectors or Currencies table (fund_holdings.bucket_table):
    rows re-add to their Total, the Total row is the column sums, and no
    bucket is more than the whole portfolio."""
    table = _table(sections.get("RESULT", ""), title)
    if not table:
        return []
    header, rows = table
    if not header or header[-1] != "Total" or len(header) < 3:
        return []
    problems = []
    body = [r for r in rows if len(r) == len(header) and r[0] != "Total"]
    for row in body:
        if not _NUMBER.match(row[-1]):
            continue
        numbers = [Decimal(c) for c in row[1:-1] if _NUMBER.match(c)]
        if abs(sum(numbers, Decimal(0)) - Decimal(row[-1])) > Decimal("0.01"):
            problems.append(f"{title} {row[0]}: Total {row[-1]} is not the sum of its cells "
                            f"({sum(numbers, Decimal(0))})")
        if Decimal(row[-1]) > 100:
            problems.append(f"{title} {row[0]}: Total {row[-1]} exceeds 100")
    totals = [r for r in rows if r and r[0] == "Total"]
    if totals and len(totals[0]) == len(header):
        for i, name in enumerate(header[1:], start=1):
            col = sum((Decimal(r[i]) for r in body if _NUMBER.match(r[i])), Decimal(0))
            if _NUMBER.match(totals[0][i]) and abs(col - Decimal(totals[0][i])) > Decimal("0.01"):
                problems.append(f"{title} Total row: {name} {totals[0][i]} is not its column "
                                f"sum ({col})")
    return problems


# --------------------------------------------------------------------------
# Brief layout (SKILL.md -> Report layout, RULES.md Part IV v10)
#
# A stock brief and a fund brief print RESULT in a fixed order: an optional
# TL;DR of up to three labelled lines, then Buffett scorecard, any extra
# lens tables, Key numbers, What changed and Red flags, then detail tables.
# --------------------------------------------------------------------------

BRIEF_MODES = ("Stock brief", "Fund brief (Mode A)")
BRIEF_TABLES = ["Buffett scorecard", "Key numbers", "What changed", "Red flags"]
TLDR_LABELS = ["Scorecard:", "Changed:", "Red flags:"]
SCORECARD_RESULTS = {"Met", "Not met", "Not available"}
# references/lenses.md -> Which lens, by name
LENS_TABLES = {
    "Graham lens", "Lynch lens", "Greenblatt lens", "Piotroski lens",
    "Terry Smith lens", "Munger lens", "Bogle lens",
}
FUND_LENSES = {"Bogle lens"}
RED_FLAG_STATUS = {
    "Filing risk": {"New", "Removed", "Reworded", "None", "Not checkable"},
    "Thesis": {"Reached", "Not reached", "Not checkable", "None on file"},
}


def _mode_line(result: str) -> str | None:
    for line in result.splitlines():
        if line.strip():
            line = line.strip()
            return line[len("Mode:"):].strip() if line.startswith("Mode:") else None
    return None


def is_brief(sections: dict[str, str]) -> bool:
    mode = _mode_line(sections.get("RESULT", "")) or ""
    return any(m in mode.split(" + ") for m in BRIEF_MODES)


def _tldr_lines(result: str) -> list[str]:
    """Non-empty lines between the Mode line and the first table's heading."""
    lines = [ln.strip() for ln in result.splitlines()]
    out: list[str] = []
    seen_mode = False
    for i, line in enumerate(lines):
        if not seen_mode:
            seen_mode = line.startswith("Mode:")
            continue
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if line and nxt.startswith("|"):
            break
        if line:
            out.append(line)
    return out


def brief_layout_problems(sections: dict[str, str]) -> list[str]:
    """A brief's TL;DR and table order against SKILL.md -> Report layout."""
    if not is_brief(sections):
        return []
    result = sections.get("RESULT", "")
    problems: list[str] = []

    tldr = _tldr_lines(result)
    if len(tldr) > 3:
        problems.append(f"TL;DR has {len(tldr)} lines, at most 3 allowed")
    labels = []
    for line in tldr:
        label = next((lab for lab in TLDR_LABELS if line.startswith(lab)), None)
        if label is None:
            problems.append(f"TL;DR line without a Scorecard:/Changed:/Red flags: label: {line!r}")
        else:
            labels.append(label)
    if labels != [lab for lab in TLDR_LABELS if lab in labels]:
        problems.append(f"TL;DR lines out of order: {labels}")

    names = list(result_tables(result))
    missing = [n for n in BRIEF_TABLES if n not in names]
    if missing:
        problems.append(f"brief is missing tables: {missing}")
        return problems
    if names[0] != "Buffett scorecard":
        problems.append(f"first brief table is {names[0]!r}, not 'Buffett scorecard'")
    positions = [names.index(n) for n in BRIEF_TABLES]
    if positions != sorted(positions):
        problems.append(f"brief tables out of order: {[n for n in names if n in BRIEF_TABLES]}")
    between = names[names.index("Buffett scorecard") + 1 : names.index("Key numbers")]
    for name in between:
        if not name.endswith(" lens"):
            problems.append(f"{name!r} sits between the scorecard and Key numbers; only lens tables may")
        elif name not in LENS_TABLES:
            problems.append(f"{name!r} is not a lens references/lenses.md defines")
    fund = "Fund brief (Mode A)" in (_mode_line(result) or "")
    for name in between:
        if name in LENS_TABLES and (name in FUND_LENSES) != fund:
            kind = "funds" if name in FUND_LENSES else "stocks"
            problems.append(f"{name} applies to {kind} only")
    for name in names[names.index("Key numbers") + 1 : names.index("Red flags")]:
        if name != "What changed":
            problems.append(f"{name!r} sits before Red flags; detail tables print after it")

    for name in ["Buffett scorecard"] + [n for n in names if n.endswith(" lens")]:
        header = _table_header(result, name)
        if "Result" not in header:
            problems.append(f"{name} has no Result column")
            continue
        col = header.index("Result")
        for row in result_tables(result)[name]:
            cell = row[col] if col < len(row) else ""
            if cell not in SCORECARD_RESULTS:
                problems.append(f"{name} Result {cell!r} is not Met / Not met / Not available")

    header = _table_header(result, "Red flags")
    if "Type" in header and "Status" in header:
        ti, si = header.index("Type"), header.index("Status")
        for row in result_tables(result)["Red flags"]:
            kind = row[ti] if ti < len(row) else ""
            status = row[si] if si < len(row) else ""
            if kind not in RED_FLAG_STATUS:
                problems.append(f"Red flags type {kind!r} is not Filing risk or Thesis")
            elif status not in RED_FLAG_STATUS[kind]:
                problems.append(f"Red flags {kind} status {status!r} is not one of {sorted(RED_FLAG_STATUS[kind])}")
    else:
        problems.append("Red flags has no Type and Status columns")
    return problems


def sources_summary_problems(sections: dict[str, str]) -> list[str]:
    """The one-line SOURCES of RULES.md Part IV v11.

    Printed only when PROOF is not; never beside the full rows; every count
    above zero backed by its METHOD line.
    """
    body = [line.strip() for line in sections.get("SOURCES", "").splitlines() if line.strip()]
    summary = [line for line in body if re.match(r"^\d+ documents? · ", line)]
    if not summary:
        return []
    problems: list[str] = []
    if len(summary) > 1:
        problems.append("SOURCES has more than one summary line")
    if any(line.startswith(("|", "- ")) for line in body):
        problems.append("SOURCES prints the summary line and rows; it is one or the other")
    if "PROOF" in sections:
        problems.append("PROOF printed, so SOURCES must print in full, not as its summary line")
    m = _SOURCES_SUMMARY.match(summary[0])
    if not m:
        problems.append(f"SOURCES summary line is not in the RULES.md Part IV shape: {summary[0]!r}")
        return problems
    if int(m["n"]) == 0:
        problems.append("SOURCES summary counts 0 documents; a run that fetched nothing prints the export-only line")
    if m["first"] > m["last"]:
        problems.append(f"SOURCES summary dates run backwards: {m['first']} to {m['last']}")
    method = sections.get("METHOD", "")
    if int(m["stale"]) and not re.search(r"stale", method, re.IGNORECASE):
        problems.append(f"SOURCES counts {m['stale']} stale but METHOD names no stale source")
    if int(m["unverified"]) and not re.search(r"^\s*Confirmation:", method, re.MULTILINE):
        problems.append(f"SOURCES counts {m['unverified']} unverified but METHOD has no Confirmation: line")
    return problems


# Pages that restate an investor's rules. references/lenses.md is the
# definition, so a brief citing one of these fetched its rules from the web
# (the old build did, on 2026-10-11, for Graham, Lynch and Bogle).
LENS_RESTATEMENT_HOSTS = (
    "wikipedia.org", "validea.com", "bogleheads.org", "investopedia.com",
    "einvestingforbeginners.com", "drwealth.com", "gurufocus.com",
)


# references/buffett.md -> Buffett notes
BUFFETT_NOTE_PRINCIPLES = {"Circle of competence", "Mr. Market", "Moat", "Index funds"}
CHECKLIST_MODE = "Buffett checklist"
CHECKLIST_TABLES = ["Four filters", "Buffett scorecard", "Key numbers", "Your position", "Red flags"]
CHECKLIST_TLDR = ["Filters:", "Position:", "Thesis:"]
FILTERS = ["1. Understand it", "2. Lasting economics", "3. Able, trustworthy management",
           "4. Sensible price"]
FILTER_ANSWERS = {
    "1. Understand it": {"Yes", "Not sure", "No"},
    "2. Lasting economics": SCORECARD_RESULTS,
    "3. Able, trustworthy management": {"Yes", "Not sure", "No"},
    "4. Sensible price": SCORECARD_RESULTS,
}


def is_checklist(sections: dict[str, str]) -> bool:
    return CHECKLIST_MODE in (_mode_line(sections.get("RESULT", "")) or "").split(" + ")


def buffett_notes_problems(sections: dict[str, str]) -> list[str]:
    """Buffett notes: right after Red flags, at most two, known principles,
    each with its letter linked."""
    result = sections.get("RESULT", "")
    tables = result_tables(result)
    if "Buffett notes" not in tables:
        return []
    problems: list[str] = []
    names = list(tables)
    if "Red flags" in names and names.index("Buffett notes") != names.index("Red flags") + 1:
        problems.append("Buffett notes must come right after Red flags")
    rows = tables["Buffett notes"]
    if len(rows) > 2:
        problems.append(f"Buffett notes has {len(rows)} rows, at most 2")
    for row in rows:
        if not row or row[0] not in BUFFETT_NOTE_PRINCIPLES:
            problems.append(f"Buffett note {row[0] if row else ''!r} is not a principle "
                            "references/buffett.md defines")
        if "berkshirehathaway.com" not in (row[-1] if row else ""):
            problems.append(f"Buffett note {row[0] if row else ''!r} does not link its letter")
    return problems


def checklist_problems(sections: dict[str, str]) -> list[str]:
    """A Buffett checklist against references/checklist.md."""
    if not is_checklist(sections):
        return []
    result = sections.get("RESULT", "")
    problems: list[str] = []
    tldr = _tldr_lines(result)
    if len(tldr) > 3:
        problems.append(f"TL;DR has {len(tldr)} lines, at most 3 allowed")
    for line in tldr:
        if not any(line.startswith(lab) for lab in CHECKLIST_TLDR):
            problems.append(f"TL;DR line without a Filters:/Position:/Thesis: label: {line!r}")
    tables = result_tables(result)
    names = [n for n in tables if n in CHECKLIST_TABLES]
    missing = [n for n in CHECKLIST_TABLES if n not in tables]
    if missing:
        problems.append(f"checklist is missing tables: {missing}")
        return problems
    if names != CHECKLIST_TABLES:
        problems.append(f"checklist tables out of order: {names}")
    rows = tables["Four filters"]
    if [r[0] for r in rows] != FILTERS:
        problems.append(f"Four filters rows are {[r[0] for r in rows]}, not {FILTERS}")
    header = _table_header(result, "Four filters")
    if "Answer" in header:
        col = header.index("Answer")
        for r in rows:
            allowed = FILTER_ANSWERS.get(r[0], set())
            if col < len(r) and r[col] not in allowed:
                problems.append(f"Four filters {r[0]}: answer {r[col]!r} is not one of {sorted(allowed)}")
    return problems


def lens_source_problems(sections: dict[str, str]) -> list[str]:
    """A brief's SOURCES must not cite a page restating a lens's rules."""
    if not is_brief(sections):
        return []
    return [f"SOURCES cites {host}: lens rules come from references/lenses.md, not the web"
            for host in LENS_RESTATEMENT_HOSTS
            if host in sections.get("SOURCES", "")]


def output_problems(text: str) -> list[str]:
    """Every contract check that applies to a composed output, in one list.

    What scripts/check_output.py runs on a draft before it is printed.
    """
    order = section_order(text)
    problems = []
    if not order or order[0] != "STATUS":
        problems.append("STATUS is not the first section")
    if order != [s for s in SECTIONS if s in order]:
        problems.append(f"sections out of order: {order}")
    sections = split_sections(text)
    problems += status_problems(sections)
    if not re.search(r"^\s*Build:\s*\S", sections.get("METHOD", ""), re.MULTILINE):
        problems.append("METHOD has no Build: line (the text of BUILD in the skill folder)")
    problems += [f"outside the sections: {line}" for line in text_outside_sections(text, subject_line=True)]
    problems += [f"banned: {hit}" for hit in banned_hits(text)]
    problems += [f"placeholder time: {hit}" for hit in placeholder_times(text)]
    problems += [f"source row without a URL: {row}" for row in sources_without_url(text)]
    for check in (coverage_problems, variant_problems, conflict_problems,
                  period_cell_problems, stocks_table_problems,
                  structural_problems, holdings_problems, allocation_problems,
                  lookthrough_problems, countries_problems,
                  sectors_problems, currencies_problems,
                  brief_layout_problems, sources_summary_problems,
                  lens_source_problems, buffett_notes_problems, checklist_problems):
        problems += check(sections)
    return problems
