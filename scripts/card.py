#!/usr/bin/env python3
"""The portfolio card: one shareable image of what a portfolio looks through to.

    python3 scripts/card.py <draft.md> --out <folder>

Reads a checked Mode C draft (a real run or the demo) and draws its
Allocation, Look-through, Hidden bets, Countries, Sectors and Holdings tables as one
1080 x 1350 image, the shape LinkedIn, X and Instagram show in full. It
writes card.svg always and card.png when Pillow is installed, and prints the
paths.

**Percentages only.** Every figure on the card is a cell of the draft's
tables, a share of the portfolio's market value, copied to the same two
decimals. No quantity, price, value or currency amount is drawn, whatever
the draft holds, so the card can be posted without saying how much anyone
has. A demo draft is labelled as the synthetic demo portfolio.

Exit codes: 0 written; 1 the draft lacks a table the card needs, or it is
Not available (the reason is printed); 2 usage.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
for folder in (HERE, HERE.parent / "tests"):
    if (folder / "contract.py").exists():
        sys.path.insert(0, str(folder))
        break

import contract  # noqa: E402

W, H = 1080, 1350
PAD = 64
REPO = "github.com/Artvarna/holdnote"

# Art direction: an issuer's fund factsheet. White page, a navy header band,
# one typeface (Inter) in two weights, hairline rules, figures right-aligned
# in tables, and one accent colour with tints of it for the parts of a bar.
PAPER = "#FFFFFF"
INK = "#14171C"
MUTED = "#5F6670"
RULE = "#DADDE2"
PANEL = "#F2F4F6"
NAVY = "#1F3A5F"
ON_NAVY = "#C9D5E4"
TRACK = "#E4E8ED"
# Parts of a bar, largest first; the folded Other is REST
SEGMENTS = ["#1F3A5F", "#4F6D8F", "#8399B3", "#B4C2D3", "#D5DEE8"]
REST = "#E4E8ED"

FONTS = HERE.parent / "assets" / "fonts"
# key -> (file, SVG family, weight, style)
FACES = {
    "sans": ("Inter_400Regular.ttf", "BB Sans", 400, "normal"),
    "sans-bold": ("Inter_600SemiBold.ttf", "BB Sans", 600, "normal"),
}
FALLBACK = {"BB Serif": "Georgia, 'Times New Roman', serif",
            "BB Sans": "'Helvetica Neue', Arial, sans-serif"}


class Missing(Exception):
    """The draft cannot make a card; the message says why."""


# --- reading the draft ----------------------------------------------------------

def tables(result: str) -> dict[str, list[list[str]]]:
    """RESULT's tables by heading name (the text before any parenthesis):
    each a list of rows, header first, separator dropped."""
    out: dict[str, list[list[str]]] = {}
    heading = ""
    for line in result.splitlines():
        s = line.strip()
        if s.startswith("|"):
            if re.match(r"^\|[\s:|-]+\|$", s):
                continue
            if heading:
                out.setdefault(heading, []).append([c.strip() for c in s.strip("|").split("|")])
        elif s:
            heading = re.split(r"\s*[(—]", s, maxsplit=1)[0].strip()
    return out


def num(cell: str) -> Decimal | None:
    try:
        return Decimal(cell)
    except (InvalidOperation, ValueError):
        return None


def pct(value: Decimal) -> str:
    return f"{value:.2f}%"


@dataclass
class Card:
    as_of: str
    demo: bool
    funds: list[str]
    direct: int
    companies: int | None
    top: list[tuple[str, Decimal]]
    hero: tuple[str, list[tuple[str, Decimal]], Decimal, Decimal] | None
    countries: list[tuple[str, Decimal]]
    sectors: list[tuple[str, Decimal]]
    overlap: tuple[str, str, Decimal] | None
    partial: bool = False
    partial_label: str = "PARTIAL · TOP-10 DEPTH"
    holdings: list[tuple[str, Decimal]] = field(default_factory=list)  # Allocation weights
    columns: list[str] = field(default_factory=list)  # Look-through's cell columns
    rows: list[tuple[str, list[str], Decimal]] = field(default_factory=list)  # top 10, cells as printed
    hidden: tuple[int, Decimal] | None = None  # Hidden bets: companies, % together


def _needed(t: dict[str, list[list[str]]], name: str) -> list[list[str]]:
    rows = t.get(name)
    if not rows:
        raise Missing(f"the draft has no {name} table; ask for the portfolio view "
                      "(\"what do I own?\") first")
    body = " ".join(" ".join(r) for r in rows[1:])
    if "Not available" in body:
        reason = next((c for r in rows[1:] for c in r if "Not available" in c), "Not available")
        raise Missing(f"{name} is {reason}")
    return rows


def _available(t: dict[str, list[list[str]]], name: str) -> bool:
    rows = t.get(name)
    return bool(rows) and "Not available" not in " ".join(" ".join(r) for r in rows[1:])


HUNDRED = Decimal(100)
# How far a whole-portfolio table's Total row may sit from 100 through
# rounding each cell to 0.01: half a hundredth per cell, for ~20 cells.
WHOLE_DRIFT = Decimal("0.10")


def _buckets(rows: list[list[str]], keep: int) -> list[tuple[str, Decimal]]:
    """Top `keep` named buckets by Total, then everything else as Other, so
    the parts add up to the table's Total row."""
    header = rows[0]
    ti = header.index("Total")
    named, rest = [], Decimal(0)
    total_row = None
    for r in rows[1:]:
        v = num(r[ti])
        if v is None:
            continue
        if r[0] == "Total":
            total_row = v
            continue
        if (r[0].startswith("Other ") or r[0].startswith("Cash and other") or "not stated" in r[0]
                or r[0] == "Not looked through"):
            rest += v
        else:
            named.append((r[0], v))
    named.sort(key=lambda kv: (-kv[1], kv[0]))
    rest += sum((v for _, v in named[keep:]), Decimal(0))
    out = named[:keep]
    # A table of the whole portfolio sums to 100 before its cells are rounded
    # one by one; its Total row can then read 100.04. Other is what the named
    # parts leave of 100, so the card adds up and Other carries no drift.
    if total_row is not None and abs(total_row - HUNDRED) <= WHOLE_DRIFT:
        rest, total_row = HUNDRED - sum((v for _, v in out), Decimal(0)), HUNDRED
    if rest > 0:
        out.append(("Other", rest))
    if total_row is not None:
        drawn = sum((v for _, v in out), Decimal(0))
        if drawn != total_row:
            raise Missing(f"{header[0]} parts sum to {drawn}, not the Total row's {total_row}")
    return out


def read(text: str) -> Card:
    problems = contract.output_problems(text)
    if problems:
        raise Missing("the draft does not pass the output contract: " + "; ".join(problems[:3]))
    sections = contract.split_sections(text)
    result = sections.get("RESULT", "")
    t = tables(result)
    lt = _needed(t, "Look-through")
    header = lt[0]
    funds = [h.split(" ", 1)[1] for h in header if h.startswith("via ")]
    has_direct = "Direct" in header
    di = header.index("Direct") if has_direct else None
    ranked = sorted((r for r in lt[1:] if num(r[-1]) is not None),
                    key=lambda r: (-num(r[-1]), r[0]))[:10]
    top = [(r[0], num(r[-1])) for r in ranked]
    columns = header[1:-1]
    rows = [(r[0], r[1:-1], num(r[-1])) for r in ranked]
    holdings = []
    alloc = t.get("Allocation")
    if alloc and "Weight (market)" in alloc[0] and "Ticker" in alloc[0]:
        ti, wi = alloc[0].index("Ticker"), alloc[0].index("Weight (market)")
        holdings = [(r[ti], num(r[wi])) for r in alloc[1:]
                    if r[ti].lower() != "total" and num(r[wi]) is not None]
    direct = sum(1 for r in lt[1:] if di is not None and num(r[di]) is not None)

    hero = None
    hb = t.get("Hidden bets")
    if hb and hb[0] == contract.HIDDEN_BETS_HEADER:
        best = None
        for r in hb[1:]:
            added, total = num(r[4]), num(r[3])
            if r[0] == "none" or added is None or total is None:
                continue
            routes = []
            for part in r[1].split(" · "):
                label, value = part.rsplit(" ", 1)
                routes.append((label, Decimal(value)))
            if best is None or added > best[3]:
                best = (r[0], routes, total, added)
        hero = best

    # Countries and Sectors are drawn when the draft carries them; a run made
    # for the card asks for both (SKILL.md -> Portfolio card).
    # A Not available one (factsheet top-10 depth gives no country or sector
    # per company) is left off, and the card says why in its place.
    countries = _buckets(t["Countries"], 4) if _available(t, "Countries") else []
    sectors = _buckets(t["Sectors"], 4) if _available(t, "Sectors") else []

    overlap = None
    hold = t.get("Holdings")
    if hold:
        for r in hold[1:]:
            shared = num(r[-1])
            m = re.match(r"^(\d+)", r[1])
            if shared and m and " - " in r[0] and (overlap is None or shared > overlap[2]):
                a, b = r[0].split(" - ", 1)
                overlap = (f"{a} and {b}", m.group(1), shared)

    hidden = None
    m = re.search(r"Hidden bets:.*?; (\d+) compan(?:y|ies), (\d+\.\d{2}) of the portfolio",
                  sections.get("METHOD", ""))
    if m:
        hidden = (int(m.group(1)), Decimal(m.group(2)))
    companies = None
    m = re.search(r"Look-through rows:.*? of (\d+) companies", sections.get("METHOD", ""))
    if m:
        companies = int(m.group(1))
    mode = next((ln for ln in result.splitlines() if ln.startswith("Mode:")), "")
    as_of = ""
    for line in sections.get("CONTEXT", "").splitlines():
        if line.strip().startswith("Data as of:"):
            as_of = line.split(":", 1)[1].strip().split()[0].rstrip("·").strip()
    # A look-through at factsheet top-10 depth says so in its heading; the
    # card says so too, since its company weights are then floors.
    # So is one that leaves a fund out (no holdings file for it): the weights
    # are then floors too.
    partial = bool(re.search(r"^Look-through\b.*\b(partial|not looked through)\b", result,
                             re.MULTILINE))
    label = ("PARTIAL · SOME FUNDS NOT LOOKED THROUGH"
             if re.search(r"^Look-through\b.*\bnot looked through\b", result, re.MULTILINE)
             else "PARTIAL · TOP-10 DEPTH")
    if partial and label == "PARTIAL · TOP-10 DEPTH":
        companies = None  # the count of companies in some top 10s says nothing of the funds
    return Card(as_of=as_of, demo="Demo" in mode, funds=funds, direct=direct,
                companies=companies, top=top, hero=hero, countries=countries,
                sectors=sectors, overlap=overlap, partial=partial, partial_label=label,
                holdings=holdings, columns=columns, rows=rows, hidden=hidden)


# --- drawing ------------------------------------------------------------------

@dataclass
class Text:
    x: float
    y: float  # baseline
    s: str
    size: int
    face: str = "sans"
    color: str = INK
    anchor: str = "start"  # start | end
    spacing: float = 0


@dataclass
class Rect:
    x: float
    y: float
    w: float
    h: float
    color: str
    r: float = 0


class Fonts:
    """The bundled faces through Pillow: they draw the PNG and measure text, so
    long names are cut to fit in both files the same way. Without Pillow,
    widths are estimated and only the SVG is written."""

    def __init__(self) -> None:
        self.ok = False
        self.cache: dict[tuple[str, int], object] = {}
        try:
            from PIL import ImageFont  # noqa: F401
            self.ok = all((FONTS / f[0]).exists() for f in FACES.values())
        except ImportError:
            pass

    def get(self, face: str, size: int):
        from PIL import ImageFont
        key = (face, size)
        if key not in self.cache:
            self.cache[key] = ImageFont.truetype(str(FONTS / FACES[face][0]), size)
        return self.cache[key]

    def width(self, s: str, size: int, face: str = "sans", spacing: float = 0) -> float:
        extra = spacing * max(len(s) - 1, 0)
        if self.ok:
            return self.get(face, size).getlength(s) + extra
        return len(s) * size * (0.56 if face.startswith("serif") else 0.54) + extra

    def fit(self, s: str, size: int, room: float, face: str = "sans") -> str:
        if self.width(s, size, face) <= room:
            return s
        while s and self.width(s + "…", size, face) > room:
            s = s[:-1]
        return s.rstrip(" ,.") + "…"


def _and(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _date(iso: str) -> str:
    try:
        y, m, d = (int(x) for x in iso.split("-"))
    except ValueError:
        return iso
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    return f"{d} {months[m - 1]} {y}"


def _section(ops: list, x: float, y: float, w: float, title: str) -> None:
    """A section heading as factsheets set them: bold, sentence case, a rule under."""
    ops.append(Text(x, y, title, 19, "sans-bold", INK))
    ops.append(Rect(x, y + 12, w, 1.5, NAVY))


def _bucket_column(ops: list, x: float, y: float, w: float, title: str,
                   buckets: list[tuple[str, Decimal]], fonts: Fonts) -> float:
    """A two-column table, label and % of the portfolio, with a thin bar per row."""
    _section(ops, x, y, w, title)
    biggest = max((v for _, v in buckets), default=Decimal(1)) or Decimal(1)
    ry = y + 44
    for label, value in buckets:
        value_s = pct(value)
        ops.append(Text(x, ry, fonts.fit(label, 17, w * 0.62), 17, "sans", INK))
        ops.append(Text(x + w, ry, value_s, 17, "sans-bold", INK, "end"))
        bar_x, bar_w = x + w * 0.64, w * 0.36 - fonts.width("00.00%", 17, "sans-bold") - 14
        ops.append(Rect(bar_x, ry - 9, bar_w, 6, TRACK))
        ops.append(Rect(bar_x, ry - 9, max(float(value / biggest) * bar_w, 2), 6,
                        REST if label == "Other" else NAVY))
        ops.append(Rect(x, ry + 10, w, 1, RULE))
        ry += 30
    return ry


def nice(name: str) -> str:
    """A name an export or factsheet prints in capitals, as a factsheet would
    set it: 'APPLE INC. - COMMON ST' -> 'Apple Inc.', 'SK HYNIX' -> 'SK Hynix'.
    Letters only change case; nothing is added or dropped but a share-type tail."""
    name = name.split(" - ")[0].strip() or name
    if name != name.upper() or " " not in name:  # a ticker (VWCE, KO) stays as it is
        return name
    return " ".join(w if len(w.strip(".,")) <= 2 else w[0] + w[1:].lower() for w in name.split())


def _hero_lines(card: Card) -> tuple[str, str] | None:
    """The company the portfolio reaches through most holdings, in words."""
    if not card.hero:
        return None
    name, routes, total, _added = card.hero
    ordered = sorted(routes, key=lambda r: (-r[1], r[0] != "Direct"))
    parts = [f"{v:.2f}% owned directly" if lab == "Direct"
             else f"{v:.2f}% through {lab.removeprefix('via ')}" for lab, v in ordered]
    return (f"{nice(name)}: {pct(total)} of the portfolio, reached through "
            f"{len(routes)} holdings", _and(parts).capitalize()[0] + _and(parts)[1:])


def layout(card: Card, fonts: Fonts) -> list[Text | Rect]:
    ops: list[Text | Rect] = [Rect(0, 0, W, H, PAPER)]
    room = W - 2 * PAD
    right = W - PAD

    # Header band
    ops.append(Rect(0, 0, W, 148, NAVY))
    ops.append(Text(PAD, 56, "Holdnote", 20, "sans-bold", "#FFFFFF"))
    ops.append(Text(PAD, 112, "Portfolio look-through", 44, "sans-bold", "#FFFFFF"))
    if card.as_of:
        ops.append(Text(right, 56, f"As of {_date(card.as_of)}", 18, "sans", "#FFFFFF", "end"))
    badge = ("DEMO · SYNTHETIC PORTFOLIO" if card.demo
             else card.partial_label if card.partial else "")
    if badge:
        bw = fonts.width(badge, 14, "sans-bold") + 28
        ops.append(Rect(right - bw, 86, bw, 30, "#2C4B73", 4))
        ops.append(Text(right - 14, 106, badge, 14, "sans-bold", ON_NAVY, "end"))

    parts = []
    if card.companies:
        parts.append(f"{card.companies:,} companies")
    holds = [f"{len(card.funds)} fund{'s' if len(card.funds) != 1 else ''}"]
    if card.direct:
        holds.append(f"{card.direct} stock{'s' if card.direct != 1 else ''}")
    deck = (" ".join(parts + ["inside " + " and ".join(holds)]) if parts
            else "Holdings: " + " and ".join(holds))
    ops.append(Text(PAD, 192, fonts.fit(deck, 20, room), 20, "sans", MUTED))

    # Portfolio composition: one bar, the Allocation weights
    y = 252
    if card.holdings:
        _section(ops, PAD, y, room, "Portfolio composition")
        held = sorted(card.holdings, key=lambda kv: -kv[1])
        total = sum((v for _, v in held), Decimal(0)) or Decimal(1)
        bx = PAD
        for i, (_, v) in enumerate(held):
            seg = float(v / total) * room
            ops.append(Rect(bx, y + 32, max(seg - 2, 1), 16, SEGMENTS[i % len(SEGMENTS)]))
            bx += seg
        lx, ly = PAD, y + 80
        for i, (name, v) in enumerate(held):
            label = fonts.fit(nice(name), 16, 220)
            item = fonts.width(label, 16) + fonts.width(pct(v), 16, "sans-bold") + 50
            if lx + item > right:
                lx, ly = PAD, ly + 26
            ops.append(Rect(lx, ly - 11, 11, 11, SEGMENTS[i % len(SEGMENTS)]))
            ops.append(Text(lx + 18, ly, label, 16, "sans", INK))
            ops.append(Text(lx + 18 + fonts.width(label, 16) + 8, ly, pct(v), 16, "sans-bold", INK))
            lx += item
        y = ly + 28

    # Key figures: three panels
    gap = 20
    bw = (room - 2 * gap) / 3
    panels = [("Largest exposure", pct(card.top[0][1]) if card.top else "-",
               nice(card.top[0][0]) if card.top else "")]
    if card.hidden:
        n, together = card.hidden
        panels.append(("In more than one holding", pct(together),
                       f"{n} compan{'y' if n == 1 else 'ies'} reached twice or more"))
    else:
        panels.append(("In more than one holding", "-", "no company reached twice"))
    top10 = card.partial and card.partial_label == "PARTIAL · TOP-10 DEPTH"
    if card.overlap and not top10:
        pair, n, shared = card.overlap
        panels.append(("Fund overlap", pct(shared),
                       f"{pair} share {int(n):,} compan{'y' if int(n) == 1 else 'ies'}"))
    elif top10:
        panels.append(("Look-through depth", "Top 10", "per fund, from its factsheet"))
    else:
        panels.append(("Look-through depth", "Full", "every holding of each fund"))
    for i, (title, value, caption) in enumerate(panels):
        px = PAD + i * (bw + gap)
        ops.append(Rect(px, y, bw, 100, PANEL))
        ops.append(Rect(px, y, 4, 100, NAVY))
        ops.append(Text(px + 20, y + 28, fonts.fit(title, 15, bw - 32), 15, "sans", MUTED))
        ops.append(Text(px + 20, y + 64, value, 30, "sans-bold", INK))
        ops.append(Text(px + 20, y + 88, fonts.fit(caption, 15, bw - 32), 15, "sans", MUTED))
    y += 100 + 42

    # Top 10 companies: a table, a column per Look-through cell as the draft prints it
    _section(ops, PAD, y, room, "Top 10 companies, all holdings combined")
    cols = card.columns if len(card.columns) <= 4 else []
    col_w = 112
    name_w = room - 40 - col_w * (len(cols) + 1)
    hy = y + 42
    ops.append(Text(PAD, hy, "#", 15, "sans", MUTED))
    ops.append(Text(PAD + 40, hy, "Company", 15, "sans", MUTED))
    for j, c in enumerate(cols + ["Total"]):
        ops.append(Text(PAD + 40 + name_w + col_w * (j + 1), hy, c, 15, "sans", MUTED, "end"))
    ops.append(Rect(PAD, hy + 12, room, 1, RULE))
    ry = hy + 40
    for i, (name, cells, total) in enumerate(card.rows or [(n, [], v) for n, v in card.top]):
        ops.append(Text(PAD, ry, f"{i + 1}", 18, "sans", MUTED))
        ops.append(Text(PAD + 40, ry, fonts.fit(nice(name), 18, name_w - 16), 18, "sans", INK))
        shown = cells if cols else []
        for j, c in enumerate(shown):
            x = PAD + 40 + name_w + col_w * (j + 1)
            ops.append(Text(x, ry, f"{c}%" if num(c) is not None else "–", 18, "sans",
                            INK if num(c) is not None else MUTED, "end"))
        ops.append(Text(right, ry, pct(total), 18, "sans-bold", INK, "end"))
        ops.append(Rect(PAD, ry + 12, room, 1, RULE))
        ry += 32
    y = ry + 4

    # The company held through most routes, in one sentence
    lines = _hero_lines(card)
    if lines:
        ops.append(Rect(PAD, y, room, 72, PANEL))
        ops.append(Rect(PAD, y, 4, 72, NAVY))
        ops.append(Text(PAD + 20, y + 30, fonts.fit(lines[0], 17, room - 40), 17, "sans-bold", INK))
        ops.append(Text(PAD + 20, y + 56, fonts.fit(lines[1], 17, room - 40), 17, "sans", INK))
        y += 72 + 40

    # Countries and sectors side by side
    columns = [(t, b) for t, b in (("Countries", card.countries), ("Sectors", card.sectors)) if b]
    gap = 48
    col_w2 = (room - gap) / 2
    for i, (title, buckets) in enumerate(columns):
        _bucket_column(ops, PAD + i * (col_w2 + gap), y, col_w2, title, buckets, fonts)
    if not columns and card.partial:
        _section(ops, PAD, y, room, "Countries and sectors")
        ops.append(Text(PAD, y + 46, fonts.fit(
            "Not shown: they need every company in each fund, and this card reads each "
            "fund's factsheet top 10 only.", 17, room), 17, "sans", MUTED))

    # Notes
    ops.append(Rect(PAD, H - 102, room, 1, RULE))
    basis = ("Weights through funds use each fund's factsheet top 10, so they are minimums."
             if top10 else "Weights through funds use each fund's full holdings file.")
    ops.append(Text(PAD, H - 72, fonts.fit("Percentages of the portfolio's market value. " + basis,
                                           14, room), 14, "sans", MUTED))
    ops.append(Text(PAD, H - 48, "For research only, not financial advice. Made with Holdnote, "
                    "free and open source.", 14, "sans", MUTED))
    ops.append(Text(right, H - 48, REPO, 14, "sans-bold", NAVY, "end"))
    return ops


def _font_faces() -> str:
    """@font-face rules with the bundled faces inline, so the SVG looks the
    same in any browser; a viewer that ignores them falls back to FALLBACK."""
    import base64
    rules = []
    for file, family, weight, style in FACES.values():
        path = FONTS / file
        if path.exists():
            data = base64.b64encode(path.read_bytes()).decode("ascii")
            rules.append(f"@font-face{{font-family:'{family}';font-weight:{weight};"
                         f"font-style:{style};src:url(data:font/ttf;base64,{data}) format('truetype')}}")
    return "".join(rules)


def svg(ops: list[Text | Rect]) -> str:
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}">', f"<style>{_font_faces()}</style>"]
    for op in ops:
        if isinstance(op, Rect):
            out.append(f'<rect x="{op.x:.1f}" y="{op.y:.1f}" width="{op.w:.1f}" height="{op.h:.1f}" '
                       f'rx="{op.r:g}" fill="{op.color}"/>')
        else:
            _, family, weight, style = FACES[op.face]
            extra = f' letter-spacing="{op.spacing:g}"' if op.spacing else ""
            out.append(f'<text x="{op.x:.1f}" y="{op.y:.1f}" font-family="\'{family}\', '
                       f'{FALLBACK[family]}" font-size="{op.size}" font-weight="{weight}" '
                       f'font-style="{style}" fill="{op.color}" text-anchor="{op.anchor}"{extra}>'
                       f'{escape(op.s)}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def png(ops: list[Text | Rect], fonts: Fonts, path: Path) -> None:
    from PIL import Image, ImageDraw
    scale = 2  # draw at 2x and downsample, for smooth edges
    img = Image.new("RGB", (W * scale, H * scale), PAPER)
    d = ImageDraw.Draw(img)
    for op in ops:
        if isinstance(op, Rect):
            box = [op.x * scale, op.y * scale, (op.x + op.w) * scale - 1, (op.y + op.h) * scale - 1]
            if op.r:
                d.rounded_rectangle(box, radius=min(op.r, op.h / 2, op.w / 2) * scale, fill=op.color)
            else:
                d.rectangle(box, fill=op.color)
            continue
        font = fonts.get(op.face, op.size * scale)
        x = op.x * scale
        if op.spacing:
            if op.anchor == "end":
                x -= fonts.width(op.s, op.size, op.face, op.spacing) * scale
            for ch in op.s:
                d.text((x, op.y * scale), ch, font=font, fill=op.color, anchor="ls")
                x += font.getlength(ch) + op.spacing * scale
        else:
            d.text((x, op.y * scale), op.s, font=font, fill=op.color,
                   anchor="rs" if op.anchor == "end" else "ls")
    img.resize((W, H), Image.LANCZOS).save(path, optimize=True)


def make(draft: Path, out: Path) -> list[Path]:
    card = read(draft.read_text(encoding="utf-8"))
    fonts = Fonts()
    ops = layout(card, fonts)
    out.mkdir(parents=True, exist_ok=True)
    written = [out / "card.svg"]
    written[0].write_text(svg(ops), encoding="utf-8")
    if fonts.ok:
        png(ops, fonts, out / "card.png")
        written.append(out / "card.png")
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("draft", type=Path, help="a checked Mode C draft (with full SOURCES)")
    ap.add_argument("--out", type=Path, required=True, help="folder to write card.svg / card.png to")
    args = ap.parse_args(argv)
    try:
        written = make(args.draft, args.out)
    except Missing as exc:
        print(f"No card: {exc}")
        return 1
    print("\n".join(p.as_posix() for p in written))
    if len(written) == 1:
        print("PNG: not made - Pillow is not installed here; the SVG opens in any browser")
    return 0


if __name__ == "__main__":
    sys.exit(main())
