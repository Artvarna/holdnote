# Brief layout

Reference for Holdnote (`holdnote`). Follow `RULES.md`. Read for every stock or fund brief (`Mode: Stock brief`, `Mode: Fund brief (Mode A)`), full or quick, and for anything that prints one (a checklist, a head-to-head).

## Report layout — stock and fund briefs

A stock brief (`Mode: Stock brief`) and a fund brief
(`Mode: Fund brief (Mode A)`) print `RESULT` in this fixed order. Every
other mode keeps the tables its own reference specifies; where a brief
combines with another mode, the brief's layout prints first.

```
RESULT
Mode: Stock brief
TL;DR              three lines at most, facts only, no table
Buffett scorecard  always, first table
<Name> lens        one table per extra lens asked for, in the order asked
Key numbers        one compact table
What changed       against the last logged run of the same instrument
Red flags          filing risks new since the prior filing + thesis checks
Buffett notes      only when a trigger fires (references/buffett.md)
<detail tables>    only when asked for
```

**TL;DR.** Up to three lines between the Mode line and the first table,
in this order, each starting with its label:

```
Scorecard: 4 of 6 met · 1 not met · 1 not available
Changed:   diluted EPS 6.08 → 6.75 (+11.0%) since 2026-09-27
Red flags: 2 new filing risks · thesis criteria 0 of 3 reached
```

`Changed:` prints `nothing since <date>` when nothing moved (rule 10) and
`no earlier run logged` when there is no run to compare. Every figure on
these lines is printed again in a table below; a TL;DR line never carries a
number the tables do not, and never an adjective of judgement. It is a
restatement, which is what keeps it inside rule 6.

**Buffett scorecard.** Always printed, always first; a request for other
lenses adds to it and never replaces it. Columns:

| Check | Metric | Value | Threshold | Result |

`Result` is `Met`, `Not met` or `Not available` — arithmetic against the
threshold, never a verdict on the instrument. Checks, metrics and
thresholds come from `references/buffett-scorecard.md`: the stock version
for a company, the fund version for an ETF. The thresholds are the user's
stated tests, printed in the table so a reader sees exactly what was
measured against what.

**Extra lenses.** "Buffett + Graham + Lynch" adds a `Graham lens` and a
`Lynch lens` table, same columns, in the order asked, from
`references/lenses.md`. A lens that file does not define is named in
`CONTEXT` → `Not available`, never improvised.

**Key numbers.** One table carrying the figures a reader needs beside the
scorecard. For a stock: revenue, gross margin, operating margin, net
margin, free cash flow, FCF margin, ROIC, net debt, diluted EPS and the
valuation multiple with its price date, each with the value five years
earlier where the filings provide it, then revenue's five-year CAGR, which
has one value only. Definitions are `references/stock-brief.md` → Margins,
Returns and Growth. For a fund: the
Fund facts rows from `references/etf-brief.md` → Mode A.

**What changed.** Against the most recent logged run of the same ISIN or
ticker in `log/` (`references/run-journal.md`), quoted from that run's
file, never reconstructed (rule 15). A logged quick brief carries only its
scorecard, so a metric it did not print is compared with the most recent
logged run that did. Columns:

| Metric | Last run (date) | Now | Change |

Nothing moved: one row, `No change since <date>`. No earlier run: one row,
`No earlier run logged`. No access to `log/`: one row, `Not available —
<reason>`. The table is never dropped.

**Red flags.** Two kinds of row, both sourced, neither invented, neither
ranked:

| Type | Item | Source | Status |

- `Filing risk` — risk factors added or removed in the latest filing
  against the one before it, in the filing's own order and wording (rule
  6). For a fund: changes to the KID's risk section or its risk indicator.
  Status: `New`, `Removed` or `Reworded`; `Not checkable` with the reason
  when the earlier filing or KID could not be fetched. Compare the filing's
  risk factor summary where it has one (else its risk factor headings), and
  match each factor to last year's by words in common: two lines sharing
  60% or more of their words are one factor `Reworded`, printed in this
  year's words, never a `New` and a `Removed`. Only `New` and `Removed`
  count as changes on the TL;DR's `Red flags:` line.
- `Thesis` — each "what would prove me wrong" criterion from the
  instrument's thesis (`references/thesis-journal.md`), quoted verbatim,
  with the current sourced figure that bears on it. Status: `Reached`,
  `Not reached` or `Not checkable`.

A filing with nothing added or removed gets one `Filing risk` row with
status `None`; an instrument with no thesis on file gets one `Thesis` row
with status `None on file`, so an empty side is a statement, not a gap.
Holdnote never writes failure scenarios of its own: a red flag is
something a filing states or a criterion the user wrote.

**Detail tables.** The module's other tables — for a stock, Business,
Segments, Geography, Financials, Margins, Expense ratios, Returns, Growth,
Balance sheet, Valuation, Peers, Capital return and Risks stated; for a fund, Top 10, Sectors and Countries — are
still built on every run, because the scorecard and Key numbers draw on
them. They print after `Red flags` only when asked for: "full detail",
"show everything", a question about one of them ("what are Apple's
segments?" prints Segments, "what are its margins?" prints Margins and
Expense ratios), or the profile's `Report length` set to `full`. `METHOD` names the ones held back on a
`Detail tables:` line.

`scripts/check_output.py` holds a brief to this order.

## Quick brief

"Quick brief on NVDA" — or any brief when the profile's `Report length` is
`quick` — prints the TL;DR's `Scorecard:` line and the Buffett scorecard,
plus a lens table only when the request names one. Nothing else: no Key
numbers, What changed, Red flags, Buffett notes or detail tables. The Mode
line says so: `Mode: Stock brief (quick)` or `Mode: Fund brief (Mode A,
quick)`.

**It fetches only what the scorecard needs**, which is what makes it quick
and light on the user's plan limits. `references/stock-brief.md` → Quick
brief and `references/etf-brief.md` → Mode A → Quick brief list those
documents; a document not on the list is not opened. The run journal is not
read, because What changed is not printed.

The scorecard itself is unchanged: the same checks, thresholds, sources and
`Not available` rules as a full brief, so a quick `Met` is the same `Met`.

`METHOD` carries one line naming what was skipped, and its `Next:` line
offers the rest:

```
Quick brief:       Key numbers, What changed, Red flags and detail tables not built
Next:              say "full brief on NVDA" for the rest
```

"Full brief", "full report" or "everything" in the request overrides a
`quick` profile setting. A checklist ("should I buy X") always runs the full
brief, because its tables need Key numbers and Red flags.
