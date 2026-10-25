# Earnings Recap

Reference for Holdnote (`holdnote`). Follow `RULES.md`.

"How did GOOGL's earnings go?" "Recap Netflix's Q3." "What did Intel
report?" One company's latest quarterly results, read from the company's own
release and filing: what it reported against the quarter before and the same
quarter a year earlier, what the estimates were and who published them, what
the company said about the next period, what management said, and where the
share price closed either side of the release.

It is a recap, not a verdict. No "beat", no "miss", no "strong quarter":
every comparison is a signed number with its two sides printed beside it,
and every forward-looking line is the company's or a named source's, never
Holdnote's (`RULES.md` rules 6 and 8).

The figures in the examples below are illustrative, not any company's
results; a run prints only what it fetched (rule 1).

## Trigger

A request about a company's **reported** quarter: "how did X's earnings
go", "X earnings recap", "X Q3 results", "what did X report", "did X beat
estimates", "recap X's call".

- **One company per output.** "Recap Apple and Microsoft" is two outputs,
  each checked on its own.
- **A stock only.** A fund has no earnings: one line of prose says so and
  offers a fund brief. An index's earnings season is out of scope.
- **The quarter** is the most recent one the company has reported, unless
  the request names one ("Q2", "last quarter", "fiscal Q3 2026"). A named
  quarter the company has not reported yet is not guessed at: the latest
  reported quarter runs, `CONTEXT` → `Not available` names the asked-for
  one with the company-announced date if there is one (`Q3 FY2026 — not
  reported yet; company-announced date 2026-10-29`), and nothing is
  estimated in its place.
- **Fiscal, not calendar.** Quarters are named as the company names them
  (`Q4 FY2026` for Apple's quarter ending September). Where the fiscal year
  is off-calendar, `Latest period` says so.
- **Not here:** "why did X fall after earnings" is a Price move
  (`references/price-move.md`), which is the only mode that prints reported
  reasons for a price; this mode's `Next:` line offers it. "Brief on X" is a
  stock brief, which reads annual filings. A recap never opens
  `portfolio.md`, `holdings.csv` or `pies.md`.

## Where the data comes from

In this order (rule 4):

1. **The results release** — the company's own press release for the
   quarter: on its investor relations page, and for a US filer as Exhibit
   99.1 to the 8-K (Item 2.02) on SEC EDGAR. It carries the income
   statement, usually the balance sheet and cash flow, segment revenue and
   any outlook. **This is the document every Results figure comes from.**
2. **The quarterly filing** — the 10-Q (or 10-K for a fourth quarter, or a
   European issuer's interim report) for any line the release does not
   carry, most often the cash flow statement.
3. **The company's other quarterly material** — CFO commentary, a
   shareholder letter, prepared remarks, the investor presentation, and a
   transcript of the call the company publishes itself.
4. **The same release of the prior quarter and of the year-ago quarter**
   — for the Prior quarter and Year-ago columns, and for the previous
   outlook. A figure the company restated since is taken from the newest
   release that states it, and `METHOD` names the restatement.
5. **Financial media**, for two things only: the consensus estimate (rule
   8: third-party data, its source named and dated) and, where the company
   publishes no transcript, a named outlet's transcript of the call.

**How to reach them.** EDGAR is browser-only (`references/stock-brief.md`
→ Step 1): open a tab on `sec.gov`, read `submissions/CIK##########.json`
for the newest 8-K with Item 2.02, and open its Exhibit 99.1. An investor
relations page usually opens with WebFetch or the browser; a PDF release is
read as text in the browser. WebFetch summarises what it reads, so a figure
it returns is a lead to check against the document's own table, never a
value to print (stock-brief Step 1). Without the browser and with no IR
page that opens, the Results table is `Not available (browser route down)`
and the rest of the output still runs.

**Estimates.** WebSearch, at most three queries, built from the company
name, the quarter and the word "estimates". A number counts only when the
article opened with WebFetch states it **and names whose it is** — "LSEG
data", "FactSet consensus", "Zacks", "analysts polled by Visible Alpha". An
article that says "analysts expected" with no provider is a lead, not a
source. The article must be published before the release or on its day;
an estimate revised after the release is not an estimate of it. The
sources that count are price-move.md's (wires, major financial media,
bylined financial news), and its exclusions apply: no price-target pages,
no advice-framed pieces, no unsigned aggregators.

**Like with like.** Consensus EPS is usually the company's adjusted
(non-GAAP) EPS. The row compares the company's figure on the **basis the
estimate source states**: an adjusted EPS estimate sits beside the
company's adjusted EPS, labelled `(non-GAAP, company-adjusted)`, never
beside GAAP diluted EPS. A source that does not state the basis leaves the
row `Not available — estimate basis not stated`.

## What it reports

Six tables, in this order, every one printed on every run. A table with
nothing to report prints its one `None` row, so an empty side is a
statement (rule 10).

### 1. Results

```
Results (Q3 FY2026 vs Q2 FY2026 and Q3 FY2025, reported, USD millions except per share)
| Metric | This quarter | Prior quarter | QoQ | Year-ago quarter | YoY |
|---|---|---|---|---|---|
| Revenue | 102,346 | 96,428 | +6.1% | 88,268 | +15.9% |
| Gross margin | 59.6% | 59.0% | +0.6pp | 57.4% | +2.2pp |
| Operating income | 31,228 | 28,104 | +11.1% | 28,521 | +9.5% |
| Operating margin | 30.5% | 29.1% | +1.4pp | 32.3% | -1.8pp |
| Net income | 26,301 | 23,212 | +13.3% | 26,301 | +0.0% |
| Diluted EPS (USD) | 2.15 | 1.89 | +13.8% | 2.12 | +1.4% |
| Operating cash flow | 30,115 | 27,700 | +8.7% | 30,698 | -1.9% |
| Free cash flow | 18,000 | 17,100 | +5.3% | 17,600 | +2.3% |
```

- **The eight rows above, always, in that order.** A company that reports
  no gross profit (a bank, an insurer) prints `Not available — not
  reported by the company` in that row, never a reconstruction.
- **Reported figures** (GAAP or IFRS, rule 3). Where the release presents
  adjusted figures, a row may follow the eight, named `<metric> (non-GAAP,
  company-adjusted)`, with the company's own reconciliation in `SOURCES`.
  An adjusted figure never replaces a reported one.
- **Changes.** `QoQ` and `YoY` are signed: a percentage change of an amount
  (`+6.1%`), or the difference of two margins in percentage points
  (`+0.6pp`). A change from a negative base is `—`, because a percentage of
  a loss reads backwards; the two values beside it still print.
- **Margins** are Holdnote's arithmetic on the release's own lines: gross
  profit ÷ revenue, operating income ÷ revenue (stock-brief → Margins), so
  every quarter means the same thing.
- **Free cash flow** is operating cash flow minus purchases of property and
  equipment, the definition stock-brief uses. Where the company's own
  free-cash-flow figure differs, it is a `(non-GAAP, company-adjusted)` row.
- **Quarterly cash flow from year-to-date statements.** A 10-Q's cash flow
  statement is year-to-date. The quarter is this year-to-date minus the
  previous quarter's, and `METHOD`'s `Cash flow basis:` line says so. A
  release that prints the quarter's own cash flow is used as printed.
- **Units** in the heading, once; per-share rows carry their currency in
  the Metric cell.

### 2. Segments

The company's own reportable segments, as the release names and orders
them, this quarter against the year-ago quarter:

```
Segments (Q3 FY2026 vs Q3 FY2025, revenue, USD millions)
| Segment | This quarter | Year-ago quarter | YoY |
|---|---|---|---|
| Google Services | 87,052 | 76,510 | +13.8% |
| Google Cloud | 15,157 | 11,353 | +33.5% |
| Other Bets | 344 | 388 | -11.3% |
```

- Revenue by segment; operating income by segment as a second block of rows
  `<segment> operating income` where the release reports it.
- A company with one reportable segment: one row, `| None — one reportable
  segment | — | — | — |`.
- Segments the company re-drew since the year-ago quarter take the recast
  year-ago figures the release prints; with none, the Year-ago cell is
  `Not available — segments re-drawn`.

### 3. Against estimates

The one table that holds someone else's expectation, and the heading says
whose:

```
Against estimates (as published by the named sources before the release — not Holdnote's)
| Metric | Reported | Estimate | Estimate source | Difference |
|---|---|---|---|---|
| Revenue (USD millions) | 102,346 | 99,890 | LSEG via Reuters, 2026-10-28 | +2.5% |
| EPS (non-GAAP, company-adjusted, USD) | 2.15 | 2.00 | LSEG via Reuters, 2026-10-28 | +7.5% |
```

- **Difference** = (Reported − Estimate) ÷ |Estimate| × 100, signed, to one
  decimal. That is the whole judgement this table makes: no `beat`, `miss`,
  `topped`, `fell short`, `surprise` or icon anywhere in the output.
- **Estimate source** names the provider and the outlet the number was read
  in, and the article's publication date: `FactSet via CNBC, 2026-10-27`.
  The article is a `SOURCES` row with its URL and both dates.
- **Revenue and EPS**, on the basis the source states. Other estimates (a
  segment's revenue, a margin) may follow when the same article states
  them, at most four rows in all.
- **Sources disagree:** both rows print, each with its source. Holdnote
  does not pick a consensus.
- **Nothing found:** one row, `| — | — | — | None found — no named source
  published an estimate before the release | — |`. That is a complete
  answer, not a failed search.

### 4. Company outlook

What the company itself published about a future period, beside what it
said a quarter earlier. Rule 8 lets a third party's projection be reported
as theirs; the company's own guidance is reported the same way, and the
heading says so:

```
Company outlook (as stated by the company — not Holdnote's forecast)
| Item | Period | Outlook as stated | Previous outlook | Change |
|---|---|---|---|---|
| Revenue | Q4 FY2026 | USD 54.0–56.0 billion | — | New |
| Capital expenditure | FY2026 | USD 91–93 billion | USD 85 billion | Raised |
| Gross margin | Q4 FY2026 | 47.0% ± 0.5pp | — | New |
```

- **Outlook as stated** is the company's figure or range, in its units,
  copied, never re-based, annualised, mid-pointed or extended to another
  period. Words with no figure ("expects continued growth") are not an
  outlook row; they may be a Management said row.
- **Previous outlook** is the same item for the same period from the
  previous quarter's release, quoted from that release; `—` when there was
  none.
- **Change** is one of `Raised`, `Lowered`, `Unchanged`, `New`, `Withdrawn`
  or `Not comparable` (a range that moved at one end only, a basis that
  changed). Raised and Lowered compare the midpoints of the two ranges, as
  arithmetic, and `METHOD` says so.
- **None given:** one row, `| None given | — | The company published no
  outlook with these results | — | — |`. Many large companies give none;
  that is what the release says, not a gap.

### 5. Management said

What the company's people said about the quarter, in Holdnote's words, as
stated — not Holdnote's reading of it:

```
Management said (as stated by the company — not Holdnote's view)
| Topic | Speaker | Said | Source |
|---|---|---|---|
| Cloud | CEO | Says cloud backlog grew to USD 155 billion at quarter end | Q3 earnings call (company transcript) |
| Capital return | Company release | States a new USD 70 billion share repurchase authorisation | Q3 results release |
```

- **At most five rows**, in the order they appear in the source: the
  release first, then the call. Never ranked by importance, never picked to
  make the quarter read well or badly.
- **Said** is a paraphrase under 30 words starting `Says` (a person) or
  `States` (the release). No quotation marks and no copied sentences.
- **Topic** is a neutral label for what the statement is about, using the
  company's own words for its products and segments; never a judgement
  (`Cloud`, not `Cloud strength`).
- **Speaker** is the role (`CEO`, `CFO`) or `Company release`.
- **Source** names the document; it is a `SOURCES` row. A transcript the
  company does not publish is credited to the outlet that does (`Q3
  earnings call (Motley Fool transcript)`).
- **Nothing about the share price.** A statement about the stock, its
  valuation or buybacks "at these prices" is left out: the price is the
  next table, and a reason for it is a Price move.
- **Nothing found:** one row, `| — | — | None found — no statement read |
  — |`, with the documents tried on `METHOD`'s `Statements read:` line.

### 6. Share price around the release

The move, without a reason (rule 7, first paragraph):

```
Share price around the release (results published 2026-10-28, after the close)
| Instrument | Close before release | First close after | Change % | Sessions |
|---|---|---|---|---|
| Alphabet Inc. Class A (GOOGL, Nasdaq, USD) | 251.20 | 263.60 | +4.94 | 2026-10-28 to 2026-10-29 |
| Benchmark: S&P 500 (price, USD) | 6801.10 | 6790.40 | -0.16 | 2026-10-28 to 2026-10-29 |
```

- **Close before release** is the last close before the release went out;
  **First close after** is the first close after it. A release before the
  open makes the previous session's close the first column and that day's
  close the second; the heading says `before the open` or `after the
  close`, from the release's own timestamp.
- Benchmark rows follow price-move.md → Move: the fixed benchmark for the
  listing, never chosen per run, never a gap printed between the rows.
- Closes come from the routes price-move.md uses, with its fallback for a
  US stock without the browser. A close that cannot be fetched is `Not
  available` with the reason; a release in the last few hours whose first
  close after has not happened yet is `Not available — no close since the
  release`.
- **No reason, anywhere.** "Shares rose on cloud growth" is the story rule
  7 forbids. This mode has no Reported reasons table; its `Next:` line
  offers a Price move for the reasons named outlets reported.

## Output

The sections of `RULES.md` Part IV, with a subject line above `STATUS`:

```
=== GOOGL — Alphabet Inc. · earnings recap Q3 2026 ===
```

`CONTEXT`, with this mode's placements:

```
Data as of:       the run's retrieval date
Latest period:    Q3 FY2026 (quarter ended 2026-09-30), released
                  2026-10-28 — off-calendar fiscal years named here
Currency / units: reporting currency; amounts in millions except per
                  share; changes in % or pp as marked
Not available:    rows and cells not fetched, with the reason
Coverage:         Results n of 8 rows · Estimates from n of m articles read ·
                  Outlook n items · Statements from n documents
```

`RESULT` opens with `Mode: Earnings recap`, then a TL;DR of up to three
lines, then the six tables, nothing between them.

**TL;DR.** Up to three labelled lines, in this order, each restating
figures printed in the tables below and adding none (`RULES.md` Part IV):

```
Results:   revenue 102,346 (YoY +15.9%) · diluted EPS 2.15 (YoY +1.4%)
Estimates: revenue +2.5% · EPS (non-GAAP) +7.5% against LSEG via Reuters
Outlook:   1 raised · 0 lowered · 2 new
```

`Estimates:` prints `none found` and `Outlook:` prints `none given` when
their tables say so. No adjective, no `beat`, no verdict.

`METHOD`, on every run:

```
Build:             [text of BUILD]
Quarter:           the latest reported | the quarter asked for; fiscal year
                   end [month]
Basis:             reported (GAAP | IFRS); adjusted rows marked and
                   reconciled in the release
Margins:           gross profit ÷ revenue, operating income ÷ revenue
Cash flow basis:   as printed for the quarter | year-to-date less prior
                   year-to-date, 10-Q
Estimates rule:    third-party, named provider and outlet, published before
                   the release (RULES.md rule 8); compared on the basis
                   the source states; Difference = (reported − estimate) ÷
                   |estimate|
Outlook rule:      the company's own figures, as stated (RULES.md rule 8);
                   Raised/Lowered by range midpoint
Statements read:   the documents read for Management said, and how many
                   statements were left out as about the share price
Price window:      the release timestamp and the two sessions used
Restatements:      prior figures the company restated, or none
Confirmation:      all rows checked | single source: [rows]
Conflict:          one line per conflict, or none
Fallbacks:         any fallback used and why, or none
Columns suppressed: [named, or none]
Next:              say "why did GOOGL move after earnings" for the reasons
                   named outlets reported
```

`PROOF`, when asked for: each change re-derived from its two values; each
margin from its two lines; each Difference from its reported figure and
estimate; each quarterly cash flow subtraction with its addends; each
Change in the outlook with the two midpoints; each close with its date and
source.

## Self-check

`RULES.md` Part IV checklist, plus:

- [ ] One company, one quarter, named as the company names it; the
      user's holdings files not opened
- [ ] Tables in order: Results, Segments, Against estimates, Company
      outlook, Management said, Share price around the release — all six
- [ ] Results carries the eight rows in order; adjusted rows only after
      them, marked `(non-GAAP, company-adjusted)`
- [ ] Every QoQ and YoY re-derives from its two values; margins in pp
- [ ] Every estimate names its provider, its outlet and its date, was
      published before the release, and is compared on its own basis
- [ ] No `beat`, `miss`, `topped`, `fell short`, `surprise`, `strong`,
      `weak` or `disappointing` anywhere in the output
- [ ] Every outlook row is the company's own figure, with its period and
      the previous outlook beside it; nothing Holdnote projected
- [ ] Every Management said row starts `Says` or `States`, is under 30
      words, is not a quotation, and says nothing about the share price
- [ ] Share price around the release carries the move and no reason; its
      sessions are the last close before and the first close after
- [ ] No causal wording of Holdnote's own outside Management said and
      Company outlook; no Reported reasons table
- [ ] TL;DR: at most three lines, labelled, every figure printed again in a
      table below

## Frequency

On request only. Never scheduled for every holding's results, and never
offered after a release the user did not ask about.
