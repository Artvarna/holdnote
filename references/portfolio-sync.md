# Portfolio Sync

Reference for BuffettBot (`buffettbot`). Follow `RULES.md`.

Rewrites `portfolio.md` from a Trading 212 CSV export. The only module that
writes to a file the user maintains by hand, so it is the one with the most
ways to destroy work quietly: a mis-parsed column does not raise an error, it
lands a wrong weight in the file that every other module then reads as fact.

The default mode is arithmetic on rows in the export and nothing else. It
fetches nothing, recalls nothing, and ends at the table.

## What it may not do

- **No fetching in the default mode.** If a number is not reconstructable
  from the export's own columns, it is `Not available`. Market prices are
  available only in Mode M (below), which is opt-in and says so on the
  `Currency / units` line of `CONTEXT` and in `METHOD`.
- **No valuation from memory, in any mode.** A share price that feels right
  is the exact failure `RULES.md` rule 1 exists to prevent.
- **No commentary on the result.** No drift-from-target reading, no
  concentration note, no "the stock pie has grown". The module prints the
  measured allocation and stops. A difference in percentage points printed
  as a number (`Diff (pp)` in etf-brief → Allocation table) is arithmetic,
  not a reading; a word about it is. Comparing it against target is the user's
  read, and an overlap question goes to `references/etf-brief.md` → Mode C.
- **No editing of prose.** The Look-through and Watchlist sections and every
  sourced note in `portfolio.md` are carried across unchanged. This module
  owns quantities, cost bases, weights and the `Last updated` stamp. Nothing
  else.

## Step 1 — Read `OWN_FROM` from `portfolio.md`

A shared account can hold positions that predate the user's involvement.
The date from which a transaction is theirs is a field in `portfolio.md`
(for an account that is only theirs, the day it opened):

```
OWN_FROM: 2026-01-05
```

Read it from the file every run. Never hardcode it, never carry it over from
an earlier run in the session, and never infer it from the first deposit in
the export — the export is the thing being checked against it.

If the field is missing, or is not an ISO `YYYY-MM-DD` date, halt. Do not
fall back to a default: a wrong cutoff silently reassigns someone else's
shares to the user, and the output looks entirely normal when it does.

`ownership.md` carries the same date on its `Cutoff:` line, alongside the
narrative of what the cutoff cannot resolve and the declared pre-cutoff ISIN
list. The two dates must agree. On disagreement, report both and halt —
`RULES.md` rule 4: a conflict is surfaced, never resolved by picking one.

## Step 2 — Parse the export

`docs/t212-csv-schema.md` is the schema as actually observed in this
account's export, re-derived from the file rather than from documentation.
Read it before parsing anything, and treat its numbered findings as the
specification. `scripts/t212_holdings.py` already implements them and is the
arithmetic engine for this module; the fields below are what it extracts.

| Field | Column | Notes |
|---|---|---|
| Action type | `Action` | subtype in brackets — match the prefix, not equality |
| Date | `Time (UTC)` | carries an explicit `+00:00` offset |
| ISIN | `ISIN` | the identity key; the ticker is not |
| Ticker | `Ticker` | display only, and it changes across venues |
| Quantity | `No. of shares` | on a dividend row this is the holding, not a movement |
| Price | `Price / share` | can be quoted in `GBX` (pence) |
| Currency | `Currency (Price / share)`, `Currency (Total)` | two different currencies on one row |
| FX rate | `Exchange rate` | direction is *tested per row*, never assumed — see below |

### The exchange rate direction is decided per row, by reconstruction

Do not key the FX direction off the `Action` value. A rule that says
"dividends multiply, trades divide" encodes one export's convention as a
law, and it fails silently the day Trading 212 changes it or emits a subtype
the rule has never seen — silently, because the wrong direction still
produces a number.

For every row carrying a quantity, a price and a rate, compute both:

```
divide    = quantity × price ÷ Exchange rate
multiply  = quantity × price × Exchange rate
```

Compare each against the row's stated `Total`, in the `Currency (Total)`
unit, and keep the direction that reproduces it **within 0.01**. The stated
`Total` is the authority; the reconstruction is the test.

- Exactly one direction matches → use it for that row.
- Both match → the rate is 1, or near enough that direction cannot change
  the answer. Either is correct. Record the row as `both` in the audit
  tally rather than treating it as ambiguous.
- Neither matches → **halt**, naming the file, line number, ISIN, both
  computed values and the stated `Total`. Do not fall back to a default
  direction, and do not widen the tolerance to make it pass. A row whose
  `Total` cannot be reconstructed from its own columns is a row this module
  does not understand, and the correct output is that fact.

Keep the per-direction tally per row kind and print it in `METHOD`. A
future export that flips its convention then shows up as a changed tally,
which is visible, instead of as a shifted weight, which is not.

The `0.01` tolerance is the rounding in the `Total` column itself, not slack
for a near-miss. A GBX price needs no ÷100 rescale, because the rate is
quoted per GBX — but that is a conclusion the reconstruction reaches on its
own, not a special case to code.

### Row kinds

**`Market buy` / `Market sell`** — the only rows that move quantity, signed
by side. `Result` is populated on sells only, and is the realised result in
the `Total` currency.

**`Dividend (…)`** — cash only. Never touches quantity. The parenthesised
subtype varies (`(Dividend)`, `(Dividends paid by us corporations)`,
`(Dividend manufactured payment)`), so match on the prefix before the
bracket. `No. of shares` is the position the dividend was paid on, not a
movement; adding it to quantity inflates the position. These rows also have
an empty `ID`, so a dedup keyed on `ID` alone collapses every dividend in
the file onto a single row.

**`Deposit`, `Withdrawal`, `Interest on cash`, `Currency conversion`** —
cash, no ISIN, no quantity. They enter no position. They are worth parsing
anyway: a deposit is usually what `OWN_FROM` was derived from, and a
`Currency conversion` row marks the Total-currency change described below.

**Pie rows.** There is no pie column in this export, and no pie-specific
`Action` value has appeared in it — `docs/t212-csv-schema.md` records the
six that have. Trading 212 does emit pie-related rows in some accounts, so
classify by shape rather than by a guessed label list:

- An unrecognised `Action` with **no ISIN and no quantity** is cash-only. It
  cannot move a position. Count it nowhere, and name it on the run's
  `Not available` line so it is visible rather than silently dropped.
- An unrecognised `Action` **carrying an ISIN or a quantity** halts the run,
  naming the value and the row. It moves shares in a shape this module has
  never seen, and guessing its sign is how a position ends up wrong.

Pie *membership* is not in the export at all. `pies.md` is the mapping,
maintained by hand, and a held ISIN listed nowhere in it halts the run.

### Rows before `OWN_FROM`

A row whose UTC date is earlier than `OWN_FROM` is the account holder's.
Exclude it from quantity, cost basis, income, realised results and weights.
Keep it as evidence: it is what establishes that a position existed at the
cutoff, which changes how that position is treated in Step 3.

Compare dates in UTC. The timestamps carry `+00:00`; a local-time comparison
moves rows across the boundary near midnight and reassigns their ownership.

## Step 3 — One chronological pass: lots and cash

A position already open on `OWN_FROM` holds an unknown mix of the account
holder's shares and the user's. Selling an inherited share and selling a
bought one are the same row in this export, so no rule recovers the split
from the data — one has to be chosen, and the choice is labelled wherever
its output appears. `docs/fifo-attribution.md` holds the rule, a worked
trace, and the bound argument.

The lot walk produces the ownership split, and **every figure derived from a
position is attributed through that same split**. Attributing quantity by
FIFO and then booking the position's whole dividend and whole realised gain
to the user contradicts the attribution in the same table: it credits income
to shares the module has just said are not theirs.

**Run the lot book and the cash ledger as a single forward pass over all
rows in timestamp order.** They are not two walks. Sale proceeds and
dividends from the lot book are inflows to the cash ledger, and which pool a
purchase draws on decides the owner of the lot it creates. Running them
separately — lots first, cash after — gives an answer that looks complete
and is wrong, because each pass needs the other's output as input.

### The lot book

Buys append a lot. Sells consume lots oldest first. What remains tagged
`mine` is the user's quantity.

A buy dated **before** `OWN_FROM` appends a `holder` lot. A buy dated on or
after it is tagged by **which cash funded it**, not by its date — see below.
Date alone is the wrong test: it says a purchase is the user's because it
happened during their tenure, which is a claim about the calendar, not about
whose money bought the shares.

### Attribution policy — funding-based or date-based

Two policies are specified. **Funding-based is the default.** Whichever ran
is printed in `METHOD`, because the same export produces materially
different positions under each, and a table that does not say which one
produced it cannot be compared against last month's.

**Funding-based** — a post-`OWN_FROM` purchase belongs to whoever's cash
paid for it, resolved by the FIFO ledger below. A buy funded from the
holder's sale proceeds is the holder's position, whatever its date.

**Date-based** — every purchase dated on or after `OWN_FROM` is the user's,
and funding is not examined. This is the simpler rule, it is what a reader
naively expects "my transactions" to mean, and it is the policy the module
used before the ledger existed.

Neither is a fact about who owns what. They are conventions, in the same
sense that FIFO and LIFO are conventions — `docs/fifo-attribution.md` makes
that argument and it applies here unchanged.

**The consequence of the default, stated plainly: funding-based attribution
lets the holder's share compound.** Their sale proceeds buy new lots that
are theirs; dividends on those lots return to their pool; that cash funds
further purchases that are also theirs. A holder who never deposits another
euro can hold a growing share of the account indefinitely, and the user's
share is bounded by their own deposits plus their own income. That is the
honest reading of "whose money bought this", and it is also the reason the
policy is worth stating rather than assuming: a user who considers the
account's post-cutoff activity to be theirs regardless of which cash it drew
on wants `--attribution-policy date`, and should get it without argument.

Date-based has the mirror-image distortion: it awards the user every
post-cutoff purchase including those funded entirely by the holder's
proceeds, which is how the 630.25 EUR gap in this module's own worked
example arose. Both distortions are reported, neither is corrected for.

### The cash ledger

Used by the funding-based policy. Under date-based it still runs, and its
output is reported as a provenance note, but it does not decide ownership.

The date test attributes securities and leaves funding unexamined, and the
two can disagree badly. A purchase made after `OWN_FROM` out of the
holder's sale proceeds is the holder's position by any reading; booking it
to the user because of its timestamp hands them shares they did not fund.

Maintain two pools of dated, owner-tagged cash:

**Inflows.**

| Row | Pool |
|---|---|
| `Deposit` dated on/after `OWN_FROM` | mine |
| `Deposit` dated before `OWN_FROM` | holder |
| Dividend | split per the income rule below, each part to its owner's pool |
| Sale proceeds | split by the quantity the sell took from each owner's lots |
| `Interest on cash` | split by each pool's balance at the interest timestamp |
| `Withdrawal` | a negative inflow, drawn by the same FIFO rule as a purchase |

**Draws.** A purchase consumes cash from the pools, and the proportion drawn
from each sets the lot's ownership: a purchase funded 60/40 from mine and
holder cash creates a lot 60% mine and 40% holder, at one unit cost. A
purchase drawing entirely on holder cash creates a wholly `holder` lot, even
though it is dated well after `OWN_FROM`.

*Which* cash it draws is a separate policy, specified next.

### Cash consumption policy

**This is its own policy, independent of lot FIFO, and it must be declared.**

Lot FIFO is a real accounting method: shares are distinguishable, a lot has
an identity and an acquisition date, and consuming the oldest one first is a
convention with a long history and a legal meaning. **Cash has none of
that.** Euros in a brokerage balance are fungible. There is no oldest euro,
no lot, and nothing in the account that records which deposit paid for which
purchase. "Oldest euros first" is not an accounting standard applied to
cash — it is a convention this module invented by analogy, and the analogy
does not hold.

It is also the largest single lever in the module. Against this module's own
worked example, a `HOLDER_CASH_AT_OWN_FROM` of 500.00 EUR moves AAPL from
3.0000 shares to 0.6190 under cash FIFO — 38.6% to 13.0% — on shares bought
seven months after the cutoff. A convention that swings a third of the
portfolio on one declared estimate cannot be left implicit.

| Policy | A purchase draws | Bias |
|---|---|---|
| `pro-rata` **(default)** | from each pool in proportion to its balance at that moment | none by construction; dampens the seed |
| `fifo` | oldest inflow first, across both pools | toward the holder — a seed is dated at `OWN_FROM` and so is always drawn first |
| `mine-first` | the user's pool until exhausted, then the holder's | maximal toward the user; the seed cannot affect anything until the user's cash runs out |
| `holder-last` | the holder's pool until exhausted, then the user's | maximal toward the holder |

**Pro-rata is the default because it is what a pooled cash account actually
does.** A balance of 1000.00 of the user's money and 500.00 of the holder's
is one balance of 1500.00; a 630.00 purchase from it takes two thirds and one
third, because that is the composition of what was spent. No ordering is
invented, and no euro is claimed to be older than another.

Its second property matters as much: it is the least sensitive of the four
to a number the user is estimating. Measured against the worked example, as
`HOLDER_CASH_AT_OWN_FROM` moves from `unknown` to 1000.00 EUR, the user's
attributed cost basis moves:

| Seed | `pro-rata` | `fifo` | `mine-first` | `holder-last` |
|---|---|---|---|---|
| unknown / 0.00 | 1000.68 | 1000.68 | 1000.68 | 1000.68 |
| 250.00 | 1000.55 | 1000.41 | 1000.68 | 1000.41 |
| 500.00 | 971.80 | 1000.14 | 1000.68 | 906.72 |
| 1000.00 | 776.21 | 630.93 | 1000.68 | 406.58 |
| **swing** | **224.47** | 369.75 | 0.00 | 594.10 |

`mine-first` shows a zero swing, and that is not a recommendation for it: it
is insensitive because it refuses to let holder cash fund anything until the
user's is gone, which is the same fact as its maximal bias. Insensitivity
earned by ignoring the input is not robustness.

Print the policy in `METHOD` beside the attribution policy. Two runs of
the same export under different cash policies are not comparable, and a
table that does not name its policy cannot be diffed against last month's.

None of the four is a fact about whose money bought what. Like FIFO and LIFO
on lots, and like funding-based versus date-based above, they are
conventions — and where the choice moves the answer materially, the module
reports the size of the move rather than presenting one convention's output
as the measurement.

**Seeding the holder pool.** The export is a window; it does not reach the
holder's cash any more than it reaches their opening positions. So the
opening balance is declared, not derived, in `DECISIONS.md`:

```
HOLDER_CASH_AT_OWN_FROM: unknown        # or e.g. 500.00 EUR
```

`unknown` is the default and seeds nothing. A declared amount seeds the
holder pool dated at `OWN_FROM`.

Declaring a balance moves shares toward the holder and never toward the user
— worth saying, because the intuition runs the other way: a number that
resolves an unattributable gap looks like it should resolve it in the user's
favour. **How far it moves them is decided by the cash consumption policy,
not by the seed alone**, and the two must be read together. Under `fifo` the
seed is the oldest cash in the ledger and is drawn before anything else;
under the `pro-rata` default it is drawn only in proportion to its share of
the balance at each purchase. The sensitivity table in that section gives
the measured spread.

A declared figure is a sourced number like any other: it comes from a
statement, and `DECISIONS.md` carries the statement's date. Never infer it
by back-solving from the shortfall — that fits the balance to the answer and
then reports the answer as measured.

### The indeterminate class

When a post-`OWN_FROM` purchase exhausts both pools, the remainder was
funded from cash the export does not account for. Those shares are neither
the user's nor provably the holder's, and forcing them into either is a
guess presented as arithmetic.

**Positions therefore carry three quantities: `mine`, `holder` and
`indeterminate`.** Indeterminate is a reported class, not an error state and
not a rounding bucket. It is the module's answer to "whose are these", and
the answer is *this export cannot say*.

Report it as its own total, per position and in aggregate, always alongside
the rows that produced it:

```
Indeterminate: 400.00 EUR cost (8.0000 sh), 25.0% of maximum claim
  2026-02-02  ABC    100.00 EUR   2.0000 sh
  2026-03-02  ABC    200.00 EUR   4.0000 sh
  2026-04-01  ABC    100.00 EUR   2.0000 sh
```

The contributing rows are not optional detail. The aggregate says how much
is unresolved; only the rows say *which purchases* the export fails to
explain, and a single missing deposit usually shows up as a shortfall
beginning at one identifiable row. That is what tells the user which wider
export would close it.

A dividend or sale on a position with an indeterminate portion splits three
ways on the same proportions. The indeterminate share of income is reported
and enters no cash pool — routing it to either pool would launder an
unresolved quantity into a resolved one.

**Sells consume lots FIFO across rows and pro rata within a row.** One buy
row can create lots for two or three owners at a single timestamp, and any
ordering imposed among them would be arbitrary and would change the answer.
Taking each owner's portion in proportion avoids inventing a tie-break.

**Cost basis.** The cost of the quantity still held, not the gross of every
buy. Sum the surviving `mine` lots: for each, its remaining quantity × that
lot's unit cost, where unit cost is the buy row's reconstructed `Total` ÷
that row's quantity. A partially consumed lot keeps its unit cost and
carries only its remaining quantity.

**Realised result.** Each sell row is split by the quantity it took from
each owner's lots, and the row's `Result` is apportioned in that
proportion:

```
my share of the row = quantity taken from 'mine' lots ÷ row quantity
my realised result  = Result × my share of the row
```

A sell that consumes only `holder` lots therefore produces **0.00 of
realised result for the user**, and the whole of it for the account holder.
This is the common case for the first sell after the cutoff, and it is the
one that is wrong most often, because the row looks like an ordinary sale of
the user's own position. Sale proceeds are split by the same proportion.

**Income.** Entitlement to a dividend is set at the **record date**, not the
pay date. Whoever held the shares on the record date is owed the payment,
even if they sold before the cash arrived. Splitting by the pay-date
position misattributes every dividend where the position changed in the
window between the two dates — typically two to six weeks, and precisely the
window in which a post-cutoff rebalance lands.

Use the record date where the export gives it. **In the schema as observed,
it does not:** `docs/t212-csv-schema.md` lists all 23 columns and none
carries a record date. So the entitlement base is resolved in this order,
and **the output names which one was used**:

1. **A record date on the row**, if a future export adds the column. Replay
   the lot book to that date and split by the open `mine` / `holder`
   quantities there.
2. **The row's own `No. of shares`.** This is the broker's view of the
   position the payment was calculated on, which is the record-date holding
   — better evidence of entitlement than anything this module derives. When
   it disagrees with the pay-date lot book, prefer it, and split it between
   owners in the ratio the lot book held at the *earliest* timestamp
   consistent with it.
3. **The pay-date open quantity**, labelled
   `(split at pay date — record date not in export)`.

Where sources 2 and 3 agree, say so: the position did not change between
record and pay date, so the distinction does not bite and the split is the
same under either. Where they disagree, report both quantities and the
basis chosen — `RULES.md` rule 4. Do not silently prefer the one that makes
the arithmetic tidier.

Withholding tax on a dividend follows that dividend's split. Interest and
conversion fees follow the pool-balance split at their own timestamps.

**Floors.** Where the export window does not reach a position's opening, the
inherited lot is understated, which sends more selling against the user's
own lots and pushes their quantity too low. That figure is a floor, printed
as `>= x (FIFO, floor)`, never as a plain number. Cost basis, income and
realised result derived from a floored quantity carry the same label.

**`--attribute none`** is the stricter reading: positions spanning the
cutoff carry no quantity, no cost basis, no income and no realised result,
and drop out of the weights entirely. It is available, and it distorts every
weight that remains, because the measured portfolio then covers only part of
the account. Whichever mode ran is stated in `METHOD`.

Positions named in the `Pre-cutoff ISINs` table of `ownership.md` are
excluded regardless of what the arithmetic says. That declaration is
additive — it carries what the user knows about the account that the CSV
cannot express. Disagreement between the declaration and the arithmetic is
reported in both directions, not resolved.

## Step 4 — Weight on cost basis

**Cost basis is the default and only weighting basis in the default mode.**

```
weight = position cost basis ÷ Σ cost bases × 100
```

Cost basis is the one valuation the export can support without fetching
anything: it is the money the user actually put into the position, in the
currency the rows settled in, measured on the same definition for every
position. That uniformity is the property that matters. A basis is usable
for weighting only when every position in the table is measured the same way
and as of the same thing.

**Last-transacted pricing is not a valid basis and is not available.** It
was in an earlier version of this module and it was wrong. Valuing each
position at the last price it happened to trade at dates every position
differently — one at last week, one at four months ago — and a column of
figures with N different as-of dates is not a snapshot of anything. It has
no date to put in `CONTEXT`, it cannot be reproduced by a reader, and it
must never be fed to `references/etf-brief.md` → Mode C, where a look-through
multiplies those weights by issuer holdings to produce single-company
exposure. Stale weights there yield a confidently wrong concentration
figure.

**Every percentage must be reproducible from the column printed beside it.**
The reader must be able to take the cost-basis column as printed, at the
precision printed, divide by the printed total and arrive at the printed
percentage. This is not a presentational nicety — it is what makes the table
auditable by hand, and Step 5 asserts it.

Cost basis and its weights are labelled as such in every table, and the
basis rides on the `Currency / units` line of `CONTEXT`.
`Weight (cost)` is not `Weight (market)`, and the two are never shown in one
column.

**Currency.** The `Total` currency changes mid-history in a Bulgarian
account — BGN for 2025 rows, EUR from 2026-01-01, with a `Currency conversion` row marking
the change. Group every figure by currency and refuse to add across them. If
the positions being weighted do not all carry cost in one currency, the
weights are computed only through a fixed rate declared in the
`ownership.md` policy block (`Fixed rate: 1 EUR = 1.95583 BGN (<source>)`,
the legal BGN/EUR conversion rate). Then the table keeps the per-currency
`Cost basis` and adds a `Cost basis (EUR)` column the weights are taken
from; `CONTEXT` names the rate, `PROOF` shows each restatement and re-adds
the EUR column, and `SOURCES` carries the rate's source. Without a declared
rate, or with a currency it does not cover, the weights are
`Not available — cost bases denominated in {list}, no rate declared in
ownership.md`. They are never computed at a rate recalled from anywhere.

## Step 4b — Mode M: market weights (opt-in)

Requested explicitly, never the default, and never silently substituted for
cost weights.

Mode M fetches a current price per position, following the `RULES.md` rule 4
hierarchy and stopping at the highest rank that answers:

1. Regulatory filings and KID/KIID — for a fund, the issuer's published NAV
2. Issuer-published data — factsheet or daily NAV/price file
3. Data-provider APIs
4. Financial media

### M1 — Resolve a price per position

**One fetch per position, one price per position.** Resolve the instrument
by ISIN, never by ticker: tickers differ by venue, and the same fund trades
under several. Stop at the highest-ranked source that answers; do not fetch
a second source to compare unless the first is ambiguous, and if two are
fetched and disagree, report both and flag it rather than picking one
(`RULES.md` rule 4).

For a fund, the issuer's published NAV is the primary price. An exchange
price for the same fund is a different number — it carries a premium or
discount to NAV — so never mix NAV for one holding with a market quote for
another in the same column. Choose one basis for the table and state it.

Record per position, and print all of it:

| Field | Note |
|---|---|
| Price | as the source states it, no added precision |
| Currency | may differ from the table currency and from cost currency |
| As-of date | the source's own date, not the date of the fetch |
| Source | the document or endpoint, named |
| Basis | NAV or exchange quote — one basis per table |

### M2 — One as-of date for the whole table

The table's as-of is a single date, and every row in it is priced to that
date. Two ways a row can fail that, and they are handled differently:

- **Priceable, but only at a different date** — the source publishes weekly,
  or its latest is older than the table's as-of. The row is dropped to
  `Not available — priced only at [its date], table as-of is [date]`. It is
  not carried at the stale price with a footnote. A footnote is what
  last-transacted pricing was, and mixed as-of dates are exactly what Mode M
  exists to prevent; recreating them inside Mode M with better labelling is
  the same defect.
- **Not priceable at all** — `Not available — [source attempted] returned no
  data`. Never back-filled from cost basis, never carried over from a
  previous run, never estimated from a related instrument.

Both are named in `Coverage`, and both make **their pie's market weights
`Not available`** — every row of that pie, not only the unpriced one — and
with them the combined pie shares. A weight is a share of a total, and a
total with a missing position is not the pie's total: pricing two of four
ETFs and printing SPPW at 73.3% "of the ETF pie" reads as an allocation and
is a ratio between two holdings. The priced rows keep their price, as-of
date and value; only the weight is withheld. A pie whose every row is priced
to the common date prints its weights in full.

Choosing the table's as-of to be the oldest available date across positions
is permitted and must be stated; it trades freshness for completeness, and
the reader needs to know which was traded. The date must not precede the
last trade in the export: quantities are read after that trade, and pricing
them at an earlier close values shares at a price from before they were
held.

### M3 — FX is fetched, never reused

A price in a currency other than the table's needs a rate, and that rate is
**fetched, with its own source and date, and printed**. Never reuse an
`Exchange rate` from a trade row: that is the rate on the day of that trade,
which is the whole reason this mode exists. A rate whose date differs from
the table's as-of is declared as such.

### M4 — Indeterminate quantity

**Market weights obey the same rule as cost weights: with `indeterminate >
0`, they are ranges, not figures**, computed with the same bounds in Step 4.
An unresolved quantity is unresolved whatever it is multiplied by, and a
fetched price does not make it known. Mode M resolves *pricing*, not
*ownership*, and the two are independent — a run can have perfect prices and
still not know whose shares they are.

### M5 — Output

Cost weights are printed alongside market weights, in their own labelled
column, so the two bases are visible together and neither is mistaken for
the other. Both are the answer to the same question — what share of the
portfolio is this — so they stay in one table rather than splitting it.

Print the per-position price, its currency and its as-of date in that table:
a market weight without its price date is the defect this mode was built to
remove, and the date has to travel with the number rather than sit in a
section the reader may not reach. The **source** of each price goes to
`SOURCES`, one row per position, with its retrieval timestamp; the table
carries the figure, not the provenance.

The single as-of date for the whole table also rides on the
`Currency / units` line of `CONTEXT`, since a reader cannot read a market
weight correctly without it.

**Mode C and the look-through require Mode M. Cost weights are not an
acceptable input to either.**

Cost basis records where money went. It is the right basis for the sync
tables, because it is uniform, reproducible and needs nothing fetched. It is
the wrong basis for exposure, and the difference is not a labelling problem
that a column header fixes.

A look-through multiplies a portfolio weight by an issuer's holdings weight
to state single-company exposure — `Apple: 15.13% of portfolio`. That
sentence is a claim about what the user is exposed to *now*. A cost weight
answers a different question: what share of contributed capital went to that
position at the time it was bought. The two diverge by the price drift since
purchase, position by position, and the drift is largest exactly where the
look-through matters most — a holding that has run up is understated by cost
weighting at the same time as its issuer weight has grown.

So a cost-weighted look-through misstates issuer exposure in a direction
that is systematic, not random, and it produces a concentration figure that
reads as measured and is not. Mode M's single as-of date is a hard
requirement for both.

If Mode M cannot price every position, the look-through is `Not available —
[positions] could not be priced to [date]` for the affected names, per
`RULES.md` rule 9. It is not computed on cost weights as a fallback, and it
is not computed on a partial set without saying which names are missing.

## What a halt is

A halt is a defined output shape, not an absence of output, and not a
licence to improvise. `RULES.md` Part IV sets the shape; this is what it
means here.

**A halt withholds exactly three things — the whole of `RESULT`:**

1. The position tables — the two pie tables and the combined table.
2. Weights, on any basis, as figures or as ranges.
3. The rewrite of `portfolio.md`. A halted run never writes.

**A halt still prints five sections:**

1. `STATUS` — the check that fired, the measured value, and the threshold
   or condition it failed against, on one line, followed by the withheld
   items.
2. `CONTEXT` — the five mandated fields. `Not available` and `Coverage`
   carry the most information precisely on a halt.
3. `METHOD` — the policies in force. The measured value that fired the
   check is a different number under each cash policy, so a halt without
   them cannot be reproduced or compared against the run that fixes it.
4. `PROOF` — the evidence the diagnostic rests on: the owner-split
   breakdown, contributing rows, shortfall rows, failed reconstructions.
   **These are diagnostics, not position tables.** A halt exists to explain
   itself, and an explanation without its evidence is an assertion.
5. `SOURCES` — what was read.

The distinction is ownership-split versus allocation. An owner-split
breakdown says *this is what the export can and cannot attribute* — it is
the finding, and under the section contract it sits in `PROOF` — on every
halt, and on a completed run whenever `PROOF` is asked for. A position table says *this is your portfolio* — it is the
conclusion the halt has declined to reach, and it is the section that goes
missing.

**Say what was withheld, not "no output".** A halt line reading `no tables
printed` above a printed breakdown is a contract contradicting itself in
public, and the reader learns to trust neither half. The correct form names
the withheld items:

```
STATUS: Halted - [check]: [measured] against [threshold].
Withheld: position tables, weights, portfolio.md rewrite.
```

`RESULT` is then absent from the output entirely. It is not printed empty,
and it is not replaced by a note standing in for it — the sections that
follow say everything a reader needs, and a placeholder where the tables
would be invites the reader to imagine them.

## Step 5 — Validate before printing anything

On any failure below, report the parse error and print **no table at all**.
A table that is nearly right is worse than no table: it gets read, and its
error propagates into every module that loads `portfolio.md` afterwards.

**1. Reproducibility — the check that matters most.** For every percentage
in every table, recompute it from the printed values beside it, at the
precision printed:

```
printed weight  ==  round(printed cost basis ÷ printed total × 100, 1 dp)
```

Assert equality for each row, each pie's in-pie column, and each pie's share
of the combined total. A percentage that cannot be re-derived from the
column it sits next to means the percentage and the column came from
different quantities — which is exactly the defect this check exists to
catch, and it is invisible to a sum-to-100 test, because a percentage column
computed from a *different* basis still sums to 100 perfectly.

**2. Cash provenance.** The lot book says which shares are the user's; this
asserts they could have paid for them.

```
attributed purchases (mine)   <= attributed inflows (mine)
attributed purchases (holder) <= attributed inflows (holder)
mine + holder + indeterminate == Σ purchases, per position and in total
```

All three hold by construction once the ledger runs, because a purchase can
only draw what a pool contains and the remainder is classed indeterminate —
which is exactly why failure is worth asserting: it means the ledger broke,
not the data.

A non-zero indeterminate total is **not** a failure. It is a reported
finding, and the run continues. Report it per Step 3, with the contributing
rows, and report the decomposition of the naive gap:

```
Σ purchases − mine inflows  =  holder-funded  +  indeterminate
```

Reporting one number hides which half is a finding and which half is the
ledger working. The usual cause of a large indeterminate total is an export
window that opens after a deposit. A wider export closes it, and that is the
remedy to state — not a smaller cutoff, and not a `HOLDER_CASH_AT_OWN_FROM`
figure back-solved to make the gap vanish.

**Halt condition.** One, and it is configurable:

```
indeterminate ÷ (mine + indeterminate)  >  INDETERMINATE_HALT_ABOVE
```

by cost, from `DECISIONS.md` (default `5%`). Above it, halt: print every
section but `RESULT`, per the halt shape above. Below it, print
everything, with weights as ranges per the next paragraph. The threshold is
a judgement about when a report stops being worth reading, not a
measurement; it is stated in `PROOF` beside the measured value so the
reader knows what bar the run
cleared.

**Weights with indeterminate > 0 are ranges, not figures.** Indeterminate
quantity makes every weight in the table uncertain — including the weights
of positions with no indeterminate share of their own, because the
denominator moves. Print both bounds and label the column:

```
lower = mine_i ÷ (mine_i + Σ_{j≠i} (mine_j + indeterminate_j))
upper = (mine_i + indeterminate_i) ÷ ((mine_i + indeterminate_i) + Σ_{j≠i} mine_j)
```

The lower bound assigns this position's indeterminate shares to the holder
and every other position's to the user; the upper bound does the reverse.
Do not print a midpoint, a "best estimate" or the mine-only weight with a
footnote. A midpoint is a figure the data does not support, and it is the
one number a reader will quote later. Where the range is wide, the width is
the finding.

Ranges are not admissible input to Mode C or the look-through, for the same
reason cost weights are not: a product of two ranges is a range, and a
concentration figure stated as a range reads as a figure by the time it is
quoted. Resolve the indeterminate class first — with a wider export — or
state the look-through as `Not available`.

**3. Sums.** Four, and they are not the same check:

- Measured weights across all attributed positions → 100%, unrounded. True
  by construction, which is why a failure is worth catching: it means the
  arithmetic broke, not the data.
- The printed, rounded table → 100.0 ± 0.1pp. *Not* true by construction.
  Rounding each weight to one decimal drifts, and this is the check that
  sees it. Report the drift as a figure. Never close it by nudging a row —
  an adjusted row breaks check 1.
- Each pie's in-pie weights → 100.0 ± 0.1pp.
- Pie shares → 100%, and the of-portfolio targets → 100%.

**4. Attribution consistency.** For every position, income and realised
result are attributed on the same split as quantity. Assert that a position
with zero attributed quantity carries zero attributed income and zero
attributed realised result, and that per-row owner shares sum to the row's
full `Total` and `Result`. Booking income to shares the same table says are
not the user's is the specific contradiction this asserts against.

**5. Entitlement cross-check.** Each dividend row's `No. of shares` against the
FIFO open quantity at its timestamp, per Step 3. Report disagreement; do not
resolve it.

**6. FX reconstruction.** Every priced row reproduced its `Total` in one
direction within 0.01, per Step 2. The per-direction tally is printed.

Then the checks `SKILL.md` already requires: any percentage over 100 or
under 0 is a parse error and not a finding; the ISIN on the row must match
the ISIN being reported; a held ISIN missing from `pies.md` halts.

## Precision

Round once, at print. Carry full precision through every intermediate —
unit costs, per-owner splits, unrounded weights — and never feed a rounded
figure into another calculation, except where Step 5 check 1 deliberately
recomputes from printed values to verify the printed table.

**Precision is a property of a column, not of the output.** Each column is
printed at the precision its own quantity carries, and the table below sets
ceilings rather than targets. A quantity column at four decimals does not
drag the weight column to four.

| Figure | Ceiling |
|---|---|
| Quantity | 4 dp |
| Currency amounts | 2 dp |
| Percentages | 1 dp |
| Exchange rates | as the row states, unrounded |

**Drop trailing zeros.** A weight of `41.0` prints `41`; a quantity of
`2.5000` prints `2.5` where the source column carries one decimal. Padding a
column to a uniform width is a typesetting instinct, and here it manufactures
digits: a reader cannot tell a `0` that was measured from a `0` that was
added to make the column line up.

**Never print more precision than the source carries.** If a source column
carries fewer decimals than the ceiling, print what the source carries — a
price stated to 3 dp is never shown to 6. Trailing digits the export did not
supply are invented precision, and invented precision reads as measurement.

A unit cost derived by division (`Total ÷ quantity`) often runs longer than
either input. It is an intermediate: carry it in full, and never print it as
though it were a sourced figure.

## Step 6 — Rewrite `portfolio.md`

Preserve the existing structure. The file keeps its headings, its section
order, its table columns and its prose. This module replaces measured values
inside the existing tables, adds measured columns beside the target one, and
stamps the date. It does not restructure, reorder or reword.

- `Last updated:` → today's date.
- `OWN_FROM:` → unchanged. This module reads that field and never writes it.
- **Pie 1 — ETFs** and **Pie 2 — Individual stocks** stay separate
  groupings, each with its own in-pie weights summing to 100%, and each with
  its measured share of the combined total. Then one combined line for the
  whole portfolio. The two pies are never merged into a single ranked table:
  they are separate allocations with separate targets, and flattening them
  discards the only structure the file has.
- Each pie table prints quantity and cost basis, and the in-pie percentage
  beside them derives from the cost-basis column as printed. No column in
  the table is computed on a basis other than the one printed next to it.
- Target and measured weights sit in adjacent columns, both labelled, and
  neither overwrites the other. Targets are a decision, not an observation,
  and are the one set of numbers in this project allowed to be unsourced.
  Measured weights are arithmetic on a dated export. Losing that distinction
  makes the file unauditable.
- Attributed income and realised result are their own labelled lines, per
  position and per pie, never netted into cost basis. Netting a dividend
  against cost basis silently changes the weighting basis of that one row.
- **Look-through** and **Watchlist** carry across unchanged. Their figures
  came from issuer holdings files, not from this export, and the default
  mode has fetched nothing. If the sync changes a direct weight the
  look-through table depends on, add one line under that table —
  `Look-through computed 2026-09-16 against direct weights this sync
  changed; stale until recomputed` — and leave its numbers alone.

Show the diff before writing. Overwriting a hand-maintained file on the
strength of a parse the user has not seen is the failure this whole module
is shaped around.

## Output contract

`RULES.md` Part IV is the contract. Sections in fixed order: `STATUS`,
`CONTEXT`, `RESULT`, `METHOD`, `PROOF`, `SOURCES` — `PROOF` only when asked
for (`--proof` on the script) or on a halt.

This module accumulated twelve header fields on top of Part IV's own, which
is what made the restructure necessary: the block introducing the table was
longer than the table. Every one of those fields is still printed. The
field placement rule decided where, and the placements are recorded below so
a later reader can tell a field that moved from a field that was lost.

### Where this module's fields went

| Field | Placement | Why |
|---|---|---|
| `Export` (filename, rows, window) | `SOURCES`, and the window on `Latest period` | It is the document. |
| `OWN_FROM` | clause on `Latest period` | Bounds the measured period — without it the reader cannot tell whose rows these are. |
| `Basis` (cost / market) | clause on `Currency / units` | A weighting basis is a unit of measure. A cost weight and a market weight are different quantities, not the same quantity labelled twice. |
| `Attribution` (fifo / none) | `METHOD` | Governs how quantities were produced. Under `none` the affected positions drop out, and `Coverage` already reports that. |
| `Policy` (funding / date) | `METHOD` | A convention, not a fact. |
| `Cash policy` (pro-rata / fifo / mine-first / holder-last) | `METHOD` | A convention, and the largest lever in the module. |
| `Holder cash` (`HOLDER_CASH_AT_OWN_FROM`) | `METHOD` | An input to the cash policy; meaningless apart from it. |
| `Entitlement` (record date / shares / pay date) | `METHOD` | A derivation basis. |
| `FX direction` tally | `METHOD` | Describes the parsing, not the result. |
| `Indeterminate` (cost, quantity, % of claim, threshold) | `PROOF` | A measurement of the run's own integrity, and the halt condition. The tables carry the consequence — the weight columns are labelled as ranges — so the reader needs no header field to read them correctly. |
| `Cash provenance` | `PROOF` | Evidence. |
| Owner split per position | `PROOF` | A diagnostic: it says what the export can and cannot attribute. That is not the allocation, and it no longer sits beside the allocation. |

Nothing in that table is optional, and nothing in it may be dropped for
brevity on a rerun. A field that stops appearing is a defect until shown
otherwise.

### STATUS

```
STATUS: Complete.
```

or

```
STATUS: Halted - cash provenance: indeterminate 28.9% of maximum claim
        against threshold 5% (INDETERMINATE_HALT_ABOVE, DECISIONS.md).
Withheld: position tables, weights, portfolio.md rewrite.
```

### CONTEXT

Exactly five fields. Module facts ride on the mandated line they qualify;
they never add a sixth.

```
Data as of:       [today — from the environment, not from the export]
Latest period:    [export window: first to last row timestamp, n rows;
                   measured from OWN_FROM [date] (portfolio.md, matches
                   ownership.md)]
Currency / units: [e.g. EUR; basis cost | market as of [date]; quantities
                   unitless; per-column precision per Precision below]
Not available:    [positions without a weight and why; unclassified rows,
                   named individually]
Coverage:         [n of m positions FULLY attributed; k partial, named;
                   j not attributed, named] — see below
```

### RESULT

Three tables, in this order, and nothing between them:

1. **Pie 1 — ETFs.** Quantity, cost basis, in-pie weight, target.
2. **Pie 2 — Individual stocks.** Same columns.
3. **Combined.** Each pie's measured share of the total, against its target.

Then the diff against the current `portfolio.md`, which is the other thing
the user asked for and is itself a result.

**The owner split does not appear here.** It was printed beside the position
tables and it is a diagnostic: `mine / holder / indeterminate` answers
*what can the export attribute*, not *what is the allocation*. It moves to
`PROOF`, whole, with its contributing rows.

**One table per question.** The two pies are separate allocations with
separate targets and stay separate tables; they are never merged into a
single ranked table, and neither grows a column to answer a question the
other table is for.

**Suppress columns that are zero or empty for every row**, and name each
suppressed column in `METHOD`. In practice this removes the income and
realised-result columns on a sync where no position received either, and the
holder column where the split resolved wholly to `mine` and
`indeterminate`. It never removes a column that is zero for *some* rows: a
zero that contrasts with a non-zero is information.

**Precision per column, trailing zeros dropped.** These are ceilings, and a
column prints at the precision its own quantity carries:

| Column | Ceiling |
|---|---|
| Quantity | 4 dp |
| Cost basis and other currency amounts | 2 dp |
| Weights and shares | 1 dp |
| Exchange rates | as the row states, unrounded |

A quantity the export states as `2.5` prints `2.5`, not `2.5000`. A weight
that lands on `41.0` prints `41`, not `41.0`. Four decimals in the quantity
column do not license four in the weight column.

Every percentage is reproducible from the cost-basis column printed beside
it, at the precision printed. `PROOF` check 1 asserts it.

### METHOD

```
Attribution:      [fifo | none] — quantity, cost, income and realised result
Policy:           [funding-based | date-based] — see Step 3
Cash policy:      [pro-rata | fifo | mine-first | holder-last] — see Step 3
Holder cash:      [HOLDER_CASH_AT_OWN_FROM: unknown | amount, source, date]
Entitlement:      [record date | No. of shares | pay date] — per Step 3
FX direction:     [tally per row kind: divide / multiply / both]
Columns suppressed: [named, or none]
```

All seven print every run, including the ones at their defaults. A default
that is not printed cannot be distinguished from a default that changed, and
two runs of the same export under different policies are not comparable.

### PROOF

The validation block of Step 5, as run, with addends — every sum shown as
its terms, not as a verdict:

```
printed combined table    47.8 + 38.6 + 13.5 = 99.9%, drift -0.1pp
                          PASS (tol 0.1pp)
```

Then, in this order:

1. **Cash provenance.** Attributed inflows and purchases per pool, and the
   naive-gap decomposition `Σ purchases − mine inflows = holder-funded +
   indeterminate`, with both terms.
2. **Indeterminate.** Cost, quantity, percentage of maximum claim, and the
   threshold it was measured against — reported at zero as well as
   non-zero. A check that passed is reported as passed.
3. **The owner split, per position**, and the contributing rows behind any
   indeterminate quantity. The aggregate says how much is unresolved; only
   the rows say which purchases the export fails to explain.
4. The remaining Step 5 checks: reproducibility, sums, attribution
   consistency, entitlement cross-check, FX reconstruction.

### SOURCES

```
SOURCES: export only — [filename], [n] rows, [first] to [last], read [UTC]
         pies.md          n/a — local file, updated [date], read [UTC]
         ownership.md     n/a — local file, updated [date], read [UTC]
```

Mode M adds one row per priced position — price, currency, as-of date,
document and retrieval timestamp — and the FX source with its own date.
The default mode fetches nothing, and `export only` is the evidence that it
behaved correctly.

### On a halt

`STATUS`, `CONTEXT`, `METHOD`, `PROOF` and `SOURCES` print. `RESULT` does
not: no position table, no weight on any basis, as a figure or as a range,
and no rewrite of `portfolio.md`.

`METHOD` prints because the measured value that fired the check was produced
by the policies in it — an indeterminate percentage is a different number
under each cash policy, and a halt nobody can reproduce is an assertion.
`PROOF` carries the diagnostic's evidence, which is where the owner split
and the contributing rows already live on a completed run; a halt prints the
same block, not a special one.

### What `Coverage` counts

`Coverage` counts **fully attributed** positions only. A position is fully
attributed when its entire quantity resolves to `mine` or `holder` with an
indeterminate share of zero. Anything else is partial, and partials are
named individually — the count alone does not say which position is
unresolved, and that is the only part a reader can act on.

```
Coverage: 2 of 3 positions fully attributed
          1 partial — SPPW (8.4091 mine / 0.0684 holder / 8.5225 indeterminate)
          0 not attributed
```

Not:

```
Coverage: 3 of 3 positions attributed
```

The second form counts a position as covered because the module produced
*an* answer for it, rather than because the answer is complete. `RULES.md`
rule 9 requires partial coverage stated up front, and a position that is
half indeterminate is the definition of partial. Reporting it as covered is
the specific failure rule 9 names: an incomplete analysis presented as
complete.

A position excluded by `ownership.md`'s pre-cutoff declaration, or dropped
for any other reason, is `not attributed` and is named too.

### Pre-output self-check

`RULES.md` Part IV's checklist, plus what this module has got wrong before.
Run it against the rendered output, not against the intention to produce it
— every item below is here because it passed in intent and failed on the
page.

- [ ] Sections present, in order (`PROOF` when asked for or halted), with `RESULT` ending the answer
- [ ] `CONTEXT` is the five mandated fields and nothing else — `OWN_FROM` on
      `Latest period`, basis on `Currency / units`, no sixth line
- [ ] Every field in the placement table above appears in the section it
      was placed in. A field missing from the output is a defect, not a
      tidier run
- [ ] `Not available` names every dropped and unclassified row
      *individually*. An unclassified row named on one run and absent from
      the next is a regression. Nothing leaves this line because a rerun
      had less to say
- [ ] `Coverage` states both numbers, n and m, counts only fully attributed
      positions, and names every partial
- [ ] `RESULT` holds the three tables and the diff, and nothing else — no
      owner split, no provenance line, no policy note between tables
- [ ] Every table has its header line: pie name, basis total, measured
      share of combined, and target for comparison
- [ ] Columns that are zero or empty for every row are suppressed, and each
      suppressed column is named in `METHOD`
- [ ] Each column printed at its own precision, trailing zeros dropped, and
      no column padded past what the source carries
- [ ] Every percentage re-derived from the column printed beside it
      (Step 5 check 1)
- [ ] `METHOD` names attribution mode, attribution policy, cash consumption
      policy, `HOLDER_CASH_AT_OWN_FROM`, entitlement basis and the FX
      tally — all of them, including those at their defaults
- [ ] `PROOF` carries addends, not verdicts, on every sum, split and
      decomposition
- [ ] Cash provenance reported in `PROOF`, including a zero indeterminate
      total — a check that passed is reported as passed, not omitted for
      brevity
- [ ] Owner split and its contributing rows are in `PROOF`, not beside the
      position tables
- [ ] Weights printed as ranges wherever indeterminate > 0, with no
      midpoint offered anywhere in the output
- [ ] Currency and units labelled on every figure
- [ ] `SOURCES` carries a retrieval timestamp per row, and `n/a — local
      file` where no publication date exists
- [ ] On a halt: `RESULT` absent entirely — not empty, not a placeholder —
      withheld items named, and `METHOD` and `PROOF` both printed
- [ ] No recommendation, forecast, or drift-from-target reading (a
      numeric `Diff (pp)` is not a reading)
- [ ] No causal story about a price or a weight change
- [ ] Nothing that appeared in a previous run has silently vanished from
      this one

The last item is the general form of the rest. A rerun after a fix is where
output contracts decay: attention goes to the thing being fixed, the output
is rebuilt from memory of what mattered, and a field that was correct last
time quietly drops out. Diff this run against the previous run's text —
`references/run-journal.md` holds it — before returning it, and treat any
field that disappeared as a defect until shown otherwise.

A restructure is that failure mode at its most dangerous, because moving a
field and losing one look identical in the diff. That is what the placement
table above is for: it is the list to check the output against, and a field
that is in the table and not on the page has been lost, not moved.

## Traps specific to this module

**A wrong weight looks plausible.** Every trap in `docs/t212-csv-schema.md`
produces a number, not an exception. The FX direction, the GBX price, the
dividend `No. of shares` — each yields a position wrong by a factor small
enough to survive a glance. This is why the FX direction is tested against
the stated `Total` per row rather than assumed, and why percentages are
re-derived from the printed column rather than trusted.

**A percentage column can sum to 100 and still be wrong.** Any set of
positive numbers normalises to 100. Summing to 100 proves normalisation
happened; it proves nothing about *what* was normalised. Only re-derivation
from the printed column does that.

**The export is a window, not a history.** A position opened before it
appears as sells with no matching buys, and nets negative. That is missing
data, not a short position.

**An export for a window with no activity is a zero-byte file** — no header,
not even column names. Check for emptiness before checking the header, or an
uneventful week is reported as a corrupt export.

**Two exports overlap.** Re-exporting a wider window re-delivers rows
already seen. Dedup on `ID` plus a fallback key, because dividend rows carry
no `ID` at all.

**Today's date comes from the environment, not from the export.** The last
row in the file is the last transaction, which is not the date of the sync.
Stamping the export's last date as `Last updated` makes a stale file look
fresh.

**A sync is not a review.** The user asked for the file to be updated. What
the new allocation means is a separate question they did not ask, and
`RULES.md` rules 6 and 11 land on the same answer: print the table, stop.
