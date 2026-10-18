# Investor Lenses

Reference for Holdnote (`holdnote`). Follow `RULES.md`.

Optional tables a stock or fund brief adds after the Buffett scorecard
(`SKILL.md` → Report layout) when the request names them: "Buffett +
Graham + Lynch", "run the magic formula on GOOGL", "all lenses". Buffett is
never one of them — the scorecard always prints, whatever is asked.

Every lens prints the scorecard's columns and follows its rules
(`references/buffett-scorecard.md`): sourced metrics, thresholds printed
beside them, `Result` of `Met`, `Not met` or `Not available` and nothing
else, arithmetic in `PROOF`, and no threshold moved to change a row.

```
| Check | Metric | Value | Threshold | Result |
```

A lens is the investor's published test, reduced to what a filing can
answer. Where the original relies on a forecast — an expected growth rate,
a forward P/E — the lens uses the historical figure instead, named in
`Metric`, because rule 8 forbids the forecast. A lens borrowing a name does
not borrow authority: the rows measure what they say and no more.

## Which lens, by name

| Asked as | Table | Applies to |
|---|---|---|
| Graham, Intelligent Investor, defensive investor | `Graham lens` | Stocks |
| Lynch, PEG | `Lynch lens` | Stocks |
| Greenblatt, magic formula | `Greenblatt lens` | Stocks |
| Piotroski, F-score | `Piotroski lens` | Stocks |
| Terry Smith, Fundsmith | `Terry Smith lens` | Stocks |
| Munger, inversion | `Munger lens` | Stocks |
| Bogle | `Bogle lens` | Funds |

Tables print in the order the request names them. "All lenses" means every
lens that applies to the instrument, in the order of this table.

**This file is the definition.** A lens's checks and thresholds are the
ones below, and nothing is fetched to define or confirm them — not
Wikipedia, not a screener's write-up of an investor, not a summary of a
book. A web page restating Graham's rules is not a source for a figure,
and `SOURCES` lists no page for a lens's rules: it lists the filings and
prices the rows were measured from. A threshold the user wants changed is
changed here.

A lens asked of the wrong kind of instrument — Bogle on a stock, Graham on
an ETF — prints no table and is named in `CONTEXT` → `Not available`:
`Graham lens (stocks only)`. So is a name this file does not define: a
lens is never improvised from what the agent recalls of an investor.

**Shared inputs.** Share price, market capitalization and the 10-year bond
yield are fetched exactly as the Buffett scorecard fetches them, for one
price date, so a brief with several lenses uses one price throughout.
Enterprise value = market capitalization + total debt − cash and
equivalents, debt as the scorecard defines it. Periods follow the
scorecard's two kinds (`references/buffett-scorecard.md` → Two kinds of
period): a record test uses fiscal years, a test of the position now — a
P/E, P/B, yield, a debt or liquidity ratio — uses TTM and the newest
balance sheet. Per-share figures are on one share basis, splits applied.

**Financial companies.** Banks and insurers have no gross profit,
working capital or EBIT in the sense these tests use. Rows that need them
are `Not available`, reason `not defined for a financial company`, never
approximated.

## Graham lens

Benjamin Graham's tests for the defensive investor, from *The Intelligent
Investor*.

| Check | Metric | Threshold |
|---|---|---|
| Earnings stability | Net income, each of the last 10 FY | Positive every year |
| Dividend record | Dividend paid, each of the last 20 FY | Paid every year |
| Earnings growth | Average EPS of the last 3 FY vs the 3 FY ten years earlier | Up by a third or more |
| Financial condition | Current ratio, newest balance sheet | 2.0 or more |
| Debt within working capital | Long-term debt vs net current assets, newest balance sheet | Debt no more than net current assets |
| Moderate P/E | Price ÷ average diluted EPS of the last 3 FY | 15 or less |
| Moderate P/B | Price ÷ book value per share, newest balance sheet | 1.5 or less |
| Graham product | P/E × P/B, as above | 22.5 or less |

Graham's P/E uses a three-year average of earnings on purpose, so one
good or bad year does not decide it; it is the one valuation row that is
not TTM. Graham's financial condition for an industrial company is two
tests — current ratio and long-term debt against net current assets —
and both print. His adequate-size test (annual sales over a dollar figure
set in 1972) has no row: the threshold has no stated modern equivalent,
and inflating it would be the agent's own number.

The dividend record needs 20 years. Where the filings fetched reach back
less far, the row is `Not available` with the years found — the company's
own dividend history page counts as issuer material (source rank 2), a
data site does not stand in for it.

## Lynch lens

Peter Lynch's tests from *One Up on Wall Street*. Lynch's PEG divides the
P/E by the **expected** growth rate; the lens uses the **historical**
five-year EPS growth, and says so, because an expected rate is a forecast.

| Check | Metric | Threshold |
|---|---|---|
| PEG | P/E (TTM diluted EPS) ÷ EPS CAGR, last 5 FY, historical | 1.0 or less |
| Inventory | Inventory growth vs revenue growth, latest FY | Inventory not growing faster |
| Debt | Total debt ÷ shareholders' equity, newest balance sheet | 0.5 or less |

The PEG row's `Value` carries Lynch's category, by the historical CAGR it
already uses: `1.6 (stalwart, EPS CAGR 12%)` — slow grower under 10%,
stalwart 10% to under 20%, fast grower 20% or more. A category is a label
for the growth rate printed beside it, not a call on what kind of company
it is; cyclicals, turnarounds and asset plays need judgement and are never
assigned. A negative CAGR leaves PEG undefined: `Value` is the CAGR,
`Result` is `Not met`. A company carrying no inventory is `Not available`
on that row.

## Greenblatt lens

Joel Greenblatt's magic formula from *The Little Book That Beats the
Market*. The formula ranks a universe of stocks against each other; a
brief looks at one, so the lens prints the two measures against absolute
thresholds the user can tune, and never claims a rank.

| Check | Metric | Threshold |
|---|---|---|
| Earnings yield | EBIT, TTM ÷ enterprise value | 8% or more |
| Return on capital | EBIT ÷ (net working capital + net PP&E), latest FY | 25% or more |

EBIT is operating income as the filing reports it. Net working capital =
current assets − cash − (current liabilities − short-term debt).
Greenblatt excludes financials and utilities from the formula; so does the
lens, `Not available`, reason `excluded from the formula`.

## Piotroski lens

Joseph Piotroski's F-score: nine yes/no signals from two consecutive
fiscal years, latest against prior. Each signal is a row; the last row is
the tally.

| Check | Metric | Threshold |
|---|---|---|
| Profitable | ROA = net income ÷ opening total assets | Above 0 |
| Cash generating | Operating cash flow | Above 0 |
| Improving ROA | ROA latest vs prior FY | Higher |
| Earnings quality | Operating cash flow vs net income | Cash flow higher |
| Less leverage | Long-term debt ÷ average total assets, latest vs prior | Lower |
| More liquidity | Current ratio, latest vs prior | Higher |
| No dilution | Shares outstanding, latest vs prior FY end | Not higher |
| Better margin | Gross margin, latest vs prior | Higher |
| Better turnover | Revenue ÷ opening total assets, latest vs prior | Higher |
| F-score | Signals met, of 9 | 7 or more |

A signal whose inputs are not available counts as not met in the F-score
row, and that row's `Value` says how many: `6 of 9 (1 not available)`. The
F-score is never scaled up to make up for a missing signal.

## Terry Smith lens

Terry Smith's three steps at Fundsmith — buy good companies, don't
overpay, do nothing. The third is a behaviour, not a measurement, and has
no row.

| Check | Metric | Threshold |
|---|---|---|
| High returns | ROCE = EBIT ÷ (total assets − current liabilities), latest FY | 20% or more |
| High margins | Gross margin, latest FY | 40% or more |
| Cash conversion | Free cash flow ÷ net income, latest FY | 90% or more |
| Not overpaying | Free-cash-flow yield, TTM, vs 10-year bond yield | Yield above the bond |

Free cash flow = operating cash flow − capex, the same definition
`references/stock-brief.md` prints in `METHOD`. Free-cash-flow yield =
free cash flow ÷ market capitalization.

## Munger lens

Charlie Munger's inversion — work out what would ruin an investment, then
look for it — turned into checks a filing can answer. It does not
write failure stories: every row is a pattern that has historically
damaged shareholders, measured in this company's own reported numbers. A
`Not met` row is a pattern present, not a prediction.

| Check | Metric | Threshold |
|---|---|---|
| No dilution | Diluted shares outstanding, latest vs five FY earlier | Not higher |
| Debt within earnings | Total debt growth vs net income growth, last 5 FY | Debt not growing faster |
| Acquisition load | Goodwill ÷ shareholders' equity, latest FY | 50% or less |
| Customer concentration | Any single customer at 10%+ of revenue, as the filing discloses | None disclosed |
| Clean accounts | Restatement, auditor change or material weakness, last 5 FY | None |
| Going concern | Going-concern doubt in the auditor's report, latest FY | None |

Customer concentration, clean accounts and going concern are read from the
filing's own disclosures — the 10-K's notes and Item 9A, the auditor's
report, an 8-K Item 4.01 for an auditor change. "None" means the filing
was read and states none, not that nothing was found by a search. Where the
relevant section was not fetched, the row is `Not available`.

Negative equity leaves the acquisition-load ratio undefined: `Value` is
`equity negative`, `Result` is `Not available`.

## Bogle lens

John Bogle's case for index funds: costs compound against the investor,
and the broadest, cheapest fund held longest wins. Stricter than the
Buffett scorecard's fund version on cost, and adds turnover.

| Check | Metric | Threshold |
|---|---|---|
| Very low cost | TER (ongoing charges) | 0.10% or less |
| Tight tracking | Tracking difference, as the scorecard's fund version reads it | No worse than −(TER + 0.05pp) |
| Whole market | Number of holdings | 1,000 or more |
| Low turnover | Portfolio turnover rate, last annual report | 10% or less |

Portfolio turnover is the rate the annual report states; neither the KID
nor the factsheet carries it, and an annual report that does not state it
leaves the row `Not available`, never estimated from holdings changes. Funds calculate
it by different methods; the method, where the report names it, is a
`METHOD` line, and two funds' rates are never compared across methods.
