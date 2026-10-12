# Buffett Scorecard

Reference for BuffettBot (`buffettbot`). Follow `RULES.md`.

The first table of every stock and fund brief (`SKILL.md` → Report layout).
It is never dropped, and a request for other lenses adds to it.

The scorecard measures; it does not judge. Each row is a metric taken from
a fetched document, a threshold the user has chosen, and the arithmetic
between them. `Met` means the number cleared the bar printed beside it and
nothing more — not that the instrument is good, cheap or worth owning
(rule 6). The thresholds are starting points the user tunes by editing this
file; the agent never adjusts one to make a row come out differently.

```
| Check | Metric | Value | Threshold | Result |
```

`Result` is `Met`, `Not met` or `Not available`, and nothing else. A row
whose input could not be fetched is `Not available`, its missing input
named in `CONTEXT` → `Not available` — never filled from memory, never
estimated (rules 1 and 2). The TL;DR's `Scorecard:` line is the tally of
this column: `4 of 6 met · 1 not met · 1 not available`.

Every row's arithmetic prints in `PROOF` with its addends when `PROOF`
prints, and runs on every run whether or not it prints.

## Stock version

Six checks. Figures are reported (IFRS or US GAAP), never adjusted, and
come from the filings `references/stock-brief.md` already fetches — the
scorecard adds two fetches of its own: a share price and a government bond
yield, both for the same price date.

**Window.** Ten fiscal years where the filings provide them; five at
minimum. Fewer than five → the row is `Not available` with the count of
years found. The window printed in `Metric` is the one actually used
(`FY2016–FY2025`), never the one intended.

**Two kinds of period.** A check about a record — Moat, Capital efficiency,
Owner earnings growth — uses fiscal years, because only annual figures are
audited and comparable year on year. A check about the position *now* —
Low debt, Margin of safety, and every valuation multiple a lens uses — uses
the **trailing twelve months (TTM)** whenever a 10-Q (or interim report) is
newer than the latest annual report, because a fiscal year can be up to a
year old: on 2026-10-11 NVIDIA's FY2026 ended 2026-01-25, and its P/E was
47 on FY2026 earnings against 29 on TTM. `Metric` names the period used.

```
TTM flow  = latest FY + current year-to-date − prior year-to-date
            (income and cash flow lines, from the 10-K and the newest 10-Q)
TTM EPS   = TTM net income ÷ diluted weighted shares of the newest quarter
balance   = the newest balance sheet (10-Q date), not the fiscal year end
```

With no interim report newer than the annual one, TTM is the latest fiscal
year and `Metric` says `FY`. The TTM arithmetic prints in `PROOF` with its
three addends.

**One share basis.** Every per-share figure and share count across the
window is restated to the current share basis using the split ratios the
filings state (XBRL `StockholdersEquityNoteStockSplitConversionRatio1` or
the filing's own split note), so a ten-year EPS series is comparable
across splits. A figure is adjusted by the splits dated **after the
`filed` date of the filing it came from** — not after its period end —
because SEC company facts keeps each value on the share basis of the filing
that reported it, and one year often appears in filings from both sides of
a split. Each split applied is a `METHOD` line:
`Split basis: 4-for-1 2021-07-20, 10-for-1 2024-06-10; each EPS divided by
the splits after its filed date`.
A split the filings do not state is never inferred from a price chart.

**Price.** The share price is the official close of the price date, taken
from a daily close history (exchange or Nasdaq history), never a quote
endpoint's "last sale", whose timestamp can label the wrong session. The
close and its date are a `METHOD` line, and the brief uses that one price
for every row and lens.

| Check | Metric | Threshold |
|---|---|---|
| Moat | Gross margin, each FY in the window | Stable or rising |
| Capital efficiency | ROE, each FY in the window | 15% or more every year |
| Low debt | Total debt ÷ net income, TTM | Under 4 years |
| Owner earnings | Net income + D&A − maintenance capex, latest FY vs five FY earlier | Growing |
| Margin of safety | Owner-earnings yield vs 10-year government bond yield | Yield above the bond |
| Understandable | One-line business model, in the filing's own words | The line names what is sold |

### Moat

Gross margin = gross profit ÷ revenue, per fiscal year.

**Stable or rising** means the latest year's margin is no more than 2.0pp
below the first year's in the window. `Value` prints both and the lowest
year: `38.1% → 46.2% (low 37.0%, FY2017)`.

A company that reports no gross profit line — banks, insurers, most
REITs — is `Not available`, reason `no gross profit line in the income
statement`. Gross profit is never reconstructed from cost lines the filing
does not total itself.

### Capital efficiency

ROE = net income ÷ average shareholders' equity (opening and closing of the
year), per fiscal year. `Value` prints the range: `15.2–24.0%`.

Where equity is zero or negative at either end of any year in the window —
common after large buybacks — ROE has no meaning for that year, and the row
switches to ROIC for every year, named in `Metric`:

```
ROIC = operating income × (1 − effective tax rate) ÷
       (total debt + shareholders' equity − cash and equivalents)
```

using the effective tax rate the filing states. The switch is a `METHOD`
line: `Capital efficiency: ROIC — equity negative in FY2023`. A threshold is
never moved to suit the metric; 15% applies to both.

### Low debt

Total debt (short- and long-term borrowings, commercial paper, and lease
liabilities where the filing includes them in debt) on the newest balance
sheet ÷ TTM net income. `Value`: `1.4 years`.

**Under 4 years** is the test Buffett describes: could the company repay
its debt from about four years of earnings. A company with no debt prints
`0 years`. A net loss makes the ratio meaningless: `Value` is `net loss`,
`Result` is `Not met`.

### Owner earnings

```
owner earnings = net income + depreciation and amortization
                 − maintenance capex
```

From the cash flow statement. Almost no company discloses maintenance
capex separately. Where the filing does, it is used. Where it does not,
**total capex** is used in its place, and the row's `Metric` says so:
`NI + D&A − total capex (maintenance not disclosed)`. Total capex is the
conservative substitute — it includes growth spending, so it can only
understate owner earnings — and it is a fetched figure, not an estimate.
The basis is a `METHOD` line on every run.

**Growing** means the latest fiscal year's owner earnings exceed those of
the year five fiscal years earlier. `Value`: `52,140 → 101,870 (USD m)`.
Negative owner earnings in the latest year → `Not met`.

### Margin of safety

No discounted cash flow, no intrinsic value, no growth assumption — those
are forecasts, and rule 8 forbids them. The check uses today's numbers
only:

```
owner-earnings yield = TTM owner earnings ÷ market capitalization
market capitalization = share price × shares outstanding
```

with the price as **Price** above, and shares outstanding from the newest
filing's cover page, its date in `METHOD`.

It is compared to the 10-year government bond yield **on the same price
date**, in the currency the shares are listed in:

| Listing currency | Bond | Source |
|---|---|---|
| USD | 10-year US Treasury, par yield | U.S. Treasury, Daily Treasury Par Yield Curve Rates — the table view (`home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve&field_tdr_date_value_month=YYYYMM`), read in the browser; the CSV download does not load there |
| EUR | 10-year German Bund | Deutsche Bundesbank daily yield series |
| Other | — | `Not available`, reason `no bond series for <ccy>` |

**Yield above the bond** means the owner-earnings yield is higher than the
bond yield. `Value`: `3.1% vs 4.2%`. This is Buffett's comparison of a
business's earnings against what a risk-free bond pays at the same moment.
It describes a gap; it says nothing about what the price will do.

A price that is not from the price date, or a bond yield from a different
date, is not used — the row is `Not available` and both dates are named.

### Understandable

`Value` is one line quoted from the filing's own business description
(10-K Item 1, or the annual report's business overview), shortened only by
cutting, never by rewording. `Met` when the quoted line names what the
company sells; `Not met` when the filing's description does not say it in
a line. It is never the agent's own summary of the business.

## Fund version

Buffett's advice for most investors is a low-cost, broad index fund held
for a long time. The fund version measures exactly those three things, plus
two that decide whether a fund can actually be held for decades. Figures
come from the documents `references/etf-brief.md` → Mode A already fetches
— KID, factsheet, annual report — and, for the last row, the index
provider's factsheet.

| Check | Metric | Threshold |
|---|---|---|
| Low cost | TER (ongoing charges) | 0.20% or less |
| Broad | Number of holdings | 500 or more |
| Not concentrated | Combined weight of the top 10 holdings | 40% or less |
| Tracks its index | Tracking difference, last full calendar year | No worse than −(TER + 0.10pp) |
| Built to last | Fund age and AUM | 5+ years and EUR 500m+ |
| Quality underneath | Index ROE = P/BV ÷ P/E, trailing | 15% or more |

**Low cost.** The TER as the KID or factsheet states it, share class
matched (rule: the ISIN on the document is the ISIN briefed). A 0.00% TER
is re-verified before printing, as `SKILL.md` → Validation requires.

**Broad.** Holdings count from the factsheet or the full holdings file, the
same figure as `Key numbers`.

**Not concentrated.** The combined top-10 weight, summed from the
individual weights rather than taken from a header total (Validation). 40%
is loose on purpose: a broad market-cap index can be top-heavy, and this
row exists to show how top-heavy, not to fail every large-cap tracker.

**Tracks its index.** Tracking difference = fund total return − index
total return for the last full calendar year, as the annual report states
it (UCITS funds disclose it), or as the factsheet's calendar-year returns
for fund and index give it. Where neither carries a calendar year, the
factsheet's trailing one-year difference (SSGA prints it as `Difference`,
fund net − index) is used in its place, its end date in `Metric`:
`Tracking difference, 1 year to 2026-09-30`. `Value`:
`−0.09pp (TER 0.07%)`. A fund that has not existed for a full year is
`Not available`. Tracking difference is never confused with tracking
error, which is a volatility, not a gap: a factsheet's `Tracking error`
figure is never used for this row.

**Built to last.** Both parts must hold: inception at least five years
before the data date, and AUM of EUR 500m or more (converted at the
factsheet date's rate if the fund reports in another currency, the rate
and its source in `METHOD`). Small, young funds are the ones issuers close.
`Value`: `9.4 years · EUR 12.1bn`.

**Quality underneath.** The index provider's factsheet publishes trailing
P/E and P/BV for the index. Their ratio is the index's return on equity:

```
ROE = (price ÷ book) ÷ (price ÷ earnings) = earnings ÷ book
```

Trailing figures only, and from the **index provider's** factsheet (MSCI,
STOXX, S&P), never the fund's: a fund factsheet's P/E is usually forward —
SSGA's is a mean analyst estimate for the next fiscal year — and a forward
P/E is a forecast (rule 8). `Value`: `P/BV 3.40 ÷ P/E 21.9 = 15.5%`. An
index factsheet that does not publish both trailing figures is
`Not available`.

## What the scorecard is not

- Not a rating. There is no total score beyond the tally, no weighting of
  one check over another, no colour.
- Not a list of reasons to act. A row that is `Not met` is a measurement,
  and rule 11 applies to it like any other.
- Not portable between instruments of different kinds. A stock scorecard
  and a fund scorecard answer different questions; they are never printed
  side by side as if comparable.
