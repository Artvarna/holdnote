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

`RESULT` follows `references/brief-layout.md`: the Mode line
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

**Quick brief** (`references/brief-layout.md` → Quick brief). Only the
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

In `references/portfolio-view.md`: the Comparison, Overlap, Allocation,
Holdings, Look-through, Holdings changes and Stocks tables, Which tables a
question gets, Where fund prices come from, Fund facts and Which weights are
admissible. Read it for any portfolio, overlap, look-through or "what do I
own" question; a fund or index brief does not need it. Older pointers of the
form "etf-brief.md → Mode C → X" mean section X of that file.

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
