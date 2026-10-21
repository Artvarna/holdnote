"""scripts/render.py: the chat view of a checked draft (RULES.md Part IV v12).

SYNTHETIC drafts from test_brief_layout; no figure is a record of a run.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))

import contract  # noqa: E402
import render  # noqa: E402
import test_brief_layout as tb  # noqa: E402

BRIEF = tb.brief(tb.FULL + tb.NOTES)
CHECKLIST = tb.brief(tb.CHECKLIST, mode="Buffett checklist")
NUMBER = re.compile(r"[-+−]?\d[\d,]*(?:\.\d+)?%?")


def test_every_result_table_survives_under_a_plain_heading():
    # Headings carry no emoji since 2026-10-21: the icons stay in result cells.
    out = render.render(BRIEF)
    for name in contract.result_tables(contract.split_sections(BRIEF)["RESULT"]):
        assert re.search(rf"^### {re.escape(name)}$", out, re.MULTILINE), name


def test_no_number_is_invented_and_none_is_lost():
    draft_result = contract.split_sections(BRIEF)["RESULT"]
    out = render.render(BRIEF)
    body = out.split("\n---\n")[0]
    assert set(NUMBER.findall(draft_result)) <= set(NUMBER.findall(body))
    allowed = set(NUMBER.findall(BRIEF))
    assert set(NUMBER.findall(body)) <= allowed


def test_results_become_icons_and_the_scorecard_folds_its_label():
    out = render.render(BRIEF)
    assert "| **Moat** · Gross margin, FY2016–FY2025 | 38.1% → 46.2% | Stable or rising | ✅ |" in out
    assert "| **Margin of safety** · Owner-earnings yield vs 10y Treasury | 3.1% vs 4.2% | Yield above Treasury | ❌ |" in out
    assert "| 📄 Filing | Supply concentration in one region | 10-K FY2025, Item 1A | 🆕 New |" in out


def test_tldr_is_a_box_and_status_is_one_quiet_line():
    out = render.render(BRIEF).splitlines()
    assert out[0] == "## AAA · Company A Inc."
    assert out[1] == "*Stock brief · data as of 2026-10-11 · USD millions*"
    assert "Complete" not in render.render(BRIEF)
    assert "> **Scorecard** 4 of 6 met · 1 not met · 1 not available  " in out


def test_every_report_ends_with_the_disclaimer_and_proof_hint():
    for draft in (BRIEF, CHECKLIST):
        out = render.render(draft)
        assert out.rstrip().endswith(f"*{render.DISCLAIMER}*")
        assert "Not financial advice" in render.DISCLAIMER
        assert "Buffett" not in render.DISCLAIMER  # removed from every report 2026-10-21
        assert 'say **"show proof"**' in out


def test_warnings_surface_and_routine_method_lines_do_not():
    draft = BRIEF.replace("Columns suppressed: none\n",
                          "Columns suppressed: none\nConflict: price 229.28 [Nasdaq] vs 230.48 [Yahoo]\n")
    out = render.render(draft)
    assert "#### ⚠️ Check before relying on this" in out
    assert "- **Conflict:** price 229.28 [Nasdaq] vs 230.48 [Yahoo]" in out
    assert "Detail tables" not in out and "Columns suppressed" not in out


def test_the_checklist_renders_its_filters():
    out = render.render(CHECKLIST)
    assert "### Four filters" in out and "### Your position" in out
    assert "> **Filters** 2 yes · 1 not sure · scorecard 4 of 6 met  " in out
    assert "| 2. Lasting economics | Moat Met, Capital efficiency Met | Met |" in out  # Answer stays words


def test_a_halt_says_so_and_points_to_proof():
    halted = ("STATUS: Halted - weight sum 97.2 outside 99.9-100.1\n\nCONTEXT\nData as of: 2026-10-11\n\n"
              "METHOD\nBuild: test\n\nPROOF\nsum 97.2\n\nSOURCES\n- local file x.csv n/a — local file\n")
    out = render.render(halted)
    assert out.splitlines()[1].startswith("⛔ **Stopped** · weight sum 97.2")
    assert 'say **"show proof"** to see which check' in out


def test_reworded_risk_gets_its_own_icon():
    draft = tb.brief(tb.SCORECARD + tb.KEY_NUMBERS + tb.WHAT_CHANGED + tb.REWORDED)
    assert "✏️ Reworded" in render.render(draft)


def test_status_line_keeps_only_the_first_units_clause():
    draft = BRIEF.replace("Currency / units: USD millions · reported, not adjusted",
                          "Currency / units: USD millions; cash never summed across currencies")
    line = render.render(draft).splitlines()[1]
    assert line == "*Stock brief · data as of 2026-10-11 · USD millions*"
