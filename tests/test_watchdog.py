"""Tests for scripts/watchdog.py: the Thesis Watchdog (references/thesis-watchdog.md)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

import watchdog as wd  # noqa: E402

DEF = "gross margin, quarter, GrossProfit / Revenues"


def run(args, cwd):
    p = subprocess.run([sys.executable, str(REPO / "scripts" / "watchdog.py"), *args],
                       cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def add(cwd, *extra, holding="AAPL", words="If services margin falls under 70%, I was wrong",
        metric="gross_margin", test="< 45", baseline="46.2"):
    return run(["add", "--watch", "watch.md", "--holding", holding, "--isin", "US0378331005",
                "--words", words, "--metric", metric, "--definition", DEF, "--test", test,
                "--baseline", baseline, "--baseline-date", "2026-08-01",
                "--baseline-source", "Apple 10-Q filed 2026-08-01", *extra], cwd)


def values(cwd, vals, as_of="2026-11-21"):
    (cwd / "v.json").write_text(json.dumps({"as_of": as_of, "values": vals}), encoding="utf-8")


def v(value, evidence="ACC-2", unit="%", definition=DEF, date="2026-10-31", **kw):
    return {"value": value, "unit": unit, "definition": definition, "date": date,
            "source": "Apple 10-Q filed 2026-10-31", "evidence": evidence, **kw}


def check(cwd, *extra):
    return run(["check", "--watch", "watch.md", "--values", "v.json", "--write", *extra], cwd)


def state(cwd, wid="AAPL-1"):
    return next(w.state for w in wd.load(cwd / "watch.md") if w.id == wid)


def test_add_then_round_trip_keeps_the_words_verbatim(tmp_path):
    words = 'If "services" | margin drops, I was wrong \\ really'
    code, out = add(tmp_path, words=words)
    assert code == 0, out
    wires = wd.load(tmp_path / "watch.md")
    assert wires[0].words == words and wires[0].id == "AAPL-1"
    code, _ = add(tmp_path)
    assert [w.id for w in wd.load(tmp_path / "watch.md")] == ["AAPL-1", "AAPL-2"]


def test_met_alerts_once_then_still_met_then_rearms(tmp_path):
    add(tmp_path)
    values(tmp_path, {"AAPL-1": v("44.1")})
    code, out = check(tmp_path)
    assert code == 0, out
    assert "1 condition you wrote has been met." in out
    assert 'You wrote: "If services margin falls under 70%, I was wrong"' in out
    assert "Subject: Holdnote weekly: 1 condition you wrote met" in out
    assert state(tmp_path) == "met 2026-10-31"

    values(tmp_path, {"AAPL-1": v("43.9", evidence="ACC-3", date="2027-01-30")})
    _, out = check(tmp_path)
    assert "No condition you wrote was met this week." in out and "still met" in out
    assert state(tmp_path) == "met 2026-10-31"

    values(tmp_path, {"AAPL-1": v("47.0", evidence="ACC-4", date="2027-05-01")})
    _, out = check(tmp_path)
    assert "no longer met" in out and state(tmp_path) == "armed"

    values(tmp_path, {"AAPL-1": v("44.0", evidence="ACC-5", date="2027-08-01")})
    _, out = check(tmp_path)
    assert "1 condition you wrote has been met." in out  # re-armed, so it alerts again


def test_the_same_filing_is_not_checked_twice(tmp_path):
    add(tmp_path)
    values(tmp_path, {"AAPL-1": v("44.1")})
    check(tmp_path)
    _, out = check(tmp_path)
    assert "no new information" in out and "has been met" not in out


def test_a_different_definition_is_not_compared(tmp_path):
    add(tmp_path)
    values(tmp_path, {"AAPL-1": v("44.1", definition="gross margin, fiscal year")})
    _, out = check(tmp_path)
    assert "not compared" in out and "not the same figure" in out
    assert state(tmp_path) == "armed"


def test_a_fraction_read_as_a_percentage_is_not_compared(tmp_path):
    add(tmp_path)
    values(tmp_path, {"AAPL-1": v("0.441")})
    _, out = check(tmp_path)
    assert "not compared" in out and "jump" in out and state(tmp_path) == "armed"


def test_wrong_unit_is_not_compared(tmp_path):
    add(tmp_path)
    values(tmp_path, {"AAPL-1": v("44.1", unit="x")})
    _, out = check(tmp_path)
    assert "not compared" in out


def test_a_value_without_evidence_refuses(tmp_path):
    add(tmp_path)
    values(tmp_path, {"AAPL-1": v("44.1", evidence="")})
    code, out = check(tmp_path)
    assert code == 1 and "no evidence id" in out


def test_a_filing_figure_needs_its_passage(tmp_path):
    add(tmp_path, metric="filing_figure", test="< 70", baseline="74.0")
    values(tmp_path, {"AAPL-1": v("68.4", unit="as stated")})
    code, out = check(tmp_path)
    assert code == 1 and "passage quoted" in out
    values(tmp_path, {"AAPL-1": v("68.4", unit="as stated",
                                  quote="Services gross margin was 68.4%")})
    code, out = check(tmp_path)
    assert code == 0 and 'Passage: "Services gross margin was 68.4%"' in out


def test_fund_text_tripwire_on_an_index_change(tmp_path):
    code, out = run(["add", "--watch", "watch.md", "--holding", "SPPW", "--kind", "fund",
                     "--words", "If they switch the index, I want to know", "--metric", "index",
                     "--definition", "benchmark index named in the factsheet", "--test", "changes",
                     "--baseline", "MSCI World Index", "--baseline-date", "2026-10-01",
                     "--baseline-source", "SSGA factsheet"], tmp_path)
    assert code == 0, out
    values(tmp_path, {"SPPW-1": v("MSCI World Index", unit="text",
                                  definition="benchmark index named in the factsheet",
                                  evidence="FS-2026-11")})
    _, out = check(tmp_path)
    assert "not met" in out
    values(tmp_path, {"SPPW-1": v("MSCI World ESG Screened Index", unit="text",
                                  definition="benchmark index named in the factsheet",
                                  evidence="FS-2026-12")})
    _, out = check(tmp_path)
    assert "1 condition you wrote has been met." in out


def test_price_alone_cannot_be_watched(tmp_path):
    code, out = add(tmp_path, metric="price")
    assert code == 1 and "not one Holdnote can watch" in out


def test_a_text_metric_needs_changes_and_a_number_metric_a_number(tmp_path):
    code, out = add(tmp_path, metric="index", test="< 3")
    assert code == 1 and "takes 'changes'" in out
    code, out = add(tmp_path, test="changes")
    assert code == 1 and "takes a number test" in out


def test_a_stock_metric_on_a_fund_refuses(tmp_path):
    code, out = add(tmp_path, "--kind", "fund", holding="SPPW")
    assert code == 1 and "is a stock metric" in out


def test_not_watchable_is_kept_and_listed(tmp_path):
    code, out = run(["add", "--watch", "watch.md", "--holding", "NVDA",
                     "--words", "If Jensen stops caring", "--not-watchable"], tmp_path)
    assert code == 0, out
    add(tmp_path)
    values(tmp_path, {"AAPL-1": v("50")})
    _, out = check(tmp_path)
    assert 'Not watchable (no document can show these): NVDA "If Jensen stops caring".' in out


def test_a_newer_thesis_after_the_tripwire_is_noted(tmp_path):
    (tmp_path / "theses").mkdir()
    (tmp_path / "theses" / "AAPL-2026-11-05.md").write_text("x", encoding="utf-8")
    add(tmp_path)
    values(tmp_path, {"AAPL-1": v("44.1")})
    _, out = check(tmp_path, "--theses", "theses")
    assert "a newer thesis was written on 2026-11-05, after this was met" in out


def test_holding_status_for_the_mirror(tmp_path):
    add(tmp_path)
    assert wd.holding_status(tmp_path / "watch.md")["AAPL"] == "watched"
    values(tmp_path, {"AAPL-1": v("44.1")})
    check(tmp_path)
    status = wd.holding_status(tmp_path / "watch.md")
    assert status["AAPL"] == status["US0378331005"] == "tripwire met 2026-10-31"


def test_a_hand_edited_broken_row_refuses_with_its_line(tmp_path):
    add(tmp_path)
    text = (tmp_path / "watch.md").read_text().replace("| armed |", "| maybe |")
    (tmp_path / "watch.md").write_text(text)
    code, out = run(["list", "--watch", "watch.md"], tmp_path)
    assert code == 1 and "watch.md:" in out and "maybe" in out


LOADED = re.compile(r"\b(sell|selling|buy|should|consider|exit|trim|broke|broken|wrong move|"
                    r"recommend|warning|danger)\b", re.I)


def test_no_instruction_words_beyond_the_users_own(tmp_path):
    add(tmp_path, words="my words")
    values(tmp_path, {"AAPL-1": v("44.1")})
    _, out = check(tmp_path)
    assert not LOADED.search(out), LOADED.search(out)


def test_the_users_own_words_pass_the_contract_but_holdnotes_do_not(tmp_path):
    sys.path.insert(0, str(REPO / "tests"))
    import contract

    add(tmp_path, words="I'd sell if margins fall, I hold it for the margin")
    values(tmp_path, {"AAPL-1": v("44.1")})
    _, out = check(tmp_path)
    assert contract.banned_hits(out) == []
    assert contract.banned_hits(out + "\nYou should sell now.") != []
    assert contract.banned_hits('| ID | Note |\n|---|---|\n| A | "sell it" |') != []


def test_nothing_checked_is_never_an_all_clear(tmp_path):
    add(tmp_path)
    add(tmp_path)
    values(tmp_path, {})
    _, out = check(tmp_path)
    assert "No condition you wrote was met" not in out
    assert "this is not an all-clear" in out
    assert "Subject: Holdnote weekly: Watchdog could not check any of your 2 tripwires" in out


def test_partly_checked_says_how_many_were_not(tmp_path):
    add(tmp_path)
    add(tmp_path)
    values(tmp_path, {"AAPL-1": v("50")})
    _, out = check(tmp_path)
    assert "Subject: Holdnote weekly: no condition you wrote was met (1 of 2 not checked)" in out


def test_values_for_a_mistyped_id_are_named(tmp_path):
    add(tmp_path)
    values(tmp_path, {"AAPL-1": v("50"), "APPL-1": v("40")})
    _, out = check(tmp_path)
    assert "Values for no tripwire on file (a mistyped ID?): APPL-1." in out


def test_a_period_instead_of_a_date_refuses_before_it_reaches_the_file(tmp_path):
    add(tmp_path)
    values(tmp_path, {"AAPL-1": v("44.1", date="Q3 2026")})
    code, out = check(tmp_path)
    assert code == 1 and "not YYYY-MM-DD" in out
    assert state(tmp_path) == "armed"  # nothing written


def test_words_on_two_lines_refuse_rather_than_being_reworded(tmp_path):
    code, out = add(tmp_path, words="line one\nline two")
    assert code == 1 and "more than one line" in out
