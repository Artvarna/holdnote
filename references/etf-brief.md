# ETF & Index Brief

Reference for Holdnote (`holdnote`). Follow `RULES.md`.

## Three modes

| Mode | Trigger | Output |
|---|---|---|
| **A — Fund brief** | Any ETF named, by ticker, ISIN or full name | Per-fund brief |
| **B — Index brief** | An index named without a fund (MSCI World, STOXX 600, S&P 500) | Methodology brief |
| **C — Portfolio view** | 2+ funds supplied, "my portfolio", or one fund asked how it has done, held or not | Performance + comparison table + overlap |

Modes combine. "Compare VWCE against what I own" = A on VWCE, C on the set.

A single fund named splits by what is asked of it. What the fund **is** —
costs, replication, index tracked, risk indicator — is Mode A. How it has
**done** is Mode C on a set of one, held or not: "how's VUSA done since
Monday", "how's iShares Core FTSE 100 done this month" and "how's my S&P
500 tracker doing" all route here rather than to
`references/market-context.md`, even though the last one names an index.
Mode C is where `portfolio.md` is read; the market-wide module never reads
it.

Mode C prints the tables the question asks for (Which tables a question
gets, under Mode C output), and a table it prints keeps its rows when the
set is small: a set of one prints its asked-for tables with their single
row, or `none` where a fund alone has nothing to put in them. A table
dropped because the set is small is a table no reader can tell has run.
A full report prints all twelve Mode C tables.

---

## Step 1 — Resolve documents

The brief is only as good as the documents behind it. Work down this list and
stop at the first that yields a current document:

1. **Local folder** — `/etfs/<TICKER>/` if it exists
2. **Issuer fund page** — fetch the KID and factsheet directly (see map below)
3. **Ask the user** — give the exact issuer URL to visit and say which file to
   download

Never proceed on memory. If no document is retrievable, the brief is
`Not available` for that fund — that is a valid and correct output.

### Issuer document map

| Issuer | Where documents live |
|---|---|
| iShares / BlackRock | ishares.com — country site, fund page, "Literature" |
| Vanguard | vanguard.[country domain] — fund page, "Documents" |
| Amundi | amundietf.[country] — fund page, "Documentation" |
| SPDR / State Street | ssga.com/spdr — fund page, "Documents & Literature" |
| Xtrackers / DWS | etf.dws.com — fund page, "Downloads" |
| Invesco | invesco.com — ETF page, "Literature" |
| VanEck | vaneck.com — fund page, "Documents" |
| HSBC AM | etf.hsbc.com |
| UBS | ubs.com/etf |
| Fidelity Intl | fidelityinternational.com |

**Always search by ISIN, not ticker.** The same fund lists on several
exchanges under different tickers with different currencies; the ISIN is
unambiguous. If the user gives only a name, resolve the ISIN first and state
which share class you resolved to — issuers commonly run Acc and Dist share
classes of the same fund under near-identical names.

### Document priority

KID/KIID > factsheet > prospectus > annual report > issuer web page > anything
else. KID figures are regulator-standardized; factsheet figures are not. On
conflict, prefer the higher-ranked document and flag the disagreement
(RULES.md Rule 4).

**Always fetch the EU PRIIPs KID.** UK KIID (SRRI) and EU KID (SRI) use
different risk methodologies and produce different numbers for the same fund —
they are not comparable and must never sit in the same table. UK pages often
rank higher in search; check which regime the fetched document belongs to. If
only a UK KIID is retrievable, label the figure `SRRI` explicitly and keep it
out of any cross-fund comparison.

---

## Mode A — Fund brief

### Fields

**Identity** — legal name · ISIN · ticker(s) and exchange(s) · issuer ·
domicile · UCITS status · inception date · AUM + as-of date · share class
(Acc/Dist) and whether other classes of the same fund exist

**Mandate** — index tracked (full name, and its return version — price,
net or gross — as the KID names it) · number of holdings · replication
method (full physical / sampled / synthetic swap) · counterparty if synthetic
and disclosed · securities lending policy if stated

**Costs** — TER / ongoing charges (annual %) · transaction costs if broken out
in the KID · performance fee if any · tracking difference vs index if
published (label whether the document gives tracking *difference* or tracking
*error* — they are not the same thing)

**Structure** — Acc or Dist · distribution frequency · base currency ·
trading currency if different · currency hedging and to what

**Exposure** — top 10 holdings with weights + as-of date · combined top-10
weight · top 5 sectors · top 5 countries · number of countries

**Risk as stated** — KID summary risk indicator (1–7) · risks the document
itself lists

Report only risks the document states. Adding your own is analysis, which
Rule 6 forbids.

### Output

`RULES.md` Part IV sets the shape: `STATUS`, `CONTEXT`, `RESULT`, `METHOD`,
`PROOF`, `SOURCES`, in that order — `PROOF` only when asked for or on a
halt. The checks it would print run every time.

The subject line sits above `STATUS` and is not a field — it names what is
being briefed, and identity is the one thing a reader resolves before
anything else:

```
=== [TICKER] — [Full legal name] · [ISIN] · [Acc/Dist] ===
```

Share class is on that line because `Acc` and `Dist` of one fund are
different instruments under near-identical names, and a reader who misses
the class misreads every figure below it.

```
STATUS: Complete.
```

```
CONTEXT
Data as of:       [date]
Latest period:    [document date — the newest of the documents used]
Currency / units: [base currency] (trading: [ccy]); TER as annual %;
                  weights as % of fund
Sources used:     [KID, factsheet — named; SOURCES carries their dates]
Not available:    [fields not found]
Coverage:         [n of m fields populated, or n of m funds briefed]
```

`Sources used` is not a mandated field. This module prints it because it
fetches documents a reader cannot identify from the five values, as
`RULES.md` Part IV → CONTEXT allows.

`RESULT` follows `SKILL.md` → Report layout: the Mode line
(`Mode: Fund brief (Mode A)`), the TL;DR, then `Buffett scorecard` (fund
version, `references/buffett-scorecard.md`), any extra lens tables,
`Key numbers`, `What changed` and `Red flags`. `Key numbers` is the Fund
facts row set:

```
Key numbers    index tracked · holdings count · replication · domicile ·
               UCITS · inception · AUM + as-of · TER · risk indicator n/7
```

`Red flags` takes its `Filing risk` rows from changes to the KID's risk
section and risk indicator against the previous KID on record.

**Quick brief** (`SKILL.md` → Report layout → Quick brief). Only the
documents the fund scorecard needs are opened, and nothing else:

1. The fund's factsheet — TER, holdings count, top 10 weights, inception,
   AUM, and the calendar-year or one-year fund and index returns behind
   Tracks its index.
2. The KID, only for a figure the factsheet does not carry (most often the
   TER, or a calendar-year return).
3. The index provider's factsheet — trailing P/E and P/BV for Quality
   underneath.

Not fetched in a quick brief: the previous KID (Red flags), the full
holdings file, the prospectus and annual report unless a scorecard row
needs one, and the run journal. Mode C questions are never quick: a quick
brief is about one fund.

The detail tables are built on every run and print after `Red flags` only
when asked for ("full detail", or a question about one of them):

```
Top 10         name, weight; with the combined top-10 total and its as-of
Sectors        top 5, weight
Countries      top 5, weight, and the count of countries
```

Holdings count sits in `Key numbers` and top-10 concentration in `Top 10`;
on a full-detail run both print, because they answer one question — how
concentrated is this fund — and a reader quoting one should see the
other.

`METHOD` — how the figures were resolved, not what they are:

```
Documents ranked:  KID > factsheet > prospectus > annual report > page
Risk regime:       [EU PRIIPs SRI | UK KIID SRRI] — never mixed
Replication basis: [as the document states it]
Costs basis:       [annual % | cumulative in currency] — never conflated
Weights basis:     [Mode C only: market weights, one as-of date, per
                   portfolio-sync.md Mode M]
Overlap depth:     [Mode C only: full holdings file | top 50 | top 10]
Stocks window:     [Mode C only: 8-Ks filed in the 30 days to the data date,
                   by EDGAR filing date | none — no stocks in the set]
Earnings dates:    [Mode C only: company-announced only, never estimated]
Columns suppressed: [named, or none]
Detail tables:     [Mode A only: held back: named | printed: full detail asked]
```

`PROOF` — the validation of the Validation section, with addends:

```
top-10 sum       5.9+4.1+3.2+... = 24.8% against stated 24.8%   PASS (0.0pp)
sector sum       ... = 99.4%, residual 0.6% (cash/other)        PASS
country sum      ... = 100.0%                                   PASS
0.00% costs      none                                           PASS
risk indicator   6/7 vs universe (global DM equity)             PASS
ISIN match       document IE00BFY0GT14 == briefed                PASS
```

Mode C's Stocks table adds three checks, reported whether or not they fire:

```
CIK match        AAA -> CIK 0000000001, "Company A Inc." ~ portfolio.md   PASS
8-K window       2 listed, 2 in the 30 days to 2026-10-01 per EDGAR       PASS
earnings date    AAA 2026-10-29 >= data date 2026-10-01, announced by company  PASS
```

Conflicts between documents are reported here, in full, both values named,
neither resolved.

`SOURCES` — one row per document:

| URL or path | Title as the document names itself | Published | Retrieved (UTC) |

Publication date and retrieval timestamp are different facts and both are
required. A factsheet published 2026-06-30 and fetched 2026-09-19 is three
months stale, and only the pair shows it — which is `RULES.md` rule 5 made
checkable.

---

## Mode B — Index brief

For when the user asks about an index itself rather than a fund tracking it.
Source from the **index provider's** own documents — MSCI, FTSE Russell,
S&P Dow Jones, STOXX, Solactive — never from a fund's KID, factsheet or
marketing page. A fund document describes what one fund does with the
index, which is a Mode A question.

Fields:

- Full index name and provider
- **Universe** — which markets, which size segments. State explicitly whether
  it covers developed only, emerging only, or both; large/mid only, or small
  caps too. This single line explains most overlap between funds.
- Number of constituents
- Weighting method (free-float market cap, equal, factor-tilted, capped)
- Any cap applied to single issuers or countries
- Rebalance and review schedule
- Top 10 constituents + weights + as-of date
- Country and sector breakdown
- Return versions the provider publishes — price, net, gross — as the
  fetched document lists them

Which return version a given fund tracks is not a Mode B field. It can be
answered only from the fund's own documents, which Mode B does not use;
it is in Mode A, from the KID's statement of the index tracked.

Index families matter: a provider's "IMI", "Standard", "Small Cap" and "All
Cap" variants of the same region differ substantially. Always state which
variant, and never treat one as a proxy for another.

### Source ladder for Index facts

Methodology PDFs are the best source and the one most often unreadable to
a fetch. Each Index facts field is resolved down this ladder, stopping at
the first rung that yields it:

1. **Provider methodology document** (PDF) — the index's own rulebook
2. **Provider HTML methodology or index page** — the provider's web page
   for the index or its methodology, on the provider's own domain
3. **Provider factsheet "Quick Facts"** — or the factsheet's equivalent
   facts block, however the provider titles it

The ladder is walked **per field**, not per brief: an unreadable PDF sends
each field down to the next rung, and a field one rung answers does not
wait on a rung that failed for another. A field no rung yields is
`Not available — [rungs tried]`. Every rung tried and what it returned —
fetched, unreadable, not found — is a `METHOD` line.

**Each Index facts row names the document it came from**, in a `Source`
column: `MSCI methodology (PDF, 2026-05)`, `STOXX index page (HTML)`,
`factsheet Quick Facts (2026-08-31)`. A reader has to be able to see that
the weighting method came from the rulebook and the constituents count from
a factsheet, because those two carry different dates.

**Staleness is per row.** A field taken from a document published more
than 12 months before the retrieval date carries a `stale` flag on its own
row — `stale: published 2025-06-30` — in a `Stale` column. One note for
the whole brief hides which fields are old; the flag goes where the figure
is. The column is suppressed, and named in `METHOD`, when no row is stale.

### Mixed dates: the dated factsheet wins

Providers often publish both a dated factsheet and an undated live list —
a constituents page, a country weights widget. The two are different
snapshots, so:

- **The dated factsheet wins for every table it covers.** Where the
  factsheet has a top 10, a country breakdown or a sector breakdown, that
  table prints from the factsheet, at the factsheet's as-of date, even
  where the live list is deeper or looks newer.
- **An undated list may only add depth the factsheet lacks** — countries
  beyond the factsheet's top 5, say. It prints as its own table, never as
  rows mixed into a dated one, and that table's heading says so:
  `Countries (undated)`. Its as-of column reads `undated`.
- **Nothing reconciles across the two.** An undated table is summed on its
  own in `PROOF` and never checked against, or used to split, a dated
  figure such as the factsheet's `Other`.

`METHOD` names which table came from which document.

### Mode B output

Same sections. `RESULT` opens with `Mode: Index construction (Mode B)`
— or `Mode: Index construction (Mode B) + Market-wide` when the request
also asks where the index closed — and then carries four tables and no prose
between them, plus any `(undated)` depth table the rule above allows:

```
Index facts    field · value · source document · stale flag — full name
               and provider · variant · universe (DM/EM, size segments) ·
               constituents count · weighting method · caps · rebalance
               and review schedule · return versions published
Top 10         constituent, weight; with the combined top-10 total and its
               as-of date
Countries      one row per country, weight, as-of date
Sectors        one row per sector, weight, breakdown scheme, as-of date
```

**Countries depth.** One row per country comes from the provider's
constituent or country file. An index factsheet usually prints only its
largest countries and an `Other` line; when that is all that could be
fetched, print those rows and `Other` as the document states it, name how
many countries `Other` covers where the document's universe list makes that
countable, and name the depth — `factsheet top 5 + Other` — in `METHOD`.
Never split `Other` into countries from memory, or from an undated list.

**Sector scheme.** Print the breakdown scheme (GICS, ICB, …) only where the
fetched document names it. Sector names that look like a known scheme are
not the document naming it: where the text does not say, the scheme is
`Not available`, and `METHOD` says so.

Constituents count and combined top-10 weight answer one question — how
concentrated is the index — so the count is in `Index facts` and the
combined weight closes `Top 10`, and neither is printed without the other.
Countries and sectors are separate tables for the same reason as in Mode A:
each sums to its own 100%, and `PROOF` checks each sum on its own.

`CONTEXT` → `Latest period` carries the methodology document's date and
the factsheet's as-of date. `METHOD` names the variant briefed, the sector
scheme, the return version whose figures are shown, the ladder rung each
Index facts field came from and every rung that failed, which table came
from which document, and any column suppressed. `PROOF` carries the top-10
sum against the stated total, and the country and sector sums, with their
addends.

---

## Mode C — Portfolio view

### Comparison table

One row per fund. Columns: Ticker · Index · Universe (DM/EM/global,
size segments) · TER · Replication · Acc/Dist · Currency · Domicile · AUM ·
Top-10 concentration. AUM is the fund's, in its base currency, from the
factsheet; a cell that can only give a share class's says so
(`EUR 46,776m, share class [justETF]`) — see Fund facts above.

Sort by TER ascending. No "winner", "best value" or "recommended" column.

### Overlap analysis

Run automatically for 3+ funds, or on request.

**Two layers, both reported:**

**1. Structural overlap** — derived from index definitions alone, before any
holdings data. State which index universes intersect and which are disjoint by
construction. This is definitional and does not require fetching holdings:
a developed-markets index and an emerging-markets index **from the same
provider** do not intersect (MSCI World and MSCI EM); a single-country index
nested inside a global one does.

**Across providers, compare country lists, never labels.** Providers classify
countries differently, so "developed vs emerging" proves nothing when the two
indexes come from different providers: the STOXX Europe 600 includes Poland,
which MSCI classifies as emerging, so MEUD and EIMI can hold the same companies.
A cross-provider pair is `disjoint` only when no country is in both
indexes' country lists, and its Index fact says so in those terms
(`no country in both lists`, `United States is not in MSCI EM's country
list`). A list that could not be fetched makes the row `Not available` and
names the missing list, never `disjoint` by assumption.
`contract.structural_problems` checks this.

**Where the country lists come from.** A factsheet's country weights are
not a country list: MSCI's print the top five and `Other`. The full list is
the factsheet's footnote, `* EM countries include: …` or `* DM countries
include: …`, read from the PDF's text in the built-in browser (the same
pdf.js route as Fund facts below). Both shells are refused by msci.com.

| Index | Country list from | Reached by |
|---|---|---|
| MSCI World | `msci.com/documents/10199/255599/msci-world-index-usd-net.pdf`, footnote `* DM countries include:` (23 countries) | *browser* — 200 |
| MSCI Emerging Markets IMI | `msci.com/documents/10199/255599/msci-emerging-markets-imi-usd-gross.pdf`, footnote `* EM countries include:` (24 countries) | *browser* — 200 |
| S&P 500 | Vanguard VUSA portfolio data, market allocation (`United States 100.0%`) | WebFetch |
| STOXX Europe 600 | `stoxx.com/index/sxxp/`, the 17 countries in Europe | *browser* |

The EM IMI file is the gross-return factsheet because the net one
(`…-imi-usd-net.pdf`) returns 404. The country list belongs to the index,
not to its return variant, so the gross file is the right document for it;
it is never a source for EIMI's performance. Print the factsheet's date
(`SEP 30, 2026` on 2026-10-05) as the source's Published date.

**A Structural `Not available` names why**, in one of two forms only:
`Not available (browser route down)`, or `Not available — <document>
returned <status>`. "Not fetched" is not a reason: the 2026-10-03 run left
VUSA · EIMI and MEUD · EIMI empty with `country list not fetched` while the
browser was up. `contract.structural_problems` checks this too.

**2. Holdings overlap** — requires actual constituent data. For the four
funds in `pies.md` it comes from each issuer's **full** holdings file, read
by `scripts/fund_holdings.py` (see Holdings and Look-through tables below).
A top 10 from the factsheet is the fallback only for a fund whose file could
not be fetched or failed its checks, or for a fund the script has no source
for; the table's heading then says `top-10 depth, partial` for that fund and
`METHOD` names why.

**Shared weight is one figure:** the sum, over the shared names, of the
smaller of the two funds' weights in each name — the part of each fund that
is the same companies in at least that size. One number per pair, never one
per fund (`26.67`, not `SPPW 26.67% · VUSA 37.8%`). A pair with no shared
names prints `0` in both columns. `contract.holdings_problems` checks this.

### Mode C output

Same sections. `RESULT` opens with `Mode: Portfolio (Mode C)` — or
`Mode: Fund brief (Mode A) + Portfolio (Mode C)` when the two combine — and
then carries the tables below — the asked-for ones, in this order — and
no prose between them. A full report carries all twelve tables:

```
Performance      Performance row, one per instrument in the set
Allocation       one row per pie holding, one total row per pie and the
                 portfolio: quantity, close, value in EUR, market weight,
                 target, difference in pp (scripts/market_weights.py)
Comparison       one row per fund, sorted by TER ascending
Structural       one row per pair: overlapping | disjoint, and the index
                 fact that makes it so
Holdings         one row per pair: shared names, shared weight
Look-through     one row per company: weight via each fund, and the total
Hidden bets      one row per company reached through two or more holdings
                 with a Total of 1.00 or more: each route, the largest, and
                 what the others add (scripts/fund_holdings.py)
Countries        one row per country: weight direct and via each fund, the
                 total, an Other countries row and a Total row
                 (scripts/fund_holdings.py)
Sectors          one row per GICS sector, same columns and rows as Countries
Currencies       one row per trading currency, same columns and rows
Holdings changes one row per fund: what its holdings file changed against
                 its snapshot 7+ days older (fund_holdings.py changes)
Stocks           one row per individual stock in the set: next
                 company-announced earnings date, latest 10-K or 10-Q, and
                 the 8-Ks filed in the last 30 days
```

### Which tables a question gets

A short answer to a narrow question beats twelve tables nobody asked for.
The question picks the tables; where it names several things, the sets
join, in the order above.

| The question is about | Tables |
|---|---|
| What I own, in general ("what do I own", "how's my portfolio") | Allocation, Look-through, Hidden bets, Countries, Stocks |
| Actual vs target weights | Allocation |
| Overlap between my funds | Comparison, Structural, Holdings |
| A single company across everything ("how much Apple do I own") | Allocation, Look-through |
| What I own through more than one holding ("what am I really betting on", "hidden bets") | Allocation, Look-through, Hidden bets |
| A portfolio card ("make a card", `SKILL.md` → Portfolio card) | Allocation, Holdings, Look-through, Hidden bets, Countries, Sectors |
| Countries · sectors · currencies | Allocation, then Countries · Sectors · Currencies |
| How it performed ("how's my portfolio done this week") | Performance |
| What changed in my funds' holdings | Holdings changes |
| My stocks' earnings dates or filings | Stocks |
| "Full report", "everything", or the scheduled weekly brief | all twelve |

`METHOD`'s first line after `Build:` names them:
`Tables: Allocation, Sectors (asked: sectors)`. A table left out is left out
because nobody asked, and that line is how a reader knows; an asked-for
table that cannot be filled still prints, as `Not available` with its
reason.

Structural and holdings overlap stay separate tables. They are different
questions answered from different evidence — one from index definitions
alone, one from constituent files — and a reader must be able to see which
is which without reading a column header.

**Performance** uses the columns and `As of` format of
`references/market-context.md` → Performance row, unchanged, and resolves
its period with that file's Period resolution — there is one parser, and
VUSA's close prints here exactly as it would anywhere else — including
the `Incl. dist %` column and its `METHOD` line when a distribution's
ex-date falls in the period (market-context → Distributions inside the
period; VUSA and the three stocks can, the three Acc funds cannot). Its rows are
the **instruments in the set**: each one the request names, or, where the
request scopes to the portfolio without naming any ("my portfolio"), each
instrument in `holdings.csv` or `portfolio.md`. Held or not decides nothing — Mode C is
reached on test 2 for a named instrument whether or not the user owns it,
so a row is never added or dropped by what `portfolio.md` contains. The
period % is the instrument's move, not the position's: a portfolio total
or a weight × move contribution needs market weights (`portfolio-sync.md`
→ Mode M) and is not a column here.

### Allocation table

What share of the portfolio each holding is at the brief's closes, next to
the target in `holdings.csv` (any broker) or `pies.md` (Trading 212). Printed when the request scopes to the portfolio
("my portfolio"); a set the user named reads `none` here, because a weight is
a share of the whole portfolio and a named set is not it.

**The table is the output of `scripts/market_weights.py`, pasted unchanged.**

- **Holdings from any broker** (`holdings.csv`): run it in Claude's
  workspace with the skill's own scripts and a copy of the file, exactly as
  `references/any-broker.md` → How the portfolio view uses it shows. Its
  first column is `Group`; a holding without a target prints `-` in Target
  and Diff.
- **Trading 212 sync**: run it in the repo folder on the user's computer
  (device shell), where the exports are:

```
cd "$HOME/mnt/<folder>" && python3 scripts/market_weights.py --prices "$HOME/prices.json"
```

(`$HOME/mnt/<folder>` is where the device shell mounts the user's own repo
folder — `SKILL.md` → Your files; request access to it first if it is not
connected.)

`prices.json` lives outside the repo (the device shell's home), so the run
leaves nothing behind in it. It is written by the run from figures it already holds, never
from memory:

- `as_of`: the latest session date, on or before the Performance end, on
  which every holding has a close on its own exchange **and** the ECB
  published reference rates — normally the Performance end itself. It moves
  earlier when an exchange was shut or its session had not closed (a Monday
  evening run before the Nasdaq close), or on a TARGET holiday when the ECB
  publishes no rates (1 January, Good Friday, Easter Monday, 1 May,
  25–26 December). `METHOD` says which date and why. A period that ends
  before the last trade in the exports has no Allocation: the script refuses
  it, and the table reads its one-line refusal.
- `prices`: one entry per held ISIN (each `holdings.csv` row, or each pie
  ISIN) — that instrument's close on `as_of`
  from the closes Performance already fetched (its end close, or its base
  close when `as_of` is the base session), its listing
  currency (`GBX` for MEUD, or `GBp` as Yahoo writes it; both are pence and the
  script divides by 100, while `GBP` is pounds), its date and source. The
  script withholds a value over 10× or under 1/10 of the holding's cost basis
  as a likely unit error, naming both figures.
- `fx`: every currency those closes are in other than EUR (`USD`, `GBP`,
  and `CHF`, `PLN`, `SEK` … for holdings that trade there) as units per 1 EUR
  from the ECB euro foreign exchange reference rates for `as_of`. Read them in the built-in browser
  from an `ecb.europa.eu` tab: `fetch('/stats/eurofxref/eurofxref-hist-90d.xml')`
  and take the `Cube time="<as_of>"` row (both shells are refused by the ECB).
  WebFetch reaches the same file and returned the same 2026-10-02 rates, but
  it summarises: its figure confirms the browser's, it never replaces it.
  A rate is never reused from a trade row of the export, and never recalled.

With `holdings.csv`, quantities are the file's, as of its `as_of`; `METHOD`
copies the script's `Allocation …` lines, which name the file, its date and
its source, and a trade after that date is not in the table until the user
imports again. With a Trading 212 sync, quantities come from the T212
exports through `scripts/t212_holdings.py`
(same cutoff, same FIFO split as the sync), so the script needs nothing else.
It refuses an `as_of` before the last trade in the exports, and withholds
every weight when any holding cannot be valued at `as_of` (portfolio-sync →
Mode M, M2); values that can be computed still print. The exports end where
the user last exported them: `METHOD` copies the script's three
`Allocation …` lines, which name the last trade they contain, so a reader
can see when the quantities were read. A buy after the last export is not in
the table until the user exports again.

**Diff is arithmetic only.** `Diff (pp)` is `Weight − Target`, signed, two
decimals. No word goes on it or near it — not "overweight", "drifted",
"rebalance", "buy" — in any section. What to do about a difference is the
user's decision. `contract.allocation_problems` checks the column and that
the holding weights sum to 100.

**Without the computer** (no device shell, or no browser for the closes and
ECB rates — Claude on the web or a phone) and with `holdings.csv`: run
`market_weights.py --holdings <holdings.csv>` with **no `--prices`**. When
the export stated every holding's value in one currency (`import_holdings`
says so: `Values: every holding's value is in the export`), the table weighs
each holding by that value, titled `Allocation (weights from the export's
values, <CCY>, as of <export date>)`, and its `METHOD` lines say no closes were
read. These are the export's weights on its date, not today's: `CONTEXT` →
`Latest period` names that date. When the values are incomplete, in two
currencies, or of unstated currency, the script prints its one-line refusal,
which is the table; ask for the currency when that is the only gap
(`--value-currency`), never assume it. With a Trading 212 sync, or no values,
the table is one line: `Not available (browser route down)` or `Not available
(computer not linked)`.

### Holdings and Look-through tables

**Both tables are the output of `scripts/fund_holdings.py`, pasted
unchanged.** It reads every company each fund holds — not a top 10 — so a
pair's shared weight and a company's look-through total are complete rather
than a floor.

**The files come from GitHub, not from the issuers.** On the user's Pro plan
neither the computer's shell nor Claude's workspace can reach the issuer
sites — only package registries and GitHub. A daily GitHub Actions job
(`.github/workflows/holdings.yml`, 05:23 UTC) runs `fund_holdings.py fetch`
on GitHub's servers and force-pushes the raw files and its `fetch.log` to the
`holdings-data` branch, which holds only the latest run. Three steps:

1. **Claude's workspace** (`Bash`): attach the user's own repo for reading
   if it is not already (`add_repo` with its `owner/name`, `SKILL.md` →
   Your files — never the public Holdnote repo, whose Action fetches
   nobody's funds), then
   `git clone --depth 1 -b holdings-data https://github.com/<owner>/<name> "$SCRATCH/holdings"`
   and read `fetch.log`. Its `utc:` line is when the files were fetched. A
   fund the log lists as `Not available` either has a `carried over` line —
   its last good file from an earlier run, dated in its name, which `report`
   reads like any other — or no file at all. Either way `METHOD` gives the
   log's reason, and for a carried-over file the date it was fetched.
2. **Copy the four files to the computer**: copy each
   `<TICKER>-<date>.<ext>` to `/mnt/user-data/outputs/`, then
   `device_commit_files` them to `<repo>/data/holdings/` on the computer
   (inside `data/`, so never committed). Files only — never paste rows into
   the conversation.
   With `holdings.csv` (any broker) skip this step: `report` runs in the
   workspace on the clone itself, as `references/any-broker.md` shows.
3. **The computer's shell** (Trading 212 sync), after the Allocation table's
   `prices.json` exists:

```
cd "$HOME/mnt/<folder>" && python3 scripts/fund_holdings.py report --prices "$HOME/prices.json"
```

Do not run `fetch` on the computer or in the workspace: both are refused at
the network, and that is expected. `report` reads the newest file per fund
and prints `Holdings`, `Look-through`, then `METHOD` and `PROOF` lines: copy
the tables into `RESULT` and the lines into those sections. Add one `METHOD`
line naming where the files came from:
`Holdings source: holdings-data branch, fetched <utc from fetch.log> by GitHub Actions`.
When that time is more than 3 days old the job has stopped running (GitHub
pauses scheduled jobs after 60 days without a push, and emails the repo
owner on a failed run): say so in that line; the tables still print, each
dated by its file's own as-of.

| Fund | Issuer file | Updated | Matching key |
|---|---|---|---|
| SPPW | SSGA daily holdings xlsx | daily | ISIN |
| MEUD | Amundi product API (`/mapi/ProductAPI/getProductsData`) | daily | ISIN, Bloomberg ticker |
| EIMI | iShares UK `latest-holdings.csv` | daily | ticker + exchange only; weights to 0.01 |
| VUSA | Vanguard UK holdings API (`/gpx/graphql`) | **month-end** | ISIN |

**One company, not one share class.** US and Canadian ISINs contain the
CUSIP, whose first six characters name the issuer, so Alphabet A and C are
one company in every column. Other ISINs match exactly. EIMI's file has no
ISINs: its rows match MEUD's through ticker and exchange (`PKO` on Warsaw is
`PKO PW`), which is how the Polish and Greek companies both funds hold are
found — at top-10 depth MEUD · EIMI read `0`.

**The files carry different dates.** Each is the issuer's latest; Vanguard
publishes month-end only. The `Holdings` heading prints each fund's as-of,
and the script's `Holdings dates` line goes into `METHOD`. This is not the
mixed-date problem of Which weights are admissible below — that rule is about
the portfolio weights, which stay Allocation's single as-of.

**Look-through** takes Allocation's `Weight (market)` for each fund and
stock, computed by `market_weights` from the same `prices.json`, so the two
tables cannot disagree. A via cell is fund weight × company weight in the
fund ÷ 100, to 0.01; Total is the sum of the row's printed cells, so every row
re-adds. It prints each directly held company, then the largest others by
Total (15 by default; `--top` changes it), and `METHOD` says how many
companies the cells reach and what the printed rows sum to. When any fund
with a weight has no file, or Allocation's weights are `Not available`, the
whole look-through is `Not available` with that reason — never a partial set.

**Hidden bets** comes from the same `report` run and is pasted unchanged:
every company the portfolio reaches through two or more holdings — a direct
stock and a fund, or two funds — whose Look-through Total is 1.00 or more,
largest Total first. Columns:

| Company | Through | Largest part | Total | Added by the others |

`Through` lists each route with its Look-through cell (`Direct 7.35 · via
SPYI 1.26 · via SPY5 0.94`) and sums to `Total`, which is the company's
Look-through Total. `Largest part` is the largest single route — all that
any one holding shows — and `Added by the others` is `Total − Largest part`.
It is read from every company the cells reach, not only the rows Look-through
prints, so `--top` changes nothing in it. No company qualifying prints one
row, `none`. At factsheet top-10 depth (no full files for a fund) it is
`Not available - needs every fund's full holdings file; a top 10 leaves out
routes`, because a company outside one fund's top 10 would lose that route
and its Total would read low; `METHOD`'s `Next:` line offers the GitHub
option (`references/setup.md`). The name says what the table finds — exposure no single holding
shows — and no word goes beside it: not "too much", "risky" or
"concentrated"; what to do about it is the user's (rule 6).
`contract.hidden_bets_problems` re-adds every row against Look-through.

**Countries** comes from the same `report` run, on the same files and the
same market weights, printed after Hidden bets and pasted unchanged. A via
cell is fund weight × the fund's % in that country ÷ 100, to 0.01 (half up,
as Allocation rounds); Direct is each stock's weight under the country the
fund files give that same company. Countries with a Total under 0.50
(`--min-country`) fold into `Other countries (n)`, whose cells are the sums
of the cells they replace; non-equity rows (cash, FX, futures) are
`Cash and other`; the Total row is the column sums, so it re-adds both ways.
The four files do not measure country the same way — SSGA gives the country
a security trades in, Amundi a country of risk, iShares a location, Vanguard
a Bloomberg ISO code — and the script's `Countries basis` line says so in
`METHOD`; it is never smoothed over. When Look-through is `Not available`,
Countries is too, with the same reason. `contract.countries_problems` checks
the row and column sums.

**Sectors and Currencies** come from the same `report` run as Countries, on
the same files and market weights, built by the same table code, printed
after Countries and pasted unchanged. Every row re-adds and the Total row is
the column sums (`contract.sectors_problems`, `contract.currencies_problems`).
Where the files differ, the script says so in `METHOD`, never smoothing it:

- **Sector** is the sector SSGA (SPPW), Amundi (MEUD) and iShares (EIMI)
  state per row; the Amundi request asks for its `sector` field. Vanguard's
  file carries none, so a VUSA company — or a MEUD row its file leaves
  blank — takes the sector another fund's file gives the same company,
  matched by ISIN issuer or Bloomberg ticker, exactly as Look-through
  matches. A company no file covers (about 1% of VUSA on 2026-10-10) is
  `Sector not stated`, its weight printed rather than spread.
- **Currency** is the currency each line **trades** in — SSGA's `Currency`,
  Amundi's `currency` and iShares' `Market Currency`. A MEUD row without one
  takes its Bloomberg exchange code's currency (`LN` GBP, `SE` CHF,
  euro-area codes EUR), which misses the London lines that trade in
  dollars. VUSA's companies take it from another fund's file. It is the listing currency, which is what an
  unhedged fund's value moves with, not where a company earns its revenue;
  the `Currencies basis` line says so.
- Each table's `sources` line in `METHOD` gives, per fund, how much of its
  equity weight took the value from its own file, from an exchange code,
  from another fund's file, or none — so a reader can see how much of a
  row rests on borrowing.

Direct stocks take their sector and currency from the fund files the same
way, named on the `direct stocks` lines. When Look-through is `Not
available`, Sectors and Currencies are too, with the same reason.

### Holdings changes table

What each fund's holdings file changed since about a week before: companies
added, companies dropped, and the largest moves in a company's weight in the
fund. It is `scripts/fund_holdings.py changes`, pasted unchanged with its
`METHOD` and `PROOF` lines.

**Where the history comes from.** The same GitHub Actions job, after
publishing `holdings-data`, runs `fund_holdings.py snapshot`: when a fund's
newest snapshot is 7 or more days older than its current file, it writes a
compact CSV — one row per company, share classes summed, with weight,
country, sector and currency — to `<TICKER>/<file as-of>.csv` on the
`holdings-history` branch. That branch is appended to, never force-pushed,
so it keeps every week. Vanguard's month-end file writes once per month-end.

**It runs in Claude's workspace, not on the computer** — it needs no prices
and no Trading 212 export. With the user's own repo attached (`<owner>/<name>`,
`SKILL.md` → Your files):

```
git clone --depth 1 -b holdings-data    https://github.com/<owner>/<name> "$SCRATCH/holdings"
git clone --depth 1 -b holdings-history https://github.com/<owner>/<name> "$SCRATCH/history"
python3 scripts/fund_holdings.py changes --holdings-dir "$SCRATCH/holdings" --history-dir "$SCRATCH/history"
```

Each fund's current file is compared with the newest snapshot at least 7
days older than it. A fund without one prints `Not available` with when its
history starts — expected for the first week after the job began writing,
and for a fund whose file was refused.

| Fund | Since | Companies | Added | Dropped | Largest moves (pp of fund) |

Weights are % of the fund as each issuer's file states them, not portfolio
weights. A move is a change in a company's weight in the fund; it carries
price moves and index changes together, and nothing in the table or near it
says which (rule 7). `0` added, `0` dropped and `none` moved is a valid row
(rule 10). `PROOF` re-adds each fund: the change in its equity weight equals
the moves plus the added minus the dropped, with every addend printed.

TER changes are not in holdings files; a fund's TER over time comes from its
factsheets, and a fund brief's `What changed` table carries it.

**Checks before a file is used** (any failure makes that fund
`Not available` with the reason, and every pair that needs it says so):
the file names the fund's own ISIN where it carries one; one as-of date
across its rows; the row count matches the issuer's stated total where it
gives one, and a paged response is refused; at least 20 equity rows (a top
10 is not a full file); all rows' weights sum to 97–102% of the fund (EIMI's
rounding to 0.01 over ~3,000 rows loses up to ~1.7pp; on 2026-10-10, 1,227
of its 2,957 equity rows read `0.00` and its rows summed to 98.23).

**When the `holdings-data` branch cannot be read** (no GitHub access this
session, or the branch is missing) or carries no usable file for a fund, fall
back to factsheet top 10s for that fund, labelled partial, with the reason in
`METHOD`. Do not move the files through the browser and the conversation
instead: ~5,000 rows per run is too much to carry by hand and cannot be
checked.

### Stocks table

One row per **individual stock in the set**, the same set the Performance
table uses: each stock the request names, or, for "my portfolio", each stock
in `holdings.csv` with kind `stock` (or `portfolio.md`'s stock pie), in that
file's order. A request that names only
funds has no stocks in its set and the table reads `none`. Held or not decides
nothing, as it decides nothing for Performance.

```
Stocks
| Ticker | Company | Next earnings | Latest periodic | Filed | 8-Ks, 30 days |
|---|---|---|---|---|---|
| AAA | Company A | 2026-10-29 | 10-Q, period 2026-06-27 | 2026-08-01 | 2 (2026-09-12, 2026-09-03) |
| BBB | Company B | Not available — not announced | 10-K, period 2026-01-25 | 2026-02-26 | 0 |
```

Cell formats, each checked by `contract.py` → `stocks_table_problems`:

- **Next earnings** — an ISO date on or after `Data as of`, or `Not available —`
  and the reason. A date before `Data as of` is the last report, not the next,
  and is never printed here.
- **Latest periodic** — `10-K` or `10-Q` (a `/A` amendment keeps its suffix),
  a comma, then `period` and the period-end date. Nothing else: no segment,
  no figure, no description of what the filing says.
- **Filed** — the EDGAR filing date of that filing, on or before `Data as of`.
- **8-Ks, 30 days** — `0`, or the count followed by each filing date in
  brackets, newest first. Window: the 30 calendar days up to and including
  `Data as of`, by EDGAR filing date. The item numbers and what the 8-Ks
  announce stay in the filings; a count is a fact and a summary is a story
  (rule 7).

`METHOD` carries two lines for this table, labelled exactly as below —
`stocks_table_problems` reads them by label:

```
Stocks window:     8-Ks filed in the 30 days to [Data as of], by EDGAR filing date
Earnings dates:    company-announced only, never estimated
```

A set with no stocks prints `Stocks window:     none — no stocks in the set`.
`8-K window` is the name of the `PROOF` check, not a `METHOD` label.

**Where the dates come from.**

- *Earnings date* — the company only: a press release or its investor
  relations events page, issuer-published material in `RULES.md` rule 4's
  order. A date that only a data provider shows is not confirmed, and the
  cell reads `Not available — not confirmed by the company`. A date
  extrapolated from last year's pattern is a forecast (rule 8) and is never
  printed. `references/market-context.md` → Earnings calendar reports the same
  dates; one fetch serves both.
- *Filings* — SEC EDGAR, the company's submissions record
  (`data.sec.gov/submissions/CIK<10-digit>.json`), read from the same index
  `references/stock-brief.md` → Step 1 names. The CIK is resolved from the
  ticker through SEC's own ticker file and the entity name in the submissions
  record has to match `portfolio.md`'s Company — never resolved by name alone.
  A stock not on EDGAR prints `Not available — not on EDGAR` in the three
  filing columns and gets its dates from the issuer's own page.

**Where the Stocks table's data comes from.** Checked live on 2026-10-01.
Same terms as Where fund prices come from below: *browser* means the
built-in browser on the user's computer.

| Ticker | CIK (SEC ticker file) | EDGAR submissions | Earnings date page |
|---|---|---|---|
| AAPL | 0000320193, `Apple Inc.` | *browser* — 200 | `investor.apple.com/investor-relations/default.aspx` (*browser*) |
| NVDA | 0001045810, `NVIDIA CORP` | *browser* — 200 | `investor.nvidia.com/events-and-presentations/events-and-presentations/default.aspx` (*browser*), `Upcoming Events` |
| GOOGL | 0001652044, `Alphabet Inc.` | *browser* — 200 | `abc.xyz/investor/` (*browser*), a `Date of … Financial Results Conference Call` release |

**EDGAR is browser-only.** `data.sec.gov` refuses both shells (the cloud
workspace's and the user's computer's) at the proxy, so it is fetched from a
tab on `data.sec.gov`: open one submissions URL with `preview_start`, then one
`fetch()` loop over the three CIKs from that tab, parsing
`filings.recent` (`form`, `filingDate`, `reportDate`, `items`) in the page.
WebFetch reached the file but summarised it: on 2026-10-01 it dropped the form
types and offered a Form 4 dated 2026-09-29 as the latest periodic report. It
is never a route for this table. Without the browser, the three filing columns
read `Not available (browser route down)`, as the performance rows do.

**Earnings dates come late.** On 2026-10-01 none of the three pages showed
the coming quarter's date. Apple's page listed only FY26 Q3 results, NVIDIA's
`Upcoming Events` was empty and its last results event was 2026-08-26, and
Alphabet's newest release was its Q2 2026 call-date notice. All three printed
`Not available — not announced`, which is the correct output, not a failed
fetch. The dates are announced a few weeks before each report.

### Where fund prices come from

Checked live on 2026-09-28 across two Mode C runs and a source check. Same
terms as `references/market-context.md` → Where the closes come from: a
record of reachability, and *browser* means the built-in browser on the
user's computer, which works only while it is on with the Claude app open.

**The listing is the one the user's broker trades.** From any other broker,
it is the listing `references/any-broker.md` settled with the user (the
exchange or currency asked about when a ticker had several). A UCITS
ETF is listed on several exchanges in several currencies, and each listing
is its own instrument (market-context → Closes). A Trading 212 export's
`Currency (Price / share)` column states which: never resolve it from the
ticker alone. The first Mode C run of 2026-09-28 put MEUD on Euronext
Paris; the export prices it in GBX, which is London.

**Order: the exchange, then Yahoo's chart data to confirm.** The exchange
that publishes a close outranks anyone repeating it, so each row's close
comes from its exchange first and Yahoo's chart data is the second source
that makes it checked. A run that takes every close from Yahoo alone has
skipped the first rung, and its rows are `single source` for that reason.

| Ticker | ISIN | Listing | Yahoo symbol | Exchange route (first) | Also |
|---|---|---|---|---|---|
| SPPW | IE00BFY0GT14 | Xetra, EUR | `SPPW.DE` | Deutsche Börse (*browser*) | SSGA fund page closing price |
| VUSA | IE00B3XXRP09 | LSE, GBP | `VUSA.L` | LSE instrument data (*browser*) | Vanguard price history (WebFetch) |
| EIMI | IE00BKM4GZ66 | LSE, USD | `EIMI.L` | LSE instrument data (*browser*) | — |
| MEUD | LU0908500753 | LSE, GBX | `MEUD.L` | LSE instrument data (*browser*) | — |

On 2026-09-28 every pair agreed exactly: SPPW's Yahoo series matched
Deutsche Börse's Xetra closes on each of the seven sessions checked
(46.471 … 47.167, then 47.054), EIMI's 2026-09-25 close matched the LSE's
previous reference price (55.51), MEUD's last close matched the LSE's
(27,052.5 GBX), and VUSA's 2026-09-25 close matched Vanguard's (110.43
GBP).

**Deutsche Börse** (Xetra listings). `boerse-frankfurt.de/etf/<isin>`
redirects to the fund's page on `live.deutsche-boerse.com`. On the
overview, `Schlusspreis des letzten Handelstages` is the latest session's
Xetra close once that session has ended (47.054 on 2026-09-28), and it is
the latest close to use. The `Kurshistorie` view
(`…/kurshistorie/historische-kurse-und-umsaetze?currency=EUR`) is the dated
table of earlier sessions, `Schluss` column; it gains the latest session
the next morning, so on a session evening the overview has a close the
table does not yet. Ignore the overview's `Letzter Preis` and
`Differenz zum Vortag`: they track the extended-hours price, not the close.

**LSE instrument data** (LSE listings). The instrument page
`londonstockexchange.com/stock/<TIDM>/<issuer>/company-page` loads
`api.londonstockexchange.com/api/gw/lse/instruments/alldata/<TIDM>`:
`lastclose` with `lastclosedate`, `currency`, and `previousreferenceprice`,
the exchange's own reference price for the session before. Those answer a
one-session period (the Mode C default) as published figures. Fetch the
endpoint from a tab already on `londonstockexchange.com` (one `fetch()`
loop covers all three TIDMs); from another origin it fails, which is why
the 2026-09-28 run had no LSE data. On 2026-09-29 it returned the
2026-09-28 closes: VUSA 109.7675 GBP, EIMI 54.73 USD, MEUD 27,052.5 GBX. The LSE gives
no dated history outside a token-protected widget, so a longer period's
base close comes from Yahoo's chart data below.

**Yahoo's chart data** (*browser*):
`https://query1.finance.yahoo.com/v8/finance/chart/<symbol>?range=10d&interval=1d`
(a wider `range` for longer periods). JSON: `meta.currency`,
`meta.exchangeName`, and one close per session in
`indicators.quote[0].close`, each at a `timestamp` that is the session's
open — take the date from it. Check `meta.exchangeName` is the listing's
exchange (`GER` for Xetra, `LSE`) and `meta.currency` its currency before
using a value: `GBp` is pence, the same unit as GBX. Closes carry float
noise (47.05400085449219): print them at the exchange's own precision
(Xetra 3 dp, LSE as the exchange quotes). Yahoo's *history pages*
(`finance.yahoo.com/quote/<symbol>/history/`) are a different thing and
were dead ends — 404 or weeks stale — on the same day the chart data was
correct.

Two gaps in the chart data. A completed session can be `null`: on
2026-09-29 all four series held `null` for 2026-09-28. And the series
carries a row for **today** while the session is still open, whose value
is an intraday price, not a close. So a Yahoo value is used only for a
session that has closed and only when it is a number; the end close for
the latest session comes from the exchange (LSE `lastclose` with its
`lastclosedate`, Deutsche Börse's `Schlusspreis des letzten
Handelstages`), with Yahoo confirming only where it has the number.

**Distributions** (VUSA, and the stocks). Vanguard's own history is
`vanguardinvestor.co.uk/investments/vanguard-s-and-p-500-ucits-etf-usd-distributing/distributions`
(*browser*: the table is rendered by script, WebFetch sees an empty page).
It lists each distribution's amount in USD with ex, record and payable
dates — quarterly, ex-date in the third week of March, June, September and
December; on 2026-09-29 the latest was USD 0.3096, ex 2026-09-17, payable
2026-09-30. Yahoo's chart data with `&events=div` (and a `range` that
covers the period) returns `events.dividends`, each `{amount, date}`, the
amount in the listing's currency: VUSA.L gave GBP 0.23187 on 2026-09-17,
the same ex-date as Vanguard's.

**Longer periods.** SPPW: Deutsche Börse's table, confirmed by Yahoo.
VUSA: Vanguard's history, confirmed by Yahoo. EIMI and MEUD: Yahoo's chart
data is the only dated history found, so their base closes are
`single source` unless the base session is also the LSE's previous
reference session.

**Without the built-in browser.** When the user's computer cannot be
reached, every route in the table above is down except WebFetch pages,
and none of those carries the held listings' closes: Yahoo's chart data
refuses WebFetch (robots.txt), and on 2026-09-29 stockanalysis.com's
history pages had VUSA with 15–24 September missing, EIMI labelled GBP
(it trades in USD) and MEUD stopping in July. So the run goes ahead, and:

- Performance rows print `Not available (browser route down)`. Never fill
  one from **another listing** of the same fund — Xetra EUR for a fund
  held on the LSE — or from an aggregator. A different listing is a
  different instrument in a different currency (above): on 2026-09-29 a
  session without the computer printed EIMI at +3.15 from its Xetra EUR
  listing where the held LSE USD listing moved +1.56.
- Comparison, Structural and Holdings still run from factsheets over
  WebFetch.
- `STATUS` is partial, and `METHOD` says the closes need the Claude
  desktop app open on the user's computer, then a re-run.

**justETF is not a close for any listing.** Its chart series
(`justetf.com/api/etfs/<isin>/performance-chart`) states no venue,
converts to whatever currency is asked for, and repeats the last value
over weekends; against Xetra closes for SPPW it differed by up to about
0.5%. It neither supplies nor confirms a close.

**Dead ends, as of 2026-09-28:** the LSE's `XD` flag as an ex-date (it
outlasts the ex-date: market-context → Distributions inside the period),
third-party dividend tables for amounts (stockanalysis.com had VUSA's June
2026 amount wrong), stockanalysis.com and Stoculator price histories
(gaps, wrong currency, other listings), Yahoo Finance history pages for all four
(404 or stale), FT markets data (blocked), stooq (robots.txt),
stockinvest.us for VUSA.L (latest row 2026-07-20), Investing.com ETF
history pages (stale by weeks).

### Fund facts: factsheet first, justETF only as a labelled fallback

**A factsheet's figures are read from its text, never from a WebFetch
summary.** Open the PDF in the built-in browser and read its text, or
download it and extract the text in a shell. WebFetch may find the URL;
it never supplies a figure. It summarises, and on 2026-10-03 two runs
WebFetched the same SPDR factsheet and were given two different top-10
totals (30.67% and 31.67%), neither printed in the document. A figure
WebFetch reports is a lead to check against the text, the same rule as for
EDGAR above. Without the browser or a shell that can reach the issuer, the
cell is `Not available (browser route down)`.

TER, fund AUM, holdings count and the top 10 come from the issuer's
factsheet or KID (rule 4, rank 2), the same as in Mode A. justETF is a data
provider (rank 3): use it only for a fund whose factsheet could not be
read, name the failed factsheet fetch in `METHOD`, and mark each figure
taken from justETF with its source in the cell. **AUM states what it
measures** — `fund` or `share class` — and in the fund's base currency:
on 2026-09-28 one run printed VUSA's AUM as USD 89,226m (fund, factsheet)
and the next as EUR 46,776m (justETF), two different measures under one
column heading. Figures of different kinds never share a column unmarked.

`METHOD` names the weights consumed and their single as-of date, the
holdings depth per fund, the period resolution applied, and, where the
Allocation table could not price every holding, that the look-through was not
computed and why. `PROOF`
carries the per-fund weight sums, each Performance row's base and end close
with its period % re-derived from them, and the reconciliation of each
look-through row against the weights that produced it.

**No "what this implies" section, in any section.** After `RESULT` the
output continues into `METHOD`, `PROOF` and `SOURCES` because those are
evidence. They are not a place to reintroduce interpretation: "double-
counts", "creates an ambiguous split", "adds exposure without intersection"
are forbidden by rule 6 wherever they appear, and the restructure does not
open a new room for them.

The look-through's weights are the Allocation table's `Weight (market)`.
When those are `Not available`, so is the look-through, with the same reason —
never computed on `pies.md` targets, on cost weights, or on equal weights.
For a set the user named rather than the portfolio, ask for the weights
instead of assuming any.

### Which weights are admissible

The look-through multiplies a portfolio weight by an issuer holdings weight
and reports the product as current single-company exposure. That claim is
only as good as the weights it consumes, so two kinds are refused:

**Cost-basis weights are not admissible.** `references/portfolio-sync.md`
weights its tables on cost basis, which is the right basis there — uniform,
reproducible, nothing fetched. It records where money went, not what the
user is exposed to now. The two diverge by the price drift since purchase,
and the divergence is systematic: a position that has appreciated is
understated by cost weighting at the same time as its issuer weight has
grown. A cost-weighted look-through therefore misstates issuer exposure in a
predictable direction while reading as measured.

**Weights with mixed as-of dates are not admissible.** A column valuing each
position at whatever price it last happened to trade at dates every row
differently. It is not a snapshot, has no date to declare in the header, and
cannot be reproduced by a reader.

Admissible input is market weights carrying **one as-of date for the whole
portfolio**, each position priced from a named source per `RULES.md` rule 4
— `portfolio-sync.md` → Mode M produces these, and so does the Allocation
table above: in Mode C the look-through takes each holding's `Weight
(market)` from it. When Allocation's weights are `Not available`, so is the
look-through, with the same reason. Where a position cannot be
priced to the common date, it is `Not available` and named, and the
look-through states which names are missing rather than proceeding on a
partial set or falling back to cost.

Report the numbers. Whether a given overlap is appropriate depends on the
user's intent, which this skill does not know and does not guess.

---

## Document handling rules

**Past performance sections are skipped** unless explicitly requested. They
lead every factsheet and describe nothing about how the fund is built.

**Holdings counts are reported with concentration.** "1,500 holdings" and
"top 10 = 25%" belong on the same line. State both; do not editorialize.

**Synthetic replication is reported neutrally** — method and counterparty,
no characterization as risky or safe.

**Cost figures**: the KID gives both an annual percentage and cumulative
costs in currency over holding periods. Never conflate them; label which.

**Stale documents**: if the newest document for a fund is over 12 months old,
flag it. TER rarely moves; AUM and holdings do.

---

## Validation — run before output, fix before shipping

These checks catch the errors that actually occur. A failed check is fixed at
source, not disclosed as a caveat.

### Arithmetic

- **Top-10 weights must sum to the stated top-10 total.** Add them. If the sum
  and the stated figure differ by more than 0.1pp, re-read the document —
  one of the two is misread. Never publish both.
- Sector and country weights: note if they sum to something other than ~100%
  and state why (cash, other, rounding).
- Any percentage over 100 or under 0 is a parse error, not a finding.

### Implausible values

Treat these as probable errors and re-verify before output:

- **A cost figure of exactly 0.00%** — transaction costs are rarely truly
  zero. Re-read the KID cost table; check whether the figure was rounded from
  a small non-zero number or belongs to a different row.
- **A risk indicator that contradicts the fund's universe** — a
  single-country large-cap fund scoring higher than a global multi-country
  fund is usually a sign the wrong share class or the wrong document was
  read. Re-resolve by ISIN and confirm the share class before reporting.
- **A TER far outside the 0.03–0.75% band** for a mainstream index tracker.
- **AUM that differs by an order of magnitude** from the fund's own page.

### Document conflicts

When two documents give different values for the same field, output both
explicitly:

`Risk indicator: 6/7 (KIID, 17 Feb 2026) — factsheet (31 Aug 2026) states 4/7. Conflict unresolved; KIID ranks higher per RULES.md Rule 4.`

Do not resolve silently, and do not present the higher-ranked value alone. A
conflict is itself information: it usually means one of the two documents was
fetched for the wrong share class.

### Share class verification

Before reporting any fund, confirm the ISIN in the fetched document matches
the ISIN being briefed. Issuers publish separate documents per share class
and their pages cross-link heavily. If the document's ISIN differs, the fetch
was wrong — discard and re-fetch.

---

## Out of scope

No performance or return comparison. No suitability or "which is better"
conclusion. No tax advice — domicile, share class and distribution policy are
reported as facts; their treatment under any tax regime is out of scope. No
forecasts of fees, flows, or index changes.

**No "what this implies" section.** `RESULT` ends the answer. Phrases like
"double-counts", "creates an ambiguous split", "adds exposure without
intersection" are interpretation wearing descriptive clothing. The structural
overlap table already states which universes intersect; restating it as
consequence is the beginning of a recommendation and is forbidden by Rule 6.

`METHOD`, `PROOF` and `SOURCES` follow `RESULT` because they are evidence,
and the sections are not a place interpretation may re-enter. A sentence
that would be forbidden beside the table is forbidden below it.

If the user wants interpretation, they will ask — and it is theirs to make.

---

## Self-check

RULES.md Part IV checklist, plus:

- [ ] Sections present, in order (`PROOF` when asked for or halted), with the subject line above
      `STATUS` carrying ticker, legal name, ISIN and share class
- [ ] `CONTEXT` is the five mandated fields and nothing else
- [ ] ISIN in each fetched document matches the ISIN being briefed
- [ ] Every figure traces to a named document and date
- [ ] `RESULT` holds tables only — fund facts, top 10, sectors, countries —
      one per question, with no method note or caveat between them
- [ ] Holdings count and top-10 concentration in the same table
- [ ] Columns empty for every row suppressed, and named in `METHOD`
- [ ] Each column at its own precision, trailing zeros dropped — a TER of
      `0.20` prints `0.2` where the KID states two decimals
- [ ] **Top-10 weights summed in `PROOF` with addends, reconciled against
      the stated total**
- [ ] **Any 0.00% cost figure re-verified against the KID cost table, and
      the re-verification reported in `PROOF` whether or not it changed**
- [ ] **Risk indicators sanity-checked across funds; conflicts shown in
      full in `PROOF`, both values, neither resolved**
- [ ] `METHOD` names the risk regime (SRI or SRRI), the cost basis, the
      replication basis, and — in Mode C — the weights basis with its
      single as-of date and the overlap depth per fund
- [ ] TER labeled as annual percentage
- [ ] Holdings carry as-of dates in the table, sources in `SOURCES`
- [ ] Mode C `Countries` is `scripts/fund_holdings.py`'s table, pasted
      unchanged, with its `Countries basis` line in `METHOD`
- [ ] Mode C `Holdings` and `Look-through` are `scripts/fund_holdings.py`'s
      tables, pasted unchanged; a fund at top-10 depth is named in the
      heading and in `METHOD` with the reason its full file was not used
- [ ] Index universe stated in plain terms for each fund
- [ ] `RESULT` opens with the Mode line
- [ ] Mode B prints its four tables — index facts, top 10, countries,
      sectors — with the country depth named in `METHOD` and the sector
      scheme either quoted from the document or `Not available`
- [ ] Mode B uses provider documents only; each Index facts row names its
      source document, down the ladder methodology PDF → provider HTML
      page → factsheet Quick Facts, with every failed rung in `METHOD`
- [ ] Mode B flags `stale` per row for a field from a document over 12
      months old — not one note for the brief
- [ ] Mode B lists the return versions the provider publishes, and no
      claim about which one funds track
- [ ] Mode B tables the dated factsheet covers print from it; undated
      depth is its own table headed `(undated)`, and `METHOD` names which
      table came from which document
- [ ] Mode C prints the asked-for tables (all twelve tables on a full report), a set of one included, names them on `METHOD`'s `Tables:` line, and its
      Performance rows are the instruments in the set — never filtered by
      whether they are held
- [ ] Stocks table: a stock's earnings date is company-announced and on or
      after `Data as of`, else `Not available —` with the reason; the
      periodic filing is a bare form and period; the 8-K cell is a count with
      its dates, newest first, inside the 30-day window; a run with no stocks
      in the set prints `none` and `Coverage` does not count the table
- [ ] Structural overlap is its own table, separate from holdings overlap
- [ ] Portfolio weights either supplied by the user or their absence stated
      in `METHOD`
- [ ] Missing fields written as `Not available` in `CONTEXT`
- [ ] `SOURCES` carries publication date and retrieval timestamp per row
- [ ] No verdict, ranking by quality, or suitability language — in `RESULT`
      or in any section after it
- [ ] **`RESULT` ends the answer — no implications or takeaways, and none
      smuggled into `METHOD` or `PROOF`**
