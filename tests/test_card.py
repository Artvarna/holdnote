"""Tests for scripts/card.py: the shareable portfolio card.

The card is drawn from a checked Mode C draft. It must carry only the draft's
own percentages -- never a quantity, close, value or amount -- label the demo
as synthetic, and refuse a draft whose look-through is Not available.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import card  # noqa: E402
import demo  # noqa: E402


@pytest.fixture(scope="module")
def demo_draft(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("demo") / "draft.md"
    draft, _ = demo.build(demo.ORDER, proof=False)
    path.write_text(draft, encoding="utf-8")
    return path


def svg_text(svg: str) -> str:
    return " ".join(re.findall(r">([^<]+)</text>", svg))


def test_demo_card_draws_the_drafts_own_figures(demo_draft, tmp_path):
    written = card.make(demo_draft, tmp_path)
    assert written[0].name == "card.svg"
    text = svg_text(written[0].read_text(encoding="utf-8"))
    assert "DEMO · SYNTHETIC PORTFOLIO" in text
    # Expected figures come from the draft, so a new snapshot changes nothing here
    t = card.tables(demo_draft.read_text(encoding="utf-8").split("RESULT", 1)[1])
    bets = [r for r in t["Hidden bets"][1:] if r[0] != "none"]
    hero = max(bets, key=lambda r: card.Decimal(r[4]))  # most Added by the others
    assert "BIGGEST HIDDEN BET" in text and f"{hero[3]}%" in text and hero[0] in text
    if hero[2].startswith("Direct "):
        assert f"{hero[2].split()[1]}% owned directly" in text
    assert f"+ {hero[4]}% more inside SPYI and SPY5" in text
    us = next(r for r in t["Countries"][1:] if r[0] == "United States")
    assert f"United States {us[-1]}%" in text
    pair = t["Holdings"][1]
    n = pair[1].split()[0]
    assert f"SPYI and SPY5 share {n} companies, {pair[-1]}% shared weight." in text
    assert "not financial advice" in text


def test_card_carries_no_amounts(demo_draft, tmp_path):
    draft = demo_draft.read_text(encoding="utf-8")
    text = svg_text(card.make(demo_draft, tmp_path)[0].read_text(encoding="utf-8"))
    alloc = card.tables(draft.split("RESULT", 1)[1])["Allocation"]
    header = alloc[0]
    # Quantities are small integers a rank or count can equal; the bare-number
    # check below covers them
    for column in ("Close", "Value (EUR)"):
        i = header.index(column)
        for row in alloc[1:]:
            value = row[i].split()[-1] if row[i] else ""
            if value:
                assert not re.search(rf"(?<![\d.,]){re.escape(value)}(?![\d.,%])", text), \
                    f"{column} {row[i]} is on the card"
    assert "EUR" not in text and "USD" not in text
    # Every bare number is a count or the date, never an amount
    c = card.read(draft)
    bare = re.findall(r"(?<![\w.,])\d[\d,]*(?:\.\d+)?(?![\d.,%]|-\d)",
                      text.replace(card._date(c.as_of), ""))
    counts = {f"{c.companies:,}", str(len(c.funds)), str(c.direct), f"{int(c.overlap[1]):,}",
              *(str(i) for i in range(1, 11))}  # the ledger's ranks
    assert set(bare) <= counts, bare


def test_every_percentage_on_the_card_is_in_the_draft(demo_draft, tmp_path):
    draft = demo_draft.read_text(encoding="utf-8")
    text = svg_text(card.make(demo_draft, tmp_path)[0].read_text(encoding="utf-8"))
    c = card.read(draft)
    # The folded Other parts: the Total row minus the named ones
    others = {f"{v:.2f}" for label, v in c.countries + c.sectors if label == "Other"}
    for value in re.findall(r"(\d+\.\d{2})%", text):
        assert value in draft or value in others, f"{value}% is not a figure of the draft"


def test_card_refuses_a_draft_without_lookthrough(demo_draft, tmp_path, capsys):
    draft = demo_draft.read_text(encoding="utf-8")
    broken = re.sub(r"Look-through \(market weights[^\n]*\n(\|[^\n]*\n)+",
                    "Look-through\n| Company | Total |\n|---|---|\n"
                    "| all | Not available - no --prices file, so no market weights |\n", draft)
    path = tmp_path / "broken.md"
    path.write_text(broken, encoding="utf-8")
    assert card.main([str(path), "--out", str(tmp_path / "out")]) == 1
    assert "No card: Look-through is Not available - no --prices file" in capsys.readouterr().out
    assert not (tmp_path / "out" / "card.svg").exists()


def test_fund_only_hero_says_none_is_owned_directly():
    c = card.Card(as_of="2026-10-15", demo=False, funds=["A", "B"], direct=0, companies=3000,
                  top=[("NVIDIA Corporation", card.Decimal("4.57"))],
                  hero=("NVIDIA Corporation", [("via A", card.Decimal("2.60")),
                                               ("via B", card.Decimal("1.97"))],
                        card.Decimal("4.57"), card.Decimal("1.97")),
                  countries=[], sectors=[], overlap=None)
    text = svg_text(card.svg(card.layout(c, card.Fonts())))
    assert "2.60% through A" in text and "+ 1.97% more inside B" in text
    assert "owned directly" not in text
    assert "DEMO" not in text
    assert "3,000 companies inside 2 funds" in text and "AS OF 15 OCT 2026" in text


def test_without_pillow_the_svg_is_still_written(demo_draft, tmp_path, monkeypatch):
    monkeypatch.setattr(card.Fonts, "__init__", lambda self: (setattr(self, "ok", False),
                                                              setattr(self, "cache", {}))[0])
    written = card.make(demo_draft, tmp_path)
    assert [p.name for p in written] == ["card.svg"]


def test_a_partial_lookthrough_is_said_on_the_card(demo_draft, tmp_path):
    draft = demo_draft.read_text(encoding="utf-8").replace(
        "Look-through (market weights, as of", "Look-through (top-10 depth, partial; market weights, as of", 1)
    assert card.read(draft).partial
    path = tmp_path / "partial.md"
    path.write_text(draft, encoding="utf-8")
    text = svg_text(card.make(path, tmp_path)[0].read_text(encoding="utf-8"))
    assert "PARTIAL · TOP-10 DEPTH" in text or "DEMO · SYNTHETIC PORTFOLIO" in text
    c = card.read(draft)
    c.demo = False
    assert "PARTIAL · TOP-10 DEPTH" in svg_text(card.svg(card.layout(c, card.Fonts())))


def test_whole_portfolio_parts_add_to_100_on_the_card():
    # Cells rounded one by one can leave a Total row at 100.04 (the demo's
    # Sectors on 2026-10-16); the card's Other is what the named parts leave.
    rows = [["Sector", "Direct", "via A", "Total"],
            ["Tech", "-", "27.41", "27.41"], ["Discretionary", "7.21", "7.33", "14.54"],
            ["Staples", "8.46", "4.07", "12.53"], ["Financials", "-", "12.51", "12.51"],
            ["Industrials", "-", "11.00", "11.00"], ["Health Care", "-", "11.00", "11.00"],
            ["Energy", "-", "11.05", "11.05"], ["Total", "15.67", "84.37", "100.04"]]
    parts = card._buckets(rows, 3)
    assert parts[-1] == ("Other", card.Decimal("45.52"))
    assert sum(v for _, v in parts) == 100


def test_a_partial_table_keeps_its_own_total():
    rows = [["Sector", "via A", "Total"], ["Tech", "30.00", "30.00"], ["Rest", "20.00", "20.00"],
            ["Total", "50.00", "50.00"]]
    assert card._buckets(rows, 1) == [("Tech", card.Decimal("30.00")), ("Other", card.Decimal("20.00"))]


def test_own_shares_read_as_shares_not_a_place():
    c = card.Card(as_of="2026-10-15", demo=False, funds=["A"], direct=1, companies=3000,
                  top=[("NVIDIA Corporation", card.Decimal("5.00"))],
                  hero=("NVIDIA Corporation", [("Direct", card.Decimal("1.00")),
                                               ("via A", card.Decimal("4.00"))],
                        card.Decimal("5.00"), card.Decimal("1.00")),
                  countries=[], sectors=[], overlap=None)
    text = svg_text(card.svg(card.layout(c, card.Fonts())))
    assert "+ 1.00% more in your own shares" in text
    assert "inside your own shares" not in text
