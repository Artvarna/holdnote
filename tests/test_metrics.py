"""Stock brief metric tables: references/stock-brief.md -> Margins, Expense
ratios, Returns, Growth.

SYNTHETIC. The ticker AAA and every figure are invented; nothing here is a
record of a run (RULES.md rule 15).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import contract  # noqa: E402
import render  # noqa: E402
from test_brief_layout import KEY_NUMBERS, RED_FLAGS, SCORECARD, TLDR, WHAT_CHANGED, brief  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

MARGINS = [
    "Margins (% of revenue, FY2021–FY2025)",
    "| Margin | FY2021 | FY2022 | FY2023 | FY2024 | FY2025 |",
    "|---|---|---|---|---|---|",
    "| Gross margin | 41.8% | 43.3% | 44.1% | 46.2% | 46.9% |",
    "| Operating margin | 29.8% | 30.3% | 29.8% | 31.5% | 31.9% |",
    "| EBITDA margin | 33.1% | 33.4% | 33.0% | 34.6% | 34.8% |",
    "| Pretax margin | 29.9% | 30.2% | 29.7% | 31.6% | 31.8% |",
    "| Net margin | 25.9% | 25.3% | 25.3% | 24.0% | 26.9% |",
    "| FCF margin | 24.0% | 28.3% | 25.8% | 27.0% | 27.4% |",
    "",
]
EXPENSES = [
    "Expense ratios (% of revenue; tax as % of pretax income)",
    "| Ratio | FY2021 | FY2022 | FY2023 | FY2024 | FY2025 |",
    "|---|---|---|---|---|---|",
    "| R&D | 6.0% | 6.7% | 7.8% | 8.0% | 7.9% |",
    "| SG&A | 6.0% | 6.4% | 6.5% | 6.7% | 6.6% |",
    "| Stock-based compensation | 2.4% | 2.3% | 2.9% | 3.1% | 3.0% |",
    "| Capex | 3.0% | 2.9% | 2.8% | 2.6% | 2.6% |",
    "| Effective tax rate | 13.3% | 16.2% | 14.7% | 24.1% | 15.6% |",
    "",
]
RETURNS = [
    "Returns (FY2021–FY2025)",
    "| Return | FY2021 | FY2022 | FY2023 | FY2024 | FY2025 |",
    "|---|---|---|---|---|---|",
    "| ROE | 147.4% | 175.5% | 156.1% | 157.4% | 151.3% |",
    "| ROIC | 47.3% | 55.6% | 56.1% | 57.5% | 64.0% |",
    "| ROA | 28.1% | 28.3% | 27.5% | 25.7% | 28.9% |",
    "| Asset turnover | 1.08 | 1.12 | 1.09 | 1.07 | 1.08 |",
    "| Cash conversion | 1.10 | 1.22 | 1.14 | 1.26 | 1.11 |",
    "",
]
GROWTH = [
    "Growth (YoY %, and CAGR FY2021–FY2025)",
    "| Line | FY2022 | FY2023 | FY2024 | FY2025 | CAGR |",
    "|---|---|---|---|---|---|",
    "| Revenue | +7.8% | -2.8% | +2.0% | +6.4% | +3.3% |",
    "| Diluted EPS | +8.9% | +0.3% | -0.8% | +10.2% | +4.5% |",
    "| Diluted shares | -3.5% | -2.9% | -2.7% | -2.5% | -2.9% |",
    "",
]
DETAIL = MARGINS + EXPENSES + RETURNS + GROWTH


def full(rows: list[str] = DETAIL) -> str:
    return brief(TLDR + SCORECARD + KEY_NUMBERS + WHAT_CHANGED + RED_FLAGS + rows)


def problems(text: str) -> list[str]:
    return contract.metric_table_problems(contract.split_sections(text))


def test_a_brief_with_every_metric_table_passes():
    assert contract.output_problems(full()) == []


def test_metric_tables_print_after_red_flags_only():
    early = brief(TLDR + SCORECARD + MARGINS + KEY_NUMBERS + WHAT_CHANGED + RED_FLAGS)
    found = contract.brief_layout_problems(contract.split_sections(early))
    assert any("'Margins" in p for p in found), found


def test_a_reasoned_gap_is_a_valid_cell():
    bank = [r.replace("| Gross margin | 41.8% |",
                      "| Gross margin | Not available — no gross profit line in the income statement |")
            for r in MARGINS]
    assert problems(full(bank)) == []


def test_a_bare_not_available_is_refused():
    bad = [r.replace("| Gross margin | 41.8% |", "| Gross margin | Not available |") for r in MARGINS]
    assert any("is not a figure" in p for p in problems(full(bad)))


def test_a_gross_margin_over_100_is_a_parse_error():
    bad = [r.replace("| Gross margin | 41.8% |", "| Gross margin | 418% |") for r in MARGINS]
    assert "Margins Gross margin 418% is over 100%: a parse error" in problems(full(bad))


def test_a_negative_tax_rate_is_refused():
    bad = [r.replace("| 13.3% |", "| -13.3% |") for r in EXPENSES]
    assert any("Effective tax rate -13.3% is negative" in p for p in problems(full(bad)))


def test_negative_margins_and_growth_are_allowed():
    loss = [r.replace("| 25.9% |", "| -4.1% |") for r in MARGINS]
    assert problems(full(loss)) == []


def test_metric_tables_render_with_plain_headings():
    out = render.render(full())
    for name in ("Margins", "Expense ratios", "Returns", "Growth"):
        assert re.search(rf"^### {name}$", out, re.MULTILINE), name


def test_the_spec_defines_every_margin_and_its_source():
    spec = (REPO / "references" / "stock-brief.md").read_text(encoding="utf-8")
    for line in ("Gross margin", "Operating margin", "EBITDA margin", "Pretax margin",
                 "Net margin", "FCF margin", "Effective tax rate", "ROIC", "Cash conversion",
                 "CAGR", "interest coverage", "current ratio", "EV/Sales", "payout ratio"):
        assert line in spec, line
    assert "`ShareBasedCompensation`" in spec and "`GrossProfit`" in spec
    skill = (REPO / "SKILL.md").read_text(encoding="utf-8")
    assert "net\nmargin" in skill or "net margin" in skill


def test_growth_cells_are_signed():
    # The AAPL run of 2026-10-21 printed "33.3%" beside "-2.8%".
    bad = [r.replace("| +7.8% |", "| 7.8% |") for r in GROWTH]
    assert "Growth Revenue 7.8% is unsigned; print +7.8%" in problems(full(bad))
