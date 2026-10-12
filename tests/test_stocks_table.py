"""Mode C Stocks table: the contract a saved run is held to.

Mode C has no script behind it: the agent composes the output from
references/etf-brief.md. These tests run contract.stocks_table_problems
against outputs built here -- one that obeys the contract, and variants that
each break one rule of it.

SYNTHETIC. Tickers, companies, CIKs, dates and counts are invented for the
test. Nothing here is a record of a run or a statement about a real company
(RULES.md rule 15).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import contract  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
AS_OF = "2026-10-01"

HEADER = "| Ticker | Company | Next earnings | Latest periodic | Filed | 8-Ks, 30 days |"
ROWS = [
    "| AAA | Company A | 2026-10-29 | 10-Q, period 2026-06-27 | 2026-08-01 | 2 (2026-09-12, 2026-09-03) |",
    "| BBB | Company B | Not available — not announced | 10-K, period 2026-01-25 | 2026-02-26 | 0 |",
    "| CCC | Company C | 2026-10-22 | 10-Q, period 2026-06-30 | 2026-07-24 | 1 (2026-09-30) |",
]


def stocks_output(rows=ROWS, *, header=HEADER, with_table=True, method_extra=True) -> str:
    """A Mode C run as etf-brief.md specifies it, reduced to what the check reads."""
    if with_table:
        stocks = ["Stocks", header, "|---|---|---|---|---|---|", *rows]
        coverage = f"{len(rows)} of {len(rows)} stocks"
        window = "Stocks window:     8-Ks filed in the 30 days to 2026-10-01, by EDGAR filing date"
    else:
        stocks = ["Stocks", "none"]
        coverage = "1 of 1 funds"
        window = "Stocks window:     none — no stocks in the set"
    method = [
        "Weights basis:     not supplied",
        window,
        "Earnings dates:    company-announced only, never estimated",
        "Columns suppressed: none",
    ]
    if not method_extra:
        method = [m for m in method if not m.startswith(("Stocks window", "Earnings dates"))]
    return "\n".join(
        [
            "STATUS",
            "",
            "Complete.",
            "",
            "CONTEXT",
            "",
            f"Data as of:       {AS_OF}",
            "Latest period:    2026-09-24 to 2026-10-01",
            "Currency / units: filing dates, ISO",
            "Not available:    none",
            f"Coverage:         {coverage}",
            "",
            "RESULT",
            "",
            "Mode: Portfolio (Mode C)",
            "",
            *stocks,
            "",
            "METHOD",
            "",
            *method,
            "",
            "SOURCES",
            "",
            "| URL | Title | Published | Retrieved (UTC) |",
            "|---|---|---|---|",
            "| https://data.sec.gov/submissions/CIK0000000001.json | Company A submissions | 2026-10-01 | 2026-10-01 09:00 |",
            "",
        ]
    )


def problems(text: str) -> list[str]:
    return contract.stocks_table_problems(contract.split_sections(text))


def with_row(index: int, old: str, new: str) -> str:
    rows = list(ROWS)
    assert old in rows[index]
    rows[index] = rows[index].replace(old, new)
    return stocks_output(rows)


def test_a_conforming_output_trips_no_check():
    text = stocks_output()
    assert problems(text) == []
    assert contract.section_order(text) == [s for s in contract.SECTIONS if s != "PROOF"]
    assert contract.placeholder_times(text) == []
    assert contract.text_outside_sections(text) == []
    assert contract.banned_hits(text) == []
    assert contract.coverage_problems(contract.split_sections(text)) == []


def test_a_fund_only_set_prints_none_and_says_so_in_method():
    assert problems(stocks_output(with_table=False)) == []


def test_a_fund_only_set_must_still_name_the_empty_window():
    text = stocks_output(with_table=False).replace("Stocks window:     none — no stocks in the set\n", "")
    assert problems(text) == ["METHOD does not say Stocks window: none"]


def test_mode_c_without_a_stocks_heading_is_caught():
    text = stocks_output(with_table=False).replace("Stocks\nnone\n", "")
    assert any("no Stocks table" in p for p in problems(text))


def test_a_run_that_is_not_mode_c_is_not_held_to_it():
    text = stocks_output().replace("Mode: Portfolio (Mode C)", "Mode: Market-wide")
    assert problems(text) == []


def test_a_past_earnings_date_is_the_last_report_not_the_next():
    (hit,) = problems(with_row(0, "2026-10-29", "2026-07-30"))
    assert "AAA" in hit and "last report" in hit


def test_an_earnings_date_equal_to_data_as_of_is_still_ahead():
    assert problems(with_row(0, "2026-10-29", AS_OF)) == []


@pytest.mark.parametrize("cell", ["Not available", "Not available —", "soon", "2026-10-3", "Oct 29"])
def test_an_earnings_cell_that_is_neither_a_date_nor_a_reasoned_gap_is_caught(cell):
    hits = problems(with_row(0, "2026-10-29", cell))
    assert hits and all(h.startswith("AAA:") for h in hits)


def test_a_reasoned_gap_passes():
    assert problems(with_row(0, "2026-10-29", "Not available — not confirmed by the company")) == []


@pytest.mark.parametrize(
    "cell",
    [
        "10-Q, period 2026-06-27, revenue up 4%",
        "10-Q",
        "8-K, period 2026-06-27",
        "10-Q period 2026-06-27",
        "Q3 report",
    ],
)
def test_a_periodic_cell_that_is_more_than_form_and_period_is_caught(cell):
    hits = problems(with_row(0, "10-Q, period 2026-06-27", cell))
    assert any("latest periodic" in h for h in hits)


def test_an_amendment_keeps_its_suffix():
    assert problems(with_row(0, "10-Q, period", "10-Q/A, period")) == []


def test_a_filing_dated_after_data_as_of_is_caught():
    (hit,) = problems(with_row(0, "| 2026-08-01 |", "| 2026-10-02 |"))
    assert "after Data as of" in hit


def test_a_filing_with_no_filed_date_is_caught():
    hits = problems(with_row(0, "| 2026-08-01 |", "| — |"))
    assert any("filed is not an ISO date" in h for h in hits)


def test_the_eight_k_count_must_match_its_dates():
    (hit,) = problems(with_row(0, "2 (2026-09-12, 2026-09-03)", "3 (2026-09-12, 2026-09-03)"))
    assert "count 3 but 2 dates" in hit


def test_eight_k_dates_are_newest_first():
    (hit,) = problems(with_row(0, "(2026-09-12, 2026-09-03)", "(2026-09-03, 2026-09-12)"))
    assert "newest first" in hit


@pytest.mark.parametrize(
    "date, inside",
    [("2026-09-01", True), ("2026-08-31", False), ("2026-10-01", True), ("2026-10-02", False)],
)
def test_eight_k_dates_must_sit_in_the_thirty_day_window(date, inside):
    hits = problems(with_row(2, "1 (2026-09-30)", f"1 ({date})"))
    assert (hits == []) is inside
    if not inside:
        assert "outside the 30 days" in hits[0]


@pytest.mark.parametrize("cell", ["None", "zero", "2", "0 ()", "1 (2026-13-40)"])
def test_a_malformed_eight_k_cell_is_caught(cell):
    assert problems(with_row(1, "| 0 |", f"| {cell} |"))


def test_a_withheld_eight_k_cell_needs_its_reason():
    assert problems(with_row(1, "| 0 |", "| Not available — not on EDGAR |")) == []
    assert problems(with_row(1, "| 0 |", "| Not available |"))


def test_the_column_set_is_fixed():
    text = stocks_output(header=HEADER.replace("Next earnings", "Earnings"))
    (hit,) = problems(text)
    assert "columns" in hit


def test_a_short_row_is_caught():
    rows = list(ROWS)
    rows[0] = "| AAA | Company A | 2026-10-29 |"
    (hit,) = problems(stocks_output(rows))
    assert "AAA" in hit and "cells" in hit


def test_method_must_state_the_window_and_the_earnings_rule():
    hits = problems(stocks_output(method_extra=False))
    assert "METHOD does not state the Stocks window" in hits
    assert "METHOD does not say Earnings dates: company-announced only" in hits


def test_coverage_cannot_count_a_stocks_table_that_did_not_run():
    text = stocks_output(with_table=False).replace(
        "Coverage:         1 of 1 funds", "Coverage:         1 of 1 funds, 0 of 0 stocks"
    )
    assert contract.coverage_problems(contract.split_sections(text)) == [
        "not run, still counted: 0 of 0 stocks"
    ]


def test_no_cell_carries_interpretation():
    # rules 6-8: the table reports dates, forms and counts. A recommendation
    # word in a cell is caught by the shared ban list.
    text = with_row(0, "2 (2026-09-12, 2026-09-03)", "2 (2026-09-12, 2026-09-03) attractive")
    assert contract.banned_hits(text)


# --------------------------------------------------------------------------
# The spec says what the checks hold the output to
# --------------------------------------------------------------------------


def _spec() -> str:
    return (REPO / "references" / "etf-brief.md").read_text(encoding="utf-8")


def test_the_spec_counts_eleven_mode_c_tables_everywhere():
    text = _spec()
    assert not re.search(r"\b(?:five|six|seven|eight|nine|ten) (?:Mode C )?tables\b", text, re.IGNORECASE)
    assert not re.search(r"all (?:five|six|seven|eight|nine|ten)\b", text, re.IGNORECASE)
    assert len(re.findall(r"\beleven (?:Mode C )?tables\b", text)) == 4


def test_the_spec_names_every_column_the_check_requires():
    section = _spec().split("### Stocks table", 1)[1].split("###", 1)[0]
    header = re.search(r"^\| Ticker .*$", section, re.MULTILINE).group(0)
    cells = [c.strip() for c in header.strip("|").split("|")]
    assert cells == contract.STOCK_COLUMNS


def test_the_spec_example_rows_pass_the_check():
    section = _spec().split("### Stocks table", 1)[1].split("###", 1)[0]
    block = re.search(r"```\nStocks\n(.*?)```", section, re.DOTALL).group(1)
    rows = [l for l in block.splitlines() if l.startswith("|") and not set(l) <= set("|-: ")]
    rows = [r for r in rows if not r.startswith("| Ticker")]
    assert len(rows) == 2
    assert problems(stocks_output(rows)) == []


def test_the_spec_keeps_forecasts_out_of_the_earnings_cell():
    section = _spec().split("### Stocks table", 1)[1].split("###", 1)[0]
    assert "rule 8" in section and "never printed" in section


def test_the_stocks_table_is_in_the_mode_c_checklist_and_method_template():
    text = _spec()
    assert "Stocks window:" in text and "Earnings dates:" in text
    assert "- [ ] Stocks table:" in text


def test_skill_md_routes_mode_c_to_the_stocks_table():
    assert "Stocks table" in (REPO / "SKILL.md").read_text(encoding="utf-8")


def test_a_question_scoped_mode_c_run_may_leave_stocks_out_and_says_so():
    result = "Mode: Portfolio (Mode C)\nSectors (market weights)\n| Sector | Total |\n|---|---|\n| IT | 43.03 |\n"
    scoped = {"RESULT": result, "METHOD": "Build: x\nTables: Allocation, Sectors (asked: sectors)\n"}
    assert contract.stocks_table_problems(scoped) == []
    unsaid = {"RESULT": result, "METHOD": "Build: x\n"}
    assert contract.stocks_table_problems(unsaid) == [
        "Mode C printed no Stocks table and METHOD's Tables: line does not leave it out"]
    listed = {"RESULT": result, "METHOD": "Build: x\nTables: Allocation, Stocks (asked: stocks)\n"}
    assert contract.stocks_table_problems(listed) != []
