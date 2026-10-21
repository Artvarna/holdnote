"""Quick brief: SKILL.md -> Report layout -> Quick brief, RULES.md v13.

SYNTHETIC. The ticker AAA and every figure are invented; nothing here is a
record of a run (RULES.md rule 15).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import contract  # noqa: E402
import render  # noqa: E402
from test_brief_layout import GRAHAM, KEY_NUMBERS, RED_FLAGS, SCORECARD  # noqa: E402

TLDR = ["Scorecard: 4 of 6 met · 1 not met · 1 not available", ""]
BOGLE = [
    "Bogle lens",
    "| Check | Metric | Value | Threshold | Result |",
    "|---|---|---|---|---|",
    "| Low cost | TER | 0.07% | 0.10% or less | Met |",
    "",
]
QUICK_METHOD = [
    "Quick brief:       Key numbers, What changed, Red flags and detail tables not built",
    'Next:              say "full brief on AAA" for the rest',
]


def quick(result_body: list[str], mode: str = "Stock brief (quick)",
          method: list[str] | None = None) -> str:
    lines = [
        "=== AAA — Company A Inc. · US0000000001 ===",
        "STATUS: Complete.",
        "",
        "CONTEXT",
        "Data as of:       2026-10-11",
        "Latest period:    FY2025, filed 2025-10-31 · FY ends September · US GAAP",
        "Currency / units: USD millions · reported, not adjusted",
        "Not available:    owner earnings (maintenance capex not disclosed)",
        "Coverage:         5 of 6 scorecard checks (quick brief)",
        "",
        "RESULT",
        f"Mode: {mode}",
        *result_body,
        "METHOD",
        "Build: test",
        *(QUICK_METHOD if method is None else method),
        "Columns suppressed: none",
        "",
        "SOURCES",
        "| URL or path | Form type and period | Filed | Retrieved (UTC) |",
        "|---|---|---|---|",
        "| https://www.sec.gov/example | 10-K FY2025 | 2025-10-31 | 2026-10-11 10:00 UTC |",
    ]
    return "\n".join(lines) + "\n"


def problems(text: str) -> list[str]:
    return contract.quick_brief_problems(contract.split_sections(text))


def test_quick_brief_passes_every_contract_check():
    assert contract.output_problems(quick(TLDR + SCORECARD)) == []


def test_named_lens_may_follow_the_scorecard():
    assert contract.output_problems(quick(TLDR + SCORECARD + GRAHAM)) == []


def test_fund_quick_brief_takes_the_fund_lens_only():
    assert problems(quick(TLDR + SCORECARD + BOGLE, mode="Fund brief (Mode A, quick)")) == []
    assert problems(quick(TLDR + SCORECARD + GRAHAM, mode="Fund brief (Mode A, quick)")) == [
        "Graham lens applies to stocks only"]
    assert problems(quick(TLDR + SCORECARD + BOGLE)) == ["Bogle lens applies to funds only"]


def test_quick_brief_is_not_held_to_the_full_layout():
    # A full brief without Key numbers would fail; a quick one must not.
    assert contract.brief_layout_problems(contract.split_sections(quick(TLDR + SCORECARD))) == []


def test_tables_beyond_the_scorecard_are_refused():
    found = problems(quick(TLDR + SCORECARD + KEY_NUMBERS + RED_FLAGS))
    assert "'Key numbers' in a quick brief; it prints the scorecard and named lenses only" in found
    assert "'Red flags' in a quick brief; it prints the scorecard and named lenses only" in found


def test_scorecard_comes_first():
    found = problems(quick(TLDR + GRAHAM + SCORECARD))
    assert "first quick brief table is 'Graham lens', not 'Buffett scorecard'" in found


def test_tldr_is_the_scorecard_line_only():
    body = ["Scorecard: 4 of 6 met · 1 not met · 1 not available",
            "Changed: diluted EPS 6.08 → 6.75 (+11.0%) since 2026-09-27", ""] + SCORECARD
    assert any("TL;DR is the Scorecard: line only" in p for p in problems(quick(body)))


def test_tldr_is_optional():
    assert problems(quick(SCORECARD)) == []


def test_method_names_what_was_skipped_and_offers_the_full_brief():
    found = problems(quick(TLDR + SCORECARD, method=[]))
    assert "quick brief METHOD has no Quick brief: line naming what was not built" in found
    assert "quick brief METHOD has no Next: line offering the full brief" in found


def test_result_cells_are_held_to_met_not_met_not_available():
    bad = [ln.replace("| Met |", "| Strong |") if ln.startswith("| Moat") else ln for ln in SCORECARD]
    assert "Buffett scorecard Result 'Strong' is not Met / Not met / Not available" in problems(quick(bad))


def test_quick_brief_cannot_cite_a_lens_restatement():
    text = quick(TLDR + SCORECARD).replace("https://www.sec.gov/example", "https://en.wikipedia.org/wiki/X")
    assert contract.lens_source_problems(contract.split_sections(text)) == [
        "SOURCES cites wikipedia.org: lens rules come from references/lenses.md, not the web"]


def test_renders_with_the_offer_of_the_full_brief():
    out = render.render(quick(TLDR + SCORECARD))
    assert "### Buffett scorecard" in out
    assert 'full brief on AAA' in out
    assert "Key numbers" not in out
