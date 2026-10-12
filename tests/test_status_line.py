"""STATUS is `Complete.` alone, or a named halt -- RULES.md Part IV.

A live Mode C run printed a completed STATUS with a single-source tally
after it, and the tally miscounted the table below it. Nothing caught it:
the parser read only a STATUS header on its own line, so the one-line form
RULES.md also allows fell outside every section and no check looked at it.
The same run labelled its 8-K window `8-K window:` in METHOD, the PROOF
check's name, because the Stocks table section never named its METHOD lines.

SYNTHETIC. Outputs are built by the market and Stocks builders; the counts
in the bad STATUS lines are invented, not quoted from that run (RULES.md
rule 15).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import contract  # noqa: E402
from test_market_contract import market_output  # noqa: E402
from test_stocks_table import stocks_output  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
HEADER_FORM = "STATUS\n\nComplete.\n"


def with_status(text: str, status: str) -> str:
    assert text.startswith(HEADER_FORM)
    return status + text[len(HEADER_FORM):]


# --------------------------------------------------------------------------
# Both forms RULES.md allows parse as STATUS
# --------------------------------------------------------------------------


def test_header_form_passes():
    text = market_output()
    assert contract.status_problems(contract.split_sections(text)) == []


def test_one_line_form_is_a_section_not_stray_text():
    text = with_status(market_output(), "STATUS: Complete.\n")
    assert contract.section_order(text)[0] == "STATUS"
    assert contract.text_outside_sections(text) == []
    assert contract.status_problems(contract.split_sections(text)) == []


def test_the_t212_scripts_lowercase_complete_still_passes():
    text = with_status(market_output(), "STATUS\n\ncomplete\n")
    assert contract.status_problems(contract.split_sections(text)) == []


# --------------------------------------------------------------------------
# Complete. is the whole line
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status",
    [
        "STATUS: Complete - 2 of 5 Performance rows rest on a single source (named in METHOD)\n",
        "STATUS: Complete, with gaps.\n",
        "STATUS\n\nComplete. All closes confirmed.\n",
    ],
)
def test_anything_after_complete_is_caught(status):
    text = with_status(market_output(), status)
    problems = contract.status_problems(contract.split_sections(text))
    assert len(problems) == 1 and "nothing more" in problems[0], problems


def test_a_second_line_under_complete_is_caught():
    text = with_status(market_output(), "STATUS\n\nComplete.\nSee METHOD for single-source rows.\n")
    problems = contract.status_problems(contract.split_sections(text))
    assert len(problems) == 1 and "runs on" in problems[0], problems


def test_the_single_source_tally_belongs_on_the_confirmation_line():
    """The right home for the tally: METHOD, which every check already reads."""
    text = market_output().replace(
        "Reused:         none",
        "Reused:         none\nConfirmation:   single source: two rows, named here",
    )
    assert contract.status_problems(contract.split_sections(text)) == []
    assert contract.text_outside_sections(text) == []


# --------------------------------------------------------------------------
# Halts
# --------------------------------------------------------------------------


def test_the_rules_halt_example_passes_wrapped_over_two_lines():
    status = (
        "STATUS: Halted - cash provenance: indeterminate 28.9% of maximum claim\n"
        "        against threshold 5%.\n"
    )
    text = with_status(market_output(), status)
    assert contract.status_problems(contract.split_sections(text)) == []


def test_the_header_form_halt_passes():
    text = with_status(market_output(), "STATUS\n\nHALTED - check_weights_sum, 99.4% != 100%\n")
    assert contract.status_problems(contract.split_sections(text)) == []


@pytest.mark.parametrize("status", ["STATUS: Halted\n", "STATUS\n\nHalted.\n", "STATUS: Partial\n"])
def test_a_status_that_is_neither_form_is_caught(status):
    text = with_status(market_output(), status)
    assert contract.status_problems(contract.split_sections(text)) != []


def test_an_output_with_no_status_is_caught():
    text = market_output()[len(HEADER_FORM):]
    assert contract.status_problems(contract.split_sections(text)) == [
        "no STATUS: it is the first line of every output"
    ]


# --------------------------------------------------------------------------
# The Stocks table's METHOD labels
# --------------------------------------------------------------------------


def test_the_proof_check_name_is_not_the_method_label():
    text = stocks_output().replace(
        "Stocks window:     8-Ks filed in the 30 days to 2026-10-01, by EDGAR filing date",
        "8-K window:        2026-09-02 to 2026-10-01 by EDGAR filing date",
    )
    problems = contract.stocks_table_problems(contract.split_sections(text))
    assert problems == ["METHOD does not state the Stocks window"]


def test_the_stocks_section_names_both_method_labels():
    spec = (REPO / "references" / "etf-brief.md").read_text(encoding="utf-8")
    section = spec.split("### Stocks table", 1)[1].split("\n### ", 1)[0]
    assert "Stocks window:     8-Ks filed in the 30 days to [Data as of]" in section
    assert "Earnings dates:    company-announced only, never estimated" in section


def test_the_rules_say_complete_is_the_whole_line():
    rules = (REPO / "RULES.md").read_text(encoding="utf-8")
    assert "**`Complete.` is the whole line.**" in rules
    assert "status_problems" in rules
