"""Earnings recap: references/earnings-recap.md, RULES.md rules 6-8 v15.

SYNTHETIC. The ticker AAA, the company, every figure, outlet and estimate
are invented; nothing here is a record of a run (RULES.md rule 15).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import contract  # noqa: E402
import render  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

TLDR = [
    "Results:   revenue 1,200 (YoY +20.0%) · diluted EPS 1.10 (YoY +10.0%)",
    "Estimates: revenue +2.6% · EPS (non-GAAP) +4.0% against LSEG via Reuters",
    "Outlook:   1 raised · 0 lowered · 1 new",
    "",
]
RESULTS = [
    "Results (Q3 FY2026 vs Q2 FY2026 and Q3 FY2025, reported, USD millions except per share)",
    "| Metric | This quarter | Prior quarter | QoQ | Year-ago quarter | YoY |",
    "|---|---|---|---|---|---|",
    "| Revenue | 1,200 | 1,100 | +9.1% | 1,000 | +20.0% |",
    "| Gross margin | 60.0% | 58.0% | +2.0pp | 55.0% | +5.0pp |",
    "| Operating income | 300 | 250 | +20.0% | 240 | +25.0% |",
    "| Operating margin | 25.0% | 22.7% | +2.3pp | 24.0% | +1.0pp |",
    "| Net income | 220 | 200 | +10.0% | -40 | — |",
    "| Diluted EPS (USD) | 1.10 | 1.00 | +10.0% | 1.00 | +10.0% |",
    "| Operating cash flow | 400 | 360 | +11.1% | 380 | +5.3% |",
    "| Free cash flow | 250 | 220 | +13.6% | 260 | -3.8% |",
    "| Diluted EPS (non-GAAP, company-adjusted, USD) | 1.30 | 1.20 | +8.3% | 1.15 | +13.0% |",
    "",
]
SEGMENTS = [
    "Segments (Q3 FY2026 vs Q3 FY2025, revenue, USD millions)",
    "| Segment | This quarter | Year-ago quarter | YoY |",
    "|---|---|---|---|",
    "| Devices | 700 | 650 | +7.7% |",
    "| Services | 500 | 350 | +42.9% |",
    "",
]
ESTIMATES = [
    "Against estimates (as published by the named sources before the release — not Holdnote's)",
    "| Metric | Reported | Estimate | Estimate source | Difference |",
    "|---|---|---|---|---|",
    "| Revenue (USD millions) | 1,200 | 1,170 | LSEG via Reuters, 2026-10-21 | +2.6% |",
    "| EPS (non-GAAP, company-adjusted, USD) | 1.30 | 1.25 | LSEG via Reuters, 2026-10-21 | +4.0% |",
    "",
]
OUTLOOK = [
    "Company outlook (as stated by the company — not Holdnote's forecast)",
    "| Item | Period | Outlook as stated | Previous outlook | Change |",
    "|---|---|---|---|---|",
    "| Revenue | Q4 FY2026 | USD 1,250–1,300 million | — | New |",
    "| Capital expenditure | FY2026 | USD 900–950 million | USD 800–850 million | Raised |",
    "",
]
SAID = [
    "Management said (as stated by the company — not Holdnote's view)",
    "| Topic | Speaker | Said | Source |",
    "|---|---|---|---|",
    "| Services | CEO | Says services subscriptions passed 50 million in the quarter | Q3 earnings call (company transcript) |",
    "| Capital return | Company release | States a new USD 500 million share repurchase authorisation | Q3 results release |",
    "",
]
PRICE = [
    "Share price around the release (results published 2026-10-22, after the close)",
    "| Instrument | Close before release | First close after | Change % | Sessions |",
    "|---|---|---|---|---|",
    "| Company A Inc. (AAA, Nasdaq, USD) | 100.00 | 104.50 | +4.50 | 2026-10-22 to 2026-10-23 |",
    "| Benchmark: S&P 500 (price, USD) | 6600.00 | 6580.20 | -0.30 | 2026-10-22 to 2026-10-23 |",
    "",
]
METHOD = [
    "METHOD",
    "Build:             test",
    "Quarter:           the latest reported; fiscal year end December",
    "Basis:             reported (US GAAP); adjusted rows marked and reconciled in the release",
    "Margins:           gross profit ÷ revenue, operating income ÷ revenue",
    "Cash flow basis:   year-to-date less prior year-to-date, 10-Q",
    "Estimates rule:    third-party, named provider and outlet, published before the release (RULES.md rule 8)",
    "Estimates searched: 3 queries, 4 articles read, 1 used; 3 left out (no provider named)",
    "Outlook rule:      the company's own figures, as stated (RULES.md rule 8); Raised/Lowered by range midpoint",
    "Statements read:   results release, company transcript; 1 left out as about the share price",
    "Price window:      release 2026-10-22 16:05 EDT; closes 2026-10-22 and 2026-10-23",
    "Restatements:      none",
    "Confirmation:      all rows checked",
    "Conflict:          none",
    "Fallbacks:         none",
    "Columns suppressed: none",
    'Next:              say "why did AAA move after earnings" for the reasons named outlets reported',
    "",
]


def output(body: list[str] | None = None, *, method: list[str] | None = None,
           latest: str = "Q3 FY2026 (quarter ended 2026-09-30), released 2026-10-22") -> str:
    if body is None:
        body = TLDR + RESULTS + SEGMENTS + ESTIMATES + OUTLOOK + SAID + PRICE
    lines = [
        "=== AAA — Company A Inc. · earnings recap Q3 2026 ===",
        "STATUS: Complete.",
        "",
        "CONTEXT",
        "Data as of:       2026-10-25",
        f"Latest period:    {latest}",
        "Currency / units: USD millions except per share; changes in % or pp as marked",
        "Not available:    none",
        "Coverage:         Results 8 of 8 rows · Estimates from 1 of 3 articles read · Outlook 2 items · Statements from 2 documents",
        "",
        "RESULT",
        "Mode: Earnings recap",
        *body,
        *(METHOD if method is None else method),
        "SOURCES",
        "| URL | Title | Published | Retrieved (UTC) |",
        "|---|---|---|---|",
        "| https://www.sec.gov/example | 8-K Exhibit 99.1 | 2026-10-22 | 2026-10-25 10:00 UTC |",
        "| https://www.reuters.com/example | Reuters preview | 2026-10-21 | 2026-10-25 10:02 UTC |",
    ]
    return "\n".join(lines) + "\n"


def problems(text: str) -> list[str]:
    return contract.earnings_recap_problems(contract.split_sections(text))


def swap(rows: list[str], old: str, new: str) -> list[str]:
    assert any(old in r for r in rows), old
    return [r.replace(old, new) for r in rows]


def body(**tables: list[str]) -> list[str]:
    parts = {"tldr": TLDR, "results": RESULTS, "segments": SEGMENTS, "estimates": ESTIMATES,
             "outlook": OUTLOOK, "said": SAID, "price": PRICE}
    parts.update(tables)
    return [line for part in parts.values() for line in part]


def test_a_recap_passes_every_contract_check():
    assert contract.output_problems(output()) == []


def test_every_table_is_required_and_in_order():
    assert any("missing tables" in p for p in problems(output(body(outlook=[]))))
    swapped = TLDR + RESULTS + ESTIMATES + SEGMENTS + OUTLOOK + SAID + PRICE
    assert any("out of order" in p for p in problems(output(swapped)))


def test_a_change_must_rederive_from_its_two_values():
    bad = swap(RESULTS, "| 1,000 | +20.0% |", "| 1,000 | +25.0% |")
    assert any("Revenue" in p and "+20.00" in p for p in problems(output(body(results=bad))))


def test_margins_change_in_pp_and_amounts_in_percent():
    bad = swap(RESULTS, "| 58.0% | +2.0pp |", "| 58.0% | +3.4% |")
    assert any("in pp" in p for p in problems(output(body(results=bad))))


def test_a_change_from_a_loss_is_a_dash():
    bad = swap(RESULTS, "| -40 | — |", "| -40 | +650.0% |")
    assert any("negative base" in p for p in problems(output(body(results=bad))))


def test_an_adjusted_figure_never_replaces_a_reported_row():
    bad = swap(RESULTS, "| Diluted EPS (USD) | 1.10 |", "| Diluted EPS (adjusted, USD) | 1.10 |")
    assert any("adjusted" in p for p in problems(output(body(results=bad))))
    unmarked = swap(RESULTS, "(non-GAAP, company-adjusted, USD)", "(adjusted, USD)")
    assert any("not marked" in p for p in problems(output(body(results=unmarked))))


def test_an_estimate_names_its_provider_and_date():
    bad = swap(ESTIMATES, "LSEG via Reuters, 2026-10-21 | +2.6%", "analysts | +2.6%")
    assert any("does not name its provider" in p for p in problems(output(body(estimates=bad))))


def test_an_estimate_published_after_the_release_is_refused():
    bad = swap(ESTIMATES, "LSEG via Reuters, 2026-10-21 | +2.6%", "LSEG via Reuters, 2026-10-24 | +2.6%")
    assert any("after the release" in p for p in problems(output(body(estimates=bad))))


def test_the_gap_to_an_estimate_rederives():
    bad = swap(ESTIMATES, "| +4.0% |", "| +6.0% |")
    assert any("printed +6.0%" in p for p in problems(output(body(estimates=bad))))


def test_no_beat_or_miss_anywhere():
    tldr = swap(TLDR, "revenue +2.6%", "revenue beat by 2.6%")
    assert any("verdict wording" in p for p in problems(output(body(tldr=tldr))))


def test_an_outlook_change_is_one_of_the_fixed_words():
    bad = swap(OUTLOOK, "| Raised |", "| Boosted |")
    assert any("Change 'Boosted'" in p for p in problems(output(body(outlook=bad))))


def test_an_outlook_row_needs_a_figure():
    bad = swap(OUTLOOK, "USD 900–950 million", "expects higher spending")
    assert any("has no figure" in p for p in problems(output(body(outlook=bad))))


def test_no_outlook_is_one_none_given_row():
    none = OUTLOOK[:3] + [
        "| None given | — | The company published no outlook with these results | — | — |", ""]
    tldr = swap(TLDR, "1 raised · 0 lowered · 1 new", "none given")
    assert problems(output(body(outlook=none, tldr=tldr))) == []


def test_the_outlook_counts_on_the_tldr_match_the_table():
    tldr = swap(TLDR, "1 raised", "2 raised")
    assert any("says 2 raised" in p for p in problems(output(body(tldr=tldr))))


def test_management_said_is_paraphrased_attributed_and_short():
    quoted = swap(SAID, "Says services subscriptions", 'Says "services subscriptions')
    assert any("quotes" in p for p in problems(output(body(said=quoted))))
    long = swap(SAID, "passed 50 million in the quarter",
                "passed 50 million in the quarter and the company sees many more ways to grow "
                "the base across every region it sells in over time, and it plans to keep doing so next year")
    assert any("words" in p for p in problems(output(body(said=long))))
    price = swap(SAID, "Says services subscriptions passed 50 million in the quarter",
                 "Says the share price does not reflect the business")
    assert any("share price" in p for p in problems(output(body(said=price))))


def test_holdnote_gives_no_reason_for_the_price():
    bad = swap(PRICE, "results published 2026-10-22, after the close",
               "results published 2026-10-22, after the close; shares rose because of services")
    assert any("judgement or cause" in p for p in problems(output(body(price=bad))))


def test_the_price_move_rederives():
    bad = swap(PRICE, "| +4.50 |", "| +5.50 |")
    assert any("printed +5.50" in p for p in problems(output(body(price=bad))))


def test_a_tldr_figure_must_be_in_a_table():
    tldr = swap(TLDR, "diluted EPS 1.10", "diluted EPS 1.12")
    assert any("1.12" in p for p in problems(output(body(tldr=tldr))))


def test_latest_period_names_the_release_date():
    assert any("released" in p for p in problems(output(latest="Q3 FY2026")))


def test_method_lines_are_required():
    method = [m for m in METHOD if not m.startswith("Estimates rule:")]
    assert any("Estimates rule:" in p for p in problems(output(method=method)))


def test_outlook_and_management_said_print_only_in_a_recap():
    text = output().replace("Mode: Earnings recap", "Mode: Stock brief")
    assert any("outside an Earnings recap" in p
               for p in contract.earnings_tables_elsewhere(contract.split_sections(text)))


def test_the_render_keeps_every_table_and_reads_statements_as_a_list():
    out = render.render(output())
    for name in ("Results", "Segments", "Against estimates", "Company outlook",
                 "Management said", "Share price around the release"):
        assert f"### {name}" in out
    assert "- **Services** — Says services subscriptions" in out
    assert "Earnings recap" in out
    assert "> **Results** revenue 1,200" in out


def test_the_spec_and_routing_name_the_mode():
    skill = (REPO / "SKILL.md").read_text(encoding="utf-8")
    rules = (REPO / "RULES.md").read_text(encoding="utf-8")
    assert "references/earnings-recap.md" in skill
    assert "`Mode: Earnings recap`" in skill
    assert "Mode: Earnings recap" in rules


# -- regressions from the 2026-10-25 review ---------------------------------


def test_an_estimate_source_names_a_provider_not_just_an_outlet():
    bad = swap(ESTIMATES, "LSEG via Reuters, 2026-10-21 | +2.6%", "Reuters, 2026-10-21 | +2.6%")
    assert any("does not name its provider" in p for p in problems(output(body(estimates=bad))))
    own = swap(ESTIMATES, "LSEG via Reuters, 2026-10-21 | +2.6%", "Zacks, 2026-10-21 | +2.6%")
    assert not any("provider" in p for p in problems(output(body(estimates=own))))


def test_missing_is_not_a_verdict():
    text = output().replace("Not available:    none",
                            "Not available:    capex row missing from the release")
    assert not any("verdict" in p for p in problems(text))


def test_a_short_row_is_a_problem_not_a_crash():
    short = ESTIMATES[:3] + ["| Revenue (USD millions) | 1,200 | 1,170 |", ""]
    found = contract.output_problems(output(body(estimates=short)))
    assert found and not any("could not read" in p for p in found)


def test_an_unchanged_figure_may_print_an_unsigned_zero():
    flat = swap(RESULTS, "| Diluted EPS (USD) | 1.10 | 1.00 | +10.0% |",
                "| Diluted EPS (USD) | 1.10 | 1.10 | 0.0% |")
    assert not any("Diluted EPS" in p for p in problems(output(body(results=flat))))


def test_a_change_beside_a_missing_value_is_refused():
    bad = swap(RESULTS, "| Gross margin | 60.0% | 58.0% | +2.0pp |",
               "| Gross margin | Not available — not reported | 58.0% | +2.0pp |")
    assert any("not a figure" in p for p in problems(output(body(results=bad))))


def test_the_price_sessions_straddle_the_release():
    bad = swap(PRICE, "2026-10-22 to 2026-10-23", "2026-10-15 to 2026-10-16")
    assert any("straddle" in p for p in problems(output(body(price=bad))))


def test_a_tldr_figure_is_not_found_in_a_date():
    # 23 is printed only inside the session date 2026-10-23
    tldr = swap(TLDR, "diluted EPS 1.10", "diluted EPS 23")
    assert any("figure 23 " in p for p in problems(output(body(tldr=tldr))))


def test_a_buyback_in_management_said_is_not_advice():
    said = swap(SAID, "States a new USD 500 million share repurchase authorisation",
                "States it will buy back up to USD 500 million of shares")
    assert not any("banned" in p for p in contract.output_problems(output(body(said=said))))
