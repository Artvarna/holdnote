# Head-to-head

Reference for Holdnote (`holdnote`). Follow `RULES.md`.

"VWCE vs IWDA." "Compare AAPL and MSFT." "SPYL or CSPX?" Two funds, or two
stocks, in one output: the same Buffett scorecard run on both, their facts
side by side with the arithmetic difference between them, and — for funds —
how much of one is the other.

**It never names a winner** (`RULES.md` rule 6). No `better`, no `best`, no
`cheaper` as a verdict, no column that says which one, no bold or icon on
the side that "wins" a row, and no ordering by which looks better. The two
instruments print in the order the user named them, every row prints for
both, and the difference is a signed number. Which side of it matters is
the user's call.

The figures in the examples below are illustrative, not any fund's or
company's documents; a run prints only what it fetched (rule 1).

## Trigger

Two named instruments and a comparing word: "X vs Y", "X or Y", "compare X
and Y", "X compared to Y", "difference between X and Y", "how does X stack
up against Y".

- **Exactly two, of the same kind.** Two funds (ETFs, index funds) or two
  stocks. Three or more funds are Mode C's Comparison and Overlap tables
  (`references/etf-brief.md` → Mode C), which this mode's `Next:` line
  offers; three or more stocks get one head-to-head per pair the user
  names, never a ranking of the set.
- **A stock and a fund** are not compared side by side: their scorecards
  measure different things. One line of prose says so and offers the two
  quick briefs, or — when the question is how much of the stock the fund
  holds — Mode C's Holdings table.
- **Two share classes of one fund** (VWCE and VWRL, Acc and Dist) are a
  head-to-head like any other; their Overlap is `100`, which the run prints
  rather than skips, and the Side by side shows what differs.
- **"Compare X to what I own"** is a fund brief plus Mode C, as SKILL.md
  routes it, not this mode.
- **The possessive changes nothing.** "My VWCE vs IWDA" compares the two
  funds. This mode never opens `portfolio.md`, `holdings.csv` or
  `pies.md`; no position size, weight or amount of the user's prints.
- **"Which is better?"** gets the comparison, with the question's verdict
  left to the user: `METHOD`'s `Order:` line says the instruments are in
  the order named and no row is scored for either.

## What it reads

Each instrument is resolved and fetched exactly as its quick brief is —
`references/stock-brief.md` → Quick brief or `references/etf-brief.md` →
Mode A → Quick brief — plus the few documents this mode's extra rows need.
The two sides are held to one footing:

- **Same date.** Every price-dependent figure (a multiple, a yield, the
  margin-of-safety check) uses closes from the **same session** for both
  instruments, named once on `Latest period`. A fund fact is each fund's
  newest factsheet; when the two factsheets' as-of dates differ, both dates
  print on `Latest period` and `METHOD` names the gap.
- **Same definitions.** Every row is computed by one definition for both
  sides — the scorecard's, stock-brief's Margins, Returns and Valuation,
  etf-brief's Fund facts. A company's own "adjusted" figure never stands in
  for one side's row.
- **Currencies are labelled, never mixed.** Each column carries its own
  currency; an amount row is not differenced across two currencies
  (Difference `—`). A ratio row (a margin, a TER, a yield) is unitless and
  is differenced whatever the currencies.

## What it reports

Funds: five tables, in this order — Buffett scorecard, Side by side,
Overlap, Shared holdings, Countries and sectors. Stocks: two — Buffett
scorecard, Side by side. Every table prints on every run of its kind; a
table that cannot be built prints its `Not available` row with the reason.

### 1. Buffett scorecard

The scorecard of `references/buffett-scorecard.md` — the fund version for
funds, the stock version for stocks — run on both, one row per check:

```
Buffett scorecard
| Check | Threshold | VWCE | IWDA |
|---|---|---|---|
| Low cost | 0.20% or less | Not met (0.22%) | Met (0.20%) |
| Broad | 500 or more | Met (3,712) | Met (1,395) |
| Not concentrated | 40% or less | Met (21.4%) | Met (25.9%) |
| Tracks its index | No worse than −(TER + 0.10pp) | Met (−0.18pp) | Met (−0.12pp) |
| Built to last | 5+ years and EUR 500m+ | Met (2019, EUR 32.1bn) | Met (2009, EUR 98.4bn) |
| Quality underneath | 15% or more | Met (16.2%) | Met (16.9%) |
```

- Each instrument cell is its result — `Met`, `Not met` or `Not
  available` — then its value in brackets; `Not available — <reason>` where
  the value could not be fetched. Nothing else.
- Checks, metrics and thresholds are the scorecard file's, unchanged. The
  threshold prints once because it is the same test for both.
- No total row and no count of who met more: the TL;DR's `Scorecard:` line
  states each side's tally, side by side, and that is a restatement, not a
  score.

### 2. Side by side

Every fact a reader checks first, both sides, and the difference:

```
Side by side (Difference = IWDA − VWCE)
| Fact | VWCE | IWDA | Difference |
|---|---|---|---|
| Index tracked | FTSE All-World (net) | MSCI World (net) | — |
| TER | 0.22% | 0.20% | -0.02pp |
| Holdings | 3,712 | 1,395 | -2,317 |
| Top-10 weight | 21.4% | 25.9% | +4.5pp |
| Replication | Physical, sampled | Physical, sampled | — |
| Distribution | Accumulating | Accumulating | — |
| Domicile | Ireland | Ireland | — |
| Base currency | USD | USD | — |
| Fund size | USD 34,800m (2026-09-30) | USD 107,200m (2026-09-30) | +72,400m |
| Inception | 2019-07-23 | 2009-09-25 | — |
| Risk indicator | 4/7 | 4/7 | 0 |
| Tracking difference, 2025 | −0.18pp | −0.12pp | +0.06pp |
```

- **Difference is the second instrument minus the first**, in the order
  named, and the heading says so. A percentage row differences in `pp`, a
  count or an amount in its own units, and a text, date or mixed-currency
  row prints `—`. It is arithmetic: a `+` is not good and a `-` is not bad.
- **Fund rows**, in this order, from etf-brief → Mode A → Fields and Fund
  facts: Index tracked, TER, Holdings, Top-10 weight, Replication,
  Distribution, Domicile, Base currency, Fund size, Inception, Risk
  indicator, Tracking difference (last full calendar year).
- **Stock rows**, in this order, from stock-brief → Key numbers, Margins,
  Returns, Growth and Valuation, latest fiscal year unless marked: Revenue,
  Revenue 5-year CAGR, Gross margin, Operating margin, Net margin, FCF
  margin, ROIC, ROE, Net debt, Diluted EPS 5-year CAGR, Shares outstanding
  5-year change, P/E, EV/EBITDA, FCF yield, Dividend yield. Two companies
  with different fiscal year ends compare their own latest fiscal years,
  and the row's Fact cell says which (`Revenue (FY to Sep 2026 · FY to Jun
  2026)`).
- **Returns are not in this table.** Past performance of two funds is a
  question of its own and gets Mode C's period-return rows on request
  ("VWCE vs IWDA performance this year"), both closes in each fund's own
  listing currency.

### 3. Overlap (funds only)

How much of the two funds is the same companies, by the shared-weight
definition of etf-brief → Mode C → Overlap analysis:

```
Overlap (full holdings files, as of 2026-10-23 and 2026-10-24)
| Measure | Value |
|---|---|
| Shared weight % | 74.8 |
| Shared companies | 1,342 |
| VWCE companies not in IWDA | 2,370 |
| IWDA companies not in VWCE | 53 |
| Structural | MSCI World's 23 countries are all in FTSE All-World's 49 |
```

- **Shared weight** is one figure for the pair: the sum, over the companies
  both hold, of the smaller of the two weights. Never one figure per fund.
- **Depth** goes in the heading: `full holdings files` (from the
  `holdings-data` branch or the issuer's file) or `top-10 depth, partial`
  when either fund was read from its factsheet top 10 only (etf-brief →
  Which weights are admissible). At top-10 depth the counts are `Not
  available — top-10 depth` and only Shared weight prints, as a floor
  `METHOD` names.
- **Structural** is the index-level fact, by country lists, never labels
  (etf-brief → Overlap analysis → Across providers).
- Companies are matched by ISIN, never by name.

### 4. Shared holdings (funds only)

The ten companies both funds hold with the largest smaller-weight, so the
reader sees what the shared weight is made of:

```
Shared holdings (top 10 by the smaller weight)
| Company | VWCE % | IWDA % | Smaller % |
|---|---|---|---|
| NVIDIA | 4.91 | 5.62 | 4.91 |
| Microsoft | 4.30 | 4.94 | 4.30 |
| ... | | | |
```

- Sorted by `Smaller %`, largest first; ties by company name. Smaller % is
  `min(VWCE %, IWDA %)` and re-derives from the row.
- No overlap: one row, `| None — no company in both funds | — | — | — |`.

### 5. Countries and sectors (funds only)

```
Countries and sectors (Difference = IWDA − VWCE)
| Exposure | VWCE % | IWDA % | Difference pp |
|---|---|---|---|
| Country: United States | 62.1 | 71.3 | +9.2 |
| Country: Japan | 5.3 | 5.4 | +0.1 |
| Sector: Technology | 27.8 | 26.9 | -0.9 |
| ... | | | |
```

- The union of each fund's top five countries and top five sectors, as
  their factsheets or holdings files state them. A fund that does not
  report a row in the other's top five prints its own weight from its full
  list, or `Not available — not in its published top 5`.
- **Sector names are each issuer's own.** FTSE's ICB and MSCI's GICS sort
  companies differently: a sector row is printed only when both funds use
  the same classification; across classifications, the sector rows print
  `Not comparable — ICB vs GICS` and only countries are differenced.
  `METHOD` names the two classifications.

## Output

The sections of `RULES.md` Part IV, with a subject line above `STATUS`:

```
=== VWCE vs IWDA — Vanguard FTSE All-World (Acc) vs iShares Core MSCI World (Acc) · head-to-head ===
```

`CONTEXT`, with this mode's placements:

```
Data as of:       the run's retrieval date
Latest period:    factsheets as of [date] and [date]; closes of [session]
                  for every price-dependent row
Currency / units: each column in its instrument's own currency; weights
                  and ratios in %; differences in pp or units as marked
Not available:    rows and cells not fetched, per instrument, with the reason
Coverage:         VWCE n of m rows · IWDA n of m rows
```

`RESULT` opens with `Mode: Head-to-head`, then a TL;DR of up to two lines,
then the tables, nothing between them:

```
Scorecard: VWCE 5 of 6 met · IWDA 6 of 6 met
Overlap:   74.8% shared weight · 1,342 shared companies
```

Each line restates figures printed in the tables below and adds none. The
`Overlap:` line is for funds only. Neither line says which side is ahead.

`METHOD`, on every run:

```
Build:             [text of BUILD]
Instruments:       VWCE (IE00BK5BQT80, Xetra, EUR listing of a USD fund)
                   · IWDA (IE00B4L5Y983, LSE, USD) — resolved by ISIN
Order:             as named by the user; no row scored for either
Difference:        second − first; % rows in pp; amounts only within one
                   currency
Scorecard:         references/buffett-scorecard.md, fund | stock version,
                   same thresholds for both
Price date:        [session] for both | not used (no price-dependent row)
Overlap depth:     full holdings files | top-10 depth, partial — [which fund
                   and why] | not run (stocks)
Classification:    [GICS | ICB] for each fund's sectors
Confirmation:      all rows checked | single source: [rows]
Conflict:          one line per conflict, or none
Fallbacks:         any fallback used and why, or none
Columns suppressed: [named, or none]
Next:              say "full brief on VWCE" or "full brief on IWDA" for the
                   rest of either
```

`PROOF`, when asked for: every Difference re-derived from its two cells;
every scorecard value with its source line; the shared-weight sum with its
addends, or its top-ten head and the count of the rest; every Smaller %
from its two weights.

## Self-check

`RULES.md` Part IV checklist, plus:

- [ ] Exactly two instruments, of the same kind, resolved by ISIN or CIK,
      in the order the user named them; the user's holdings files not
      opened
- [ ] Tables in order — funds: Buffett scorecard, Side by side, Overlap,
      Shared holdings, Countries and sectors; stocks: Buffett scorecard,
      Side by side
- [ ] Every scorecard cell starts `Met`, `Not met` or `Not available`;
      thresholds are the scorecard file's
- [ ] Every Difference is the second minus the first, re-derivable from
      its row; `—` for text, dates and mixed currencies
- [ ] Price-dependent rows use one session for both instruments
- [ ] Shared weight is one figure, the sum of the smaller weights; Shared
      holdings sorted by Smaller %
- [ ] No winner: no `better`, `best`, `worse`, `winner`, `wins`, `cheaper`,
      `superior`, `stronger`, `weaker`, `edge`, `advantage`, `prefer` or
      `pick`; no bold, no icon and no total marking either side
- [ ] TL;DR: at most two lines, labelled `Scorecard:` and `Overlap:`, each
      figure printed again in a table below

## Frequency

On request only.
