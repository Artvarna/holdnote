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

# Art direction: Holdnote's brand. Obsidian page, sand ink, the browline
# glasses in the header; Outfit for headlines and the big figures, Inter for
# the small type and tables; one accent (sand) with darker steps of it for
# the parts of a bar. Sand on obsidian is 7.9:1, MUTED on obsidian 4.6:1.
PAPER = "#161616"
INK = "#C2A284"
MUTED = "#8C7863"
RULE = "#38322C"
PANEL = "#221F1C"
SAND = "#C2A284"
ON_SAND = "#161616"
TRACK = "#2C2824"
# Parts of a bar, largest first; the folded Other is REST
SEGMENTS = ["#C2A284", "#9C8269", "#77644F", "#5A4D3F", "#433A31"]
REST = "#2C2824"
LOGO = HERE.parent / "assets" / "card" / "glasses.png"
LOGO_RATIO = 480 / 184  # width / height of glasses.png

FONTS = HERE.parent / "assets" / "fonts"
# key -> (file, SVG family, weight, style)
FACES = {
    "sans": ("Inter_400Regular.ttf", "BB Sans", 400, "normal"),
    "sans-bold": ("Inter_600SemiBold.ttf", "BB Sans", 600, "normal"),
    "display": ("Outfit_700Bold.ttf", "BB Display", 700, "normal"),
    "display-semi": ("Outfit_600SemiBold.ttf", "BB Display", 600, "normal"),
}
FALLBACK = {"BB Serif": "Georgia, 'Times New Roman', serif",
            "BB Display": "'Helvetica Neue', Arial, sans-serif",
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


@dataclass
class Picture:
    x: float
    y: float
    w: float
    h: float
    path: Path


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
    ops.append(Rect(x, y + 12, w, 1.5, SAND))


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
                        REST if label == "Other" else SAND))
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


def _header(ops: list, fonts: "Fonts", title: str, as_of: str, badge: str | None) -> None:
    """The brand line (glasses + Holdnote), the date, an optional badge, and
    the card's title in large type."""
    right = W - PAD
    gh = 26
    if LOGO.exists():
        ops.append(Picture(PAD, 44, gh * LOGO_RATIO, gh, LOGO))
    ops.append(Text(PAD + gh * LOGO_RATIO + 14, 66, "Holdnote", 26, "display-semi", SAND))
    ops.append(Text(right, 64, f"As of {as_of}", 18, "sans", MUTED, "end"))
    if badge:
        bw = fonts.width(badge, 13, "sans-bold", 1.2) + 28
        ops.append(Rect(right - bw, 84, bw, 30, SAND, 15))
        ops.append(Text(right - 14, 104, badge, 13, "sans-bold", ON_SAND, "end", 1.2))
    ops.append(Text(PAD, 172, title, 58, "display", SAND, spacing=-1))


def _figure(ops: list, fonts: "Fonts", x: float, y: float, w: float, h: float,
            title: str, value: str, caption: str = "", value_size: int = 34) -> None:
    """A sand panel with a big figure: the numbers people screenshot."""
    ops.append(Rect(x, y, w, h, SAND, 18))
    ops.append(Text(x + 22, y + 32, fonts.fit(title.upper(), 13, w - 40, "sans-bold"), 13,
                    "sans-bold", ON_SAND, spacing=1.2))
    ops.append(Text(x + 22, y + 32 + value_size + 14, value, value_size, "display", ON_SAND))
    if caption:
        ops.append(Text(x + 22, y + h - 18, fonts.fit(caption, 15, w - 40), 15, "sans", ON_SAND))


def layout(card: Card, fonts: Fonts) -> list[Text | Rect]:
    ops: list[Text | Rect] = [Rect(0, 0, W, H, PAPER)]
    room = W - 2 * PAD
    right = W - PAD

    badge = ("DEMO · SYNTHETIC PORTFOLIO" if card.demo
             else card.partial_label if card.partial else "")
    _header(ops, fonts, "What this portfolio owns", _date(card.as_of) if card.as_of else "",
            badge or None)

    parts = []
    if card.companies:
        parts.append(f"{card.companies:,} companies")
    holds = [f"{len(card.funds)} fund{'s' if len(card.funds) != 1 else ''}"]
    if card.direct:
        holds.append(f"{card.direct} stock{'s' if card.direct != 1 else ''}")
    deck = (" ".join(parts + ["inside " + " and ".join(holds)]) if parts
            else "Holdings: " + " and ".join(holds))
    ops.append(Text(PAD, 214, fonts.fit(deck, 21, room), 21, "sans", MUTED))

    # Portfolio composition: one bar, the Allocation weights
    y = 262
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
        _figure(ops, fonts, PAD + i * (bw + gap), y, bw, 128, title, value, caption)
    y += 128 + 36

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
        ops.append(Rect(PAD, y, room, 72, PANEL, 14))
        ops.append(Rect(PAD, y + 14, 4, 44, SAND, 2))
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
    ops.append(Text(right, H - 48, REPO, 14, "sans-bold", SAND, "end"))
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
    w, h = int(ops[0].w), int(ops[0].h)  # the page: the first op is always its background
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
           f'viewBox="0 0 {w} {h}">', f"<style>{_font_faces()}</style>"]
    import base64
    for op in ops:
        if isinstance(op, Picture):
            data = base64.b64encode(op.path.read_bytes()).decode("ascii")
            out.append(f'<image x="{op.x:.1f}" y="{op.y:.1f}" width="{op.w:.1f}" height="{op.h:.1f}" '
                       f'href="data:image/png;base64,{data}"/>')
            continue
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
    w, h = int(ops[0].w), int(ops[0].h)
    img = Image.new("RGB", (w * scale, h * scale), PAPER)
    d = ImageDraw.Draw(img)
    for op in ops:
        if isinstance(op, Picture):
            logo = Image.open(op.path).convert("RGBA").resize(
                (round(op.w * scale), round(op.h * scale)), Image.LANCZOS)
            img.paste(logo, (round(op.x * scale), round(op.y * scale)), logo)
            continue
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
    img.resize((w, h), Image.LANCZOS).save(path, optimize=True)


# --- the Decision Mirror card (references/decision-mirror.md -> Card) -------

def _pct_value(text: str | None) -> Decimal | None:
    if not text or not text.endswith("%"):
        return None
    try:
        return Decimal(text.rstrip("%"))
    except InvalidOperation:
        return None


def mirror_layout(summary: dict, fonts: "Fonts") -> list[Text | Rect]:
    """Me vs my lazy twin: percentages of the money put in, and nothing else."""
    ops: list[Text | Rect] = [Rect(0, 0, W, H, PAPER)]
    room = W - 2 * PAD
    right = W - PAD
    lazy = summary["twin"] == "lazy"
    _header(ops, fonts, "Me vs my lazy twin" if lazy else "My picks vs my twin's",
            _date(summary["as_of"]), "DEMO · SYNTHETIC" if summary.get("demo") else None)
    twin_line = (f"The twin put every deposit into {summary['benchmark']} at once and never touched it."
                 if lazy else
                 f"The twin made the same purchases on the same days, in {summary['benchmark']}.")
    ops.append(Text(PAD, 214, fonts.fit(twin_line, 21, room), 21, "sans", MUTED))
    ops.append(Text(PAD, 244, f"{_date(summary['from'])} to {_date(summary['as_of'])}",
                    21, "sans", MUTED))

    # The headline: the one number people share
    y = 288
    ops.append(Rect(PAD, y, room, 300, SAND, 24))
    ops.append(Text(PAD + 40, y + 52, "ME MINUS MY TWIN", 15, "sans-bold", ON_SAND, spacing=1.6))
    shown = summary["gap_pct"]
    if shown.startswith("-"):
        shown = "\u2212" + shown[1:]  # a true minus sign, as wide as the plus
    ops.append(Text(PAD + 34, y + 206, shown, 160, "display", ON_SAND, spacing=-4))
    ops.append(Text(PAD + 40, y + 262, f"of {summary['basis']}", 21, "sans", ON_SAND))
    y += 300 + 36

    # Where it came from
    parts = [("What I picked", summary["picks_pct"])]
    if lazy and summary.get("waiting_pct"):
        parts.append(("Cash left waiting", summary["waiting_pct"]))
    gap = 20
    bw = (room - gap * (len(parts) - 1)) / len(parts)
    for i, (title, value) in enumerate(parts):
        px = PAD + i * (bw + gap)
        ops.append(Rect(px, y, bw, 104, PANEL, 18))
        ops.append(Text(px + 24, y + 34, title.upper(), 13, "sans-bold", MUTED, spacing=1.2))
        ops.append(Text(px + 24, y + 82, value or "-", 36, "display", INK))
    y += 104 + 44

    # By holding: a bar either side of zero
    rows = [(t, v, raw) for t, raw in summary.get("holdings_pct", {}).items()
            if (v := _pct_value(raw)) is not None]
    rows.sort(key=lambda kv: -abs(kv[1]))
    rows = rows[:6]
    if rows:
        _section(ops, PAD, y, room, "By holding, me minus my twin")
        ry = y + 52
        scale = max(abs(v) for _, v, _ in rows) or Decimal(1)
        mid = PAD + 200 + (room - 320) / 2
        half = (room - 320) / 2
        for name, v, raw in rows:
            ops.append(Text(PAD, ry, fonts.fit(name, 18, 180), 18, "sans", INK))
            length = float(abs(v) / scale) * half
            x = mid if v >= 0 else mid - length
            ops.append(Rect(x, ry - 14, max(length, 2), 16, SAND if v >= 0 else SEGMENTS[2]))
            ops.append(Text(right, ry, raw, 18, "sans-bold", INK, "end"))
            ry += 36
        ops.append(Rect(mid, y + 34, 1, ry - y - 46, RULE))
        y = ry + 8
        name, v, raw = rows[0]
        y += 24
        ops.append(Rect(PAD, y, room, 72, PANEL, 14))
        ops.append(Rect(PAD, y + 14, 4, 44, SAND, 2))
        ops.append(Text(PAD + 20, y + 30, fonts.fit(f"Largest single holding: {name}, {raw}. "
                                                    f"Picks gap in total: {summary['picks_pct']}.",
                                                    17, room - 40), 17, "sans-bold", INK))
        ops.append(Text(PAD + 20, y + 56, fonts.fit("One holding's run is one holding's story, "
                                                    "not a pattern.", 17, room - 40),
                        17, "sans", INK))
        y += 72 + 16

    note = (f"History: {summary['months']} months, {summary['trades']} trades."
            + (" This much history says little about skill." if summary.get("short_history") else ""))
    ops.append(Text(PAD, y + 24, fonts.fit(note, 17, room), 17, "sans-bold" if summary.get(
        "short_history") else "sans", INK))
    if not summary.get("complete", True):
        ops.append(Text(PAD, y + 52, fonts.fit("Not every holding could be included; the report "
                                               "says which.", 16, room), 16, "sans", MUTED))

    ops.append(Rect(PAD, H - 102, room, 1, RULE))
    ops.append(Text(PAD, H - 72, fonts.fit("Percentages of the money put in. The past only: "
                                           "it changes with every day's prices.", 14, room),
                    14, "sans", MUTED))
    ops.append(Text(PAD, H - 48, "For research only, not financial advice. Made with Holdnote, "
                    "free and open source.", 14, "sans", MUTED))
    ops.append(Text(right, H - 48, REPO, 14, "sans-bold", SAND, "end"))
    return ops


WW, WH = 1200, 675  # the wide Mirror card: the shape X shows in full in a timeline


def mirror_wide_layout(summary: dict, fonts: "Fonts") -> list[Text | Rect]:
    """The same Mirror card for X's timeline: the big figure on the right, the
    parts and the history under it. Percentages only, like the tall card."""
    ops: list = [Rect(0, 0, WW, WH, PAPER)]
    pad = 56
    lazy = summary["twin"] == "lazy"
    gh = 24
    if LOGO.exists():
        ops.append(Picture(pad, 44, gh * LOGO_RATIO, gh, LOGO))
    ops.append(Text(pad + gh * LOGO_RATIO + 12, 64, "Holdnote", 24, "display-semi", SAND))
    if summary.get("demo"):
        badge = "DEMO · SYNTHETIC"
        bw = fonts.width(badge, 12, "sans-bold", 1.2) + 26
        ops.append(Rect(WW - pad - bw, 40, bw, 28, SAND, 14))
        ops.append(Text(WW - pad - 13, 59, badge, 12, "sans-bold", ON_SAND, "end", 1.2))

    left = 470
    ops.append(Text(pad, 168, "Me vs my" if lazy else "My picks vs", 54, "display", SAND, spacing=-1))
    ops.append(Text(pad, 228, "lazy twin" if lazy else "my twin's", 54, "display", SAND, spacing=-1))
    words = (f"The twin put every deposit into {summary['benchmark']} at once and never touched it."
             if lazy else f"The twin made the same purchases on the same days, in {summary['benchmark']}.").split()
    lines, cur = [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        if fonts.width(trial, 18) <= left - pad - 10:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    lines.append(cur)
    ty = 282
    for ln in lines[:4]:
        ops.append(Text(pad, ty, ln, 18, "sans", MUTED))
        ty += 26
    ops.append(Text(pad, ty + 8, f"{_date(summary['from'])} to {_date(summary['as_of'])}", 18, "sans", MUTED))

    # the big figure
    bx, by, bw2, bh = left + 24, 100, WW - pad - left - 24, 300
    ops.append(Rect(bx, by, bw2, bh, SAND, 24))
    ops.append(Text(bx + 36, by + 50, "ME MINUS MY TWIN", 14, "sans-bold", ON_SAND, spacing=1.6))
    shown = summary["gap_pct"]
    if shown.startswith("-"):
        shown = "\u2212" + shown[1:]
    size = 150
    while size > 90 and fonts.width(shown, size, "display", -4) > bw2 - 64:
        size -= 6
    ops.append(Text(bx + 30, by + 205, shown, size, "display", ON_SAND, spacing=-4))
    ops.append(Text(bx + 36, by + 262, f"of {summary['basis']}", 19, "sans", ON_SAND))

    parts = [("What I picked", summary["picks_pct"])]
    if lazy and summary.get("waiting_pct"):
        parts.append(("Cash left waiting", summary["waiting_pct"]))
    py, gap = by + bh + 20, 20
    pw = (bw2 - gap * (len(parts) - 1)) / len(parts)
    for i, (title, value) in enumerate(parts):
        px = bx + i * (pw + gap)
        ops.append(Rect(px, py, pw, 96, PANEL, 18))
        ops.append(Text(px + 22, py + 32, title.upper(), 12, "sans-bold", MUTED, spacing=1.2))
        ops.append(Text(px + 22, py + 76, value or "-", 32, "display", INK))

    note = (f"History: {summary['months']} months, {summary['trades']} trades."
            + (" This much history says little about skill." if summary.get("short_history") else ""))
    ops.append(Text(pad, WH - 92, fonts.fit(note, 15, WW - 2 * pad), 15,
                    "sans-bold" if summary.get("short_history") else "sans", INK))
    ops.append(Rect(pad, WH - 72, WW - 2 * pad, 1, RULE))
    ops.append(Text(pad, WH - 40, "Percentages of the money put in. The past only. Not financial advice.",
                    14, "sans", MUTED))
    ops.append(Text(WW - pad, WH - 40, REPO, 14, "sans-bold", SAND, "end"))
    return ops


def make_mirror(summary_path: Path, out: Path) -> list[Path]:
    import json

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if _pct_value(summary.get("gap_pct")) is None:
        raise Missing(f"{summary_path.name} has no gap to draw ({summary.get('gap_pct')})")
    fonts = Fonts()
    ops = mirror_layout(summary, fonts)
    out.mkdir(parents=True, exist_ok=True)
    written = [out / "mirror-card.svg"]
    written[0].write_text(svg(ops), encoding="utf-8")
    wide = mirror_wide_layout(summary, fonts)
    (out / "mirror-card-wide.svg").write_text(svg(wide), encoding="utf-8")
    if fonts.ok:
        png(ops, fonts, out / "mirror-card.png")
        written.append(out / "mirror-card.png")
        png(wide, fonts, out / "mirror-card-wide.png")
        written.append(out / "mirror-card-wide.png")
    written.append(out / "mirror-card-wide.svg")
    return written


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
    ap.add_argument("draft", type=Path, nargs="?", help="a checked Mode C draft (with full SOURCES)")
    ap.add_argument("--mirror", type=Path, default=None,
                    help="a Decision Mirror summary (mirror.py report --json) instead of a draft")
    ap.add_argument("--out", type=Path, required=True, help="folder to write card.svg / card.png to")
    args = ap.parse_args(argv)
    if (args.draft is None) == (args.mirror is None):
        ap.error("give a Mode C draft or --mirror, one of the two")
    try:
        written = make_mirror(args.mirror, args.out) if args.mirror else make(args.draft, args.out)
    except Missing as exc:
        print(f"No card: {exc}")
        return 1
    print("\n".join(p.as_posix() for p in written))
    if len(written) == 1:
        print("PNG: not made - Pillow is not installed here; the SVG opens in any browser")
    return 0


if __name__ == "__main__":
    sys.exit(main())
