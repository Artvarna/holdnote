"""Market-wide output contract, and the routing vectors that choose it.

Market-wide mode has no script: the agent composes the output from
references/market-context.md. What can be tested is the contract a parser
holds that output to, so these tests run contract.py's checks against
outputs built here -- one that obeys the contract, and variants that each
break it the way a live run did on 2026-09-27.

SYNTHETIC. Every figure below is invented for the test, round on purpose so
nobody mistakes it for a market level, and the constituents are unnamed.
These are not records of any run; the runs themselves are not quoted here
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

# --------------------------------------------------------------------------
# Output builder
# --------------------------------------------------------------------------

DEFAULT_SET = [
    ("S&P 500", "price, USD", "NYSE", "S&P DJI; WSJ"),
    ("Nasdaq Composite", "price, USD", "Nasdaq", "Nasdaq; WSJ"),
    ("Dow Jones Industrial Average", "price, USD", "NYSE", "S&P DJI; WSJ"),
    ("STOXX Europe 600", "price, EUR", "STOXX", "STOXX; FT"),
    ("MSCI World", "price, USD", "MSCI", "MSCI; FT"),
    ("MSCI EM", "price, USD", "MSCI", "MSCI; FT"),
]
SECTOR_SET = [
    ("S&P 500 Energy", "price, USD", "NYSE", "S&P DJI; WSJ"),
    ("STOXX Europe 600 Banks", "price, EUR", "STOXX", "STOXX; FT"),
]
RATES = [
    ("US 10Y (yield, %)", "4.10", "4.16", "US Treasury; FRED"),
    ("Euro area 10Y (yield, %)", "2.70", "2.74", "ECB; Bundesbank"),
    ("EUR/USD", "1.1000", "1.1050", "ECB; Fed H.10"),
]
BASE, END = "2026-09-18", "2026-09-25"


def _row(name, variant, venue, sources, move):
    end = 1000 * (1 + move / 100)
    cell = f"{name} ({variant})"
    result = f"| {cell} | {end:.2f} | {move:+.2f} | {END} ({venue} close) |"
    proof = (
        f"{cell}  base {BASE} 1000.00 [{sources}]  end {END} {end:.2f} "
        f"[{sources}]  ({end:.2f} / 1000.00 - 1) x 100 = {move:.2f}%  PASS"
    )
    return result, proof


def market_output(
    *,
    named: list[str] | None = None,
    contribution: bool = False,
    data_as_of: str = "2026-09-27 13:14 EEST",
) -> str:
    """A Market-wide run as market-context.md -> Output specifies it."""
    indexes = [r for r in DEFAULT_SET if named is None or r[0] in named]
    sectors = SECTOR_SET if named is None else []
    rates = RATES if named is None else []

    idx_rows, sec_rows, proof_rows = [], [], []
    for i, spec in enumerate(indexes):
        res, prf = _row(*spec, move=0.5 + i / 10)
        idx_rows.append(res)
        proof_rows.append(prf)
    for i, spec in enumerate(sectors):
        res, prf = _row(*spec, move=-0.4 - i / 10)
        sec_rows.append(res)
        proof_rows.append(prf)
    rate_rows = []
    for name, base, end, sources in rates:
        rate_rows.append(f"| {name} | {end} | {float(end) - float(base):+.2f} | {END} |")
        proof_rows.append(
            f"{name}  base {BASE} {base} [{sources}]  end {END} {end} "
            f"[{sources}]  {end} - {base} = {float(end) - float(base):+.2f}  PASS"
        )

    tables = ["Indexes", "| Instrument | Level | Period % | As of |", "|---|---|---|---|"]
    tables += idx_rows
    if sectors:
        tables += ["", "Sectors", "| Instrument | Level | Period % | As of |", "|---|---|---|---|"]
        tables += sec_rows
    if rates:
        tables += ["", "Rates & FX", "| Instrument | Level | Change | As of |", "|---|---|---|---|"]
        tables += rate_rows
    if contribution:
        tables += [
            "",
            "Contribution",
            "| Index | Constituent | Weight % | Move % | Contribution pp | Weight as of |",
            "|---|---|---|---|---|---|",
            "| S&P 500 | Constituent A | 7.0 | 2.0 | 0.14 | 2026-09-24 |",
        ]
        proof_rows.append("Constituent A  7.0 x 2.0 / 100 = 0.14pp >= 0.10pp  PASS")

    not_run = []
    if named is not None:
        not_run.append("Sectors, Rates & FX (out of scope)")
    if not contribution:
        not_run.append("Contribution (not requested)")
    scope = (
        "Scope:          default set"
        if named is None
        else "Scope:          named indexes only — " + ", ".join(named)
    )
    contrib = (
        "Contribution:   on (requested) — weight x move / 100, 0.10pp threshold,"
        " S&P DJI constituent file 2026-09-24"
        if contribution
        else "Contribution:   off (not requested)"
    )
    m = len(DEFAULT_SET) if named is None else len(named)
    return "\n".join(
        [
            "STATUS",
            "",
            "Complete.",
            "",
            "CONTEXT",
            "",
            f"Data as of:       {data_as_of}",
            f'Latest period:    {BASE} to {END} ("this week")',
            "Currency / units: index points, % change; yields in %, changes in pp",
            "Not available:    none",
            f"Coverage:         {len(indexes)} of {m} indexes",
            "",
            "RESULT",
            "",
            "Mode: Market-wide",
            "",
            *tables,
            "",
            "METHOD",
            "",
            scope,
            contrib,
            "Tables not run: " + ("; ".join(not_run) or "none"),
            "Sector scheme:  as each provider names it",
            "Session:        a session is complete once its exchange has closed",
            "Period:         \"this week\" -> last session before Monday",
            "Reused:         none",
            "Columns suppressed: none",
            "",
            "PROOF",
            "",
            *proof_rows,
            "",
            "SOURCES",
            "",
            "| URL | Title | Published | Retrieved (UTC) |",
            "|---|---|---|---|",
            f"| https://www.spglobal.com/spdji/ | S&P 500 | {END} | 2026-09-27 10:14 |",
            "",
        ]
    )


def sections(text: str) -> dict[str, str]:
    return contract.split_sections(text)


# --------------------------------------------------------------------------
# The builder obeys the contract -- otherwise every failure below is noise
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "named, contribution",
    [(None, False), (["S&P 500"], False), (["S&P 500"], True)],
    ids=["default", "named", "contribution"],
)
def test_a_conforming_output_trips_no_check(named, contribution):
    text = market_output(named=named, contribution=contribution)
    s = sections(text)
    assert contract.section_order(text) == contract.SECTIONS
    assert contract.placeholder_times(text) == []
    assert contract.text_outside_sections(text) == []
    assert contract.close_row_problems(s["PROOF"]) == []
    assert contract.variant_problems(s) == []
    assert contract.scope_problems(s, named) == []
    assert contract.contribution_problems(s, contribution) == []
    assert contract.conflict_problems(s) == []
    assert contract.sources_without_url(text) == []
    assert contract.period_cell_problems(s) == []
    assert contract.banned_hits(text) == []


# --------------------------------------------------------------------------
# 1. No placeholder time
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "printed", ["2026-09-27 13:1x EEST", "2026-09-27 1?:05 EEST", "2026-09-27 HH:MM EEST",
                "2026-09-27T13:1xZ", "2026-09-27 25:00 EEST"],
)
def test_a_placeholder_time_is_caught(printed):
    text = market_output(data_as_of=printed)
    assert contract.placeholder_times(text), printed


@pytest.mark.parametrize("printed", ["2026-09-27", "2026-09-27 13:14 EEST", "2026-09-27T10:14Z"])
def test_an_exact_time_or_a_bare_date_passes(printed):
    assert contract.placeholder_times(market_output(data_as_of=printed)) == []


def test_ratios_and_urls_are_not_times():
    assert contract.placeholder_times("a 2:1 split, https://x.test/a, Mode: B") == []


# --------------------------------------------------------------------------
# 2. No text outside the six sections
# --------------------------------------------------------------------------


def test_a_note_after_sources_is_outside_the_sections():
    text = market_output() + "\nNote: MSCI levels are provisional until T+1.\n"
    stray = contract.text_outside_sections(text)
    assert stray == ["Note: MSCI levels are provisional until T+1."]


def test_a_note_before_status_is_outside_the_sections():
    text = "Quick summary before the report.\n\n" + market_output()
    assert contract.text_outside_sections(text) == ["Quick summary before the report."]


def test_the_same_note_in_method_is_inside():
    text = market_output().replace(
        "Reused:         none",
        "Reused:         none\nMSCI levels are provisional until T+1.",
    )
    assert contract.text_outside_sections(text) == []


def test_only_a_specified_subject_line_may_sit_above_status():
    subject = "=== VWCE — Vanguard FTSE All-World UCITS ETF · IE00BK5BQT80 · Acc ===\n"
    assert contract.text_outside_sections(subject + market_output(), subject_line=True) == []
    assert contract.text_outside_sections(subject + market_output()) != []


# --------------------------------------------------------------------------
# 3. Single source is never PASS; every row carries its base date
# --------------------------------------------------------------------------


def test_a_single_source_close_marked_pass_is_caught():
    text = market_output().replace(
        "base 2026-09-18 4.10 [US Treasury; FRED]", "base 2026-09-18 4.10 [US Treasury]"
    )
    problems = contract.close_row_problems(sections(text)["PROOF"])
    assert len(problems) == 1 and problems[0].startswith("single source marked PASS")
    assert "US 10Y" in problems[0]


def test_a_single_source_close_tagged_single_source_passes():
    text = market_output()
    lines = sections(text)["PROOF"].splitlines()
    lines = [
        re.sub(r"\[US Treasury; FRED\](.*)PASS$", r"[US Treasury]\1single source", l, count=1)
        if l.startswith("US 10Y") else l
        for l in lines
    ]
    assert contract.close_row_problems("\n".join(lines)) == []


def test_a_rates_row_without_its_base_date_is_caught():
    proof = "US 10Y (yield, %)  base 4.10 [US Treasury; FRED]  end 2026-09-25 4.16 [US Treasury; FRED]  +0.06  PASS"
    assert contract.close_row_problems(proof) == [f"no base date: {proof}"]


STOXX_ROW = "| STOXX Europe 600 (price, EUR) | 1008.00 | +0.80 | 2026-09-25 (STOXX close) |"
STOXX_PROOF_PREFIX = "STOXX Europe 600 (price, EUR)  base 2026-09-18"
CONFLICT_LINE = (
    "STOXX Europe 600 (price, EUR)  base 2026-09-18 1000.00 (price, EUR) [STOXX] "
    "vs 2026-09-18 1006.10 (price, EUR) [FT] gap 0.61%  "
    "end 2026-09-25 1008.00 [STOXX; FT]  CONFLICT"
)


def with_proof_line(text: str, line: str) -> str:
    """Replace the STOXX Europe 600 PROOF line."""
    out = [line if l.startswith(STOXX_PROOF_PREFIX) else l for l in text.splitlines()]
    return "\n".join(out)


def withheld_for_conflict(proof_line: str = CONFLICT_LINE) -> str:
    """A default run whose STOXX Europe 600 row is withheld on a conflict."""
    text = market_output().replace(
        STOXX_ROW,
        "| STOXX Europe 600 (price, EUR) | Not available — sources conflict | "
        "Not available — sources conflict | 2026-09-25 (STOXX close) |",
    ).replace(
        "Not available:    none",
        "Not available:    STOXX Europe 600 (price, EUR) — sources conflict",
    )
    return with_proof_line(text, proof_line)


def test_a_withheld_conflict_still_prints_both_figures_in_proof():
    s = sections(withheld_for_conflict())
    assert contract.conflict_problems(s) == []
    assert contract.close_row_problems(s["PROOF"]) == []
    assert contract.close_row_problems(CONFLICT_LINE.replace("CONFLICT", "PASS"))


def test_a_withheld_conflict_without_its_figures_is_caught():
    bare = (
        "STOXX Europe 600 (price, EUR)  base 2026-09-18 [STOXX; FT]  "
        "end 2026-09-25 [STOXX; FT]  sources conflict  CONFLICT"
    )
    s = sections(withheld_for_conflict(bare))
    assert contract.conflict_problems(s) == [
        "STOXX Europe 600 (price, EUR): CONFLICT without both dated, sourced figures"
    ]


def test_a_withheld_row_with_no_conflict_line_is_caught():
    s = sections(withheld_for_conflict(STOXX_PROOF_PREFIX + " 1000.00 [STOXX; FT]  "
                                       "end 2026-09-25 1008.00 [STOXX; FT]  PASS"))
    assert contract.conflict_problems(s) == [
        "Indexes: STOXX Europe 600 (price, EUR) withheld with no CONFLICT line in METHOD or PROOF"
    ]


def without_proof(text: str, method_lines=()) -> str:
    """The default form: PROOF dropped, extra METHOD lines appended."""
    before, _, rest = text.partition("\nPROOF\n")
    _, _, after = rest.partition("\nSOURCES\n")
    head, _, method = before.partition("\nMETHOD\n")
    method = method.rstrip("\n") + "".join(f"\n{l}" for l in method_lines) + "\n"
    return f"{head}\nMETHOD\n{method}\nSOURCES\n{after}"


def test_default_run_without_proof_obeys_the_contract():
    text = without_proof(market_output(), ["Confirmation:   all rows checked",
                                           "Conflict:       none",
                                           "Fallbacks:      none"])
    assert contract.section_order(text) == [
        "STATUS", "CONTEXT", "RESULT", "METHOD", "SOURCES"
    ]
    assert contract.text_outside_sections(text) == []
    assert contract.conflict_problems(sections(text)) == []


def test_a_conflict_without_proof_is_a_method_line():
    """With PROOF hidden, the withheld row's figures are on METHOD's line."""
    text = without_proof(withheld_for_conflict(), [f"Conflict:       {CONFLICT_LINE}"])
    assert "PROOF" not in sections(text)
    assert contract.conflict_problems(sections(text)) == []


def test_a_conflict_hidden_with_proof_is_caught():
    """Dropping PROOF must not drop the conflict with it."""
    text = without_proof(withheld_for_conflict())
    assert contract.conflict_problems(sections(text)) == [
        "Indexes: STOXX Europe 600 (price, EUR) withheld with no CONFLICT line in METHOD or PROOF"
    ]


def test_price_against_net_is_two_instruments_not_a_conflict():
    # A net total return level sits well above the price level of the same
    # index. Comparing them manufactures a conflict out of two instruments.
    across = CONFLICT_LINE.replace("1006.10 (price, EUR) [FT] gap 0.61%",
                                   "1300.00 (net, EUR) [FT] gap 30.00%")
    assert contract.conflict_problems(sections(withheld_for_conflict(across))) == [
        "STOXX Europe 600 (price, EUR): compared (price, EUR) with (net, EUR) "
        "-- two instruments, not a conflict"
    ]
    # Handled correctly: the net figure is no source for the price row, which
    # prints, and is left with one matching source for its base close.
    right = (
        "STOXX Europe 600 (price, EUR)  base 2026-09-18 1000.00 [STOXX]  "
        "end 2026-09-25 1008.00 [STOXX; FT]  (1008.00 / 1000.00 - 1) x 100 = 0.80%  "
        "single source"
    )
    s = sections(with_proof_line(market_output(), right))
    assert contract.conflict_problems(s) == []
    assert contract.close_row_problems(s["PROOF"]) == []


def test_a_currency_mismatch_is_not_a_conflict_either():
    across = CONFLICT_LINE.replace("1006.10 (price, EUR)", "1006.10 (price, USD)")
    assert "two instruments, not a conflict" in contract.conflict_problems(
        sections(withheld_for_conflict(across))
    )[0]


def test_a_gap_within_tolerance_is_not_a_conflict():
    close = CONFLICT_LINE.replace("1006.10", "1004.00").replace("0.61%", "0.40%")
    assert contract.conflict_problems(sections(withheld_for_conflict(close))) == [
        "STOXX Europe 600 (price, EUR): gap 0.40% is not over 0.5%"
    ]


# --------------------------------------------------------------------------
# 4. Named-index scope
# --------------------------------------------------------------------------


def test_a_named_run_that_prints_the_default_set_is_caught():
    # The request named the S&P 500; the output printed everything anyway.
    text = market_output().replace("Scope:          default set",
                                   "Scope:          named indexes only — S&P 500")
    problems = contract.scope_problems(sections(text), ["S&P 500"])
    assert "index not named in the request: MSCI World" in problems
    assert "Sectors printed on a named-index run" in problems
    assert "Rates & FX printed on a named-index run" in problems


def test_a_named_run_must_say_so_in_method():
    text = market_output(named=["S&P 500"]).replace(
        "Scope:          named indexes only — S&P 500", "Scope:          default set"
    )
    assert contract.scope_problems(sections(text), ["S&P 500"]) == [
        "METHOD does not say Scope: named indexes only"
    ]


def test_a_named_index_outside_the_default_set_still_prints():
    text = market_output(named=["S&P 500"]).replace(
        "| S&P 500 (price, USD) |", "| FTSE 100 (price, GBP) |"
    )
    method = sections(text)["METHOD"].replace("— S&P 500", "— FTSE 100")
    s = {**sections(text), "METHOD": method}
    assert contract.scope_problems(s, ["FTSE 100"]) == []


def test_a_breadth_table_is_caught():
    text = market_output().replace(
        "\nMETHOD", "\nBreadth\n| Index | Advancers | Decliners |\n|---|---|---|\n| S&P 500 | 1 | 1 |\n\nMETHOD", 1
    )
    assert "Breadth table printed; it is not part of Market-wide" in contract.scope_problems(
        sections(text), None
    )


# --------------------------------------------------------------------------
# Variant per row
# --------------------------------------------------------------------------


def test_an_instrument_cell_without_variant_is_caught():
    text = market_output().replace("| MSCI World (price, USD) |", "| MSCI World |")
    assert contract.variant_problems(sections(text)) == [
        "Indexes: no variant and currency in 'MSCI World'"
    ]


def test_variant_not_stated_must_be_listed_as_not_available():
    text = market_output().replace("| MSCI World (price, USD) |",
                                   "| MSCI World (variant not stated, USD) |")
    assert contract.variant_problems(sections(text)) == [
        "Indexes: MSCI World variant not listed as Not available"
    ]
    listed = text.replace("Not available:    none", "Not available:    MSCI World variant")
    assert contract.variant_problems(sections(listed)) == []


# --------------------------------------------------------------------------
# Headline convention: an unlabelled headline level is the price index
# --------------------------------------------------------------------------


def _close_line(instrument: str, base_sources: str, verdict: str = "PASS") -> str:
    return (
        f"{instrument}  base 2026-09-18 1000.00 [{base_sources}]  "
        f"end 2026-09-25 1005.00 [A; B]  (1005.00 / 1000.00 - 1) x 100 = 0.50%  {verdict}"
    )


@pytest.mark.parametrize(
    "instrument",
    ["S&P 500 (price, USD)", "Dow Jones Industrial Average (price, USD)",
     "Nasdaq Composite (price, USD)", "STOXX Europe 600 (price, EUR)"],
)
def test_an_unlabelled_headline_level_confirms_the_price_index(instrument):
    line = _close_line(instrument, "Provider; WSJ (variant not stated)")
    assert contract.close_row_problems(line) == []


@pytest.mark.parametrize(
    "instrument",
    ["MSCI World (price, USD)", "MSCI EM (net, USD)", "S&P 500 Energy (price, USD)"],
)
def test_an_unlabelled_level_confirms_nothing_outside_the_convention(instrument):
    line = _close_line(instrument, "Provider; FT (variant not stated)")
    assert contract.close_row_problems(line) == [f"single source marked PASS: {line}"]
    assert contract.close_row_problems(line.replace("PASS", "single source")) == []


def test_an_unlabelled_headline_level_is_price_not_net():
    line = _close_line("S&P 500 (net, USD)", "S&P DJI; WSJ (variant not stated)")
    assert contract.close_row_problems(line) == [f"single source marked PASS: {line}"]


def _conflict(instrument: str, second: str) -> dict[str, str]:
    line = (
        f"{instrument}  base 2026-09-18 1000.00 (price, USD) [Provider] "
        f"vs 2026-09-18 1006.10 ({second}) [Vendor] gap 0.61%  "
        "end 2026-09-25 1005.00 [Provider; Vendor]  CONFLICT"
    )
    return {"PROOF": line, "RESULT": ""}


def test_an_unlabelled_headline_level_can_conflict_with_the_price_index():
    assert contract.conflict_problems(_conflict("S&P 500 (price, USD)",
                                                "variant not stated, USD")) == []


def test_an_explicit_total_return_level_is_another_instrument():
    problems = contract.conflict_problems(_conflict("S&P 500 (price, USD)", "net, USD"))
    assert problems and "two instruments, not a conflict" in problems[0]


def test_an_unlabelled_msci_level_cannot_conflict():
    problems = contract.conflict_problems(_conflict("MSCI World (price, USD)",
                                                    "variant not stated, USD"))
    assert problems and "not a conflict" in problems[0]


# --------------------------------------------------------------------------
# URLs live inside SOURCES
# --------------------------------------------------------------------------


def test_a_sources_link_list_after_the_section_is_caught():
    text = market_output() + "\nSources:\n- https://www.spglobal.com/spdji/\n"
    stray = contract.text_outside_sections(text)
    assert "Sources:" in stray
    assert "separate link list: - https://www.spglobal.com/spdji/" in stray


def test_a_bare_link_list_under_the_table_is_caught():
    text = market_output() + "- https://www.stoxx.com/\n"
    assert contract.text_outside_sections(text) == [
        "separate link list: - https://www.stoxx.com/"
    ]


def test_every_sources_row_carries_its_url():
    text = market_output().replace(
        "| https://www.spglobal.com/spdji/ | S&P 500 |", "| S&P DJI | S&P 500 |"
    )
    assert contract.sources_without_url(text) == [
        "| S&P DJI | S&P 500 | 2026-09-25 | 2026-09-27 10:14 |"
    ]


def test_a_local_file_row_needs_no_url():
    assert contract.sources_without_url(
        "SOURCES\n\n- pies.md (updated 2026-09-17) - published n/a - local file\n"
    ) == []


# --------------------------------------------------------------------------
# Period % cells are bare signed numbers
# --------------------------------------------------------------------------


@pytest.mark.parametrize("cell", ["+0.80%", "0.80", "+0.80 %", "0.8pc"])
def test_a_period_cell_with_a_unit_or_no_sign_is_caught(cell):
    text = market_output().replace(STOXX_ROW, STOXX_ROW.replace("+0.80", cell))
    assert contract.period_cell_problems(sections(text)) == [
        f"Indexes: STOXX Europe 600 (price, EUR) Period % cell {cell!r}"
    ]


def test_a_withheld_period_cell_is_not_a_number_to_check():
    assert contract.period_cell_problems(sections(withheld_for_conflict())) == []


def _dist_table(dist_cell: str, other_cell: str = "—") -> dict[str, str]:
    """A Mode C Performance table carrying Incl. dist % (synthetic)."""
    return {
        "RESULT": "\n".join([
            "Performance",
            "| Instrument | Level | Period % | Incl. dist % | As of |",
            "|---|---|---|---|---|",
            f"| Fund D (DDD) | 100.00 GBP | +1.00 | {dist_cell} | 2026-01-09 (LSE close) |",
            f"| Fund A (AAA) | 50.000 EUR | -0.50 | {other_cell} | 2026-01-09 (Xetra close) |",
        ])
    }


@pytest.mark.parametrize("cell", ["+1.20", "Not available (amount not sourced)"])
def test_an_incl_dist_cell_that_is_a_signed_number_or_withheld_passes(cell):
    assert contract.period_cell_problems(_dist_table(cell)) == []


@pytest.mark.parametrize("cell", ["1.20", "+1.20%", "n/a"])
def test_an_incl_dist_cell_with_a_unit_or_no_sign_is_caught(cell):
    assert contract.period_cell_problems(_dist_table(cell)) == [
        f"Performance: Fund D (DDD) Incl. dist % cell {cell!r}"
    ]


def test_a_dash_is_only_allowed_in_the_incl_dist_column():
    table = _dist_table("+1.20")
    table["RESULT"] = table["RESULT"].replace("| -0.50 |", "| — |")
    assert contract.period_cell_problems(table) == [
        "Performance: Fund A (AAA) Period % cell '—'"
    ]


# --------------------------------------------------------------------------
# Contribution is opt-in
# --------------------------------------------------------------------------


def test_contribution_printed_unasked_is_caught():
    text = market_output(named=["S&P 500"], contribution=True)
    assert "Contribution printed without being requested" in contract.contribution_problems(
        sections(text), requested=False
    )


def test_contribution_asked_and_missing_is_caught():
    text = market_output(named=["S&P 500"])
    assert "Contribution requested and not printed" in contract.contribution_problems(
        sections(text), requested=True
    )


def test_a_multi_day_contribution_is_flagged_in_context():
    # The builder's period is "this week": several sessions, while the
    # Contribution table measures the last one.
    text = market_output(named=["S&P 500"], contribution=True)
    assert contract.contribution_problems(sections(text), True, multi_day=True) == [
        "CONTEXT Not available does not say: "
        "contribution for multi-day periods; last session shown"
    ]
    flagged = text.replace(
        "Not available:    none",
        "Not available:    contribution for multi-day periods; last\n"
        "                  session shown",
    )
    assert contract.contribution_problems(sections(flagged), True, multi_day=True) == []
    assert contract.contribution_problems(sections(text), True) == []  # one session


@pytest.mark.parametrize(
    "request_, asked",
    [
        ("which stocks drove the S&P", True),
        ("which stocks drove the S&P 500 today", True),
        ("what moved the Nasdaq today", True),
        ("biggest contributors to the STOXX 600", True),
        ("how's the S&P 500 done since Monday", False),
        ("how's the market done the last couple of days", False),
    ],
)
def test_contribution_trigger(request_, asked):
    assert contract.contribution_requested(request_) is asked


# --------------------------------------------------------------------------
# Routing vectors (SKILL.md) and stale references
# --------------------------------------------------------------------------


def _vectors() -> list[tuple[str, str, str]]:
    text = (REPO / "SKILL.md").read_text(encoding="utf-8")
    block = text.split("### Routing test vectors", 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in block.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[1].startswith("`Mode:"):
            rows.append((cells[0], cells[1].strip("`"), cells[2]))
    return rows


def test_every_routing_vector_names_a_mode_line_the_rules_define():
    rules = (REPO / "RULES.md").read_text(encoding="utf-8")
    defined = {"Mode: Market-wide", "Mode: Portfolio (Mode C)",
               "Mode: Index construction (Mode B)"}
    defined |= set(re.findall(r"^Mode: [^<\n]+$", rules, re.MULTILINE))
    vectors = _vectors()
    assert len(vectors) >= 9
    for _, mode, _ in vectors:
        # Routes combine as "Mode: A + B" (RULES.md Part IV, RESULT): each
        # part must be a route the rules define.
        parts = mode.removeprefix("Mode: ").split(" + ")
        assert all(f"Mode: {part}" in defined for part in parts), mode


def test_the_contribution_vector_is_in_skill_md():
    market = [v for v in _vectors() if v[1] == "Mode: Market-wide"]
    asked = [v for v in market if "Contribution table runs" in v[2]]
    assert asked, "no routing vector for the opt-in contribution trigger"
    for request, _, why in market:
        requests = [r.strip().strip('"') for r in request.split("·")]
        expected = "Contribution table runs" in why
        assert all(contract.contribution_requested(r) is expected for r in requests), request


def test_no_stale_references_to_retired_fields():
    docs = [REPO / "SKILL.md", *sorted((REPO / "references").glob("*.md"))]
    retired = [
        (r"\bbreadth\b", "Market-wide breadth"),
        (r"\badvancers\b", "Market-wide breadth"),
        (r"11\s+GICS\s+sectors", "Market-wide GICS sector table"),
        (r"funds\s+typically\s+track", "Mode B tracked-version field"),
    ]
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        for pattern, what in retired:
            assert not re.search(pattern, text, re.IGNORECASE), f"{doc.name}: {what}"


def test_no_reference_counts_six_context_fields():
    # CONTEXT has had five mandated fields since RULES.md v5. Six is the
    # number of *sections*, which is why the pattern needs "fields".
    docs = [REPO / "SKILL.md", REPO / "RULES.md", *sorted((REPO / "references").glob("*.md"))]
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        hit = re.search(r"\bsix\s+(?:mandated\s+|header\s+|CONTEXT\s+)?fields\b", text,
                        re.IGNORECASE)
        assert not hit, f"{doc.name}: {hit.group(0)!r}"


def test_coverage_never_counts_a_table_that_did_not_run():
    text = market_output(named=["S&P 500"]).replace(
        "Coverage:         1 of 1 indexes",
        "Coverage:         1 of 1 indexes, 0 of 0 rates & FX rows",
    )
    assert contract.coverage_problems(sections(text)) == [
        "not run, still counted: 0 of 0 rates & FX rows"
    ]
    assert contract.coverage_problems(sections(market_output(named=["S&P 500"]))) == []


def test_sources_grouped_under_a_dated_heading_are_not_rows():
    """The v9 run printed a dated heading with bare indented URLs under it."""
    grouped = market_output().replace(
        "| URL | Title | Published | Retrieved (UTC) |\n|---|---|---|---|\n"
        "| https://www.spglobal.com/spdji/ | S&P 500 | 2026-09-25 | 2026-09-27 10:14 |",
        "S&P DJI index-data endpoint, EOD series through 2026-09-25, retrieved 2026-09-28:\n"
        "  https://www.spglobal.com/spdji/   19:49",
    )
    assert grouped != market_output()
    stray = contract.text_outside_sections(grouped)
    assert any("https://www.spglobal.com/spdji/" in line for line in stray)

