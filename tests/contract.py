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
    mode = next((ln for ln in sections.get("RESULT", "").splitlines() if ln.startswith("Mode:")), "")
    # Market-wide's Sectors rows are sector indexes; Mode C's Sectors table,
    # under the same bare heading when it is Not available, is the portfolio's.
    names = ("Indexes", "Sectors") if "Market-wide" in mode or not mode else ("Indexes",)
    for name in names:
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


HIDDEN_BETS_HEADER = ["Company", "Through", "Largest part", "Total", "Added by the others"]
_ROUTE = re.compile(r"^(?P<label>Direct|via \S+) (?P<value>\d+\.\d{2})$")


def hidden_bets_problems(sections: dict[str, str]) -> list[str]:
    """Hidden bets: every row reached through two or more holdings, its routes
    summing to its Total, Largest part being the largest route, Added by the
    others = Total - Largest part, the Total matching Look-through's for the
    same company, and the rows in descending Total.
    """
    result = sections.get("RESULT", "")
    table = _table(result, "Hidden bets")
    if not table:
        return []
    header, rows = table
    if header != HIDDEN_BETS_HEADER:
        if header and header[-1] == "Total" and len(rows) == 1 and "Not available" in " ".join(rows[0]):
            return []
        return [f"Hidden bets header is {header}, not {HIDDEN_BETS_HEADER}"]
    lookthrough: dict[str, str] = {}
    lt = _table(result, "Look-through")
    if lt and lt[0] and lt[0][-1] == "Total":
        lookthrough = {r[0]: r[-1] for r in lt[1] if r}
    problems, last = [], None
    for row in rows:
        if len(row) != len(header):
            problems.append(f"Hidden bets row has {len(row)} cells: {row}")
            continue
        company, through, largest, total, added = row
        if company == "none":
            continue
        routes = [_ROUTE.match(p.strip()) for p in through.split(" · ")]
        if not all(routes) or len(routes) < 2:
            problems.append(f"Hidden bets {company}: Through must be two or more 'Direct x' or "
                            f"'via TICKER x' parts, not {through!r}")
            continue
        values = [Decimal(m["value"]) for m in routes]
        if not _NUMBER.match(total) or not _NUMBER.match(added):
            problems.append(f"Hidden bets {company}: Total and Added by the others must be numbers")
            continue
        if sum(values, Decimal(0)) != Decimal(total):
            problems.append(f"Hidden bets {company}: Total {total} is not the sum of its routes "
                            f"({sum(values, Decimal(0))})")
        lm = _ROUTE.match(largest.strip())
        if not lm or Decimal(lm["value"]) != max(values):
            problems.append(f"Hidden bets {company}: Largest part {largest} is not its largest route")
        elif Decimal(total) - Decimal(lm["value"]) != Decimal(added):
            problems.append(f"Hidden bets {company}: Added by the others {added} is not "
                            f"Total - Largest part ({Decimal(total) - Decimal(lm['value'])})")
        if company in lookthrough and lookthrough[company] != total:
            problems.append(f"Hidden bets {company}: Total {total} differs from Look-through's "
                            f"{lookthrough[company]}")
        if last is not None and Decimal(total) > last:
            problems.append(f"Hidden bets {company}: rows are not in descending Total")
        last = Decimal(total)
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


# --------------------------------------------------------------------------
# Quick brief (SKILL.md -> Report layout -> Quick brief, RULES.md v13)
#
# The Scorecard: TL;DR line, the Buffett scorecard, and only the lens tables
# the request named. METHOD names what was not built and offers the rest.
# --------------------------------------------------------------------------

QUICK_MODES = ("Stock brief (quick)", "Fund brief (Mode A, quick)")


def is_quick(sections: dict[str, str]) -> bool:
    mode = _mode_line(sections.get("RESULT", "")) or ""
    return any(m in mode.split(" + ") for m in QUICK_MODES)


def quick_brief_problems(sections: dict[str, str]) -> list[str]:
    if not is_quick(sections):
        return []
    result = sections.get("RESULT", "")
    method = sections.get("METHOD", "")
    problems: list[str] = []
    tldr = _tldr_lines(result)
    if len(tldr) > 1 or any(not line.startswith("Scorecard:") for line in tldr):
        problems.append(f"quick brief TL;DR is the Scorecard: line only, not {tldr}")
    names = list(result_tables(result))
    if not names or names[0] != "Buffett scorecard":
        problems.append(f"first quick brief table is {names[0] if names else None!r}, "
                        "not 'Buffett scorecard'")
    fund = "Fund brief (Mode A, quick)" in (_mode_line(result) or "")
    for name in names[1:]:
        if not name.endswith(" lens"):
            problems.append(f"{name!r} in a quick brief; it prints the scorecard and named lenses only")
        elif name not in LENS_TABLES:
            problems.append(f"{name!r} is not a lens references/lenses.md defines")
        elif (name in FUND_LENSES) != fund:
            kind = "funds" if name in FUND_LENSES else "stocks"
            problems.append(f"{name} applies to {kind} only")
    for name in [n for n in names if n == "Buffett scorecard" or n.endswith(" lens")]:
        header = _table_header(result, name)
        if "Result" not in header:
            problems.append(f"{name} has no Result column")
            continue
        col = header.index("Result")
        for row in result_tables(result)[name]:
            cell = row[col] if col < len(row) else ""
            if cell not in SCORECARD_RESULTS:
                problems.append(f"{name} Result {cell!r} is not Met / Not met / Not available")
    if not re.search(r"^\s*Quick brief:\s*\S", method, re.MULTILINE):
        problems.append("quick brief METHOD has no Quick brief: line naming what was not built")
    if not re.search(r"^\s*Next:.*full brief", method, re.MULTILINE | re.IGNORECASE):
        problems.append("quick brief METHOD has no Next: line offering the full brief")
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
    if not (is_brief(sections) or is_quick(sections)):
        return []
    return [f"SOURCES cites {host}: lens rules come from references/lenses.md, not the web"
            for host in LENS_RESTATEMENT_HOSTS
            if host in sections.get("SOURCES", "")]


# --------------------------------------------------------------------------
# Price move (references/price-move.md, RULES.md rule 7 v14)
#
# The one mode that prints reported reasons. These checks hold the narrow
# allowance narrow: reasons only in their own table, each attributed, dated
# inside its window and short; events typed and dated; contributions that
# add up; and no causal wording anywhere else in RESULT.
# --------------------------------------------------------------------------

PRICE_MOVE_MODE = "Price move"
PRICE_MOVE_TABLES = ["Move", "Contribution", "Dated events", "Reported reasons"]
PRICE_MOVE_REQUIRED = ["Move", "Dated events", "Reported reasons"]
CONTRIBUTION_HEADER = ["Holding", "Weight %", "Move %", "Contribution pp"]
EVENTS_HEADER = ["Date", "About", "Event", "Source"]
REASONS_HEADER = ["About", "Published", "Source", "Reason as reported", "Premise"]
EVENT_TYPES = ("Results release:", "Filing:", "Company release:", "Ex-dividend:",
               "Index change:", "Rate decision:", "Fund notice:")
PREMISE_VALUES = {"Matches primary source", "Not in primary sources", "Not checkable"}
REASON_VERBS = ("Says ", "Reports ", "Writes ", "States ")
REASON_MAX_WORDS = 30
REASONS_PER_ABOUT = 5
NOT_A_SOURCE = {"", "—", "-", "analysts", "reports", "media", "news", "the market",
                "market", "holdnote", "claude", "unknown", "various"}
PRICE_MOVE_METHOD = ["Benchmark:", "Contribution:", "Events window:", "Reasons window:",
                     "Reasons rule:", "Reasons searched:"]
# Holdnote's own reason, in the shapes it usually takes. Outside the
# Reported reasons table none of these may appear in RESULT.
CAUSAL_WORDING = [
    r"\bbecause\b", r"\bdue to\b", r"\bdriven by\b", r"\bthanks to\b",
    r"\bas a result of\b", r"\bin response to\b", r"\bweighed on\b",
    r"\bcaused\b", r"\btriggered\b", r"\bsparked\b", r"\bfuel(?:l)?ed\b",
    r"\bled to\b", r"\bsent (?:shares|the stock|the fund|it)\b",
    r"\bon (?:fears|hopes|worries|concerns|optimism|pessimism)\b",
    r"\bthe reason (?:for|behind)\b",
]
# The user's money never enters a Price move (rule 11).
USER_POSITION = re.compile(
    r"\byour (?:position|holding|shares|stake|portfolio)\b|\byou (?:lost|gained|own)\b",
    re.IGNORECASE,
)
_PERIOD_BOUNDS = re.compile(rf"({_ISO}) close to ({_ISO}) close")
# A reason for a price Move never printed (references/price-move.md).
OFF_SESSION = re.compile(r"\b(?:pre-?market|after-?hours|extended[- ]hours|futures)\b",
                         re.IGNORECASE)


def _context_field(sections: dict[str, str], name: str) -> str:
    """A CONTEXT field's value, its continuation lines joined."""
    lines = sections.get("CONTEXT", "").splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{name}:"):
            value = [line.split(":", 1)[1]]
            for nxt in lines[i + 1:]:
                if nxt.startswith((" ", "\t")) and not re.match(r"^\s*[A-Z][\w /]*:\s", nxt):
                    value.append(nxt)
                else:
                    break
            return re.sub(r"\s+", " ", " ".join(value)).strip()
    return ""


def is_price_move(sections: dict[str, str]) -> bool:
    mode = _mode_line(sections.get("RESULT", "")) or ""
    return PRICE_MOVE_MODE in mode.split(" + ")


def _named(result: str, prefix: str) -> str | None:
    """The full heading of the first RESULT table whose heading starts with prefix."""
    return next((n for n in result_tables(result) if n.split(" (")[0] == prefix), None)


def _float(cell: str) -> float | None:
    try:
        return float(cell.replace(",", "").replace("+", ""))
    except ValueError:
        return None


def _without_table(result: str, heading: str) -> str:
    """RESULT with one table (heading line and its pipe rows) cut out."""
    lines = result.splitlines()
    out: list[str] = []
    skipping = False
    for line in lines:
        if line.strip() == heading:
            skipping = True
            continue
        if skipping and line.strip().startswith("|"):
            continue
        skipping = False
        out.append(line)
    return "\n".join(out)


def reported_reasons_elsewhere(sections: dict[str, str]) -> list[str]:
    """Rule 7 v14: only a Price move prints reported reasons."""
    result = sections.get("RESULT", "")
    if is_price_move(sections) or _named(result, "Reported reasons") is None:
        return []
    return ["Reported reasons printed outside a Price move (RULES.md rule 7)"]


def price_move_problems(sections: dict[str, str]) -> list[str]:
    """A Price move against references/price-move.md."""
    if not is_price_move(sections):
        return []
    result = sections.get("RESULT", "")
    method = sections.get("METHOD", "")
    problems: list[str] = []

    # Windows come from Latest period's base and end sessions.
    latest = _context_field(sections, "Latest period")
    bounds = _PERIOD_BOUNDS.search(latest)
    base = end = None
    if bounds:
        base, end = _date(bounds.group(1)), _date(bounds.group(2))
    else:
        problems.append("Latest period is not 'YYYY-MM-DD close to YYYY-MM-DD close'")

    # Tables: the four, in order, the three required ones present.
    names = [n.split(" (")[0] for n in result_tables(result)]
    for name in names:
        if name not in PRICE_MOVE_TABLES:
            problems.append(f"{name!r} in a Price move; it prints Move, Contribution, "
                            "Dated events and Reported reasons only")
    known = [n for n in names if n in PRICE_MOVE_TABLES]
    if known != [n for n in PRICE_MOVE_TABLES if n in known]:
        problems.append(f"Price move tables out of order: {known}")
    missing = [n for n in PRICE_MOVE_REQUIRED if n not in names]
    if missing:
        problems.append(f"Price move is missing tables: {missing}")

    for label in PRICE_MOVE_METHOD:
        if not re.search(rf"^\s*{re.escape(label)}\s*\S", method, re.MULTILINE):
            problems.append(f"Price move METHOD has no {label} line")

    # Move: the instrument first, every other row a benchmark.
    fund_move = None
    move = _named(result, "Move")
    if move:
        header = _table_header(result, move)
        rows = result_tables(result)[move]
        if not rows:
            problems.append("Move has no rows")
        elif rows[0][0].startswith("Benchmark"):
            problems.append("Move's first row is the benchmark; the instrument comes first")
        else:
            if "Period %" in header:
                fund_move = _float(rows[0][header.index("Period %")])
            for row in rows[1:]:
                if not row[0].startswith("Benchmark: "):
                    problems.append(f"Move row {row[0]!r} is neither the instrument nor "
                                    "a `Benchmark: ` row")

    # Contribution: weight x move / 100, sorted, and a residual that adds up.
    contrib = _named(result, "Contribution")
    if contrib:
        header = _table_header(result, contrib)
        if header != CONTRIBUTION_HEADER:
            problems.append(f"Contribution header is {header}, not {CONTRIBUTION_HEADER}")
        else:
            rows = result_tables(result)[contrib]
            body = [r for r in rows if r[0] != "Rest of fund"]
            rest = next((r for r in rows if r[0] == "Rest of fund"), None)
            values: list[float] = []
            gap = False
            for r in body:
                w, m, c = (_float(x) for x in r[1:4])
                if c is None:
                    gap = True
                    continue
                values.append(c)
                if w is not None and m is not None and abs(w * m / 100 - c) > 0.01:
                    problems.append(f"Contribution {r[0]}: {r[1]} x {r[2]} / 100 is "
                                    f"{w * m / 100:.4f}, printed {r[3]}")
            if [abs(v) for v in values] != sorted((abs(v) for v in values), reverse=True):
                problems.append("Contribution rows are not sorted by size of contribution")
            if rest is None:
                problems.append("Contribution has no Rest of fund row")
            else:
                cell = rest[3]
                if gap:
                    if not cell.startswith("Not available"):
                        problems.append("Rest of fund must be Not available when a "
                                        "contribution is")
                elif fund_move is not None:
                    want = fund_move - sum(values)
                    got = _float(cell)
                    if got is None or abs(want - got) > 0.01 + 0.005 * len(values):
                        problems.append(f"Rest of fund is {cell}, but {fund_move} - "
                                        f"{' - '.join(f'{v}' for v in values)} = {want:.2f}")

    # Dated events: typed, dated inside the window, or the one None row.
    events = _named(result, "Dated events")
    if events:
        header = _table_header(result, events)
        if header != EVENTS_HEADER:
            problems.append(f"Dated events header is {header}, not {EVENTS_HEADER}")
        else:
            for date, _about, event, source in (r[:4] for r in result_tables(result)[events]):
                if event == "None in window":
                    if date != "—" or not source.startswith("checked:"):
                        problems.append("Dated events None row is `| — | <About> | None in "
                                        "window | checked: <sources> |`")
                    continue
                if not event.startswith(EVENT_TYPES):
                    problems.append(f"Dated events event {event!r} does not start with "
                                    f"one of {list(EVENT_TYPES)}")
                day = _date(date)
                if day is None:
                    problems.append(f"Dated events date {date!r} is not YYYY-MM-DD")
                elif base and end and not base <= day <= end:
                    problems.append(f"Dated events {date} is outside the window "
                                    f"{base} to {end}")

    # Reported reasons: attributed, dated, short, a known Premise, at most 5.
    reasons = _named(result, "Reported reasons")
    if reasons:
        header = _table_header(result, reasons)
        if header != REASONS_HEADER:
            problems.append(f"Reported reasons header is {header}, not {REASONS_HEADER}")
        else:
            per_about: dict[str, int] = {}
            dates: list[_dt.date] = []
            for about, published, source, reason, premise in (
                    r[:5] for r in result_tables(result)[reasons]):
                if reason.startswith("None found"):
                    if (published, source, premise) != ("—", "—", "—"):
                        problems.append("Reported reasons None row is `| <About> | — | — | "
                                        "None found — ... | — |`")
                    continue
                per_about[about] = per_about.get(about, 0) + 1
                if source.strip().lower() in NOT_A_SOURCE:
                    problems.append(f"Reported reason with no named source: {source!r}")
                if not reason.startswith(REASON_VERBS):
                    problems.append(f"Reported reason does not open with Says/Reports/"
                                    f"Writes/States: {reason!r}")
                if len(reason.split()) >= REASON_MAX_WORDS:
                    problems.append(f"Reported reason is {len(reason.split())} words; "
                                    f"under {REASON_MAX_WORDS}")
                if OFF_SESSION.search(reason):
                    problems.append(f"Reported reason is about a move outside the session "
                                    f"closes: {reason!r}")
                if premise not in PREMISE_VALUES:
                    problems.append(f"Premise {premise!r} is not one of {sorted(PREMISE_VALUES)}")
                day = _date(published)
                if day is None:
                    problems.append(f"Reported reason published {published!r} is not YYYY-MM-DD")
                    continue
                dates.append(day)
                if base and end and not base <= day <= end + _dt.timedelta(days=1):
                    problems.append(f"Reported reason published {published} is outside "
                                    f"{base} to {end + _dt.timedelta(days=1)}")
            for about, n in per_about.items():
                if n > REASONS_PER_ABOUT:
                    problems.append(f"{n} reported reasons for {about}; at most "
                                    f"{REASONS_PER_ABOUT}")
            if dates != sorted(dates):
                problems.append("Reported reasons are not in order of publication date")

    # No reason of Holdnote's own anywhere else in RESULT.
    outside = _without_table(result, reasons) if reasons else result
    for pat in CAUSAL_WORDING:
        for m in re.finditer(pat, outside, re.IGNORECASE):
            snippet = outside[max(0, m.start() - 30): m.end() + 30].replace("\n", " ")
            problems.append(f"causal wording outside Reported reasons: {snippet!r}")
    for m in USER_POSITION.finditer(result):
        problems.append(f"the user's position in a Price move: {m.group(0)!r}")
    return problems


# --------------------------------------------------------------------------
# Stock brief metric tables (references/stock-brief.md -> Margins, Expense
# ratios, Returns, Growth). What a parser can hold: every cell a figure or a
# reasoned Not available, and the bounds a ratio cannot cross.
# --------------------------------------------------------------------------

METRIC_TABLES = ("Margins", "Expense ratios", "Returns", "Growth")
_METRIC_CELL = re.compile(r"^(?:[+-]?\d[\d,]*(?:\.\d+)?%?|—|Not available — \S.*)$")
# Ratios that cannot exceed 100% of revenue, or go below zero, whatever the year.
_AT_MOST_100 = {"Gross margin"}
_NOT_NEGATIVE = {"Effective tax rate", "R&D", "SG&A", "Stock-based compensation", "Capex",
                 "Asset turnover"}


def metric_table_problems(sections: dict[str, str]) -> list[str]:
    if not is_brief(sections):
        return []
    result = sections.get("RESULT", "")
    problems: list[str] = []
    for name in result_tables(result):
        table = name.split(" (")[0]
        if table not in METRIC_TABLES:
            continue
        for row in result_tables(result)[name]:
            metric, cells = row[0], row[1:]
            for cell in cells:
                if not _METRIC_CELL.match(cell):
                    problems.append(f"{table} {metric}: cell {cell!r} is not a figure, — "
                                    "or `Not available — reason`")
                    continue
                value = _float(cell.rstrip("%")) if cell[:1].isdigit() or cell[:1] in "+-" else None
                if value is None:
                    continue
                if table == "Growth" and not cell[:1] in "+-" and value != 0:
                    problems.append(f"Growth {metric} {cell} is unsigned; print +{cell}")
                if metric in _AT_MOST_100 and value > 100:
                    problems.append(f"{table} {metric} {cell} is over 100%: a parse error")
                if metric in _NOT_NEGATIVE and value < 0:
                    problems.append(f"{table} {metric} {cell} is negative; a loss year is "
                                    "`Not available — pretax loss`")
    return problems


# --------------------------------------------------------------------------
# Shared by Earnings recap and Head-to-head: numbers as printed.
# --------------------------------------------------------------------------

_NUM_CELL = re.compile(
    r"^(?P<ccy>[A-Z]{3} )?(?P<sign>[+\-−]?)(?P<num>\d[\d,]*(?:\.\d+)?)"
    r"(?P<unit>%|pp|m|bn|/7)?(?: \(.*\))?$"
)


def _num(cell: str) -> tuple[float, str, str] | None:
    """A printed figure as (value, unit, currency); None for anything else."""
    m = _NUM_CELL.match(cell.strip())
    if not m:
        return None
    value = float(m["num"].replace(",", ""))
    if m["sign"] in ("-", "−"):
        value = -value
    return value, m["unit"] or "", (m["ccy"] or "").strip()


def _decimals(cell: str) -> int:
    m = re.search(r"\.(\d+)", cell)
    return len(m.group(1)) if m else 0


def _tolerance(*cells: str) -> float:
    """Half a unit in the last printed place of the coarsest cell, plus slack."""
    places = min(_decimals(c) for c in cells)
    return 0.5 * 10 ** -places + 1e-9


def _pct_change(new: float, old: float) -> float:
    return (new - old) / abs(old) * 100


def _change_problems(table: str, metric: str, new_cell: str, old_cell: str,
                     change: str) -> list[str]:
    """A QoQ / YoY cell against the two values beside it."""
    if change in ("—", "-") or change.startswith("Not available"):
        return []
    new, old, ch = _num(new_cell), _num(old_cell), _num(change)
    if not re.match(r"^[+\-−]\d+(?:\.\d+)?(?:%|pp)$", change):
        return [f"{table} {metric}: change {change!r} is not a signed % or pp, — or "
                "`Not available — reason`"]
    if new is None or old is None or ch is None:
        return []
    if new[1] == "%" and old[1] == "%":
        if ch[1] != "pp":
            return [f"{table} {metric}: a change of two margins is in pp, not {change!r}"]
        want = new[0] - old[0]
        tol = _tolerance(new_cell, old_cell) * 2 + _tolerance(change)
    else:
        if ch[1] != "%":
            return [f"{table} {metric}: a change of two amounts is in %, not {change!r}"]
        if old[0] <= 0:
            return [f"{table} {metric}: a change from a zero or negative base is —, "
                    f"not {change!r}"]
        want = _pct_change(new[0], old[0])
        rel = 10 ** -min(_decimals(new_cell), _decimals(old_cell)) / abs(old[0]) * 100
        tol = rel + _tolerance(change)
    if abs(want - ch[0]) > tol:
        return [f"{table} {metric}: {new_cell} against {old_cell} is {want:+.2f}, "
                f"printed {change}"]
    return []


def _numbers_in(text: str) -> set[str]:
    return {n.replace(",", "") for n in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}


def _tldr_numbers_problems(result: str, lines: list[str], labels: tuple[str, ...]) -> list[str]:
    """Every figure on these TL;DR lines is printed again in a table."""
    tables = result_tables(result)
    printed: set[str] = set()
    for name, rows in tables.items():
        printed |= _numbers_in(name)
        for row in rows:
            printed |= _numbers_in(" ".join(row))
    problems = []
    for line in lines:
        if not line.startswith(labels):
            continue
        for n in _numbers_in(line.split(":", 1)[1]):
            if n not in printed:
                problems.append(f"TL;DR figure {n} is in no table below: {line!r}")
    return problems


def _tables_by_prefix(result: str) -> dict[str, tuple[str, list[list[str]]]]:
    """RESULT tables keyed by the heading's name before any bracket."""
    out = {}
    for heading, rows in result_tables(result).items():
        out.setdefault(heading.split(" (")[0].strip(), (heading, rows))
    return out


# --------------------------------------------------------------------------
# Earnings recap (references/earnings-recap.md, RULES.md rules 6-8 v15)
#
# One company's reported quarter. The checks hold the comparisons to
# arithmetic (every change re-derives, an estimate's gap is a signed number
# with its provider named), the outlook to the company's own figures, and
# the price table to a move with no reason.
# --------------------------------------------------------------------------

EARNINGS_MODE = "Earnings recap"
EARNINGS_TABLES = ["Results", "Segments", "Against estimates", "Company outlook",
                   "Management said", "Share price around the release"]
EARNINGS_RESULTS_HEADER = ["Metric", "This quarter", "Prior quarter", "QoQ",
                           "Year-ago quarter", "YoY"]
EARNINGS_RESULTS_ROWS = ["Revenue", "Gross margin", "Operating income", "Operating margin",
                         "Net income", "Diluted EPS", "Operating cash flow", "Free cash flow"]
ADJUSTED_MARK = "(non-GAAP, company-adjusted)"
SEGMENTS_HEADER = ["Segment", "This quarter", "Year-ago quarter", "YoY"]
ESTIMATES_HEADER = ["Metric", "Reported", "Estimate", "Estimate source", "Difference"]
ESTIMATES_MAX_ROWS = 6
OUTLOOK_HEADER = ["Item", "Period", "Outlook as stated", "Previous outlook", "Change"]
OUTLOOK_CHANGES = {"Raised", "Lowered", "Unchanged", "New", "Withdrawn", "Not comparable"}
SAID_HEADER = ["Topic", "Speaker", "Said", "Source"]
SAID_VERBS = ("Says ", "States ")
SAID_MAX_ROWS = 5
SAID_MAX_WORDS = 30
SHARE_PRICE_HEADER = ["Instrument", "Close before release", "First close after", "Change %",
                      "Sessions"]
EARNINGS_TLDR = ("Results:", "Estimates:", "Outlook:")
EARNINGS_METHOD = ["Quarter:", "Basis:", "Margins:", "Cash flow basis:", "Estimates rule:",
                   "Outlook rule:", "Statements read:", "Price window:"]
# The verdicts a recap never prints: the gap is a signed number.
EARNINGS_VERDICTS = [r"\bbeat(?:s|ing)?\b", r"\bmiss(?:ed|es|ing)?\b", r"\btopped\b",
                     r"\bfell short\b", r"\bsurprise[sd]?\b", r"\bblowout\b", r"\bcrushed\b"]
# Judgement adjectives, allowed only inside what management said.
EARNINGS_ADJECTIVES = [r"\bstrong(?:er)?\b", r"\bweak(?:er)?\b", r"\bdisappoint\w*\b",
                       r"\bimpressive\b", r"\bsolid\b", r"\bstellar\b", r"\bdismal\b"]
_SHARE_PRICE_TALK = re.compile(
    r"\b(?:share|stock) price\b|\bvaluation\b|\bshares (?:rose|fell|jumped|dropped|rallied|sank)\b",
    re.IGNORECASE)
_RELEASED = re.compile(rf"released ({_ISO})")


def is_earnings_recap(sections: dict[str, str]) -> bool:
    return EARNINGS_MODE in (_mode_line(sections.get("RESULT", "")) or "").split(" + ")


def earnings_tables_elsewhere(sections: dict[str, str]) -> list[str]:
    """RULES.md rule 8 v15: the company's outlook prints in an Earnings recap only."""
    if is_earnings_recap(sections):
        return []
    tables = _tables_by_prefix(sections.get("RESULT", ""))
    return [f"{name} printed outside an Earnings recap (RULES.md rule 8)"
            for name in ("Company outlook", "Management said", "Against estimates")
            if name in tables]


def earnings_recap_problems(sections: dict[str, str]) -> list[str]:
    """An Earnings recap against references/earnings-recap.md."""
    if not is_earnings_recap(sections):
        return []
    result = sections.get("RESULT", "")
    method = sections.get("METHOD", "")
    problems: list[str] = []
    tables = _tables_by_prefix(result)

    # Six tables, in order, nothing else.
    names = [n.split(" (")[0].strip() for n in result_tables(result)]
    for name in names:
        if name not in EARNINGS_TABLES:
            problems.append(f"{name!r} in an Earnings recap; it prints {EARNINGS_TABLES} only")
    known = [n for n in names if n in EARNINGS_TABLES]
    if known != [n for n in EARNINGS_TABLES if n in known]:
        problems.append(f"Earnings recap tables out of order: {known}")
    missing = [n for n in EARNINGS_TABLES if n not in names]
    if missing:
        problems.append(f"Earnings recap is missing tables: {missing}")

    for label in EARNINGS_METHOD:
        if not re.search(rf"^\s*{re.escape(label)}\s*\S", method, re.MULTILINE):
            problems.append(f"Earnings recap METHOD has no {label} line")

    released = _RELEASED.search(_context_field(sections, "Latest period"))
    release_date = _date(released.group(1)) if released else None
    if release_date is None:
        problems.append("Latest period does not say `released YYYY-MM-DD`")

    # Results: the eight rows in order, adjusted rows marked and after them,
    # every change re-derived.
    if "Results" in tables:
        heading, rows = tables["Results"]
        header = _table_header(result, heading)
        if header != EARNINGS_RESULTS_HEADER:
            problems.append(f"Results header is {header}, not {EARNINGS_RESULTS_HEADER}")
        else:
            metrics = [r[0] for r in rows]
            head = metrics[: len(EARNINGS_RESULTS_ROWS)]
            if len(head) < len(EARNINGS_RESULTS_ROWS) or not all(
                    m == want or m.startswith(want + " (")
                    for m, want in zip(head, EARNINGS_RESULTS_ROWS)):
                problems.append(f"Results rows are {head}, not {EARNINGS_RESULTS_ROWS} in order")
            for m in metrics[len(EARNINGS_RESULTS_ROWS):]:
                if "non-GAAP, company-adjusted" not in m:
                    problems.append(f"Results row {m!r} after the eight is not marked "
                                    f"{ADJUSTED_MARK}")
            for m in head:
                if "non-GAAP" in m or "adjusted" in m.lower():
                    problems.append(f"Results row {m!r} replaces a reported row with an "
                                    "adjusted one")
            for r in rows:
                if len(r) < 6:
                    continue
                problems += _change_problems("Results", r[0], r[1], r[2], r[3])
                problems += _change_problems("Results", r[0], r[1], r[4], r[5])
                if r[0] in ("Gross margin", "Operating margin"):
                    for cell in (r[1], r[2], r[4]):
                        v = _num(cell)
                        if v and (v[0] > 100 or v[0] < -100):
                            problems.append(f"Results {r[0]} {cell} is outside ±100%: "
                                            "a parse error")

    # Segments: changes re-derived, or the one None row.
    if "Segments" in tables:
        heading, rows = tables["Segments"]
        header = _table_header(result, heading)
        if header != SEGMENTS_HEADER:
            problems.append(f"Segments header is {header}, not {SEGMENTS_HEADER}")
        else:
            for r in rows:
                if r[0].startswith("None"):
                    continue
                if len(r) >= 4:
                    problems += _change_problems("Segments", r[0], r[1], r[2], r[3])

    # Against estimates: provider and date named, before the release, the gap
    # a signed number that re-derives.
    if "Against estimates" in tables:
        heading, rows = tables["Against estimates"]
        header = _table_header(result, heading)
        if header != ESTIMATES_HEADER:
            problems.append(f"Against estimates header is {header}, not {ESTIMATES_HEADER}")
        else:
            real = [r for r in rows if not r[3].startswith("None found")]
            if len(real) > ESTIMATES_MAX_ROWS:
                problems.append(f"Against estimates has {len(real)} rows, at most "
                                f"{ESTIMATES_MAX_ROWS}")
            for r in rows:
                metric, reported, estimate, source, diff = r[:5]
                if source.startswith("None found"):
                    if (metric, reported, estimate, diff) != ("—", "—", "—", "—"):
                        problems.append("Against estimates None row is `| — | — | — | "
                                        "None found — ... | — |`")
                    continue
                if "EPS" in metric and "Diluted" not in metric and ADJUSTED_MARK not in metric \
                        and "GAAP" not in metric:
                    problems.append(f"Against estimates {metric!r} does not state its basis")
                day = re.search(_ISO, source)
                who = source.split(",")[0].strip().lower()
                if not day or who in NOT_A_SOURCE or who.startswith(("analyst", "consensus")):
                    problems.append(f"Against estimates source {source!r} does not name its "
                                    "provider or outlet and date (`LSEG via Reuters, YYYY-MM-DD`)")
                elif release_date and _date(day.group(0)) and _date(day.group(0)) > release_date:
                    problems.append(f"Against estimates source {source!r} is dated after the "
                                    f"release {release_date}")
                if diff.startswith("Not available") or estimate.startswith("Not available"):
                    continue
                rep, est, d = _num(reported), _num(estimate), _num(diff)
                if not re.match(r"^[+\-−]\d+(?:\.\d+)?%$", diff) or d is None:
                    problems.append(f"Against estimates {metric}: Difference {diff!r} is not "
                                    "a signed %")
                    continue
                if rep and est and est[0] != 0:
                    want = _pct_change(rep[0], est[0])
                    rel = 10 ** -min(_decimals(reported), _decimals(estimate)) / abs(est[0]) * 100
                    if abs(want - d[0]) > rel + _tolerance(diff):
                        problems.append(f"Against estimates {metric}: ({reported} − {estimate}) "
                                        f"÷ |{estimate}| is {want:+.2f}%, printed {diff}")

    # Company outlook: the company's figures, a known Change, or None given.
    if "Company outlook" in tables:
        heading, rows = tables["Company outlook"]
        header = _table_header(result, heading)
        if header != OUTLOOK_HEADER:
            problems.append(f"Company outlook header is {header}, not {OUTLOOK_HEADER}")
        elif "as stated by the company" not in heading:
            problems.append("Company outlook heading does not say `as stated by the company`")
        else:
            for r in rows:
                if r[0] == "None given":
                    if r[4] != "—":
                        problems.append("Company outlook None row is `| None given | — | ... "
                                        "| — | — |`")
                    continue
                if r[4] not in OUTLOOK_CHANGES:
                    problems.append(f"Company outlook {r[0]}: Change {r[4]!r} is not one of "
                                    f"{sorted(OUTLOOK_CHANGES)}")
                if not re.search(r"\d", r[2]):
                    problems.append(f"Company outlook {r[0]}: {r[2]!r} has no figure; words "
                                    "without one are not an outlook row")

    # Management said: paraphrased, attributed, short, nothing about the price.
    if "Management said" in tables:
        heading, rows = tables["Management said"]
        header = _table_header(result, heading)
        if header != SAID_HEADER:
            problems.append(f"Management said header is {header}, not {SAID_HEADER}")
        else:
            real = [r for r in rows if not r[2].startswith("None found")]
            if len(real) > SAID_MAX_ROWS:
                problems.append(f"Management said has {len(real)} rows, at most {SAID_MAX_ROWS}")
            for topic, speaker, said, source in (r[:4] for r in real):
                if not said.startswith(SAID_VERBS):
                    problems.append(f"Management said does not open with Says/States: {said!r}")
                if len(said.split()) >= SAID_MAX_WORDS:
                    problems.append(f"Management said is {len(said.split())} words; "
                                    f"under {SAID_MAX_WORDS}")
                if re.search(r"[\"“”]", said):
                    problems.append(f"Management said quotes instead of paraphrasing: {said!r}")
                if _SHARE_PRICE_TALK.search(said):
                    problems.append(f"Management said is about the share price: {said!r}")
                if source.strip().lower() in NOT_A_SOURCE:
                    problems.append(f"Management said with no source document: {source!r}")
                if speaker.strip().lower() in NOT_A_SOURCE:
                    problems.append(f"Management said with no speaker: {speaker!r}")

    # Share price around the release: the instrument, benchmarks, a move that
    # re-derives.
    if "Share price around the release" in tables:
        heading, rows = tables["Share price around the release"]
        header = _table_header(result, heading)
        if header != SHARE_PRICE_HEADER:
            problems.append(f"Share price around the release header is {header}, not "
                            f"{SHARE_PRICE_HEADER}")
        elif rows:
            if rows[0][0].startswith("Benchmark"):
                problems.append("Share price's first row is the benchmark; the instrument "
                                "comes first")
            for r in rows[1:]:
                if not r[0].startswith("Benchmark: "):
                    problems.append(f"Share price row {r[0]!r} is neither the instrument nor "
                                    "a `Benchmark: ` row")
            for r in rows:
                before, after, change = (_num(c) for c in r[1:4])
                if before and after and change and before[0]:
                    want = _pct_change(after[0], before[0])
                    if abs(want - change[0]) > _tolerance(r[3]) + 0.006:
                        problems.append(f"Share price {r[0]}: {r[1]} to {r[2]} is "
                                        f"{want:+.2f}%, printed {r[3]}")

    # Verdicts nowhere; adjectives and causes only in what the company said.
    scope = result + "\n" + sections.get("CONTEXT", "")
    for pat in EARNINGS_VERDICTS:
        for m in re.finditer(pat, scope, re.IGNORECASE):
            snippet = scope[max(0, m.start() - 30): m.end() + 30].replace("\n", " ")
            problems.append(f"verdict wording in an Earnings recap: {snippet!r}")
    outside = result
    for name in ("Management said", "Company outlook"):
        if name in tables:
            outside = _without_table(outside, tables[name][0])
    for pat in EARNINGS_ADJECTIVES + CAUSAL_WORDING:
        for m in re.finditer(pat, outside, re.IGNORECASE):
            snippet = outside[max(0, m.start() - 30): m.end() + 30].replace("\n", " ")
            problems.append(f"Holdnote's own judgement or cause in an Earnings recap: {snippet!r}")
    for m in USER_POSITION.finditer(result):
        problems.append(f"the user's position in an Earnings recap: {m.group(0)!r}")

    # TL;DR: labelled, in order, figures from the tables, outlook counts true.
    tldr = _tldr_lines(result)
    if len(tldr) > 3:
        problems.append(f"TL;DR has {len(tldr)} lines, at most 3 allowed")
    labels = []
    for line in tldr:
        label = next((lab for lab in EARNINGS_TLDR if line.startswith(lab)), None)
        if label is None:
            problems.append(f"TL;DR line without a Results:/Estimates:/Outlook: label: {line!r}")
        else:
            labels.append(label)
    if labels != [lab for lab in EARNINGS_TLDR if lab in labels]:
        problems.append(f"TL;DR lines out of order: {labels}")
    problems += _tldr_numbers_problems(result, tldr, ("Results:", "Estimates:"))
    outlook_line = next((ln for ln in tldr if ln.startswith("Outlook:")), None)
    if outlook_line and "Company outlook" in tables:
        changes = [r[4] for r in tables["Company outlook"][1] if r[0] != "None given"]
        for n, word in re.findall(r"(\d+) (raised|lowered|unchanged|new|withdrawn)",
                                  outlook_line, re.IGNORECASE):
            count = sum(1 for c in changes if c.lower() == word.lower())
            if int(n) != count:
                problems.append(f"TL;DR Outlook: says {n} {word}, the table has {count}")
    return problems


# --------------------------------------------------------------------------
# Head-to-head (references/head-to-head.md, RULES.md rule 6 v15)
#
# Two instruments of one kind, one scorecard, one set of definitions. The
# checks hold the comparison to arithmetic and keep any winner out of it.
# --------------------------------------------------------------------------

H2H_MODE = "Head-to-head"
H2H_FUND_TABLES = ["Buffett scorecard", "Side by side", "Overlap", "Shared holdings",
                   "Countries and sectors"]
H2H_STOCK_TABLES = ["Buffett scorecard", "Side by side"]
FUND_SCORECARD_CHECKS = {"Low cost", "Broad", "Not concentrated", "Tracks its index",
                         "Built to last", "Quality underneath"}
H2H_TLDR = ("Scorecard:", "Overlap:")
H2H_METHOD = ["Instruments:", "Order:", "Difference:", "Scorecard:", "Price date:",
              "Overlap depth:"]
# A winner, in the words it usually takes. None of these may appear in a
# head-to-head's RESULT or CONTEXT.
H2H_WINNER = [r"\bbetter\b", r"\bbest\b", r"(?<!\bno )\bworse\b", r"\bworst\b", r"\bwinners?\b",
              r"\bwins?\b", r"\bwon\b", r"\bcheaper\b", r"\bpricier\b", r"\bsuperior\b",
              r"\binferior\b", r"\bstronger\b", r"\bweaker\b", r"\bedge\b",
              r"\badvantages?\b", r"\bprefer(?:red|able)?\b", r"\bpicks?\b", r"\bbeats?\b",
              r"\boutperform\w*\b", r"\bunderperform\w*\b"]
_H2H_MARKS = re.compile(r"\*\*|🏆|👑|⭐|🥇|🥈|✔")
_DIFF_HEADING = re.compile(r"Difference = (?P<b>.+?) [−-] (?P<a>.+?)\)?$")


def is_head_to_head(sections: dict[str, str]) -> bool:
    return H2H_MODE in (_mode_line(sections.get("RESULT", "")) or "").split(" + ")


def _difference_problems(table: str, label: str, a: str, b: str, diff: str) -> list[str]:
    """Difference = b − a: pp for percentages, units for counts, — otherwise."""
    va, vb = _num(a), _num(b)
    comparable = (va is not None and vb is not None and va[1] == vb[1]
                  and va[2] == vb[2] and va[1] != "pp" or
                  (va is not None and vb is not None and va[1] == vb[1] == "pp"))
    if not comparable:
        if diff not in ("—", "-") and not diff.startswith(("Not available", "Not comparable")):
            return [f"{table} {label}: {a!r} and {b!r} are not one unit and currency, so "
                    f"Difference is —, not {diff!r}"]
        return []
    if diff.startswith(("Not available", "Not comparable")):
        return []
    d = _num(diff)
    if d is None:
        return [f"{table} {label}: Difference {diff!r} is not a figure"]
    want = vb[0] - va[0]
    if va[1] in ("%", "pp") and not diff.endswith("pp") and table == "Side by side":
        return [f"{table} {label}: a difference of two percentages is in pp, not {diff!r}"]
    if want != 0 and not re.match(r"^[+\-−]", diff.strip()):
        return [f"{table} {label}: Difference {diff!r} is unsigned"]
    if abs(want - d[0]) > _tolerance(a, b) * 2 + _tolerance(diff):
        return [f"{table} {label}: {b} − {a} is {want:+g}, printed {diff}"]
    return []


def head_to_head_problems(sections: dict[str, str]) -> list[str]:
    """A Head-to-head against references/head-to-head.md."""
    if not is_head_to_head(sections):
        return []
    result = sections.get("RESULT", "")
    method = sections.get("METHOD", "")
    problems: list[str] = []
    tables = _tables_by_prefix(result)

    # The scorecard decides the kind, and names the two instruments.
    a = b = None
    fund = False
    if "Buffett scorecard" in tables:
        heading, rows = tables["Buffett scorecard"]
        header = _table_header(result, heading)
        if len(header) != 4 or header[:2] != ["Check", "Threshold"]:
            problems.append(f"Head-to-head scorecard header is {header}, not "
                            "[Check, Threshold, <first>, <second>]")
        else:
            a, b = header[2], header[3]
            fund = any(r[0] in FUND_SCORECARD_CHECKS for r in rows)
            for r in rows:
                for name, cell in zip((a, b), r[2:4]):
                    if not cell.startswith(("Met", "Not met", "Not available")) or \
                            cell.startswith("Met") and not re.match(r"^Met(?: \(.+\))?$", cell):
                        problems.append(f"Buffett scorecard {r[0]} for {name}: {cell!r} does "
                                        "not start Met / Not met / Not available")
    want_tables = H2H_FUND_TABLES if fund else H2H_STOCK_TABLES
    names = [n.split(" (")[0].strip() for n in result_tables(result)]
    for name in names:
        if name not in want_tables:
            problems.append(f"{name!r} in a {'fund' if fund else 'stock'} Head-to-head; it "
                            f"prints {want_tables} only")
    known = [n for n in names if n in want_tables]
    if known != [n for n in want_tables if n in known]:
        problems.append(f"Head-to-head tables out of order: {known}")
    missing = [n for n in want_tables if n not in names]
    if missing:
        problems.append(f"Head-to-head is missing tables: {missing}")

    for label in H2H_METHOD:
        if not re.search(rf"^\s*{re.escape(label)}\s*\S", method, re.MULTILINE):
            problems.append(f"Head-to-head METHOD has no {label} line")

    # Side by side: the same two, in the same order, every Difference b − a.
    if "Side by side" in tables and a and b:
        heading, rows = tables["Side by side"]
        header = _table_header(result, heading)
        if header != ["Fact", a, b, "Difference"]:
            problems.append(f"Side by side header is {header}, not ['Fact', {a!r}, {b!r}, "
                            "'Difference']")
        else:
            m = _DIFF_HEADING.search(heading)
            if not m or m["a"].strip() != a or m["b"].strip() != b:
                problems.append(f"Side by side heading does not say `(Difference = {b} − {a})`")
            for r in rows:
                if len(r) >= 4:
                    problems += _difference_problems("Side by side", r[0], r[1], r[2], r[3])

    if fund and a and b:
        if "Overlap" in tables:
            heading, rows = tables["Overlap"]
            if _table_header(result, heading) != ["Measure", "Value"]:
                problems.append("Overlap header is not ['Measure', 'Value']")
            shared = next((r for r in rows if r[0].startswith("Shared weight")), None)
            if shared is None:
                problems.append("Overlap has no Shared weight % row: one figure for the pair")
            else:
                v = _num(shared[1])
                if v and not 0 <= v[0] <= 100:
                    problems.append(f"Overlap shared weight {shared[1]} is outside 0-100: "
                                    "a parse error")
            if not re.search(r"full holdings files|top-10 depth", heading):
                problems.append("Overlap heading does not name its depth (full holdings "
                                "files | top-10 depth, partial)")
        if "Shared holdings" in tables:
            heading, rows = tables["Shared holdings"]
            want = ["Company", f"{a} %", f"{b} %", "Smaller %"]
            if _table_header(result, heading) != want:
                problems.append(f"Shared holdings header is {_table_header(result, heading)}, "
                                f"not {want}")
            else:
                smaller: list[float] = []
                for r in rows:
                    if r[0].startswith("None"):
                        continue
                    wa, wb, ws = (_num(c) for c in r[1:4])
                    if wa and wb and ws:
                        if abs(min(wa[0], wb[0]) - ws[0]) > 1e-9:
                            problems.append(f"Shared holdings {r[0]}: Smaller % is "
                                            f"{min(wa[0], wb[0])}, printed {r[3]}")
                        smaller.append(ws[0])
                if smaller != sorted(smaller, reverse=True):
                    problems.append("Shared holdings are not sorted by Smaller %, largest first")
        if "Countries and sectors" in tables:
            heading, rows = tables["Countries and sectors"]
            want = ["Exposure", f"{a} %", f"{b} %", "Difference pp"]
            if _table_header(result, heading) != want:
                problems.append(f"Countries and sectors header is "
                                f"{_table_header(result, heading)}, not {want}")
            else:
                for r in rows:
                    if not r[0].startswith(("Country: ", "Sector: ")):
                        problems.append(f"Countries and sectors row {r[0]!r} does not start "
                                        "Country: or Sector:")
                    problems += _difference_problems("Countries and sectors", r[0],
                                                     r[1], r[2], r[3])

    # No winner, in words or in marks.
    scope = result + "\n" + sections.get("CONTEXT", "")
    for pat in H2H_WINNER:
        for m in re.finditer(pat, scope, re.IGNORECASE):
            snippet = scope[max(0, m.start() - 30): m.end() + 30].replace("\n", " ")
            problems.append(f"a winner in a Head-to-head (RULES.md rule 6): {snippet!r}")
    for m in _H2H_MARKS.finditer(result):
        problems.append(f"a mark on one side in a Head-to-head: {m.group(0)!r}")
    for m in USER_POSITION.finditer(result):
        problems.append(f"the user's position in a Head-to-head: {m.group(0)!r}")

    # TL;DR: Scorecard: (and Overlap: for funds), tallies true.
    tldr = _tldr_lines(result)
    if len(tldr) > 2:
        problems.append(f"Head-to-head TL;DR has {len(tldr)} lines, at most 2")
    for line in tldr:
        if not line.startswith(H2H_TLDR):
            problems.append(f"TL;DR line without a Scorecard:/Overlap: label: {line!r}")
        elif line.startswith("Overlap:") and not fund:
            problems.append("Overlap: TL;DR line in a stock Head-to-head")
    problems += _tldr_numbers_problems(result, [ln for ln in tldr if ln.startswith("Overlap:")],
                                       ("Overlap:",))
    score = next((ln for ln in tldr if ln.startswith("Scorecard:")), None)
    if score and a and b and "Buffett scorecard" in tables:
        rows = tables["Buffett scorecard"][1]
        for i, name in ((2, a), (3, b)):
            m = re.search(rf"{re.escape(name)} (\d+) of (\d+) met", score)
            met = sum(1 for r in rows if len(r) > i and re.match(r"^Met\b", r[i]))
            if not m:
                problems.append(f"TL;DR Scorecard: has no `{name} n of m met`")
            elif (int(m.group(1)), int(m.group(2))) != (met, len(rows)):
                problems.append(f"TL;DR Scorecard: says {name} {m.group(1)} of {m.group(2)} "
                                f"met, the table has {met} of {len(rows)}")
    return problems


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
                  lookthrough_problems, hidden_bets_problems, countries_problems,
                  sectors_problems, currencies_problems,
                  brief_layout_problems, quick_brief_problems, sources_summary_problems,
                  lens_source_problems, buffett_notes_problems, checklist_problems,
                  price_move_problems, reported_reasons_elsewhere, metric_table_problems,
                  earnings_recap_problems, earnings_tables_elsewhere, head_to_head_problems):
        problems += check(sections)
    return problems
