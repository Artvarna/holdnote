"""Price move: references/price-move.md, RULES.md rule 7 v14.

SYNTHETIC. The tickers AAA and FFF, every company, outlet headline and
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

MOVE = [
    "Move",
    "| Instrument | Level | Period % | As of |",
    "|---|---|---|---|",
    "| Company A Inc. (AAA, Nasdaq, USD) | 95.40 USD | -4.31 | 2026-10-20 (Nasdaq close) |",
    "| Benchmark: S&P 500 (price, USD) | 6612.40 | -0.85 | 2026-10-20 (NYSE close) |",
    "",
]
EVENTS = [
    "Dated events (2026-10-16 to 2026-10-20)",
    "| Date | About | Event | Source |",
    "|---|---|---|---|",
    "| 2026-10-17 | AAA | Filing: 8-K, Item 2.02 Results of Operations and Financial Condition | SEC EDGAR |",
    "| 2026-10-17 | AAA | Results release: Company A Reports Third Quarter Results | Company A newsroom |",
    "",
]
REASONS_HEADING = "Reported reasons (as published by the named sources — not Holdnote's view)"
REASONS = [
    REASONS_HEADING,
    "| About | Published | Source | Reason as reported | Premise |",
    "|---|---|---|---|---|",
    "| AAA | 2026-10-17 | Reuters | Reports shares fell after the revenue outlook came in below analyst estimates | Matches primary source |",
    "| AAA | 2026-10-18 | CNBC | Says some analysts pointed to slower data-centre orders | Not checkable |",
    "",
]
METHOD = [
    "METHOD",
    "Build:             test",
    "Period:            \"today\": last complete session, from market-context",
    "Benchmark:         US-listed stock: S&P 500 (price, USD)",
    "Contribution:      not run (not an ETF)",
    "Events window:     2026-10-16 to 2026-10-20, both inclusive",
    "Reasons window:    published 2026-10-16 to 2026-10-21",
    "Reasons rule:      attributed only (RULES.md rule 7); never Holdnote's own; not ranked by plausibility; at most 5 per About",
    "Reasons searched:  3 queries, 5 articles read, 2 used; 3 left out (no named source)",
    "Confirmation:      all rows checked",
    "Conflict:          none",
    "Fallbacks:         none",
    "Columns suppressed: none",
    'Next:              say "brief on AAA" for the filings behind these dates',
    "",
]


def output(body: list[str], *, mode: str = "Price move",
           latest: str = '2026-10-16 close to 2026-10-20 close ("this week")',
           method: list[str] | None = None) -> str:
    lines = [
        "=== AAA — Company A Inc. · price move ===",
        "STATUS: Complete.",
        "",
        "CONTEXT",
        "Data as of:       2026-10-21",
        f"Latest period:    {latest}",
        "Currency / units: USD; Period % in %",
        "Not available:    none",
        "Coverage:         Move 2 of 2 rows · Dated events 3 of 3 sources checked · Reported reasons from 2 of 5 articles read",
        "",
        "RESULT",
        f"Mode: {mode}",
        *body,
        *(METHOD if method is None else method),
        "SOURCES",
        "| URL | Title | Published | Retrieved (UTC) |",
        "|---|---|---|---|",
        "| https://www.sec.gov/example | 8-K | 2026-10-17 | 2026-10-21 10:00 UTC |",
        "| https://www.reuters.com/example | Reuters story | 2026-10-17 | 2026-10-21 10:02 UTC |",
        "| https://www.cnbc.com/example | CNBC story | 2026-10-18 | 2026-10-21 10:03 UTC |",
    ]
    return "\n".join(lines) + "\n"


def stock(**kw) -> str:
    return output(MOVE + EVENTS + REASONS, **kw)


def problems(text: str) -> list[str]:
    return contract.price_move_problems(contract.split_sections(text))


def replace_row(rows: list[str], old: str, new: str) -> list[str]:
    assert any(old in r for r in rows), old
    return [r.replace(old, new) for r in rows]


# -- the whole output --------------------------------------------------------


def test_a_stock_price_move_passes_every_contract_check():
    assert contract.output_problems(stock()) == []


ETF_MOVE = [
    "Move",
    "| Instrument | Level | Period % | As of |",
    "|---|---|---|---|",
    "| Fund F UCITS ETF (FFF, LSE, GBP) | 104.20 GBP | -1.20 | 2026-10-20 (LSE close) |",
    "| Benchmark: S&P 500 (price, USD) | 6612.40 | -0.85 | 2026-10-20 (NYSE close) |",
    "",
]
CONTRIBUTION = [
    "Contribution (top 10 holdings, weights as of 2026-09-30)",
    "| Holding | Weight % | Move % | Contribution pp |",
    "|---|---|---|---|",
    "| Company A | 8.00 | -4.31 | -0.34 |",
    "| Company B | 6.00 | -1.00 | -0.06 |",
    "| Company C | 5.00 | 0.40 | 0.02 |",
    "| Rest of fund | | | -0.82 |",
    "",
]


def etf(contribution: list[str] = CONTRIBUTION) -> str:
    method = [m.replace("Contribution:      not run (not an ETF)",
                        "Contribution:      weight x move / 100, top 10 as of 2026-09-30, "
                        "Rest of fund as the residual") for m in METHOD]
    reasons = [r.replace("| AAA |", "| Company A |") for r in REASONS]
    events = [r.replace("| AAA |", "| Company A |") for r in EVENTS]
    return output(ETF_MOVE + contribution + events + reasons, method=method)


def test_an_etf_price_move_with_contribution_passes():
    assert contract.output_problems(etf()) == []


def test_nothing_found_is_a_complete_answer():
    events = EVENTS[:3] + ["| — | AAA | None in window | checked: SEC EDGAR, Company A newsroom |", ""]
    reasons = REASONS[:3] + [
        "| AAA | — | — | None found — no named source attributed this move | — |", ""]
    assert contract.output_problems(output(MOVE + events + reasons)) == []


# -- tables -------------------------------------------------------------------


def test_tables_in_order_and_none_missing():
    assert "Price move tables out of order: ['Move', 'Reported reasons', 'Dated events']" in \
        problems(output(MOVE + REASONS + EVENTS))
    assert "Price move is missing tables: ['Reported reasons']" in problems(output(MOVE + EVENTS))


def test_no_other_table_in_a_price_move():
    extra = ["Key numbers", "| Metric | Value |", "|---|---|", "| Revenue | 1 |", ""]
    found = problems(output(MOVE + extra + EVENTS + REASONS))
    assert any("'Key numbers' in a Price move" in p for p in found)


def test_the_instrument_comes_before_its_benchmark():
    swapped = MOVE[:3] + [MOVE[4], MOVE[3], ""]
    assert "Move's first row is the benchmark; the instrument comes first" in \
        problems(output(swapped + EVENTS + REASONS))


def test_a_second_row_must_be_labelled_benchmark():
    rows = replace_row(MOVE, "| Benchmark: S&P 500", "| S&P 500")
    assert any("neither the instrument nor a `Benchmark: ` row" in p
               for p in problems(output(rows + EVENTS + REASONS)))


def test_method_names_its_windows_and_rule():
    method = [m for m in METHOD if not m.startswith(("Reasons rule:", "Events window:"))]
    found = problems(stock(method=method))
    assert "Price move METHOD has no Reasons rule: line" in found
    assert "Price move METHOD has no Events window: line" in found


def test_latest_period_names_both_sessions():
    assert "Latest period is not 'YYYY-MM-DD close to YYYY-MM-DD close'" in \
        problems(stock(latest='2026-10-17 to 2026-10-20 ("this week")'))


# -- contribution ------------------------------------------------------------


def test_contribution_is_weight_times_move():
    bad = replace_row(CONTRIBUTION, "| 8.00 | -4.31 | -0.34 |", "| 8.00 | -4.31 | -0.50 |")
    assert any(p.startswith("Contribution Company A: 8.00 x -4.31 / 100") for p in problems(etf(bad)))


def test_rest_of_fund_is_the_residual():
    bad = replace_row(CONTRIBUTION, "| Rest of fund | | | -0.82 |", "| Rest of fund | | | -0.20 |")
    assert any(p.startswith("Rest of fund is -0.20") for p in problems(etf(bad)))


def test_contribution_sorted_by_size():
    rows = CONTRIBUTION[:3] + [CONTRIBUTION[4], CONTRIBUTION[3]] + CONTRIBUTION[5:]
    assert "Contribution rows are not sorted by size of contribution" in problems(etf(rows))


def test_a_missing_move_makes_the_residual_not_available():
    rows = replace_row(CONTRIBUTION, "| 6.00 | -1.00 | -0.06 |",
                       "| 6.00 | Not available (browser route down) | Not available |")
    assert "Rest of fund must be Not available when a contribution is" in problems(etf(rows))
    rows = replace_row(rows, "| Rest of fund | | | -0.82 |", "| Rest of fund | | | Not available |")
    assert problems(etf(rows)) == []


# -- dated events ------------------------------------------------------------


def test_events_are_typed():
    bad = replace_row(EVENTS, "Results release: Company A", "Company A")
    assert any("does not start with one of" in p for p in problems(output(MOVE + bad + REASONS)))


def test_events_sit_inside_the_window():
    bad = replace_row(EVENTS, "| 2026-10-17 | AAA | Filing", "| 2026-10-14 | AAA | Filing")
    assert "Dated events 2026-10-14 is outside the window 2026-10-16 to 2026-10-20" in \
        problems(output(MOVE + bad + REASONS))


# -- reported reasons ------------------------------------------------------------


def test_reported_reasons_only_in_a_price_move():
    text = stock().replace("Mode: Price move", "Mode: Portfolio (Mode C)")
    assert contract.reported_reasons_elsewhere(contract.split_sections(text)) == [
        "Reported reasons printed outside a Price move (RULES.md rule 7)"]
    assert contract.reported_reasons_elsewhere(contract.split_sections(stock())) == []


def test_a_reason_names_who_gave_it():
    bad = replace_row(REASONS, "| Reuters |", "| analysts |")
    assert "Reported reason with no named source: 'analysts'" in problems(output(MOVE + EVENTS + bad))


def test_a_reason_is_framed_as_the_sources():
    bad = replace_row(REASONS, "Reports shares fell", "Shares fell")
    assert any("does not open with Says/Reports/Writes/States" in p
               for p in problems(output(MOVE + EVENTS + bad)))


def test_a_reason_is_short():
    long = "Reports " + " ".join(["word"] * 30)
    bad = replace_row(REASONS, "Reports shares fell after the revenue outlook came in below analyst estimates", long)
    assert any("words; under 30" in p for p in problems(output(MOVE + EVENTS + bad)))


def test_premise_has_three_values():
    bad = replace_row(REASONS, "| Not checkable |", "| Probably true |")
    assert any("Premise 'Probably true'" in p for p in problems(output(MOVE + EVENTS + bad)))


def test_a_reason_published_outside_its_window_is_refused():
    bad = replace_row(REASONS, "| 2026-10-18 | CNBC |", "| 2026-10-23 | CNBC |")
    assert "Reported reason published 2026-10-23 is outside 2026-10-16 to 2026-10-21" in \
        problems(output(MOVE + EVENTS + bad))
    # the day after the end session is inside: evening and next-morning pieces
    ok = replace_row(REASONS, "| 2026-10-18 | CNBC |", "| 2026-10-21 | CNBC |")
    assert problems(output(MOVE + EVENTS + ok)) == []


def test_at_most_five_reasons_per_instrument():
    row = REASONS[4]
    bad = REASONS[:5] + [row] * 4 + [""]
    assert "6 reported reasons for AAA; at most 5" in problems(output(MOVE + EVENTS + bad))


def test_reasons_are_in_date_order_not_ranked():
    bad = REASONS[:3] + [REASONS[4], REASONS[3], ""]
    assert "Reported reasons are not in order of publication date" in \
        problems(output(MOVE + EVENTS + bad))


def test_causal_wording_is_refused_outside_reported_reasons():
    bad = replace_row(EVENTS, "Company A Reports Third Quarter Results",
                      "Company A results, which sent shares lower")
    found = problems(output(MOVE + bad + REASONS))
    assert any(p.startswith("causal wording outside Reported reasons") for p in found)


def test_causal_wording_inside_reported_reasons_is_the_sources_and_allowed():
    ok = replace_row(REASONS, "Says some analysts pointed to slower data-centre orders",
                     "Says the drop was due to slower data-centre orders")
    assert problems(output(MOVE + EVENTS + ok)) == []


def test_the_users_position_never_enters():
    bad = replace_row(MOVE, "| Company A Inc. (AAA, Nasdaq, USD)", "| Your position in AAA")
    assert any("the user's position" in p for p in problems(output(bad + EVENTS + REASONS)))


# -- rendering and wiring ----------------------------------------------------------


def test_renders_with_its_title_and_attributed_table():
    out = render.render(stock())
    assert out.startswith("## AAA · Company A Inc. · why it moved")
    assert "### 🗞️ Reported reasons" in out
    assert "*as published by the named sources — not Holdnote's view*" in out
    assert "✅ Matches primary source" in out
    assert "📌 Dated events" in out


def test_rule_7_allows_reported_reasons_only_here():
    rules = (REPO / "RULES.md").read_text(encoding="utf-8")
    rule7 = rules.split("### 7.", 1)[1].split("### 8.", 1)[0]
    assert "Do not explain why a price moved." in rule7
    assert "references/price-move.md" in rule7
    assert "Mode: Price move" in rules


def test_skill_routes_why_questions_to_price_move():
    skill = (REPO / "SKILL.md").read_text(encoding="utf-8")
    assert "`references/price-move.md`" in skill
    assert '"why did NVDA drop today" | `Mode: Price move`' in skill


def test_an_empty_conflict_line_is_not_a_warning():
    # METHOD prints `Conflict: none` on every run (RULES.md Part IV); the
    # report showed it as a warning until 2026-10-21.
    assert "⚠️" not in render.render(stock())
    flagged = stock().replace("Conflict:          none",
                              "Conflict:          AAA end 95.40 [Nasdaq] vs 95.90 [Yahoo] gap 0.52% CONFLICT")
    out = render.render(flagged)
    assert "⚠️ *Conflict:" in out and "95.40 [Nasdaq] vs 95.90 [Yahoo]" in out
