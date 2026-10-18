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

# Art direction: an annual letter. Cream paper, ink, hairline rules, a serif
# display face for the title and the large figures, and one accent: the
# hidden part of the biggest bet, drawn in ochre beside the part a single
# holding shows.
PAPER = "#F4EFE4"
INK = "#1B1A17"
MUTED = "#6E6A60"
RULE = "#D6CDBA"
TRACK = "#E6DECD"
GREEN = "#1F5B43"
OCHRE = "#B07A1F"
# Stacked-bar parts, largest first; the folded Other is REST
SEGMENTS = ["#1F5B43", "#B07A1F", "#7A8F6A", "#8C5A4B"]
REST = "#CFC5B0"

FONTS = HERE.parent / "assets" / "fonts"
# key -> (file, SVG family, weight, style)
FACES = {
    "serif": ("Fraunces_600SemiBold.ttf", "BB Serif", 600, "normal"),
    "serif-italic": ("Fraunces_600SemiBold_Italic.ttf", "BB Serif", 600, "italic"),
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


def _label(x: float, y: float, s: str, color: str = MUTED, anchor: str = "start") -> Text:
    """Small tracked capitals: section labels."""
    return Text(x, y, s.upper(), 15, "sans-bold", color, anchor, 2.2)


def _date(iso: str) -> str:
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", iso or "")
    return f"{int(m[3])} {months[int(m[2]) - 1]} {m[1]}" if m else iso


def _bucket_column(ops: list, x: float, y: float, w: float, title: str,
                   buckets: list[tuple[str, Decimal]], fonts: Fonts) -> None:
    ops.append(_label(x, y, title))
    total = sum((v for _, v in buckets), Decimal(0)) or Decimal(1)
    bx = x
    for i, (label, value) in enumerate(buckets):
        seg = float(value / total) * w
        color = REST if label == "Other" else SEGMENTS[i % len(SEGMENTS)]
        ops.append(Rect(bx, y + 16, max(seg - 2, 1), 10, color))
        bx += seg
    for i, (label, value) in enumerate(buckets):
        ry = y + 58 + i * 30
        color = REST if label == "Other" else SEGMENTS[i % len(SEGMENTS)]
        ops.append(Rect(x, ry - 11, 10, 10, color, 5))
        value_s = pct(value)
        room = w - 22 - fonts.width(value_s, 20, "sans-bold") - 16
        ops.append(Text(x + 20, ry, fonts.fit(label, 20, room), 20, "sans", INK))
        ops.append(Text(x + w, ry, value_s, 20, "sans-bold", INK, "end"))


def layout(card: Card, fonts: Fonts) -> list[Text | Rect]:
    ops: list[Text | Rect] = [Rect(0, 0, W, H, PAPER)]
    room = W - 2 * PAD
    right = W - PAD

    # Masthead
    ops.append(Text(PAD, 78, "BUFFETTBOT", 18, "sans-bold", INK, spacing=4))
    badge = ("DEMO · SYNTHETIC PORTFOLIO" if card.demo
             else "PARTIAL · TOP-10 DEPTH" if card.partial else "")
    if badge:
        ops.append(_label(right, 78, badge, OCHRE, "end"))
    elif card.as_of:
        ops.append(_label(right, 78, f"As of {_date(card.as_of)}", MUTED, "end"))
    ops.append(Rect(PAD, 102, room, 1.5, INK))

    # Title, the second line in italic: the editorial turn
    ops.append(Text(PAD, 186, "What this portfolio", 64, "serif", INK))
    ops.append(Text(PAD, 256, "actually owns.", 64, "serif-italic", GREEN))
    parts = []
    if card.companies:
        parts.append(f"{card.companies:,} companies")
    holds = [f"{len(card.funds)} fund{'s' if len(card.funds) != 1 else ''}"]
    if card.direct:
        holds.append(f"{card.direct} stock{'s' if card.direct != 1 else ''}")
    deck = " ".join(parts + ["inside " + " and ".join(holds)])
    if (badge or not card.as_of) and card.as_of:
        deck += f" · as of {_date(card.as_of)}"
    ops.append(Text(PAD, 304, fonts.fit(deck, 24, room), 24, "sans", MUTED))

    # Hero: the biggest hidden bet, and the bar that splits it
    y = 340
    ops.append(Rect(PAD, y, room, 1, RULE))
    if card.hero:
        name, routes, total, added = card.hero
        top_label, largest = max(routes, key=lambda r: (r[1], r[0] == "Direct"))
        others = [("your own shares" if lab == "Direct" else lab.removeprefix("via "))
                  for lab, _ in routes if lab != top_label]
        ops.append(_label(PAD, y + 42, "The biggest hidden bet", OCHRE))
        big = pct(total)
        ops.append(Text(PAD - 4, y + 168, big, 132, "serif", INK))
        left = PAD + fonts.width(big, 132, "serif") + 36
        avail = right - left
        ops.append(Text(left, y + 98, fonts.fit(name, 34, avail, "serif"), 34, "serif", INK))
        seen = (f"{largest:.2f}% owned directly" if top_label == "Direct"
                else f"{largest:.2f}% through {top_label.removeprefix('via ')}")
        ops.append(Text(left, y + 134, fonts.fit(seen, 22, avail), 22, "sans", INK))
        ops.append(Text(left, y + 166, fonts.fit(f"+ {added:.2f}% more inside {_and(others)}",
                                                 22, avail), 22, "sans-bold", OCHRE))
        # The signature: one bar, the part a single holding shows in ink and
        # the part the others add in ochre
        by = y + 200
        split = float(largest / total) * room
        ops.append(Rect(PAD, by, split - 2, 14, INK))
        ops.append(Rect(PAD + split, by, room - split, 14, OCHRE))
        ops.append(Text(PAD, by + 40, "what one holding shows", 17, "sans", MUTED))
        ops.append(Text(right, by + 40, "what the others add", 17, "sans", OCHRE, "end"))
    else:
        name, total = card.top[0]
        ops.append(_label(PAD, y + 42, "The largest company, all holdings combined", GREEN))
        ops.append(Text(PAD - 4, y + 168, pct(total), 132, "serif", INK))
        left = PAD + fonts.width(pct(total), 132, "serif") + 36
        ops.append(Text(left, y + 120, fonts.fit(name, 34, right - left, "serif"), 34, "serif", INK))
    y = 604
    ops.append(Rect(PAD, y, room, 1, RULE))

    # Top 10: a ledger -- rank, name, a hairline bar, the figure
    ops.append(_label(PAD, y + 44, "Top 10 companies, all holdings combined"))
    biggest = max((v for _, v in card.top), default=Decimal(1)) or Decimal(1)
    rank_w, name_w, val_w = 44, 400, 92
    bar_x = PAD + rank_w + name_w
    bar_w = room - rank_w - name_w - val_w
    for i, (name, value) in enumerate(card.top):
        ry = y + 86 + i * 30
        ops.append(Text(PAD, ry, f"{i + 1}", 20, "serif-italic", MUTED))
        ops.append(Text(PAD + rank_w, ry, fonts.fit(name, 21, name_w - 24), 21, "sans", INK))
        ops.append(Rect(bar_x, ry - 9, bar_w, 4, TRACK, 2))
        ops.append(Rect(bar_x, ry - 9, max(float(value / biggest) * bar_w, 4), 4, GREEN, 2))
        ops.append(Text(right, ry, pct(value), 21, "sans-bold", INK, "end"))
    y = y + 86 + 30 * (len(card.top) - 1) + 28
    ops.append(Rect(PAD, y, room, 1, RULE))

    # Countries and sectors side by side
    columns = [(t, b) for t, b in (("Countries", card.countries), ("Sectors", card.sectors)) if b]
    gap = 48
    col_w = (room - gap) / 2
    for i, (title, buckets) in enumerate(columns):
        _bucket_column(ops, PAD + i * (col_w + gap), y + 44, col_w, title, buckets, fonts)
    if columns:
        y += 44 + 58 + 30 * (max(len(b) for _, b in columns) - 1) + 8

    # Overlap, in the serif's italic, where it clears the footer
    if card.overlap and y + 44 <= H - 104:
        pair, n, shared = card.overlap
        text = f"{pair} share {int(n):,} companies, {pct(shared)} shared weight."
        ops.append(Text(PAD, y + 44, fonts.fit(text, 24, room, "serif-italic"), 24,
                        "serif-italic", INK))

    # Footer
    ops.append(Rect(PAD, H - 92, room, 1.5, INK))
    ops.append(Text(PAD, H - 58, "Made with BuffettBot, free and open source", 18, "sans-bold", INK))
    ops.append(Text(right, H - 58, REPO, 18, "sans-bold", GREEN, "end"))
    ops.append(Text(PAD, H - 30, "Percentages of the portfolio's market value. Research, "
                    "not financial advice.", 15, "sans", MUTED))
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
