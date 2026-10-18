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
              "before acting. Not affiliated with Warren Buffett or Berkshire Hathaway.")

ICONS = {
    "Buffett scorecard": "🏰", "Key numbers": "📊", "What changed": "🔄", "Red flags": "🚩",
    "Buffett notes": "💡", "Four filters": "🧭", "Your position": "🧺",
    "Allocation": "🎯", "Look-through": "🔍", "Hidden bets": "🕵️", "Countries": "🌍", "Sectors": "🏭",
    "Currencies": "💱", "Holdings changes": "📅", "Holdings": "🔗", "Comparison": "⚖️",
    "Structural": "🧱", "Performance": "📈", "Stocks": "🗓️",
}
# Cells that are a result against a stated threshold or a status the spec fixes
RESULT_CELLS = {
    "Met": "✅", "Not met": "❌", "Not available": "⚪",
    "New": "🆕 New", "Removed": "➖ Removed", "Reworded": "✏️ Reworded", "None": "—",
    "Reached": "🔴 Reached", "Not reached": "🟢 Not reached", "Not checkable": "⚪ Not checkable",
    "None on file": "— none on file",
}
RESULT_COLUMNS = {"Result", "Status"}
TYPE_CELLS = {"Filing risk": "📄 Filing", "Thesis": "📝 Thesis"}
# METHOD lines a reader must see even with METHOD hidden (RULES.md Part IV v9)
WARNING_LABELS = ("Conflict", "Source conflict", "Stale", "Stale source", "Fallback")
TLDR_LABELS = ("Scorecard:", "Changed:", "Red flags:", "Filters:", "Position:", "Thesis:")


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


def _status(sections: dict[str, str]) -> str:
    status = sections.get("STATUS", "").strip()
    context = sections.get("CONTEXT", "")
    if status.lower().startswith("complete"):
        head = "✅ **Complete**"
    else:
        head = f"⛔ **Stopped** · {status.removeprefix('Halted - ').removeprefix('halted - ')}"
    asof = _field(context, "Data as of")
    # One line: the units' first clause only. The full field stays in the
    # draft, which "show proof" prints.
    units = (_field(context, "Currency / units") or _field(context, "Currency/units")).split(";")[0].strip()
    bits = [b for b in (f"data as of {asof}" if asof else "", units) if b]
    return " · ".join([head, *bits])


def _heading(line: str) -> tuple[str, str]:
    """'Sectors (market weights, as of 2026-10-09)' -> ('Sectors', 'market weights, ...')."""
    m = re.match(r"^(?P<name>[^(—]+?)\s*(?:\((?P<sub>.+)\)|—\s*(?P<sub2>.+))?$", line.strip())
    if not m:
        return line.strip(), ""
    return m["name"].strip(), (m["sub"] or m["sub2"] or "").strip()


def _icon(name: str) -> str:
    if name.endswith(" lens"):
        return "📐"
    return ICONS.get(name, "📄")


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
    out_header = ["" if h in RESULT_COLUMNS and h == "Result" else h for h in header]
    out = [_row(out_header), _row(["---"] * len(header))]
    for r in body:
        cells = []
        for i, c in enumerate(r):
            col = header[i] if i < len(header) else ""
            if col in RESULT_COLUMNS and c in RESULT_CELLS:
                c = RESULT_CELLS[c]
            elif col == "Type" and c in TYPE_CELLS:
                c = TYPE_CELLS[c]
            cells.append(c)
        out.append(_row(cells))
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
            out += ["", f"### {_icon(name)} {name}"]
            if sub:
                out.append(f"*{sub}*")
            out.append("")
            j = i + 1
            block = []
            while j < len(lines) and lines[j].strip().startswith("|"):
                block.append(lines[j])
                j += 1
            out += _table(block)
            i = j
            continue
        if nxt == "none":  # a heading with nothing under it, as the spec prints it
            name, sub = _heading(line)
            out += ["", f"### {_icon(name)} {name}", "", "*none*"]
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
        single = label == "Confirmation" and ("one source" in lower or "single source" in lower)
        if label in WARNING_LABELS or single or (label == "Self-check" and "not run" in lower) \
                or ("stale" in lower and label not in ("Build", "Tables")):
            found.append(line if len(line) <= 140 else line[:137] + "...")
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


def render(text: str) -> str:
    sections = contract.split_sections(text)
    result = sections.get("RESULT", "")
    mode = re.search(r"^\s*Mode:\s*(.+)$", result, re.MULTILINE)
    mode = mode.group(1).strip() if mode else ""
    out = [_title(text, mode), _status(sections)]
    missing = _field(sections.get("CONTEXT", ""), "Not available")
    if missing and missing.lower() not in ("none", "-", "—"):
        out.append(f"⚪ *Missing: {missing}*")
    if result.strip():
        out += _result(result)
    else:
        out += ["", "Nothing was printed because a check stopped the run; "
                    'say **"show proof"** to see which check and why.']
    warnings = _warnings(sections.get("METHOD", ""))
    if warnings:
        out += ["", "⚠️ *" + " · ".join(warnings) + "*"]
    nxt = _next(sections.get("METHOD", ""))
    if nxt:
        out += ["", f"👉 *{nxt}*"]
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
