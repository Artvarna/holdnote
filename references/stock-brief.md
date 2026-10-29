# Stock Brief

Reference for Holdnote (`holdnote`). Follow `RULES.md`.

Covers individual companies. Same discipline as the ETF brief: fetched
figures only, conflicts surfaced, no verdict at the end.

## Step 1 — Resolve the filing source

**US-listed** → SEC EDGAR. `data.sec.gov` serves standardized company facts as
JSON, free and unlimited; the filing index at `sec.gov/edgar` has the source
documents. This is the highest-quality source available and costs nothing.

**Read it in the built-in browser, never through WebFetch.** Both shells are
refused by `data.sec.gov`, and WebFetch summarises the JSON instead of
returning it: on 2026-10-01 it dropped the form types and offered a Form 4 as
the latest periodic report. Open a tab on `data.sec.gov` and `fetch()` the
`submissions/CIK##########.json` and `api/xbrl/companyfacts/…` files from it
(`references/etf-brief.md` → Stocks table, "EDGAR's full JSON files are browser-only"). A figure
WebFetch reports from those two large files is a lead to check against the
JSON, never a value to print.

**Without the browser** (a phone, the web): `references/no-browser.md` →
SEC EDGAR. The same figures come from smaller SEC documents WebFetch reads
whole — one XBRL concept per figure, the filing's own statement pages, the
cover-page shares concept for the filing list — and each figure prints only
when the concept and the statement page agree. The brief runs in full; it
is not `Not available (browser route down)`.

**European-listed** → the company's own investor relations page. Annual and
interim reports are published as PDFs. There is no clean API; fetch and read
the report.

**Anywhere else** → the local exchange filing portal, then the company's IR
page.

Resolve the entity by ISIN or the filer's CIK, not by name. Companies share
names, list in several places, and run subsidiaries that file separately.

If no filing is retrievable, the brief is `Not available`. Do not fall back
to a summary site, a broker page, or memory.

## Step 2 — Extract

### Identity
Legal name · ISIN · ticker(s) and exchange(s) · sector · fiscal year end ·
reporting standard (IFRS or US GAAP) · reporting currency

### What the business does
Plain language, two or three sentences, drawn from the filing's own business
description. Segments and their revenue split if disclosed. Geographic
revenue split if disclosed.

Describe the business as the company describes it. Do not characterize it as
a moat, a compounder, a turnaround, or any other framing the filing does not
use.

### Financials — five years where available

| Line | Notes |
|---|---|
| Revenue | |
| Gross profit | |
| Research and development | Where the income statement shows it |
| Selling, general and administrative | Where the income statement shows it |
| Operating income | |
| Interest expense | |
| Income before tax | |
| Income tax expense | |
| Net income | Reported, not adjusted |
| Diluted EPS | |
| Depreciation and amortization | From the cash flow statement |
| Stock-based compensation | From the cash flow statement |
| Operating cash flow | |
| Capital expenditure | |
| Free cash flow | State the definition used — it is not standardized |
| Shares outstanding, diluted | Dilution is invisible in per-share figures alone |

Label every figure: currency, units, fiscal or calendar year, reported or
adjusted. Where the company presents both reported and adjusted figures,
report the reported one and show the adjusted alongside, marked.

**Where each line comes from** in SEC company facts, by its standard
`us-gaap` tag — the first that the company reports, in this order:

| Line | Tags |
|---|---|
| Revenue | `Revenues`, `RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueNet` |
| Gross profit | `GrossProfit` — never revenue minus a cost line the filing does not total itself |
| Research and development | `ResearchAndDevelopmentExpense` |
| Selling, general and administrative | `SellingGeneralAndAdministrativeExpense` |
| Operating income | `OperatingIncomeLoss` |
| Interest expense | `InterestExpense`, `InterestExpenseNonoperating` |
| Income before tax | `IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest`, `IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments` |
| Income tax expense | `IncomeTaxExpenseBenefit` |
| Net income | `NetIncomeLoss` |
| Depreciation and amortization | `DepreciationDepletionAndAmortization`, `DepreciationAndAmortization` |
| Stock-based compensation | `ShareBasedCompensation` |
| Operating cash flow | `NetCashProvidedByUsedInOperatingActivities` |
| Capital expenditure | `PaymentsToAcquirePropertyPlantAndEquipment` |

A tag the company does not use is the extension-tag trap below: the line
is read from the filing's own statement, or is `Not available`. Which tag
filled each line goes in `PROOF`.

### Margins — five years

Each line of the income or cash flow statement as a share of revenue, per
fiscal year, from the Financials figures of the same year:

| Margin | Definition |
|---|---|
| Gross margin | gross profit ÷ revenue |
| Operating margin | operating income ÷ revenue |
| EBITDA margin | (operating income + depreciation and amortization) ÷ revenue |
| Pretax margin | income before tax ÷ revenue |
| Net margin | net income ÷ revenue |
| FCF margin | free cash flow ÷ revenue |

**EBITDA is Holdnote's, not the company's.** It is computed by the
definition above from reported lines, so every company's is the same sum;
a company-presented "adjusted EBITDA" is shown alongside only where the
filing presents one, marked adjusted, never in its place.

A company with no gross profit line (banks, insurers, most REITs) prints
Gross margin `Not available — no gross profit line in the income
statement`, the scorecard's rule. EBITDA is not meaningful for a bank's
income statement either and is `Not available` for one. The other margins
still print.

### Expense ratios — five years

Where revenue goes, per fiscal year:

| Ratio | Definition |
|---|---|
| R&D | research and development ÷ revenue |
| SG&A | selling, general and administrative ÷ revenue |
| Stock-based compensation | stock-based compensation ÷ revenue |
| Capex | capital expenditure ÷ revenue |
| Effective tax rate | income tax expense ÷ income before tax |

A company that does not break out R&D or SG&A prints that row
`Not available — not shown separately in the income statement`. An
effective tax rate on a pretax loss is `Not available — pretax loss`,
never a negative rate.

### Returns — five years

| Return | Definition |
|---|---|
| ROE | net income ÷ average shareholders' equity |
| ROIC | operating income × (1 − effective tax rate) ÷ (total debt + shareholders' equity − cash and equivalents) |
| ROA | net income ÷ average total assets |
| Asset turnover | revenue ÷ average total assets |
| Cash conversion | operating cash flow ÷ net income |

ROE and ROIC are the scorecard's definitions (`references/buffett-scorecard.md`
→ Capital efficiency), so the same year prints the same figure in both
places. Averages are the year's opening and closing balance sheets. ROE
with zero or negative equity at either end is `Not available — equity
negative in FY____`; ROIC with zero or negative invested capital likewise.
Cash conversion on a net loss is `Not available — net loss`.

### Growth — five years

Year-over-year change for revenue, operating income, diluted EPS, free
cash flow and diluted shares outstanding, plus the compound annual growth
rate across the window:

```
YoY % = (this year ÷ last year − 1) × 100
CAGR % = ((latest ÷ earliest) ^ (1 ÷ years) − 1) × 100
```

These are **history, not a forecast** (rule 8): every figure is between two
reported years. A change from or to a negative figure has no meaningful
percentage and prints `Not available — negative base`. The CAGR uses the
same years the columns print, and `years` is their count minus one.

### Balance sheet
Total debt · cash and equivalents · net debt · total equity · net debt to
EBITDA (EBITDA as defined under Margins) · current ratio (current assets ÷
current liabilities) · interest coverage (operating income ÷ interest
expense; `Not available — no interest expense reported` where there is
none) · maturity profile if stated

**Net debt** = total debt − cash and cash equivalents, from the same
balance sheet. Total debt is short-term debt plus the current portion of
long-term debt plus long-term debt; lease liabilities and marketable
securities are left out unless the filing's own net debt figure includes
them, which `METHOD` then says. A negative result prints as negative (net
cash), never as zero.

### Valuation
P/E, EV/EBITDA, EV/Sales, P/S, P/B, FCF yield, dividend yield — each with
the price date and the earnings period used. A multiple without both is
meaningless. EV = market capitalization + total debt − cash and
equivalents, from the same balance sheet. A P/E on negative earnings is
`Not available — net loss`, never a negative multiple. PEG belongs to the
Lynch lens, which defines its growth rate as historical
(`references/lenses.md`); no forecast growth rate is used anywhere (rule 8).

Peer comparison: name the peers and their source. Do not assemble a peer set
from memory; use the company's own stated competitors or an index
constituent list.

### Risks
Only what the filing's risk section states. Summarize, do not editorialize,
do not rank them by severity, and do not add risks the company does not name.

### Capital returns
Dividend per share and history · payout ratio (dividends paid ÷ net
income) · buyback authorization and actual repurchases · FCF returned
((dividends paid + repurchases) ÷ free cash flow) · share count trend

## Step 3 — Output

`RULES.md` Part IV sets the shape: `STATUS`, `CONTEXT`, `RESULT`, `METHOD`,
`PROOF`, `SOURCES`, in that order — `PROOF` only when asked for or on a
halt. The checks it would print run every time.

The subject line sits above `STATUS` and is not a field:

```
=== [TICKER] — [Legal name] · [ISIN] ===
```

```
STATUS: Complete.
```

```
CONTEXT
Data as of:       [date]
Latest period:    [FY2025, filed 2025-11-01] · FY ends [month] ·
                  [IFRS | US GAAP]
Currency / units: [e.g. USD millions] · reported, not adjusted
Sources used:     [form type and period — SOURCES carries filing dates]
Not available:    [fields not found]
Coverage:         [n of m fields populated]
```

`Sources used` is not a mandated field. This module prints it because it
fetches documents a reader cannot identify from the five values, as
`RULES.md` Part IV → CONTEXT allows.

Fiscal year end and reporting standard ride on `Latest period` because a
reader cannot compare a June year-end against a December one without them,
and cannot read a margin without knowing which standard produced it. They
are reader-critical, so they fold into a mandated line rather than adding a
sixth.

`RESULT` follows `SKILL.md` → Report layout: the Mode line
(`Mode: Stock brief`), the TL;DR, then `Buffett scorecard` (stock version,
`references/buffett-scorecard.md`), any extra lens tables, `Key numbers`,
`What changed` and `Red flags`. The scorecard's `Understandable` row
carries a one-line business model drawn from the filing's own wording.

The detail tables below are built on every run, because the scorecard and
Key numbers draw on them, and print after `Red flags` only when asked for
("full detail", or a question about one of them). A question names a
table by what it asks: "margins" or "how profitable" prints Margins and
Expense ratios; "returns", "ROE" or "ROIC" prints Returns; "growth" or
"how fast is it growing" prints Growth; "debt" or "balance sheet" prints
Balance sheet; "valuation", "multiples" or "is it expensive" prints
Valuation (and is answered with the figures, never a word of judgement,
rule 6). Business is the one prose block among them, two or three
sentences from the filing:

```
Business       [2–3 sentences from the filing]
Segments       segment, revenue, share — if disclosed
Geography      region, revenue, share — if disclosed
Financials     five years: the lines in the Financials table above
Margins        five years: gross, operating, EBITDA, pretax, net, FCF
Expense ratios five years: R&D, SG&A, stock-based compensation, capex,
               effective tax rate
Returns        five years: ROE, ROIC, ROA, asset turnover, cash conversion
Growth         five years of YoY %, and the CAGR: revenue, operating
               income, diluted EPS, FCF, diluted shares
Balance sheet  total debt, cash, net debt, equity, net debt/EBITDA,
               current ratio, interest coverage, maturity profile
Valuation      multiple, value, price date, earnings period used
Peers          peer, source of the peer set, the same multiples
Capital return dividend per share, buyback authorization, actual
               repurchases, share count trend
Risks stated   risk as the filing states it, in the filing's order
```

`Red flags` takes its `Filing risk` rows from a diff of `Risks stated`
against the prior year's filing — risk factors added, removed or reworded
(`SKILL.md` → Red flags) — so the prior filing is fetched whenever the
current one is.

**Quick brief** (`SKILL.md` → Report layout → Quick brief). Only the
documents the stock scorecard needs are opened, in this order, and nothing
else:

1. SEC submissions (`data.sec.gov/submissions/CIK##########.json`) — the
   newest 10-K and 10-Q, and the cover-page shares outstanding date.
2. SEC company facts (`…/api/xbrl/companyfacts/CIK##########.json`) — every
   figure for Moat, Capital efficiency, Low debt and Owner earnings, and
   the TTM addends.
3. The newest 10-K's Item 1, read only as far as its first description of
   what the company sells — the `Understandable` line.
4. The daily close history for the price date (Price, in
   `references/buffett-scorecard.md`).
5. The 10-year government bond yield for the same date.

Without the browser, 1 is the cover-page shares concept and 2 is one
concept per figure plus the newest 10-K's statement pages
(`references/no-browser.md` → SEC EDGAR); 4 is the two-page US close
(`references/no-browser.md` → Closes).

The extension-tag fallback below still applies: a scorecard year missing
from company facts is read from the filing it names, and that filing joins
the list. Not fetched in a quick brief: the prior year's filing (Red flags),
segment, geography and peer data, capital-return detail and the run
journal. A lens the request names adds only what that lens's rows need from
company facts, which is already open. `Coverage` counts scorecard checks:
`5 of 6 scorecard checks (quick brief)`.

**Where the numbers come from, and two traps.** SEC company facts
(`data.sec.gov/api/xbrl/companyfacts/CIK##########.json`) carries the
standard-tag figures for every period. Two things in it are easy to get
wrong:

- **It misses a company's own tags.** A figure a company reported under an
  extension tag is not in company facts (NVIDIA's FY2017–FY2021 capex, for
  one). Read those years from the filing's cash flow statement, whose
  comparative columns give the prior years, and name each on a `METHOD`
  line: `FY2021 capex 1,128 from the FY2022 10-K cash flow statement (not
  in company facts)`. A year found in neither is `Not available`.
- **Per-share history mixes share bases.** Each fact keeps the share basis
  of the filing it came from, so one fiscal year can appear before and
  after a split. Adjust each figure by the splits dated after its own
  `filed` date, not after its period end (`references/buffett-scorecard.md`
  → One share basis).

Risks keep the filing's own order. Reordering them is ranking by severity,
which rule 6 forbids, and a table sorted by anything is a table making a
claim about what matters.

Segments and geography are separate tables: they answer different questions
and a company may disclose one and not the other. Where a company discloses
neither, both tables are absent and `Not available` names them — an absent
table is not a suppressed column, and the suppression rule does not cover
it.

**Suppress columns empty for every row**, named in `METHOD`. In practice
this removes the adjusted column where the company presents no adjusted
figures, and the buyback columns for a company that has never repurchased.

**Precision per column.** Revenue in millions at 0 dp does not drag EPS to
0 dp, and EPS at 2 dp does not drag a margin to 2 dp. Print each at what the
filing states, trailing zeros dropped.

**Round half up, never truncate.** A derived figure is computed in full and
rounded once, at print: 339.50 ÷ 8.76 = 38.756 prints `38.8`, not `38.7`.
(The AAPL run of 2026-10-21 truncated its P/E; every other ratio in it
re-derived exactly.) Growth cells are signed like Period %: `+6.4%`,
`-2.8%`. A cell with no figure is `Not available — reason`, in Key numbers
as everywhere: never `not fetched` alone.

`METHOD` — how the figures were resolved:

```
Filing source:     [SEC EDGAR CIK nnnnnnn | issuer IR page]
Entity resolved by: [ISIN | CIK] — never by name
Basis:             reported (IFRS/US GAAP); adjusted shown where the
                   company presents it, marked, never substituted
FCF definition:    [the definition used — it is not standardized]
Peer set source:   [company's own stated competitors | index constituent
                   list] — never assembled from memory
Metric definitions: as in this file → Margins, Expense ratios, Returns,
                   Growth; EBITDA = operating income + D&A, Holdnote's own
                   sum, not the company's adjusted EBITDA
Valuation inputs:  price date [date], earnings period [period]
Currency basis:    [as reported | constant currency, where the filing
                   provides it and which is shown]
Columns suppressed: [named, or none]
Detail tables:     [held back: named | printed: full detail asked]
```

`PROOF` — with addends:

```
segment revenue   12,410+8,205+3,100 = 23,715 against reported 23,715  PASS
geography         ... = 23,715                                          PASS
FCF               OCF 30,110 − capex 4,200 = 25,910                     PASS
net debt          debt 18,400 − cash 12,900 = 5,500                     PASS
EPS               net income 9,820 ÷ diluted shares 1,204 = 8.16        PASS
net margin FY2025 net income 9,820 ÷ revenue 23,715 = 41.4%            PASS
EBITDA FY2025     operating income 11,300 + D&A 1,450 = 12,750          PASS
ROIC FY2025       11,300 × (1 − 0.16) ÷ (18,400 + 40,100 − 12,900)
                  = 9,492 ÷ 45,600 = 20.8%                              PASS
revenue CAGR      (23,715 ÷ 16,200) ^ (1 ÷ 4) − 1 = 10.0%               PASS
restatement       FY2023 revenue 21,090 in FY2025 filing vs 21,040 as
                  originally filed — restated, both reported
segment defs      unchanged across the five years shown
share count       1,261 → 1,204 diluted, −4.5% over five years
ISIN match        document US0378331005 == briefed                      PASS
```

A restatement, a segment redefinition and a share-count trend are checks,
not findings, and they report whether or not they fired. Silence is not a
pass.

`SOURCES` — one row per filing:

| URL or path | Form type and period | Filed | Retrieved (UTC) |

Filing date and retrieval timestamp are different facts and both are
required.

Stop there. `RESULT` ended the answer; the sections after it are evidence,
not a place for a verdict to re-enter.

## Traps specific to company filings

**Adjusted figures are the default in presentations and the exception in
filings.** Investor decks lead with adjusted numbers because they are
flattering. The financial statements carry the reported ones. Use the
statements.

**Fiscal years are not calendar years.** A company with a June year-end
reporting "FY2026" covers a different period from one with a December
year-end. Never compare across companies without stating both year-ends.

**Restatements happen.** If a prior year in the current filing differs from
that year in its original filing, report the current figure and note the
restatement.

**Share count matters more than it looks.** Rising net income with faster-
rising share count is not the same as rising earnings per share. Report both.

**Currency changes distort trends.** For companies reporting in a currency
that moved substantially, note whether the filing provides constant-currency
figures and label which basis is shown.

**Segment definitions change.** When a company reorganizes segments, prior
years are usually restated — but not always. Check before drawing a five-year
segment trend.

---

## Self-check

`RULES.md` Part IV checklist, plus:

- [ ] Sections present, in order (`PROOF` when asked for or halted), subject line above `STATUS`
- [ ] `CONTEXT` is the five mandated fields — FY end and reporting standard
      folded onto `Latest period`, not added as lines of their own
- [ ] Entity resolved by ISIN or CIK, and the ISIN in each filing matches
      the one being briefed
- [ ] `RESULT` opens with the business description and is tables after that
      — no method note, no caveat, no valuation commentary between tables
- [ ] Segments and geography are separate tables; where neither is
      disclosed, both are absent and named in `Not available`
- [ ] Risks in the filing's own order, unranked
- [ ] Columns empty for every row suppressed and named in `METHOD`
- [ ] Each column at its own precision, trailing zeros dropped
- [ ] Reported figures used throughout; adjusted shown alongside and marked,
      never substituted
- [ ] FCF definition named in `METHOD` — it is not standardized
- [ ] Every multiple carries its price date and earnings period
- [ ] Every margin, ratio and return re-derives from the Financials and
      balance sheet figures of the same year, its addends in `PROOF`
- [ ] Gross margin and EBITDA `Not available` for a bank or insurer; no
      negative tax rate, P/E or percentage change off a negative base
- [ ] Growth is between reported years only — no forecast growth anywhere
- [ ] Peer set sourced, never assembled from memory
- [ ] `PROOF` carries addends: segment and geography sums against reported
      revenue, FCF, net debt, EPS
- [ ] Restatement, segment-definition and share-count checks reported
      whether or not they fired
- [ ] `SOURCES` carries filing date and retrieval timestamp per row
- [ ] No recommendation, target, forecast, or causal story about price
- [ ] `RESULT` ends the answer, and no verdict re-enters in `METHOD`,
      `PROOF` or `SOURCES`
