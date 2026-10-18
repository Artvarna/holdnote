"""Brief layout: SKILL.md -> Report layout, RULES.md Part IV v10.

SYNTHETIC. The ticker AAA and every figure are invented; nothing here is a
record of a run (RULES.md rule 15).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import contract  # noqa: E402

TLDR = [
    "Scorecard: 4 of 6 met · 1 not met · 1 not available",
    "Changed: diluted EPS 6.08 → 6.75 (+11.0%) since 2026-09-27",
    "Red flags: 1 new filing risk · thesis criteria 0 of 1 reached",
    "",
]
SCORECARD = [
    "Buffett scorecard",
    "| Check | Metric | Value | Threshold | Result |",
    "|---|---|---|---|---|",
    "| Moat | Gross margin, FY2016–FY2025 | 38.1% → 46.2% | Stable or rising | Met |",
    "| Capital efficiency | ROE, each of last 10 FY | 15.2–24.0% | Above 15% every year | Met |",
    "| Low debt | Total debt / net income | 1.4 years | Under 4 years | Met |",
    "| Owner earnings | NI + D&A − maintenance capex | Not available | Growing | Not available |",
    "| Margin of safety | Owner-earnings yield vs 10y Treasury | 3.1% vs 4.2% | Yield above Treasury | Not met |",
    "| Understandable | Business model, filing wording | Sells devices and services | One line exists | Met |",
    "",
]
GRAHAM = [
    "Graham lens",
    "| Check | Metric | Value | Threshold | Result |",
    "|---|---|---|---|---|",
    "| P/E | Price / diluted EPS FY2025 | 31.2 | Under 15 | Not met |",
    "",
]
KEY_NUMBERS = [
    "Key numbers",
    "| Metric | FY2020 | FY2025 |",
    "|---|---|---|",
    "| Revenue (USD m) | 274,515 | 391,035 |",
    "| Diluted EPS (USD) | 3.28 | 6.75 |",
    "",
]
WHAT_CHANGED = [
    "What changed",
    "| Metric | Last run (2026-09-27) | Now | Change |",
    "|---|---|---|---|",
    "| Diluted EPS (USD) | 6.08 | 6.75 | +11.0% |",
    "",
]
RED_FLAGS = [
    "Red flags",
    "| Type | Item | Source | Status |",
    "|---|---|---|---|",
    "| Filing risk | Supply concentration in one region | 10-K FY2025, Item 1A | New |",
    "| Thesis | \"Services growth below 5% for two years\" | thesis 2025-10-13 | Not reached |",
    "",
]
SEGMENTS = [
    "Segments",
    "| Segment | Revenue (USD m) | Share |",
    "|---|---|---|",
    "| Devices | 300,000 | 76.7% |",
    "| Services | 91,035 | 23.3% |",
    "",
]


def brief(result_body: list[str], mode: str = "Stock brief") -> str:
    lines = [
        "=== AAA — Company A Inc. · US0000000001 ===",
        "STATUS: Complete.",
        "",
        "CONTEXT",
        "Data as of:       2026-10-11",
        "Latest period:    FY2025, filed 2025-10-31 · FY ends September · US GAAP",
        "Currency / units: USD millions · reported, not adjusted",
        "Not available:    owner earnings (maintenance capex not disclosed)",
        "Coverage:         5 of 6 scorecard checks",
        "",
        "RESULT",
        f"Mode: {mode}",
        *result_body,
        "METHOD",
        "Build: test",
        "Detail tables:     held back: Business, Financials, Balance sheet",
        "Columns suppressed: none",
        "",
        "SOURCES",
        "| URL or path | Form type and period | Filed | Retrieved (UTC) |",
        "|---|---|---|---|",
        "| https://www.sec.gov/example | 10-K FY2025 | 2025-10-31 | 2026-10-11 10:00 UTC |",
    ]
    return "\n".join(lines) + "\n"


def layout(text: str) -> list[str]:
    return contract.brief_layout_problems(contract.split_sections(text))


FULL = TLDR + SCORECARD + GRAHAM + KEY_NUMBERS + WHAT_CHANGED + RED_FLAGS + SEGMENTS


def test_full_brief_passes_every_contract_check():
    assert contract.output_problems(brief(FULL)) == []


def test_tldr_is_optional():
    assert layout(brief(SCORECARD + KEY_NUMBERS + WHAT_CHANGED + RED_FLAGS)) == []


def test_fund_brief_and_combined_mode_use_the_layout():
    body = SCORECARD + KEY_NUMBERS + WHAT_CHANGED + RED_FLAGS
    assert layout(brief(body, mode="Fund brief (Mode A)")) == []
    assert layout(brief(body, mode="Fund brief (Mode A) + Portfolio (Mode C)")) == []
    assert "missing" in layout(brief(KEY_NUMBERS, mode="Fund brief (Mode A)"))[0]


def test_other_modes_are_not_held_to_the_layout():
    assert layout(brief(SEGMENTS, mode="Portfolio (Mode C)")) == []


def test_four_tldr_lines_fail():
    body = [TLDR[0], *TLDR[:3]] + [""] + SCORECARD + KEY_NUMBERS + WHAT_CHANGED + RED_FLAGS
    assert any("at most 3" in p for p in layout(brief(body)))


def test_unlabelled_or_reordered_tldr_fails():
    body = ["This company looks solid.", ""] + SCORECARD + KEY_NUMBERS + WHAT_CHANGED + RED_FLAGS
    assert any("without a" in p for p in layout(brief(body)))
    body = [TLDR[1], TLDR[0], ""] + SCORECARD + KEY_NUMBERS + WHAT_CHANGED + RED_FLAGS
    assert any("out of order" in p for p in layout(brief(body)))


def test_missing_scorecard_fails():
    problems = layout(brief(KEY_NUMBERS + WHAT_CHANGED + RED_FLAGS))
    assert problems == ["brief is missing tables: ['Buffett scorecard']"]


def test_detail_table_before_red_flags_fails():
    body = SCORECARD + KEY_NUMBERS + SEGMENTS + WHAT_CHANGED + RED_FLAGS
    assert any("'Segments' sits before Red flags" in p for p in layout(brief(body)))


def test_non_lens_table_between_scorecard_and_key_numbers_fails():
    body = SCORECARD + SEGMENTS + KEY_NUMBERS + WHAT_CHANGED + RED_FLAGS
    assert any("only lens tables may" in p for p in layout(brief(body)))


def test_lenses_after_key_numbers_fail():
    body = SCORECARD + KEY_NUMBERS + GRAHAM + WHAT_CHANGED + RED_FLAGS
    assert any("'Graham lens' sits before Red flags" in p for p in layout(brief(body)))


def test_scorecard_result_must_be_arithmetic_not_a_verdict():
    bad = [line.replace("| Met |", "| Excellent |", 1) if i == 3 else line
           for i, line in enumerate(SCORECARD)]
    problems = layout(brief(bad + KEY_NUMBERS + WHAT_CHANGED + RED_FLAGS))
    assert problems == ["Buffett scorecard Result 'Excellent' is not Met / Not met / Not available"]


def test_red_flag_rows_are_filing_risks_or_thesis_criteria_only():
    invented = RED_FLAGS[:3] + [
        "| Scenario | Competitor could undercut prices | Holdnote | Possible |",
        "",
    ]
    problems = layout(brief(SCORECARD + KEY_NUMBERS + WHAT_CHANGED + invented))
    assert problems == ["Red flags type 'Scenario' is not Filing risk or Thesis"]


def test_empty_red_flags_sides_are_stated():
    empty = RED_FLAGS[:3] + [
        "| Filing risk | No risk factors added or removed | 10-K FY2025, Item 1A | None |",
        "| Thesis | No thesis on file | thesis journal | None on file |",
        "",
    ]
    assert layout(brief(SCORECARD + KEY_NUMBERS + WHAT_CHANGED + empty)) == []


def test_unknown_lens_fails():
    made_up = ["Dalio lens"] + GRAHAM[1:]
    problems = layout(brief(SCORECARD + made_up + KEY_NUMBERS + WHAT_CHANGED + RED_FLAGS))
    assert problems == ["'Dalio lens' is not a lens references/lenses.md defines"]


def test_lens_on_the_wrong_kind_of_instrument_fails():
    bogle = ["Bogle lens"] + GRAHAM[1:]
    problems = layout(brief(SCORECARD + bogle + KEY_NUMBERS + WHAT_CHANGED + RED_FLAGS))
    assert problems == ["Bogle lens applies to funds only"]
    problems = layout(brief(SCORECARD + GRAHAM + KEY_NUMBERS + WHAT_CHANGED + RED_FLAGS,
                            mode="Fund brief (Mode A)"))
    assert problems == ["Graham lens applies to stocks only"]


def test_lenses_file_defines_every_table_the_checker_allows():
    text = (Path(__file__).resolve().parent.parent / "references" / "lenses.md").read_text(encoding="utf-8")
    for name in contract.LENS_TABLES:
        assert f"`{name}`" in text and f"## {name}" in text, name


# --------------------------------------------------------------------------
# One-line SOURCES (RULES.md Part IV v11)
# --------------------------------------------------------------------------

SUMMARY = '3 documents · published 2025-10-31 to 2026-10-09 · 0 stale · 0 unverified · full list on "show proof"'
BODY = SCORECARD + KEY_NUMBERS + WHAT_CHANGED + RED_FLAGS


def collapsed(summary: str = SUMMARY, method_extra: list[str] | None = None, proof: bool = False) -> str:
    text = brief(BODY)
    head, _ = text.split("SOURCES\n")
    if method_extra:
        head = head.replace("Columns suppressed: none\n", "Columns suppressed: none\n" + "\n".join(method_extra) + "\n")
    if proof:
        head = head.replace("\nSOURCES", "") + "PROOF\nISIN match   document US0000000001 == briefed   PASS\n\n"
    return head + "SOURCES\n" + summary + "\n"


def test_summary_line_passes_every_contract_check():
    assert contract.output_problems(collapsed()) == []


def test_summary_line_in_the_wrong_shape_fails():
    problems = contract.output_problems(collapsed("3 documents · sources hidden"))
    assert any("not in the RULES.md Part IV shape" in p for p in problems)


def test_summary_line_beside_proof_fails():
    problems = contract.output_problems(collapsed(proof=True))
    assert any("PROOF printed, so SOURCES must print in full" in p for p in problems)


def test_summary_line_beside_rows_fails():
    text = brief(BODY).rstrip("\n") + "\n" + SUMMARY + "\n"
    assert any("one or the other" in p for p in contract.output_problems(text))


def test_stale_count_needs_its_method_line():
    stale = SUMMARY.replace("0 stale", "1 stale")
    assert any("METHOD names no stale source" in p for p in contract.output_problems(collapsed(stale)))
    ok = collapsed(stale, ["Stale source: factsheet published 2026-06-30, before the FY2025 report"])
    assert contract.output_problems(ok) == []


def test_unverified_count_needs_a_confirmation_line():
    unverified = SUMMARY.replace("0 unverified", "1 unverified")
    assert any("no Confirmation: line" in p for p in contract.output_problems(collapsed(unverified)))
    ok = collapsed(unverified, ["Confirmation: Key numbers diluted EPS rests on one source (10-K)"])
    assert contract.output_problems(ok) == []


def test_summary_dates_must_run_forwards():
    backwards = SUMMARY.replace("2025-10-31 to 2026-10-09", "2026-10-09 to 2025-10-31")
    assert any("run backwards" in p for p in contract.output_problems(collapsed(backwards)))


def test_a_brief_citing_a_page_that_restates_a_lens_fails():
    text = brief(FULL).rstrip("\n") + (
        "\n| https://en.wikipedia.org/wiki/Graham_number | Graham number | n/a | 2026-10-11 |\n")
    problems = contract.output_problems(text)
    assert problems == ["SOURCES cites wikipedia.org: lens rules come from references/lenses.md, not the web"]


def test_lens_source_check_leaves_other_modes_alone():
    sections = {"RESULT": "Mode: Market-wide\n", "SOURCES": "| https://en.wikipedia.org/x | x | n/a | x |"}
    assert contract.lens_source_problems(sections) == []


# --------------------------------------------------------------------------
# Buffett notes and the Buffett checklist (references/buffett.md, checklist.md)
# --------------------------------------------------------------------------

NOTES = [
    "Buffett notes",
    "| Principle | Why it's here | Letter |",
    "|---|---|---|",
    "| Mr. Market | The price moved 18% in 30 days; the filings behind the scorecard are the same | [2013](https://www.berkshirehathaway.com/letters/2013ltr.pdf) |",
    "",
]


def test_buffett_notes_after_red_flags_pass():
    assert contract.output_problems(brief(BODY + NOTES)) == []


def test_buffett_notes_must_follow_red_flags_and_link_a_letter():
    misplaced = SCORECARD + KEY_NUMBERS + WHAT_CHANGED + RED_FLAGS + SEGMENTS + NOTES
    assert "Buffett notes must come right after Red flags" in contract.output_problems(brief(misplaced))
    unlinked = NOTES[:3] + ["| Moat | Moat is not met | 2007 |", ""]
    assert any("does not link its letter" in p for p in contract.output_problems(brief(BODY + unlinked)))


def test_buffett_notes_hold_at_most_two_known_principles():
    row = NOTES[3]
    many = NOTES[:3] + [row, row, row.replace("Mr. Market", "Be greedy"), ""]
    problems = contract.output_problems(brief(BODY + many))
    assert "Buffett notes has 3 rows, at most 2" in problems
    assert any("'Be greedy' is not a principle" in p for p in problems)


def test_his_name_never_vouches_for_a_result():
    vouched = [TLDR[0] + " · Buffett-approved", *TLDR[1:]]
    assert any("Buffett[- ]approved" in p for p in contract.output_problems(brief(vouched + BODY)))


CHECK_TLDR = [
    "Filters: 2 yes · 1 not sure · scorecard 4 of 6 met",
    "Position: 15.76% of your portfolio is already Company A, across 3 lines",
    "Thesis: none on file",
    "",
]
FOUR_FILTERS = [
    "Four filters",
    "| Filter | Evidence | Answer |",
    "|---|---|---|",
    "| 1. Understand it | Your answer; Information Technology is in your circle | Yes |",
    "| 2. Lasting economics | Moat Met, Capital efficiency Met | Met |",
    "| 3. Able, trustworthy management | Your answer; Clean accounts: none in 5 FY | Not sure |",
    "| 4. Sensible price | Margin of safety: 3.1% vs 4.2% | Not met |",
    "",
]
POSITION = [
    "Your position",
    "| Line | Now |",
    "|---|---|",
    "| Company A already held, all routes | 15.76 |",
    "| Thesis on file | none |",
    "",
]
CHECKLIST = CHECK_TLDR + FOUR_FILTERS + SCORECARD + KEY_NUMBERS + POSITION + RED_FLAGS


def test_a_checklist_passes_every_contract_check():
    assert contract.output_problems(brief(CHECKLIST, mode="Buffett checklist")) == []


def test_checklist_answers_are_the_users_or_the_scorecards():
    scored = [line.replace("| Not sure |", "| Probably |") for line in CHECKLIST]
    problems = contract.output_problems(brief(scored, mode="Buffett checklist"))
    assert any("answer 'Probably'" in p for p in problems)


def test_checklist_needs_all_four_filters_in_order():
    three = [line for line in CHECKLIST if not line.startswith("| 3. ")]
    problems = contract.output_problems(brief(three, mode="Buffett checklist"))
    assert any("Four filters rows are" in p for p in problems)
    no_position = [line for line in CHECKLIST if line not in POSITION]
    assert any("missing tables: ['Your position']" in p
               for p in contract.output_problems(brief(no_position, mode="Buffett checklist")))


# Live NVIDIA run 2026-10-11: an exact-text diff read three rewordings as
# three new and three removed risks. A reworded factor is its own status.
REWORDED = RED_FLAGS[:3] + [
    "| Filing risk | Supply concentration in one region | 10-K FY2025, risk factor summary | New |",
    "| Filing risk | Security incidents could disrupt operations | 10-K FY2025, risk factor summary | Reworded |",
    "| Thesis | No thesis on file | me/theses | None on file |",
    "",
]


def test_reworded_and_not_checkable_filing_risks_pass():
    assert layout(brief(SCORECARD + KEY_NUMBERS + WHAT_CHANGED + REWORDED)) == []
    unfetched = RED_FLAGS[:3] + [
        "| Filing risk | Prior 10-K not fetched (SEC refused) | 10-K FY2024 | Not checkable |",
        "",
    ]
    assert layout(brief(SCORECARD + KEY_NUMBERS + WHAT_CHANGED + unfetched)) == []


def test_a_filing_risk_status_outside_the_list_still_fails():
    bad = RED_FLAGS[:3] + ["| Filing risk | Something | 10-K FY2025 | Changed |", ""]
    assert any("status 'Changed'" in p for p in layout(brief(SCORECARD + KEY_NUMBERS + WHAT_CHANGED + bad)))
