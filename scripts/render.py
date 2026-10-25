"""Render a checked Holdnote draft as the report the user reads.

    python3 scripts/render.py draft.md

The draft is the strict RULES.md Part IV output: six sections, checked by
scripts/check_output.py, kept in the run journal, quoted by "show proof".
This script turns it into the chat view, the same way every time: one status
line, the TL;DR in a box, every RESULT table under its own heading with
icons for results, real warnings on one line, and a footer with the build,
the sources and the disclaimer. It adds no figure the draft lacks and drops
no table or warning the draft has. RULES.md Part IV v12.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for folder in (HERE, HERE.parent / "tests"):
    if (folder / "contract.py").exists():
        sys.path.insert(0, str(folder))
        break

import contract  # noqa: E402

DISCLAIMER = ("Not financial advice. Research from public documents; check the originals "
              "before acting.")

# What the line under the title calls each route (RULES.md Part IV, Mode line)
MODE_LABELS = {
    "Price move": "Why it moved", "Stock brief": "Stock brief", "Stock brief (quick)": "Quick brief",
    "Fund brief (Mode A)": "Fund brief", "Fund brief (Mode A, quick)": "Quick brief",
    "Buffett checklist": "Buffett checklist", "Market-wide": "Market",
    "Index construction (Mode B)": "Index construction", "Portfolio (Mode C)": "Portfolio",
    "Demo + Portfolio (Mode C)": "Synthetic portfolio",
    "Earnings recap": "Earnings recap", "Head-to-head": "Head-to-head",
}
# Tables whose rows are sentences read as a list on a phone: (lead column,
# main column, columns after it). Every cell is kept; only the shape changes.
LIST_TABLES = {
    "Dated events": ("Date", "Event", ["Source"]),
    "Reported reasons": ("Source", "Reason as reported", ["Premise"]),
    "Management said": ("Topic", "Said", ["Speaker", "Source"]),
}
# Cells that are a result against a stated threshold or a status the spec fixes
RESULT_CELLS = {
    "Met": "✅", "Not met": "❌", "Not available": "⚪",
    "New": "🆕 New", "Removed": "➖ Removed", "Reworded": "✏️ Reworded", "None": "—",
    "Reached": "🔴 Reached", "Not reached": "🟢 Not reached", "Not checkable": "⚪ Not checkable",
    "None on file": "— none on file",
}
RESULT_COLUMNS = {"Result", "Status"}
# A Price move's Premise column: whether the fact a source cites is in a
# primary document (references/price-move.md). Never whether it caused the move.
PREMISE_CELLS = {
    "Matches primary source": "✅ Matches primary source",
    "Not in primary sources": "❔ Not in primary sources",
    "Not checkable": "⚪ Not checkable",
}
TYPE_CELLS = {"Filing risk": "📄 Filing", "Thesis": "📝 Thesis"}
# METHOD lines a reader must see even with METHOD hidden (RULES.md Part IV v9)
WARNING_LABELS = ("Conflict", "Source conflict", "Stale", "Stale source", "Fallback", "Fallbacks")
TLDR_LABELS = ("Scorecard:", "Changed:", "Red flags:", "Filters:", "Position:", "Thesis:",
               "Results:", "Estimates:", "Outlook:", "Overlap:")
# A head-to-head scorecard cell: the result, then the value in brackets
# (references/head-to-head.md). Only the result gets its icon; no side is marked.
_SIDE_RESULT = re.compile(r"^(?P<result>Met|Not met|Not available)(?: \((?P<value>.+)\)|(?P<rest> — .+))?$")


def _field(block: str, name: str) -> str:
    """A CONTEXT field's value, continuation lines joined."""
    lines = block.splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{name}:"):
            value = [line.split(":", 1)[1].strip()]
            for nxt in lines[i + 1:]:
                if nxt.startswith((" ", "\t")) and ":" not in nxt.split()[0]:
                    value.append(nxt.strip())
                else:
                    break
            return " ".join(v for v in value if v)
    return ""


def _title(text: str, mode: str) -> str:
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    m = re.match(r"^=== (?P<ticker>[^—]+?)\s+—\s+(?P<name>[^·]+?)(?:\s+·.*)?\s*===$", first)
    if m:
        return f"## {m['ticker']} · {m['name']}"
    names = {"Portfolio (Mode C)": "Your portfolio", "Market-wide": "The market",
             "Demo": "Demo portfolio",
             "Portfolio sync": "Portfolio update", "Thesis journal": "Thesis journal"}
    return f"## {names.get(mode.split(' + ')[0], mode or 'Holdnote')}"


def _status(sections: dict[str, str], mode: str) -> str:
    """One quiet line under the title: what ran, as of when, in what units.

    A complete run needs no badge; only a stop is announced, and first."""
    status = sections.get("STATUS", "").strip()
    context = sections.get("CONTEXT", "")
    asof = _field(context, "Data as of")
    # The units' first clause only. The full field stays in the draft, which
    # "show proof" prints.
    units = (_field(context, "Currency / units") or _field(context, "Currency/units"))
    units = units.split(";")[0].split(" · ")[0].strip()
    label = MODE_LABELS.get(mode, mode.split(" + ")[0].split(" (")[0])
    bits = [b for b in (label, f"data as of {asof}" if asof else "", units) if b]
    line = "*" + " · ".join(bits) + "*" if bits else ""
    if not status.lower().startswith("complete"):
        stop = f"⛔ **Stopped** · {status.removeprefix('Halted - ').removeprefix('halted - ')}"
        return stop + ("  \n" + line if line else "")
    return line


def _heading(line: str) -> tuple[str, str]:
    """'Sectors (market weights, as of 2026-10-09)' -> ('Sectors', 'market weights, ...')."""
    m = re.match(r"^(?P<name>[^(—]+?)\s*(?:\((?P<sub>.+)\)|—\s*(?P<sub2>.+))?$", line.strip())
    if not m:
        return line.strip(), ""
    return m["name"].strip(), (m["sub"] or m["sub2"] or "").strip()


def _row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


SCORECARD_HEADER = ["Check", "Metric", "Value", "Threshold", "Result"]


def _table(lines: list[str]) -> list[str]:
    """A pipe table with result cells as icons; a scorecard folds Check and
    Metric into one column, the way the report design shows it."""
    rows = [[c.strip() for c in ln.strip().strip("|").split("|")] for ln in lines]
    header, body = rows[0], [r for r in rows[1:] if not set("".join(r)) <= set("-: ")]
    if header == SCORECARD_HEADER:
        header = ["Check", "Value", "Bar", "Result"]
        body = [[f"**{r[0]}** · {r[1]}", *r[2:]] if len(r) == 5 else r for r in body]
    head_to_head = len(header) == 4 and header[:2] == ["Check", "Threshold"]
    out_header = ["" if h in RESULT_COLUMNS and h == "Result" else h for h in header]
    out = [_row(out_header), _row(["---"] * len(header))]
    for r in body:
        cells = []
        for i, c in enumerate(r):
            col = header[i] if i < len(header) else ""
            if head_to_head and i >= 2 and _SIDE_RESULT.match(c):
                m = _SIDE_RESULT.match(c)
                # "Not available — reason" keeps its words; an icon alone
                # would leave the reason reading as a sentence fragment.
                rest = f"{m['result']}{m['rest']}" if m["rest"] else ""
                c = " ".join(b for b in (RESULT_CELLS[m["result"]], m["value"] or rest) if b)
            elif col in RESULT_COLUMNS and c in RESULT_CELLS:
                c = RESULT_CELLS[c]
            elif col == "Type" and c in TYPE_CELLS:
                c = TYPE_CELLS[c]
            elif col == "Premise" and c in PREMISE_CELLS:
                c = PREMISE_CELLS[c]
            cells.append(c)
        out.append(_row(cells))
    return out


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _as_list(name: str, lines: list[str]) -> list[str]:
    """A sentence table as a list: **lead** · main — *the rest*. Every cell
    is kept except an About column that says the same thing on every row."""
    lead, main, rest = LIST_TABLES[name]
    header, body = _cells(lines[0]), [_cells(ln) for ln in lines[1:]]
    body = [r for r in body if not set("".join(r)) <= set("-: ")]
    col = {h: i for i, h in enumerate(header)}
    abouts = {r[col["About"]] for r in body} if "About" in col else set()
    out = []
    for r in body:
        get = lambda h: r[col[h]] if h in col and col[h] < len(r) else ""  # noqa: E731
        bits = [f"**{get(lead)}**"] if get(lead) not in ("", "—") else []
        if len(abouts) > 1:
            bits.append(get("About"))
        if name == "Reported reasons" and get("Published") not in ("", "—"):
            bits.append(get("Published"))
        head = " · ".join(bits)
        tail = [PREMISE_CELLS.get(get(h), get(h)) for h in rest if get(h) not in ("", "—")]
        text = get(main)
        line = f"- {head} — {text}" if head else f"- {text}"
        if tail:
            line += " · *" + " · ".join(tail) + "*"
        out.append(line)
    return out


def _result(result: str) -> list[str]:
    lines = result.splitlines()
    out: list[str] = []
    tldr: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if not line or line.startswith("Mode:"):
            i += 1
            continue
        if line.startswith(TLDR_LABELS) and not nxt.startswith("|"):
            label, rest = line.split(":", 1)
            tldr.append(f"> **{label}** {rest.strip()}")
            i += 1
            continue
        if nxt.startswith("|"):
            name, sub = _heading(line)
            out += ["", f"### {name}"]
            if sub:
                out.append(f"*{sub[0].upper() + sub[1:]}*")
            out.append("")
            j = i + 1
            block = []
            while j < len(lines) and lines[j].strip().startswith("|"):
                block.append(lines[j])
                j += 1
            out += _as_list(name, block) if name in LIST_TABLES else _table(block)
            i = j
            continue
        if nxt == "none":  # a heading with nothing under it, as the spec prints it
            name, sub = _heading(line)
            out += ["", f"### {name}", "", "*none*"]
            i += 2
            continue
        out += ["", line]
        i += 1
    if tldr:
        # two trailing spaces keep the box's lines apart
        out = ["", *[t + "  " for t in tldr[:-1]], tldr[-1], *out]
    return out


def _warnings(method: str) -> list[str]:
    found = []
    for raw in method.splitlines():
        line = raw.strip()
        label = line.split(":", 1)[0]
        lower = line.lower()
        value = line.split(":", 1)[1].strip().lower() if ":" in line else ""
        if value in ("none", "none.", "-", "—"):
            continue  # "Conflict: none" is the absence of a warning, not one
        single = label == "Confirmation" and ("one source" in lower or "single source" in lower)
        if label in WARNING_LABELS or single or (label == "Self-check" and "not run" in lower) \
                or ("stale" in lower and label not in ("Build", "Tables")):
            label, _, value = line.partition(":")
            found.append(f"**{label.strip()}:** {re.sub(r'\s+', ' ', value).strip()}")
    return found[:3]


def _next(method: str) -> str:
    m = re.search(r"^\s*Next:\s*(.+)$", method, re.MULTILINE)
    return m.group(1).strip() if m else ""


def _footer(sections: dict[str, str]) -> str:
    build = re.search(r"^\s*Build:\s*(.+)$", sections.get("METHOD", ""), re.MULTILINE)
    body = [ln.strip() for ln in sections.get("SOURCES", "").splitlines() if ln.strip()]
    summary = next((ln for ln in body if re.match(r"^\d+ documents? · ", ln)), "")
    if summary:
        sources = summary.split(' · full list on')[0]
    elif any(ln.startswith("SOURCES: export only") for ln in body):
        sources = "your export only"
    else:
        rows = [ln for ln in body if ln.startswith("|")][2:] or [ln for ln in body if ln.startswith("- ")]
        sources = f"{len(rows)} sources" if rows else "no sources"
    parts = [f"Build {build.group(1).strip()}" if build else "", sources,
             'say **"show proof"** for method, working and sources']
    return "*" + " · ".join(p for p in parts if p) + "*"


def _lede(sections: dict[str, str], mode: str) -> str:
    """A Price move's answer in one line, restated from its Move table and
    Latest period: **NVDA -6.61%** · S&P 500 -1.95% · the two closes."""
    if mode.split(" + ")[0] != "Price move":
        return ""
    result = sections.get("RESULT", "")
    rows = contract.result_tables(result).get("Move")
    if not rows:
        return ""
    header = contract._table_header(result, "Move")
    if "Period %" not in header:
        return ""
    col = header.index("Period %")
    bits = []
    for i, r in enumerate(rows):
        name = r[0].removeprefix("Benchmark: ")
        short = re.search(r"\((?P<t>[A-Z0-9.]+),", name) if i == 0 else None
        label = short["t"] if short else re.sub(r"\s*\(.*\)$", "", name)
        cell = r[col] if col < len(r) else ""
        move = f"{cell}%" if contract._SIGNED.match(cell) else cell
        bits.append(f"**{label} {move}**" if i == 0 else f"{label} {move}")
    period = _field(sections.get("CONTEXT", ""), "Latest period")
    if period:
        bits.append(re.sub(r"\s*\(.*\)$", "", period))
    return " · ".join(bits)


def _missing(context: str) -> str:
    """Partial coverage, stated before the results (rule 9)."""
    missing = _field(context, "Not available")
    if not missing or missing.lower() in ("none", "-", "—"):
        return ""
    return f"*Not available: {missing}*"


def render(text: str) -> str:
    sections = contract.split_sections(text)
    result = sections.get("RESULT", "")
    mode = re.search(r"^\s*Mode:\s*(.+)$", result, re.MULTILINE)
    mode = mode.group(1).strip() if mode else ""
    out = [_title(text, mode)]
    status = _status(sections, mode)
    if status:
        out.append(status)
    lede = _lede(sections, mode)
    if lede:
        out += ["", lede]
    missing = _missing(sections.get("CONTEXT", ""))
    if missing:
        out += ["", missing]
    if result.strip():
        out += _result(result)
    else:
        out += ["", "Nothing was printed because a check stopped the run; "
                    'say **"show proof"** to see which check and why.']
    warnings = _warnings(sections.get("METHOD", ""))
    if warnings:
        out += ["", "#### ⚠️ Check before relying on this", ""] + [f"- {w}" for w in warnings]
    nxt = _next(sections.get("METHOD", ""))
    if nxt:
        out += ["", f"**Next** · {nxt}"]
    out += ["", "---", _footer(sections) + "  ", f"*{DISCLAIMER}*"]
    return "\n".join(out).rstrip() + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python3 scripts/render.py <draft file>")
        return 2
    print(render(Path(argv[1]).read_text(encoding="utf-8")), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
