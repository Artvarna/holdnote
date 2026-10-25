"""Head-to-head: references/head-to-head.md, RULES.md rule 6 v15.

SYNTHETIC. The tickers FFA, FFB, AAA and BBB, every fund, company and
figure are invented; nothing here is a record of a run (RULES.md rule 15).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import contract  # noqa: E402
import render  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

FUND_TLDR = [
    "Scorecard: FFA 5 of 6 met · FFB 6 of 6 met",
    "Overlap:   74.8% shared weight · 1,342 shared companies",
    "",
]
FUND_SCORECARD = [
    "Buffett scorecard",
    "| Check | Threshold | FFA | FFB |",
    "|---|---|---|---|",
    "| Low cost | 0.20% or less | Not met (0.22%) | Met (0.20%) |",
    "| Broad | 500 or more | Met (3,712) | Met (1,395) |",
    "| Not concentrated | 40% or less | Met (21.4%) | Met (25.9%) |",
    "| Tracks its index | No worse than −(TER + 0.10pp) | Met (−0.18pp) | Met (−0.12pp) |",
    "| Built to last | 5+ years and EUR 500m+ | Met (2019, EUR 32.1bn) | Met (2009, EUR 98.4bn) |",
    "| Quality underneath | 15% or more | Met (16.2%) | Met (16.9%) |",
    "",
]
FUND_SIDE = [
    "Side by side (Difference = FFB − FFA)",
    "| Fact | FFA | FFB | Difference |",
    "|---|---|---|---|",
    "| Index tracked | Index One (net) | Index Two (net) | — |",
    "| TER | 0.22% | 0.20% | -0.02pp |",
    "| Holdings | 3,712 | 1,395 | -2,317 |",
    "| Top-10 weight | 21.4% | 25.9% | +4.5pp |",
    "| Replication | Physical, sampled | Physical, sampled | — |",
    "| Distribution | Accumulating | Accumulating | — |",
    "| Domicile | Ireland | Ireland | — |",
    "| Base currency | USD | USD | — |",
    "| Fund size | USD 34,800m (2026-09-30) | USD 107,200m (2026-09-30) | +72,400m |",
    "| Inception | 2019-07-23 | 2009-09-25 | — |",
    "| Risk indicator | 4/7 | 4/7 | 0 |",
    "| Tracking difference, 2025 | −0.18pp | −0.12pp | +0.06pp |",
    "",
]
OVERLAP = [
    "Overlap (full holdings files, as of 2026-10-23 and 2026-10-24)",
    "| Measure | Value |",
    "|---|---|",
    "| Shared weight % | 74.8 |",
    "| Shared companies | 1,342 |",
    "| FFA companies not in FFB | 2,370 |",
    "| FFB companies not in FFA | 53 |",
    "| Structural | Index Two's 23 countries are all in Index One's 49 |",
    "",
]
SHARED = [
    "Shared holdings (top 10 by the smaller weight)",
    "| Company | FFA % | FFB % | Smaller % |",
    "|---|---|---|---|",
    "| Company A | 4.91 | 5.62 | 4.91 |",
    "| Company B | 4.30 | 4.94 | 4.30 |",
    "| Company C | 2.60 | 2.40 | 2.40 |",
    "",
]
EXPOSURE = [
    "Countries and sectors (Difference = FFB − FFA)",
    "| Exposure | FFA % | FFB % | Difference pp |",
    "|---|---|---|---|",
    "| Country: United States | 62.1 | 71.3 | +9.2 |",
    "| Country: Japan | 5.3 | 5.4 | +0.1 |",
    "| Sector: Technology | 27.8 | 26.9 | -0.9 |",
    "",
]
METHOD = [
    "METHOD",
    "Build:             test",
    "Instruments:       FFA (IE0000000001, Xetra, EUR) · FFB (IE0000000002, LSE, USD) — resolved by ISIN",
    "Order:             as named by the user; no row scored for either",
    "Difference:        second − first; % rows in pp; amounts only within one currency",
    "Scorecard:         references/buffett-scorecard.md, fund version, same thresholds for both",
    "Price date:        not used (no price-dependent row)",
    "Overlap depth:     full holdings files",
    "Classification:    GICS for both",
    "Confirmation:      all rows checked",
    "Conflict:          none",
    "Fallbacks:         none",
    "Columns suppressed: none",
    'Next:              say "full brief on FFA" or "full brief on FFB" for the rest of either',
    "",
]


def output(body: list[str], *, method: list[str] | None = None,
           subject: str = "=== FFA vs FFB — Fund A (Acc) vs Fund B (Acc) · head-to-head ===") -> str:
    lines = [
        subject,
        "STATUS: Complete.",
        "",
        "CONTEXT",
        "Data as of:       2026-10-25",
        "Latest period:    factsheets as of 2026-09-30 and 2026-09-30",
        "Currency / units: each column in its fund's own currency; weights and ratios in %",
        "Not available:    none",
        "Coverage:         FFA 12 of 12 rows · FFB 12 of 12 rows",
        "",
        "RESULT",
        "Mode: Head-to-head",
        *body,
        *(METHOD if method is None else method),
        "SOURCES",
        "| URL | Title | Published | Retrieved (UTC) |",
        "|---|---|---|---|",
        "| https://example.com/ffa.pdf | Fund A factsheet | 2026-09-30 | 2026-10-25 10:00 UTC |",
        "| https://example.com/ffb.pdf | Fund B factsheet | 2026-09-30 | 2026-10-25 10:01 UTC |",
    ]
    return "\n".join(lines) + "\n"


def funds(**parts: list[str]) -> str:
    base = {"tldr": FUND_TLDR, "score": FUND_SCORECARD, "side": FUND_SIDE, "overlap": OVERLAP,
            "shared": SHARED, "exposure": EXPOSURE}
    base.update(parts)
    return output([line for part in base.values() for line in part])


STOCK_SCORECARD = [
    "Buffett scorecard",
    "| Check | Threshold | AAA | BBB |",
    "|---|---|---|---|",
    "| Moat | Stable or rising | Met (46.2% → 47.0%) | Met (68.9% → 69.4%) |",
    "| Capital efficiency | 15% or more every year | Met (min 147%) | Met (min 29.6%) |",
    "| Low debt | Under 4 years | Met (0.9 years) | Met (0.4 years) |",
    "| Owner earnings | Growing | Met | Met |",
    "| Margin of safety | Yield above the bond | Not met (2.7% vs 4.1%) | Not met (2.4% vs 4.1%) |",
    "| Understandable | The line names what is sold | Met | Met |",
    "",
]
STOCK_SIDE = [
    "Side by side (Difference = BBB − AAA)",
    "| Fact | AAA | BBB | Difference |",
    "|---|---|---|---|",
    "| Revenue (FY to Sep 2026 · FY to Jun 2026) | USD 416,161m | USD 281,724m | -134,437m |",
    "| Gross margin | 47.0% | 69.4% | +22.4pp |",
    "| Operating margin | 32.0% | 45.6% | +13.6pp |",
    "| P/E | 33.1 | 31.0 | -2.1 |",
    "",
]
STOCK_METHOD = [m.replace("fund version", "stock version")
                 .replace("Price date:        not used (no price-dependent row)",
                          "Price date:        2026-10-24 close for both")
                 .replace("Overlap depth:     full holdings files", "Overlap depth:     not run (stocks)")
                for m in METHOD]


def stocks(side: list[str] = STOCK_SIDE, tldr: list[str] | None = None) -> str:
    tldr = ["Scorecard: AAA 5 of 6 met · BBB 5 of 6 met", ""] if tldr is None else tldr
    return output(tldr + STOCK_SCORECARD + side, method=STOCK_METHOD,
                  subject="=== AAA vs BBB — Company A vs Company B · head-to-head ===")


def problems(text: str) -> list[str]:
    return contract.head_to_head_problems(contract.split_sections(text))


def swap(rows: list[str], old: str, new: str) -> list[str]:
    assert any(old in r for r in rows), old
    return [r.replace(old, new) for r in rows]


def test_a_fund_head_to_head_passes_every_contract_check():
    assert contract.output_problems(funds()) == []


def test_a_stock_head_to_head_passes_every_contract_check():
    assert contract.output_problems(stocks()) == []


def test_a_fund_comparison_needs_its_overlap():
    assert any("missing tables" in p for p in problems(funds(overlap=[])))


def test_a_stock_comparison_has_no_overlap_table():
    text = stocks(side=STOCK_SIDE + OVERLAP)
    assert any("'Overlap' in a stock Head-to-head" in p for p in problems(text))


def test_every_scorecard_cell_is_a_result():
    bad = swap(FUND_SCORECARD, "Met (3,712)", "Yes (3,712)")
    assert any("does not start Met" in p for p in problems(funds(score=bad)))


def test_the_difference_is_the_second_minus_the_first():
    bad = swap(FUND_SIDE, "| -0.02pp |", "| +0.02pp |")
    assert any("TER" in p for p in problems(funds(side=bad)))


def test_a_difference_of_percentages_is_in_pp():
    bad = swap(FUND_SIDE, "| +4.5pp |", "| +4.5% |")
    assert any("in pp" in p for p in problems(funds(side=bad)))


def test_amounts_in_two_currencies_are_not_differenced():
    bad = swap(FUND_SIDE, "USD 107,200m (2026-09-30) | +72,400m", "EUR 92,000m (2026-09-30) | +57,200m")
    assert any("not one unit and currency" in p for p in problems(funds(side=bad)))


def test_the_heading_names_the_order():
    bad = swap(FUND_SIDE, "(Difference = FFB − FFA)", "(Difference)")
    assert any("heading does not say" in p for p in problems(funds(side=bad)))


def test_no_winner_in_words():
    bad = swap(FUND_SIDE, "| TER |", "| TER (FFB cheaper) |")
    assert any("a winner" in p for p in problems(funds(side=bad)))
    tldr = ["Scorecard: AAA 5 of 6 met · BBB 5 of 6 met · BBB is the better business", ""]
    assert any("a winner" in p for p in problems(stocks(tldr=tldr)))


def test_no_winner_in_marks():
    bad = swap(FUND_SIDE, "| 0.20% | -0.02pp |", "| **0.20%** | -0.02pp |")
    assert any("a mark on one side" in p for p in problems(funds(side=bad)))


def test_shared_weight_is_one_figure_in_range():
    bad = swap(OVERLAP, "| Shared weight % | 74.8 |", "| Shared weight % | 174.8 |")
    assert any("outside 0-100" in p for p in problems(funds(overlap=bad)))


def test_the_overlap_names_its_depth():
    bad = swap(OVERLAP, "full holdings files, ", "")
    assert any("name its depth" in p for p in problems(funds(overlap=bad)))


def test_shared_holdings_take_the_smaller_weight_and_sort_by_it():
    wrong = swap(SHARED, "| 2.60 | 2.40 | 2.40 |", "| 2.60 | 2.40 | 2.60 |")
    assert any("Smaller % is 2.4" in p for p in problems(funds(shared=wrong)))
    unsorted = SHARED[:3] + [SHARED[5], SHARED[3], SHARED[4], ""]
    assert any("not sorted" in p for p in problems(funds(shared=unsorted)))


def test_countries_and_sectors_rederive():
    bad = swap(EXPOSURE, "| +9.2 |", "| +9.9 |")
    assert any("United States" in p for p in problems(funds(exposure=bad)))


def test_the_scorecard_tally_on_the_tldr_is_true():
    tldr = swap(FUND_TLDR, "FFA 5 of 6", "FFA 6 of 6")
    assert any("says FFA 6 of 6" in p for p in problems(funds(tldr=tldr)))


def test_an_overlap_tldr_figure_must_be_in_a_table():
    tldr = swap(FUND_TLDR, "74.8%", "80.1%")
    assert any("80.1" in p for p in problems(funds(tldr=tldr)))


def test_method_lines_are_required():
    method = [m for m in METHOD if not m.startswith("Order:")]
    assert any("Order:" in p for p in problems(output(FUND_TLDR + FUND_SCORECARD + FUND_SIDE
                                                      + OVERLAP + SHARED + EXPOSURE,
                                                      method=method)))


def test_the_render_keeps_both_columns_and_marks_only_results():
    out = render.render(funds())
    assert "## FFA vs FFB · Fund A (Acc) vs Fund B (Acc)" in out
    assert "Head-to-head" in out
    assert "❌ 0.22%" in out and "✅ 0.20%" in out
    reasoned = funds(score=swap(FUND_SCORECARD, "Met (16.9%)",
                                "Not available — index factsheet not fetched"))
    assert "⚪ Not available — index factsheet not fetched" in render.render(reasoned)
    for name in ("Buffett scorecard", "Side by side", "Overlap", "Shared holdings",
                 "Countries and sectors"):
        assert f"### {name}" in out
    assert "> **Overlap** 74.8% shared weight" in out


def test_the_spec_and_routing_name_the_mode():
    skill = (REPO / "SKILL.md").read_text(encoding="utf-8")
    rules = (REPO / "RULES.md").read_text(encoding="utf-8")
    assert "references/head-to-head.md" in skill
    assert "`Mode: Head-to-head`" in skill
    assert "Mode: Head-to-head" in rules


# -- regressions from the 2026-10-25 review ---------------------------------


def test_two_risk_regimes_take_a_dash():
    side = swap(FUND_SIDE, "| Risk indicator | 4/7 | 4/7 | 0 |",
                "| Risk indicator | 6/7 (UK KIID SRRI) | 4/7 (PRIIPs SRI) | — |")
    assert problems(funds(side=side)) == []


def test_a_company_called_best_buy_is_not_a_winner():
    shared = [r.replace("Company C", "Best Buy") for r in SHARED]
    assert not any("a winner" in p for p in problems(funds(shared=shared)))


def test_a_short_row_is_a_problem_not_a_crash():
    short = SHARED[:3] + ["| Company A | 4.91 |", ""]
    found = contract.output_problems(funds(shared=short))
    assert found and not any("could not read" in p for p in found)
