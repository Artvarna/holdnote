# Market Context

Reference for BuffettBot (`buffettbot`). Follow `RULES.md`.

The narrowest module in the system, deliberately. Market-level commentary is
where research tools generate the most confident-sounding nonsense, so this
one reports dated facts and nothing else.

Two modes:

| Mode | Trigger | Output |
|---|---|---|
| **Holdings-scoped** (default) | Rates, inflation, earnings dates, index changes touching what the user holds | The dated-facts list below |
| **Market-wide** | "The market", the indexes, a sector, a region — anything not scoped to holdings | Index, sector-index and rates/FX tables; index contribution only on request |

## What it reports

- **Index levels** — current level and date, for indexes the user's holdings
  track. Nothing else.
- **Policy rates** — ECB, Fed, BoE, BNB. Current rate, effective date, date
  of the next scheduled meeting.
- **Inflation** — latest published print for the eurozone, Bulgaria and the
  US, with the reference month and release date.
- **Earnings calendar** — confirmed reporting dates for companies the user
  holds directly. Company-announced only: a date a data provider shows and the
  company does not is `Not available`, and a date extrapolated from last
  year's pattern is a forecast (rule 8). The Mode C Stocks table
  (`references/etf-brief.md`) prints the same dates beside each stock's
  newest filings; one fetch serves both.
- **Index changes** — announced additions and deletions affecting tracked
  indexes, with the effective date.

Each item carries its source and its date. An item without both is dropped.

## What it never reports

- Why anything moved. "Stocks fell on rate fears" is a story assembled after
  the fact. Report the move and the dated facts; the connection is the user's
  to draw.
- What "the market expects", "sentiment", or "investors are pricing in".
- Forecasts of any kind. Third-party forecasts may be reported as data with
  the forecaster and date named, never restated as the system's own view.
- Anything framed as a reason to act.

## Default output

For a long-horizon portfolio, most weeks contain nothing material. The
correct output then is:

```
Data as of: [date]
Nothing material has changed since [previous run date].
Policy rates unchanged. No index changes affecting held funds.
Next scheduled events: [dates].
```

This is a complete and correct answer. Manufacturing significance to justify
a longer output is a failure of the module, not a service to the user.

The market-wide mode below has no such default: a quiet week still has
levels and closes, and they are what was asked for. Rule 10 still governs
everything it says beyond them.

---

## Market-wide mode

### Trigger

Four tests, in order; the first that matches decides the route. The router
never opens `portfolio.md` to decide — which instruments the user holds is a
question for the module being routed to, not an input to the routing.

1. **Possessive or first-person ownership scope** — "my portfolio", "my
   S&P 500 tracker", "my direct stock pie", "what I own", "what I bought" →
   portfolio view (`references/etf-brief.md` → Mode C). This test fires
   before any index-name match: "how's my S&P 500 tracker doing" names an
   index and is still a question about a position.
2. **A specific instrument named** — ticker, ISIN or fund name, held or not
   → `references/etf-brief.md`, which chooses between Mode A and Mode C
   itself. "How's VUSA done since Monday" carries no possessive and is still
   a question about a position.
3. **An index or sector named, asked how it is built** — universe,
   constituents, weighting, caps, rebalance → Mode B. "What's in the
   S&P 500", "how is MSCI World built".
4. **Anything else about the market, an index, a sector or a region** —
   levels, closes, moves → this mode. "How's the market done the last couple
   of days", "how's the S&P 500 done since Monday".

This mode is reached only by elimination, and that is the point: **scope
decides, not subject matter.** An S&P 500 question is market-wide even when
the user holds an S&P 500 tracker, and a sector question is market-wide even
when every name in that sector sits in the portfolio. What moves a request
to test 1 or 2 is the user scoping it to something held — never the bare
fact that the subject overlaps with the portfolio.

A request that asks both how an index is built and where it closed runs
tests 3 and 4, each in its own tables.

### Scope

Once a request lands here, what it names decides which rows print:

- **One or more indexes named** — "how's the S&P 500 done since Monday",
  "MSCI World and MSCI EM this month" → **only those indexes.** The
  Indexes table carries one row per named index and no other; Sectors and
  Rates & FX do not print. `METHOD` says `Scope: named indexes only`. A
  named sector index ("S&P 500 Energy") or a named index's sectors ("how
  did the S&P 500 sectors do") is a named index: the Sectors table prints,
  for that parent only.
- **No index named** — "the market", "markets", "how are things looking"
  → the full default index set, the sector indexes of both default
  providers, and Rates & FX. `METHOD` says `Scope: default set`.

A sector named without a parent index ("how's tech done") is matched to
the sector indexes of the two default providers, by the provider's own
index names; `METHOD` names the index each phrase was matched to, and a
phrase no provider index name matches is asked about, not guessed.

The scope rule removes rows the user did not ask for; it never adds one.
An index the default set lacks ("FTSE 100") prints when it is named, and
`Coverage` counts against the named set, not the default one.

### Contribution (opt-in)

The Contribution table is **off by default** and runs only when the request
asks what moved an index: "which stocks drove the S&P", "what moved the
Nasdaq today", "biggest contributors to the STOXX 600". The same pattern as
`references/portfolio-sync.md` → Mode M: requested explicitly, never the
default, and `METHOD` names it either way — `Contribution: on (requested)`
or `Contribution: off (not requested)`.

"Drove" in the request is answered with arithmetic, not a cause (rule 7):
the table says how many pp of the move each constituent's weight and price
move account for, and nothing about why the stock moved. A request that
asks what moved an index names it, so the scope rule above applies too;
"which stocks drove the market" names none, and the table then runs for
each index in the default set. The table measures a session's move: over a
longer period it covers the period's last session only. `METHOD` says so,
and `CONTEXT` → `Not available` carries `contribution for multi-day
periods; last session shown`, because a reader who stops at the header
must not take a one-session table for the period's attribution — how to
attribute a multi-session move is not decided (`DECISIONS.md`).

**This mode does not open `portfolio.md`.** No weights, no position sizes,
no weight × move contribution in pp, no mention of which listed names the
user happens to hold. SKILL.md's instruction to read `portfolio.md` is
scoped to requests that touch the portfolio; a market-wide request does not,
and reading it here is what produces the answer nobody asked for. A market
question answered in units of the user's portfolio has quietly replaced the
question, and that substitution is the form in which market commentary turns
into a prompt to act (rule 11).

### What it reports

1. **Major indexes** — level and period % change, over the period resolved
   below. The default set, printed when no index is named (Scope above):
   S&P 500, Nasdaq Composite, Dow Jones Industrial Average, STOXX 600,
   MSCI World, MSCI EM. Each as of **its own** most recent complete
   session, dated per row. These markets close at different hours and on
   different holidays, and a single header date would misdate most of the
   rows. A session still in progress is not a close: report the prior
   complete session, or write `Not available` for the row.
2. **Sector indexes** — the sector index closes the index provider itself
   publishes: the S&P 500 sector indices (S&P Dow Jones Indices) and the
   STOXX Europe 600 supersector indices (STOXX). Each is an index with its
   own closes, so its period % comes from **its own** base and end close
   by the formula below, in the same Performance row as the Indexes table
   — never derived from constituents, never read off a heat map, and never
   stood in for by a sector ETF. Where those closes can be fetched from is
   under Where the closes come from, below. The
   classification scheme is printed only as the provider names it in the
   fetched document; sector names that look like a known scheme are not
   the provider naming it, and where it does not, the scheme is
   `Not available`.
3. **Rates and FX** — the US 10Y benchmark yield, the euro-area 10Y
   benchmark alongside it, and EUR/USD. Anything further is included only
   when it bears on a EUR-based investor and carries a source and a date.
4. **Index-moving single stocks** — on request only (Contribution above). A
   constituent appears only when its arithmetic contribution to the index's
   session move is at least 0.10pp:

   ```
   contribution (pp) = index weight (%) × price move (%) ÷ 100
   ```

   Both inputs are fetched — the weight from the index provider's own
   published constituent file, with its as-of date, and the move from the
   session close. If the weight cannot be retrieved, the row is
   `Not available`; a weight reasoned toward from market caps is rule 1
   again. A name never appears here because the user owns it, and the
   contribution is arithmetic, not an explanation of why the stock moved
   (rule 7).

Staleness and conflicts are handled as in every other module: a figure older
than its source's own publication cadence is flagged as stale rather than
quietly printed, and two sources that disagree are both reported with the
conflict named (rules 4 and 5). The next section makes both checkable per
close.

### Closes: variant, sources, reuse

**The variant is part of the instrument.** A price index, a net total
return index and a gross total return index of the same name are three
instruments with three levels, and in a different currency they are three
more. The Instrument cell of every index row — Indexes and Sectors alike —
states both: `MSCI World (price, USD)`, `STOXX Europe 600 (price, EUR)`.
Where the fetched source does not state the variant, the cell reads
`MSCI World (variant not stated, USD)` and `CONTEXT` → `Not available`
lists `MSCI World variant`. A variant inferred from the level is a guess
(rule 2).

**Every close names its sources, and one source is not confirmation.**
Every row's base and end close are tracked with their own session dates
and the source or sources that gave them — printed in `PROOF` when it is
asked for, and summed up on `METHOD` → `Confirmation` on every run. A close
confirmed by two sources for the same session and variant is checked; a
close only one source gave prints `single source` in the row's verdict,
never `PASS`. That is not a halt and not a defect in the row — it is the
honest state of a figure nobody has cross-checked, and `PASS` over it is a
claim the evidence does not make.

**Sources are compared only within one instrument.** Two closes are
compared — for confirmation or for conflict — only when both are for the
same index, the same variant, the same currency and the same session. A
price close against a net total return close, or a USD level against a EUR
one, is two instruments, not a conflict, however far apart they are: the
figure that is not the row's variant and currency is simply not a source
for that row, and it neither confirms the row nor conflicts with it. A row
left with one matching source is `single source`.

**A source that states no variant** is matched by one of two rules,
depending on the index:

- **Headline convention** — S&P 500, Dow Jones Industrial Average, Nasdaq
  Composite, STOXX Europe 600. The level these indexes are quoted at
  without qualification is the price index: a source quoting a headline
  level without naming a variant counts as the **price** version for
  confirmation and conflict. Only a source that explicitly states net or
  total return is a different instrument. The convention names these four
  and no others; their sector indexes, and any index named outside the
  default set, follow the strict rule.
- **Strict rule** — every other index, MSCI World and MSCI EM included.
  MSCI price and net levels are both widely quoted without a label, so an
  unlabelled MSCI level could be either: a source that does not state its
  variant cannot be matched, and it neither confirms nor conflicts.

The convention settles confirmation only. The Instrument cell still states
the variant a fetched source named, and reads `variant not stated` when
none did. A close the convention matches carries the mark in its source
list — `[S&P DJI; WSJ (variant not stated)]` — so `PROOF` shows which
confirmation rested on it, and `METHOD` names the convention whenever it
was used.

**Two matching sources more than 0.5% apart are a conflict.** On the same
session, variant and currency, when `|a − b| ÷ b × 100 > 0.5` (b the
higher-ranked source, rule 4), the row is a conflict. Its Level and
Period % in `RESULT` read `Not available — sources conflict`, listed as
such in `CONTEXT` → `Not available`, and neither figure is picked. The
row is withheld from `RESULT`, not from the output: both figures are
printed, each with its variant and currency, its source and its session
date, and the gap, marked `CONFLICT` — on a `Conflict:` line in `METHOD`,
and as the row's line in `PROOF` when `PROOF` prints. A withheld figure
that is not printed with its source and date anywhere is undeclared data
(rule 5), and the reader cannot tell a conflict from a failed fetch. At or
below 0.5%, the higher-ranked source's close is used, and `PROOF`, when
shown, prints both.

**Reused fetches.** A run may reuse a close fetched earlier in the same
session only if **no new session has closed on that instrument's exchange
since the fetch** — the figure is then still the most recent complete
session, and fetching it again would return the same number. `METHOD`
names every reused figure and when it was fetched: `Reused: S&P 500
(price, USD) end close, fetched 2026-09-27 13:14 EEST`. If a session has
closed since, or the fetch time is not known to the minute, re-fetch. A
reused figure keeps its original retrieval timestamp in `SOURCES`; it is
not re-stamped as though fetched again.

**Times are exact or absent.** Every time this mode prints — `Data as of`,
a reuse note, a retrieval timestamp — is either an exact `HH:MM` with its
zone or left off in favour of the date alone. A placeholder digit
(`13:1x`, `1?:05`, `HH:MM`) is never printed: it is a figure that was not
recorded, dressed as one that was (rule 2).

### Where the closes come from

What has worked, and what has not, observed in the live runs of 2026-09-27
and 2026-09-28. This is a record of reachability, not a rank: rule 4 still
decides which source outranks which. Re-check a dead end before writing a
row off as `Not available` — sites change.

**Two routes, and which one a source needs.** Most pages below are read with
WebFetch. The two provider data routes marked *browser* load their data by
script: WebFetch gets an empty page, and they are read through the built-in
browser on the user's computer. That works only while the computer is on
with the Claude app open; when it is not, say so in `METHOD` and fall back
to the next row for that family rather than printing `Not available`.

| Instruments | Source | Route | Notes |
|---|---|---|---|
| S&P 500, Nasdaq Composite, Dow | AP "How major US stock indexes fared" wires (abcnews.com and syndicating local sites) | WebFetch | Close, point and % change, week and YTD. Cross-check with a second wrap (Yahoo Finance live blog, TheStreet) |
| S&P 500 sectors | S&P DJI index-data endpoint, one URL per sector (below) | browser | The provider's daily series, with `indexReturnTypeDescription` (`Price Return`) and `currencyCode` stated, so the variant is sourced, not assumed. Levels arrive to ~15 dp: print 2 dp in `RESULT` |
| S&P 500 sectors, fallback | Investing.com `…/indices/s-p-500-<sector>-historical-data` | WebFetch | States no variant: `variant not stated`, strict rule. Staleness check below |
| STOXX Europe 600 and its supersectors | `stoxx.com/index/<symbol>/` — **no `www`** | browser for the daily series; WebFetch for the headline figures | The provider's page: EUR price return, last value, daily change, `Week to Week` and YTD %. The browser reads its chart series, which gives base and end closes from the provider |
| STOXX supersectors, second source and fallback | Investing.com `…/indices/stoxx-600-<name>-pr-historical-data` | WebFetch | `PR` in the name states the price variant, so a matching close **confirms** the STOXX close for the same session: fetch it for every STOXX row that has such a page, and the row is checked rather than `single source`. Base closes from any page; end closes only from a page whose latest row is the end session (staleness check below). Also the fallback when the browser route is down |
| US 10Y | US Treasury daily par yield curve (`home.treasury.gov`, `TextView?type=daily_treasury_yield_curve`) | WebFetch | |
| EUR/USD | ECB reference rates, `eurofxref-hist-90d.xml` | WebFetch | |

**S&P DJI endpoint.**
`https://www.spglobal.com/spdji/en/util/redesign/index-data/get-performance-data-for-datawidget-redesign.dot?indexId=<id>&language_id=1`,
with these ids for the eleven S&P 500 sectors, as resolved from the
provider's sector pages on 2026-09-28: Communication Services 339,
Consumer Discretionary 139, Consumer Staples 213, Energy 25, Financials
279, Health Care 253, Industrials 81, Information Technology 307,
Materials 41, Real Estate 2436, Utilities 356. An id that returns a
different index name than its row is a halt for that row, not a lookup
to guess past.

**STOXX supersectors: the ICB 2019 set of 20 is the default.** STOXX's
index pages describe the current scheme as "11 industries, 20
supersectors", and the Europe 600 supersector index for each, as resolved
from STOXX's own index search on 2026-09-28, is:

| Supersector | Symbol | Supersector | Symbol |
|---|---|---|---|
| Automobiles and Parts | `SXAP` | Industrial Goods and Services | `SXNP` |
| Banks | `SX7P` | Insurance | `SXIP` |
| Basic Resources | `SXPP` | Media | `SXMP` |
| Chemicals | `SX4P` | Personal Care, Drug and Grocery Stores | `S600PDP` |
| Construction and Materials | `SXOP` | Real Estate | `SX86P` |
| Consumer Products and Services | `S600CPP` | Retail | `SXRP` |
| Energy | `S600ENP` | Technology | `SX8P` |
| Financial Services | `SXFP` | Telecommunications | `SXKP` |
| Food, Beverage and Tobacco | `S600FOP` | Travel and Leisure | `SXTP` |
| Health Care | `SXDP` | Utilities | `SX6P` |

STOXX still publishes three indexes under pre-2019 supersector names —
`SX3P` Food & Beverage, `SXEP` Oil & Gas, `SXQP` Personal & Household
Goods. They are not part of the 20 and never stand in for `S600FOP`,
`S600ENP`, `S600CPP` or `S600PDP`: a table that mixes them in is two
schemes at once. They print only when named. `METHOD` → `Sector scheme`
reads `STOXX Europe 600 supersectors, ICB 2019, 20`, and `Coverage`
counts against 20. A symbol that no longer resolves to its supersector's
page is `Not available` for that row, re-resolved by name from STOXX's own
search, never guessed.

**When today's point is a close.** A STOXX series point for today is the
day's close only once the page carries its end-of-day stamp (observed as
`05:50 pm CET` on every final close so far); European trading ends at
17:30 CET, so after that and before the stamp, the point is `not yet
published as a final close` — never `in progress`, which by then it is
not. A US session is closed once the provider's series or the AP wire
dates it. Either way the rule is the one under What it reports: a point
that is not a published close is not used.

**Investing.com serves stale snapshots.** On 2026-09-28 its S&P 500 Energy
history page ended on 2026-09-15 and its STOXX 600 Banks page on
2026-09-18, and a quote page paired a last price with a previous close from
another month. Before using any row from it, check that the page's latest
row is the latest complete session. A stale page may still give a **base**
close — history does not change — but never the end close, and the row
names the page's latest date in `METHOD`. Where both the provider and
Investing.com give a close for the same session and variant, the two
confirm each other: on 2026-09-28 they agreed exactly on S&P 500
Information Technology (7074.89 / 7295.25) and STOXX 600 Banks (424.64).

**Never back a close out of a change figure.** `last close − daily change`
is a derived number, not a close anyone published for that session; the
~0.5% STOXX 600 gap in the 2026-09-27 run came from setting such a figure
against a fetched one. Compare fetched closes only (Closes, above). The
provider's `Week to Week` % may confirm a one-week Period %, as a
percentage and not as a close; its window is not stated on the page, so a
mismatch is reported, not resolved.

**Every `SOURCES` row carries its whole URL and its own dates.** One row
per URL fetched, printed in full — no `…`, no `(same endpoint)`, no
`[a|b|c]` pattern standing in for several addresses — and each row states
its publication date and retrieval time itself. A group heading that
carries the dates for indented URLs beneath it is not a row, and the rows
under it are not rows either: every line of `SOURCES` is a `- ` item or a
table row. A URL a reader cannot paste is not a source they can check,
and a date a reader must look up from another line is not on its row.

**Dead ends, as of 2026-09-28:** `www.stoxx.com` and its `HistoricalData`
text files (refused by robots.txt — use `stoxx.com` without `www`), CNBC
quote pages (403), MarketWatch and WSJ (blocked), Yahoo Finance
`^SP500-xx` (404), Google Finance (rate-limited). Yahoo Finance history
for `^DJI` and `EURUSD=X` returned stale and contradictory rows on
2026-09-27 and was discarded. `spglobal.com/spdji` sector *pages* hold no
levels in their HTML — the endpoint above is where the data is.

### Period resolution

The one parser for "since Monday", "this month" and their kind. This mode
and `references/etf-brief.md` → Mode C both use it; neither keeps its own.

A period resolves to a **base close** and an **end close**, and

```
period % = (end close ÷ base close − 1) × 100
```

The end close is the instrument's most recent complete session. The base
close is the last complete session **before** the period opens — "since
Monday" measures from Friday's close, because Monday's own move is part of
what was asked.

| Phrase | Period opens | Base close |
|---|---|---|
| none stated, "today" | the last complete session | the session before it |
| "since Monday", "this week" | Monday of the current week | last session before that Monday |
| "last week" | Monday of the previous week; ends that Friday | last session before that Monday |
| "this month", "month to date" | 1st of the current month | last session of the previous month |
| "this year", "YTD" | 1 January | last session of the previous year |
| "since [date]" | that date | last session before it |
| "last couple of days" | 2 complete sessions back | the session before those 2 |
| "last few days" | 3 complete sessions back | the session before those 3 |
| anything else — "lately", "recently" | not resolved | ask; never pick a window |

"Couple" as 2 and "few" as 3 are conventions, not readings of the user's
mind, and `METHOD` names them whenever they are used. Sessions are counted
on each instrument's own exchange calendar, so a holiday on one exchange
moves that row's base close and nobody else's. If the period contains no
complete session yet — "since Monday" asked on Monday before the close —
the row is `Not available`, not a zero.

The calendar bounds go on `Latest period` as dates, with the phrase after
them and never in their place: `2026-09-21 to 2026-09-22 ("since
Monday")`. The base and end close each
row actually used go in `PROOF`.

### Performance row

One row format, printed identically wherever a level and its move appear —
the Indexes table here and the Performance table in Mode C — so one close
reads the same way whichever mode printed it:

```
Instrument | Level | Period % | As of
```

- **Instrument** — for an index, the name with its variant and currency,
  `MSCI World (price, USD)`, per Closes above; for a fund or stock, the
  name and ticker as Mode C prints them.
- **Level** — the end close, in index points for an index and in the
  listing's trading currency for a fund or stock, with the currency code
  in the cell.
- **Period %** — the formula above, at the precision the two closes carry,
  printed as a signed number only: `+1.21`, `-0.40`, and `0.00` for no
  move. No `%` in the cell: the column header carries the unit, and a
  cell that repeats it is one more token to strip before the column can
  be added up.
- **As of** — the end close's own session, as `YYYY-MM-DD (exchange
  close)`: `2026-09-21 (LSE close)`. Per row, never a shared header date.

One column is added only when it has something to say. When a row's period
contains a distribution's ex-date (Distributions inside the period, below),
the table prints `Incl. dist %` between `Period %` and `As of`:

```
Instrument | Level | Period % | Incl. dist % | As of
```

Its cells are bare signed numbers like `Period %`; a row with no ex-date in
its period prints `—`, and a row whose distribution could not be sourced
prints `Not available`. A table with no ex-date in any row keeps the four
columns. Price indexes never carry it.

### Distributions inside the period

`Period %` is the listing's price move and stays that. But a distributing
fund or a dividend-paying stock drops by the payout on its ex-date — the
money moves from the price to the holder, it is not lost — so a period that
contains an ex-date prints a price move that reads worse than what the
holder got. The row must say so, never leave the drop to look like a loss.

**When it applies.** A row for a distributing fund (`Dist` in
`portfolio.md` or the factsheet) or a stock, whose period contains an
ex-date: base session < ex-date ≤ end session. An ex-date on or before the
base session is already in the base close and changes nothing.
Accumulating funds do not distribute and are not checked.

**The figure.**

```
Incl. dist % = ((end close + D) ÷ base close − 1) × 100
```

D is the distribution per share in the **listing's trading currency**,
summed if the period holds more than one ex-date. It is not reinvested —
over a period of days to months the difference is below the printed
precision.

**Sources.** Ex-date and declared amount from the issuer first (the fund's
distribution history; a company's investor-relations dividend page).
Yahoo's chart data with `&events=div` appended (Where fund prices come from
→ Yahoo's chart data in `references/etf-brief.md`) confirms the ex-date and
gives D already in the listing's currency, converted at a rate it does not
state. When the issuer declares in the listing's currency, D is the
issuer's figure. When it declares in another (VUSA declares in USD and
trades in GBP on the LSE), D is Yahoo's converted amount, and `METHOD` says
it is a conversion at an unstated rate, with both figures. If the ex-dates
disagree, the issuer's stands and the row's `Incl. dist %` is
`Not available`.

**The METHOD line**, whenever an ex-date falls in a printed row's period,
even when `Incl. dist %` is `Not available`:

```
Distribution in period: VUSA ex 2026-09-17, USD 0.3096 declared (Vanguard),
GBP 0.23187 used (Yahoo's conversion, rate not stated); Period % is price
only
```

Worked, from Yahoo's VUSA.L series: base 2026-09-16 close 107.48 GBP, end
2026-09-18 close 108.0275 GBP, ex-date 2026-09-17 in between. Period % =
(108.0275 ÷ 107.48 − 1) × 100 = +0.51; Incl. dist % =
((108.0275 + 0.23187) ÷ 107.48 − 1) × 100 = +0.73. The distribution is
worth 0.22 pp that the price column does not show.

**Not an ex-date:** the LSE instrument page's `XD` flag. It stays up after
the ex-date (it was showing on 2026-09-28 for VUSA's 2026-09-17 ex-date),
so it marks a recent distribution, never its date. Nor are third-party
dividend tables a source for the amount: on 2026-09-29 one printed VUSA's
June distribution as USD 0.31974 where Vanguard declares USD 0.3236.

### Output

The sections of Part IV — five, or six when `PROOF` is asked for — and
**nothing outside them**: no
note before `STATUS`, between sections, or after the last `SOURCES` row —
a trailing `Sources:` link list included, since each URL sits on its own
`SOURCES` row. A remark that wants to be printed — a fallback, a caveat
about a source, a convention — is a `METHOD` line. Placements that are
specific to this mode:

```
CONTEXT   Data as of:       the run's retrieval date, or the date and an
                            exact HH:MM with zone — never a placeholder
                            digit; per-row session dates are columns in
                            RESULT, not header lines
          Latest period:    the resolved period's calendar bounds, with the
                            phrase that produced them
          Currency / units: index points, % change; yields in %, changes
                            in pp; pp for contributions when that table ran
          Not available:    rows and fields not fetched, each variant not
                            stated, each row withheld on a source conflict,
                            and "contribution for multi-day periods; last
                            session shown" when Contribution ran over a
                            period longer than one session
          Coverage:         n of m per table that ran — indexes, sector
                            indexes per parent, rates & FX rows — m counted
                            in the scope in force. A table that did not
                            run is not counted: never `0 of 0`, which
                            reads as a fetch that found nothing
```

`RESULT` opens with `Mode: Market-wide`, or `Mode: Index construction
(Mode B) + Market-wide` when tests 3 and 4 both ran. Then one table per
question, no prose between them, and only the tables the scope calls for:

```
Indexes        Performance row, one per index in scope
Sectors        Performance row, one per sector index in scope — default
               set, or a named parent's sectors
Rates & FX     one row per instrument: level, change, as-of date —
               default set only
Contribution   on request only: one row per qualifying constituent —
               index, weight, move, contribution in pp, weight as-of date
```

A table the scope does not call for is not printed, and `METHOD` names it
as out of scope, so a missing table is distinguishable from a forgotten
one.

`METHOD` names, on every run:

```
Scope:          default set | named indexes only — [the names]
Contribution:   on (requested) — the formula, its 0.10pp threshold and the
                constituent file each weight came from | off (not requested)
Tables not run: [named, with the reason — out of scope, not requested]
Sector scheme:  per provider, as the provider names it, or Not available
Session:        the definition of a complete session used
Period:         the resolution applied, with the couple/few convention
                when it was used
Reused:         each reused close and when it was fetched, or none
Variant rule:   headline convention used for [sources, per index] | not used
Confirmation:   all rows checked | single source: [rows] | all rows single source
Conflict:       one line per conflict, in the PROOF line form below
                (instrument, both dated figures with variant, currency and
                source, gap, CONFLICT) — or none
Fallbacks:      any fallback source used and why (provider route not
                reachable, stale page and its latest date) — or none
Columns suppressed: [named, or none]
```

`Confirmation`, `Conflict` and `Fallbacks` print on every run: they are
the three things `PROOF` would have shown that a reader needs even when
`PROOF` is hidden (`RULES.md` Part IV).

`PROOF`, when asked for, carries the addends. One line per row of every
table — Indexes, Sectors and Rates & FX alike — with the base date on every one (figures
illustrative):

```
S&P 500 (price, USD)  base 2026-09-18 1000.00 [S&P DJI; WSJ (variant not stated)]  end 2026-09-25 1005.40 [S&P DJI; WSJ]  (1005.40 / 1000.00 - 1) x 100 = 0.54%  PASS
US 10Y (yield, %)  base 2026-09-18 4.10 [US Treasury]  end 2026-09-25 4.16 [US Treasury; FRED]  4.16 - 4.10 = +0.06pp  single source
STOXX Europe 600 (price, EUR)  base 2026-09-18 1000.00 (price, EUR) [STOXX] vs 2026-09-18 1006.10 (price, EUR) [FT] gap 0.61%  end 2026-09-25 1005.00 [STOXX; FT]  CONFLICT
```

Sources for each close sit in brackets, separated by `; `. A row whose base
or end close has one source ends `single source`, never `PASS`; a row with
a gap over 0.5% ends `CONFLICT`, as Closes above sets out, and prints each
conflicting figure as `date figure (variant, currency) [source]` — so the
line itself shows both figures, their dates and sources, and that the two
were the same instrument. A source that stated no variant is marked
`(variant not stated)` in the list, and counts toward confirmation only
under the headline convention. Each contribution row, when that table ran,
is re-derived from the weight and move printed beside it, and every
staleness flag carries the two dates that raised it.

### Self-check

`RULES.md` Part IV checklist, plus:

- [ ] Scope printed in `METHOD`; a named-index run prints only the named
      indexes, and no Sectors or Rates & FX unless those were named
- [ ] Contribution printed only when the request asked what moved an index;
      `METHOD` says `Contribution: on (requested)` or `off (not requested)`
- [ ] `RESULT` holds only Indexes, Sectors, Rates & FX and, on request,
      Contribution — no other table
- [ ] Every index row's Instrument cell states variant and currency, or
      `variant not stated`, listed in `Not available`
- [ ] An unlabelled level confirms a close only for the four headline
      indexes, as price, marked `(variant not stated)` in `PROOF`; never
      for MSCI or a sector index
- [ ] Period % cells are signed numbers with no `%` sign
- [ ] Every time is an exact `HH:MM` with zone, or the date alone — no
      placeholder digit anywhere
- [ ] `PROOF` printed only when asked for; when it prints, every row
      carries its base date, Rates & FX included, and a single-source
      close ends `single source`, never `PASS`
- [ ] `METHOD` carries `Confirmation`, `Conflict` and `Fallbacks` on every
      run, `PROOF` or not
- [ ] Sources more than 0.5% apart are a `CONFLICT`, not a pick — compared
      only within one variant and currency, and printed on a `METHOD`
      `Conflict:` line with both figures, sources and dates even though
      `RESULT` withholds the row
- [ ] A Contribution table over a multi-day period is flagged in `CONTEXT`
      → `Not available`: `contribution for multi-day periods; last session
      shown`
- [ ] Every reused close named in `METHOD` with its fetch time
- [ ] Nothing printed outside the sections

There is no per-run "not financial advice" footer, here or anywhere else —
rule 14 is project-level and lives in SKILL.md's `Scope`. Parity with the
portfolio modes is the point: a disclaimer that appears on one mode and not
the others reads as a claim about the difference between them.

---

## Frequency

Run on request only. Do not schedule, do not prompt the user to check, and do
not offer unprompted updates. A tool that surfaces macro data continuously
creates pressure to act on it, which works against the holding period the
portfolio is built for.
