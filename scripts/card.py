#!/usr/bin/env python3
"""The portfolio card: one shareable image of what a portfolio looks through to.

    python3 scripts/card.py <draft.md> --out <folder>

Reads a checked Mode C draft (a real run or the demo) and draws its
Look-through, Hidden bets, Countries, Sectors and Holdings tables as one
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
from dataclasses import dataclass
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
PAD = 72
REPO = "github.com/Artvarna/buffettbot"

BG = "#0E1A2B"
PANEL = "#16263D"
INK = "#F4F1EA"
MUTED = "#9AA8BA"
GOLD = "#E8B04B"
TRACK = "#22344F"
REST = "#3A5072"  # the folded "Other" part of a stacked bar
# Stacked-bar segments: largest first, then the folded rest in TRACK.
SEGMENTS = ["#E8B04B", "#5FA8D3", "#8CC084", "#C77DBA"]

FONT_STACK = "Inter, 'Helvetica Neue', Arial, sans-serif"
FONT_FILES = {
    False: ["/usr/share/fonts/opentype/inter/Inter-Regular.otf",
            "/usr/share/fonts/truetype/inter/Inter-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/Library/Fonts/Arial.ttf", "C:/Windows/Fonts/arial.ttf"],
    True: ["/usr/share/fonts/opentype/inter/Inter-Bold.otf",
           "/usr/share/fonts/truetype/inter/Inter-Bold.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
           "/Library/Fonts/Arial Bold.ttf", "C:/Windows/Fonts/arialbd.ttf"],
}


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
        if r[0].startswith("Other ") or r[0].startswith("Cash and other") or "not stated" in r[0]:
            rest += v
        else:
            named.append((r[0], v))
    named.sort(key=lambda kv: (-kv[1], kv[0]))
    rest += sum((v for _, v in named[keep:]), Decimal(0))
    out = named[:keep]
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
    top = sorted(((r[0], num(r[-1])) for r in lt[1:] if num(r[-1]) is not None),
                 key=lambda kv: (-kv[1], kv[0]))[:10]
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
    countries = _buckets(_needed(t, "Countries"), 3) if "Countries" in t else []
    sectors = _buckets(_needed(t, "Sectors"), 3) if "Sectors" in t else []

    overlap = None
    hold = t.get("Holdings")
    if hold:
        for r in hold[1:]:
            shared = num(r[-1])
            m = re.match(r"^(\d+)", r[1])
            if shared and m and " - " in r[0] and (overlap is None or shared > overlap[2]):
                a, b = r[0].split(" - ", 1)
                overlap = (f"{a} and {b}", m.group(1), shared)

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
    partial = bool(re.search(r"^Look-through\b.*\bpartial\b", result, re.MULTILINE))
    return Card(as_of=as_of, demo="Demo" in mode, funds=funds, direct=direct,
                companies=companies, top=top, hero=hero, countries=countries,
                sectors=sectors, overlap=overlap, partial=partial)


# --- drawing ------------------------------------------------------------------

@dataclass
class Text:
    x: float
    y: float
    s: str
    size: int
    color: str = INK
    bold: bool = False
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
    """Pillow fonts when available: used to draw the PNG and to measure text,
    so long names are cut to fit in both files the same way."""

    def __init__(self) -> None:
        self.ok = False
        self.cache: dict[tuple[int, bool], object] = {}
        try:
            from PIL import ImageFont  # noqa: F401
            self.ok = True
        except ImportError:
            pass

    def get(self, size: int, bold: bool):
        from PIL import ImageFont
        key = (size, bold)
        if key not in self.cache:
            font = None
            for path in FONT_FILES[bold]:
                if Path(path).exists():
                    font = ImageFont.truetype(path, size)
                    break
            self.cache[key] = font or ImageFont.load_default(size)
        return self.cache[key]

    def width(self, s: str, size: int, bold: bool = False, spacing: float = 0) -> float:
        if self.ok:
            return self.get(size, bold).getlength(s) + spacing * max(len(s) - 1, 0)
        return len(s) * size * (0.6 if bold else 0.55) + spacing * max(len(s) - 1, 0)

    def fit(self, s: str, size: int, room: float, bold: bool = False) -> str:
        if self.width(s, size, bold) <= room:
            return s
        while s and self.width(s + "…", size, bold) > room:
            s = s[:-1]
        return s.rstrip() + "…"


def _routes(routes: list[tuple[str, Decimal]]) -> tuple[Decimal | None, list[str]]:
    direct = next((v for lab, v in routes if lab == "Direct"), None)
    funds = [lab.removeprefix("via ") for lab, _ in routes if lab != "Direct"]
    return direct, funds


def _and(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def layout(card: Card, fonts: Fonts) -> list[Text | Rect]:
    ops: list[Text | Rect] = [Rect(0, 0, W, H, BG)]
    room = W - 2 * PAD

    ops.append(Text(PAD, 96, "BUFFETTBOT", 22, GOLD, True, spacing=4))
    badge = ("DEMO · SYNTHETIC PORTFOLIO" if card.demo
             else "PARTIAL · FACTSHEET TOP 10s" if card.partial else "")
    if badge:
        bw = fonts.width(badge, 16, True, 1.5) + 32
        ops += [Rect(W - PAD - bw, 72, bw, 36, PANEL, 18),
                Text(W - PAD - 16, 96, badge, 16, MUTED, True, "end", 1.5)]
    ops.append(Text(PAD, 172, "What this portfolio actually owns", 50, INK, True))
    parts = []
    if card.companies:
        parts.append(f"{card.companies:,} companies")
    holds = [f"{len(card.funds)} fund{'s' if len(card.funds) != 1 else ''}"]
    if card.direct:
        holds.append(f"{card.direct} stock{'s' if card.direct != 1 else ''}")
    parts.append("inside " + " and ".join(holds))
    sub = " ".join(parts) + (f" · as of {card.as_of}" if card.as_of else "")
    ops.append(Text(PAD, 218, fonts.fit(sub, 24, room), 24, MUTED))

    # Hero: the biggest hidden bet
    y = 252
    ops.append(Rect(PAD, y, room, 196, PANEL, 20))
    if card.hero:
        name, routes, total, added = card.hero
        direct, funds = _routes(routes)
        ops.append(Text(PAD + 36, y + 50, "BIGGEST HIDDEN BET", 17, GOLD, True, spacing=2))
        big = pct(total)
        ops.append(Text(PAD + 36, y + 150, big, 84, GOLD, True))
        left = PAD + 36 + fonts.width(big, 84, True) + 40
        avail = PAD + room - 36 - left
        ops.append(Text(left, y + 108, fonts.fit(name, 34, avail, True), 34, INK, True))
        if direct is not None:
            line1 = f"{direct:.2f}% bought directly"
            line2 = f"+ {added:.2f}% more through {_and(funds)}"
        else:
            line1 = f"all of it through {_and(funds)}"
            line2 = "none of it bought directly"
        ops.append(Text(left, y + 146, fonts.fit(line1, 24, avail), 24, MUTED))
        ops.append(Text(left, y + 178, fonts.fit(line2, 24, avail), 24, MUTED))
    else:
        name, total = card.top[0]
        ops.append(Text(PAD + 36, y + 50, "LARGEST COMPANY", 17, GOLD, True, spacing=2))
        ops.append(Text(PAD + 36, y + 150, pct(total), 84, GOLD, True))
        left = PAD + 36 + fonts.width(pct(total), 84, True) + 40
        ops.append(Text(left, y + 120, fonts.fit(name, 34, PAD + room - 36 - left, True), 34, INK, True))

    # Top 10 companies
    y = 500
    ops.append(Text(PAD, y, "TOP 10 COMPANIES, ALL HOLDINGS COMBINED", 17, MUTED, True, spacing=2))
    biggest = max((v for _, v in card.top), default=Decimal(1)) or Decimal(1)
    name_w, val_w = 380, 96
    bar_x, bar_w = PAD + name_w, room - name_w - val_w
    for i, (name, value) in enumerate(card.top):
        ry = y + 20 + i * 36
        ops.append(Text(PAD, ry + 23, fonts.fit(name, 22, name_w - 20), 22, INK))
        ops.append(Rect(bar_x, ry + 6, bar_w, 22, TRACK, 11))
        ops.append(Rect(bar_x, ry + 6, max(float(value / biggest) * bar_w, 22), 22, GOLD, 11))
        ops.append(Text(W - PAD, ry + 23, pct(value), 22, INK, True, "end"))

    # Countries and sectors: one stacked bar each, legend under it
    y = 500 + 20 + 36 * len(card.top) + 50
    for title, buckets in (("COUNTRIES", card.countries), ("SECTORS", card.sectors)):
        if not buckets:
            continue
        ops.append(Text(PAD, y, title, 17, MUTED, True, spacing=2))
        total = sum((v for _, v in buckets), Decimal(0)) or Decimal(1)
        x = float(PAD)
        legend = []
        for i, (label, value) in enumerate(buckets):
            w = float(value / total) * room
            color = REST if label == "Other" else SEGMENTS[i % len(SEGMENTS)]
            ops.append(Rect(x, y + 16, max(w, 2), 26, color))
            x += w
            legend.append((label, value, color))
        lx, ly = float(PAD), y + 74
        for label, value, color in legend:
            item = f"{label} {pct(value)}"
            iw = fonts.width(item, 20) + 22
            if lx + iw > W - PAD:
                lx, ly = float(PAD), ly + 30
            ops.append(Rect(lx, ly - 13, 12, 12, color, 6))
            ops.append(Text(lx + 20, ly, item, 20, INK))
            lx += iw + 22
        y = ly + 52

    # The overlap line only where it clears the footer
    if card.overlap and y <= H - 122:
        pair, n, shared = card.overlap
        text = f"Fund overlap: {pair} share {int(n):,} companies · {pct(shared)} shared weight"
        ops.append(Text(PAD, y, fonts.fit(text, 22, room), 22, INK))

    ops.append(Rect(PAD, H - 96, room, 1, TRACK))
    ops.append(Text(PAD, H - 58, f"Made with BuffettBot · free and open source · {REPO}", 20, INK))
    ops.append(Text(PAD, H - 28, "Percentages of the portfolio's market value · research, "
                    "not financial advice", 16, MUTED))
    return ops


def svg(ops: list[Text | Rect]) -> str:
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'viewBox="0 0 {W} {H}">']
    for op in ops:
        if isinstance(op, Rect):
            out.append(f'<rect x="{op.x:.1f}" y="{op.y:.1f}" width="{op.w:.1f}" height="{op.h:.1f}" '
                       f'rx="{op.r:g}" fill="{op.color}"/>')
        else:
            extra = f' letter-spacing="{op.spacing:g}"' if op.spacing else ""
            out.append(f'<text x="{op.x:.1f}" y="{op.y:.1f}" font-family="{FONT_STACK}" '
                       f'font-size="{op.size}" font-weight="{700 if op.bold else 400}" '
                       f'fill="{op.color}" text-anchor="{op.anchor}"{extra}>{escape(op.s)}</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def png(ops: list[Text | Rect], fonts: Fonts, path: Path) -> None:
    from PIL import Image, ImageDraw
    scale = 2  # draw at 2x and downsample, for smooth edges
    img = Image.new("RGB", (W * scale, H * scale), BG)
    d = ImageDraw.Draw(img)
    for op in ops:
        if isinstance(op, Rect):
            box = [op.x * scale, op.y * scale, (op.x + op.w) * scale - 1, (op.y + op.h) * scale - 1]
            if op.r:
                d.rounded_rectangle(box, radius=min(op.r, op.h / 2, op.w / 2) * scale, fill=op.color)
            else:
                d.rectangle(box, fill=op.color)
        else:
            font = fonts.get(op.size * scale, op.bold)
            x = op.x * scale
            if op.spacing:
                width = fonts.width(op.s, op.size, op.bold, op.spacing) * scale
                if op.anchor == "end":
                    x -= width
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
