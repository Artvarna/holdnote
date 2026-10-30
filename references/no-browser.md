# Without the browser — the phone and web routes

Reference for Holdnote (`holdnote`). Follow `RULES.md`.

On a phone, on claude.ai in a browser, or whenever the user's computer is
off, there is no built-in browser and the cloud shell reaches only package
registries and GitHub. Until 2026-10-29 that left a stock brief with no
EDGAR figures and a fund brief with no factsheet figures: every cell
`Not available (browser route down)`. The routes below were each checked
live on 2026-10-29 with WebFetch alone and give the same primary documents
— SEC filings, issuer factsheets and KIDs, the ECB, MSCI — so the research
runs in full. Only one thing still needs the computer: **exchange closes
for funds** (Exchange closes, below).

Use these routes whenever the built-in browser is not in this session or
cannot reach the computer. When the browser is up, the browser routes in
each module stay first; these are not a second source for them.

## The read-back gate

WebFetch hands the page to a small model and returns its answer, not the
page. On 2026-10-01 it dropped form types from a large JSON file, and on
2026-10-03 two reads of one factsheet gave two different top-10 totals.
Both failures had the same shape: a big document, a loose question, and
nothing to check the answer against. So a figure read through WebFetch is
printed only when it passes this gate.

**1. Ask for values, never passages.** The prompt names the fields and
says `copy verbatim, digit for digit, no summary`, and asks for rows as
`a | b | c` lines or a markdown table. WebFetch will not quote more than
about 125 characters of prose, so a heading or a sentence is asked for as
its first 12 words, copied exactly, followed by `…`. Never ask it to
interpret, total or compare: Holdnote does the arithmetic in its own
shell, on the values returned.

**2. Read small documents.** A file over about 100,000 characters is read
only in part (WebFetch says so and gives an `offset` to read on). Every
route below was picked because the document that carries the figure is
small: one XBRL concept, not all company facts; one statement page, not
the whole 10-K.

**3. Confirm before printing**, by one of these, in this order:

| Confirmation | What it is | Example |
|---|---|---|
| `two documents` | A second, independent document from the same publisher states the same figure for the same period | SEC concept JSON 416,161,000,000 and the 10-K's statement page 416,161 ($ millions) |
| `own totals` | The document's own arithmetic holds on the values read: a list adds to its printed total, a statement's subtotals add | Top 10 adding to the factsheet's `Total of Portfolio 27.78%`; Net sales − Cost of sales = Gross margin |
| `read twice` | No second document and no total exists: a second WebFetch of the same URL, with the fields asked in a different order and different words, returns the same digits | A KID's SRI, a fund's inception date |

A figure that fails its confirmation is never printed: the cell is
`Not available — WebFetch reads disagree`, with both readings on a
`Conflict:` line in `METHOD`. A figure with no confirmation is
`Not available (browser route down; unconfirmed)`.

**4. Say so in `METHOD`**, on one line, every run that used a route here:

```
Route:             no browser — WebFetch; 41 figures: 28 two documents, 11 own totals, 2 read twice
```

The conflict and single-source rules (`RULES.md` Part IV) apply as on any
run. A figure confirmed by `read twice` rests on one document, so it is
named on the `Confirmation:` line as `single source` and counted on the
`SOURCES` line like any other.

**If a URL is refused.** WebFetch may refuse an address it was not shown.
Every URL template below is spelled out in this file; if one is still
refused, WebSearch for the document by name (`Apple 10-K 2025 sec.gov`)
and fetch the address the search returns.

## SEC EDGAR (US-listed stocks)

`data.sec.gov` and `www.sec.gov` refuse the cloud shell, and the full
`submissions/…json` and `companyfacts/…json` files are too large for
WebFetch (on 2026-10-29 the submissions file came back cut off, with no
`form` column). Five smaller documents carry everything a brief needs:

| Need | Document | URL |
|---|---|---|
| CIK from a ticker | EDGAR company search | `https://efts.sec.gov/LATEST/search-index?keysTyped=<TICKER>` — gives entity name, CIK and tickers. The name must match the company briefed |
| The 10-K and 10-Q list | The cover-page shares concept: one entry per periodic filing, with `form`, `fp`, `fy`, `filed`, `accn` and the share count | `https://data.sec.gov/api/xbrl/companyconcept/CIK##########/dei/EntityCommonStockSharesOutstanding.json` |
| One figure over every period | One XBRL concept | `https://data.sec.gov/api/xbrl/companyconcept/CIK##########/us-gaap/<Tag>.json` — ask for the entries with the `form` and `fp` needed (`10-K`/`FY`, or `10-Q`/`Q1`–`Q3`) as `end \| val \| fy \| form \| filed \| accn \| frame` |
| A filing's statements | The filing's index, then its statement pages | `https://www.sec.gov/Archives/edgar/data/<CIK>/<accn without dashes>/FilingSummary.xml` names the `R<n>.htm` page of each statement (MenuCategory `Statements`); each `…/R<n>.htm` is one statement as a table, with its units line |
| 8-Ks, for Earnings recap | EDGAR full-text search | `https://efts.sec.gov/LATEST/search-index?q=%22results%20of%20operations%22&ciks=<10-digit CIK>&forms=8-K&dateRange=custom&startdt=<YYYY-MM-DD>&enddt=<YYYY-MM-DD>` — each hit's `_id` is `<accn>:<file>`, its `items` include `2.02`; the `ex99` file is the release, at `…/Archives/edgar/data/<CIK>/<accn without dashes>/<file>` |

**Confirmation for EDGAR figures is `two documents`:** the concept JSON
value and the same period's line on a statement page (`R<n>.htm`) of a
filing that reports it, after scaling the page's units (`$ in Millions`).
A 10-K's income and cash flow statements carry three years and its
balance sheet two, so the newest 10-K, the one two years before it and the
one four years before cover a five-year Key numbers table. The statement
page's subtotals are checked as well (`own totals`): a misread digit breaks
one of them.

Checked 2026-10-29 on Apple: `RevenueFromContractWithCustomerExcludingAssessedTax`
gave FY2025 416,161,000,000 (accn 0000320193-25-000079); the same filing's
`R3.htm` gave Net sales 416,161 and Cost of sales 220,960, Gross margin
195,201, which adds. The shares concept listed every 10-K and 10-Q back to
FY2024 with its accession number.

- **The tag list** is the one `references/stock-brief.md` → Margins,
  Returns and Growth map; a figure under a company's own extension tag has
  no concept file, and is read from the statement page alone, confirmed by
  `own totals` — named on a `METHOD` line as in stock-brief's extension-tag
  fallback.
- **Risk factors** come from the 10-K's main document
  (`…/<primary>.htm`, the largest `.htm` in the filing index): ask for every
  Item 1A heading's first 12 words, in order, with the sub-section titles.
  On 2026-10-29 Apple's FY2025 10-K gave all 28, in five sub-sections, and
  said the text read reached Item 1B. Do the same for the prior 10-K and
  diff them as `SKILL.md` → Red flags says, matching on the words given.
  A heading list that does not reach Item 1B is read on with `offset`.
- **`Understandable`** (the scorecard) takes Item 1's first description of
  what the company sells, asked for as its first 12 words.

## Fund documents (factsheets, KIDs, index factsheets)

WebFetch reads issuer PDFs. On 2026-10-29 the iShares Core MSCI World
factsheet (`ishares.com/uk/individual/en/literature/fact-sheet/swda-ishares-core-msci-world-ucits-etf-fund-fact-sheet-en-gb.pdf`)
gave its two as-of dates, TER 0.20%, net assets 151,362.25 USD m, 1,250
holdings and a top 10 that added to its printed `Total of Portfolio
27.78%`.

- **Top 10, Sectors, Countries** — confirmed by `own totals`: the weights
  read must add to the factsheet's printed total (to 0.01 pp). With no
  printed total, they are `read twice`.
- **TER** — `two documents`: the factsheet and the KID's ongoing charges.
  Where the two differ, both are printed (rule 4 ranks the KID first).
- **AUM, holdings count, inception, SRI** — `read twice`, or
  `two documents` where the KID or the issuer's fund page states it.
- **Index country lists** (Structural table) — the MSCI factsheet's
  `* DM countries include:` footnote is too long to quote, so ask for the
  countries as a list. On 2026-10-29 MSCI World's gave 23; the count is
  confirmed against the number the footnote or the factsheet states, else
  `read twice`.
- **A factsheet WebFetch cannot open** (SSGA's returned a client error on
  2026-10-29): WebSearch for `<fund name> factsheet pdf` and try the
  address found; failing that, justETF as the labelled rank-3 fallback
  `references/etf-brief.md` → Fund facts describes, then `Not available`.

## ECB reference rates

`https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml` (today's)
and `…/eurofxref-hist-90d.xml` (90 days) both open with WebFetch: ask for
the `Cube time` and the currencies needed. The same day's rate in both
files is `two documents`. On 2026-10-29 the daily file gave 2026-10-28,
USD 1.1133, GBP 0.83785.

## Closes

- **US-listed stocks** — two history pages WebFetch can read (StockAnalysis,
  Investing.com, Yahoo Finance) agreeing within 0.10% on the same session
  and listing: `references/price-move.md` → Without the built-in browser,
  which every module uses, including a brief's price date. The price date
  is the newest session both pages state; these pages lag (StockAnalysis's
  newest AAPL row on 2026-10-29 was 2026-10-26), so `METHOD` names the date
  and the route.
- **Exchange closes for funds and non-US stocks still need the browser.**
  Checked again 2026-10-29: the LSE instrument page has no price in its
  served HTML and its API refuses another origin; Deutsche Börse's page
  carries no close without its scripts; Yahoo's chart data refuses
  WebFetch. Those rows stay `Not available (browser route down)`, and the
  rest of the run goes on. A portfolio's weights still print from the
  export's own values (`references/any-broker.md`).
- **US 10-year Treasury yield** — the Treasury's table view already opens
  with WebFetch (`references/buffett-scorecard.md`); confirm by
  `read twice`.

## What a phone run prints

A full stock brief, fund brief, quick brief, Earnings recap, Head-to-head,
Price move and the Stocks table now run without the computer. `STATUS` is
`Complete.` as on any run. Exchange closes left `Not available (browser
route down)` are partial coverage (rule 9): they go in `CONTEXT` →
`Not available` and `Coverage`, never on `STATUS`, and `METHOD`'s `Next:`
line says the closes need the Claude desktop app open on the user's
computer, then a re-run.
