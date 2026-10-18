# Decisions

Follow RULES.md.

Last updated: 2026-10-01

Policies that have been decided but are not implemented. **Nothing in this
file is read by any code, now or ever.** `scripts/t212_holdings.py` parses
`ownership.md` and `pies.md`, and every key in those two files is honoured
by the importer; a key it does not implement halts the run rather than being
skipped. This file is where a decision waits until that is true of it.

Each entry states what was decided, why, and what the script would have to
grow before the decision could move a number.

Entries headed **DECIDED** are in force already, in the reference files
they name. Those entries record the reasoning behind a rule, so it is not
lost when the rule is reworded.

## Cash consumption: pro-rata across the pooled balance

**NOT IMPLEMENTED.** The script has no cash ledger, no pooled balance and no
fourth ownership class. No run is affected by this decision.

Declared until 2026-09-20 in `ownership.md` as `CASH_CONSUMPTION: pro-rata`,
where it was read by nothing.

`CASH_CONSUMPTION` decides which pool a purchase draws on: `pro-rata`
(default), `fifo`, `mine-first` or `holder-last`. It is the largest lever in
the importer, which is why it is a declaration rather than an assumption.
`references/portfolio-sync.md` states each option's bias and the measured
sensitivity of each to the seed below: on the worked example, the user's
attributed cost basis swings 224.47 under `pro-rata` against 369.75 under
`fifo` and 594.10 under `holder-last`, as the seed moves from `unknown` to
1000.00 EUR.

Pro-rata is the choice because it is what a pooled cash account actually
does. A balance of 1000.00 of my money and 500.00 of the holder's is one
balance of 1500.00; a 630.00 purchase from it takes two thirds and one
third, because that is the composition of what was spent. No ordering is
invented, and no euro is claimed to be older than another.

### Why FIFO-on-cash was rejected

Cash is fungible and has no lots. Ordering it is therefore an invented
convention, not a fact about the money: nothing in the account records which
euro arrived first, because no euro is distinguishable from any other. A
FIFO rule over cash does not recover a hidden truth — it manufactures one and
then reports the result as a measurement.

This is the point where the cash policy and the share policy part company,
and the distinction is easy to lose. Lot FIFO over *shares* is defensible
because shares do have lots: an acquisition order exists in the account, the
export records it, and `docs/fifo-attribution.md` argues the case and gives
the bound. None of that argument transfers to cash. Reusing the word FIFO
across both would suggest the same standing for two rules with nothing in
common beyond a name, and that is precisely the kind of borrowed authority
this project is supposed to refuse.

The measured cost is the second reason. Cash FIFO dates any declared seed at
the cutoff and so always draws it first, biasing toward the holder, and it
carries the largest seed sensitivity of the three non-degenerate options. On
the worked example in `references/portfolio-sync.md` it moves a position
from 3.0000 shares to 0.6190 — 38.6% of the portfolio to 13.0% — on shares
bought seven months after the cutoff, on the strength of one estimated
figure.

`mine-first` was rejected for the opposite reason. Its zero sensitivity to
the seed is not robustness: it is insensitive because it refuses to let
holder cash fund anything until mine is gone, which is the same fact as its
maximal bias toward me. Insensitivity earned by ignoring the input is not a
virtue.

## HOLDER_CASH_AT_OWN_FROM: unknown

**NOT IMPLEMENTED.** The script has no cash ledger, no pooled balance and no
fourth ownership class. Declaring a figure here would change nothing.

Declared until 2026-09-20 in `ownership.md` as
`HOLDER_CASH_AT_OWN_FROM: unknown`, where it was read by nothing.

The field was to carry the account holder's uninvested cash balance on the
cutoff date. The export is a window of transactions, not a statement, so it
does not contain an opening balance — this field is where that figure would
be declared if I ever obtain it from a statement, and it would be dated and
sourced like any other number when I do.

It is `unknown` because I do not have it. `unknown` is a valid value and is
the default, and it seeds nothing: a purchase that exhausts every inflow the
export accounts for then draws on cash of unknown ownership, and its shares
are classed `indeterminate` rather than attributed to either side.

A declared figure would seed the holder pool at the cutoff date. It narrows
the indeterminate class, and it moves shares toward the holder — by how much
depends entirely on the cash consumption policy above. Under `fifo` the seed
is the oldest cash in the ledger and so is drawn first, which is the most
aggressive reading; under `pro-rata` it is drawn only in proportion to its
share of the balance. Declaring a balance never moves shares toward me under
any of the four policies, which is worth stating plainly: obtaining this
number can only reduce what I claim.

## INDETERMINATE_HALT_ABOVE: 5%

**NOT IMPLEMENTED.** The script has no cash ledger, no pooled balance and no
fourth ownership class, so there is no indeterminate quantity to measure and
no threshold that could fire.

Declared until 2026-09-20 in `ownership.md` as
`INDETERMINATE_HALT_ABOVE: 5%`, where it was read by nothing.

The threshold is the share of my maximum claim — `indeterminate ÷ (mine +
indeterminate)`, by cost — beyond which a run should refuse to print
attributed weights at all. Above 5%, the tables stop being worth reading:
a weight built on a denominator that is more than a twentieth unallocated
describes the arithmetic rather than the portfolio, and a reader cannot tell
the two apart from the figure alone. Refusing to print is the honest
response; a footnote on a printed number is not, because the number will be
read and the footnote will not.

It is a judgement about when a report stops being worth reading, not a
measurement. Like the target weights in `pies.md`, it is allowed to be
unsourced because it is a decision.

### What the indeterminate class was to cover

Shares whose purchase cannot be traced to either owner's cash. The cash
provenance ledger was to hold two pools, mine and the holder's, credited by
the inflows the export records from the cutoff onward. A purchase draws from
those pools under the policy above. A purchase that exhausts them both draws
on money the export does not account for — deposits before the window,
interest, or the holder's opening balance while it stays `unknown` — and the
shares it bought belong to neither side on the evidence available.

`indeterminate` is the class for exactly those shares. It is a fourth
ownership state alongside the three the script has today (`mine`,
`spans_cutoff`, `pre_cutoff_only`), and it differs from `spans_cutoff` in
what is unknown: `spans_cutoff` is a position whose *opening* predates the
cutoff, while `indeterminate` is a position opened after it whose *funding*
cannot be attributed. Both are gaps, but they are different gaps, and
collapsing them would hide which one a given figure suffers from.

## Corporate actions: no discontinuity detector

**NOT IMPLEMENTED.** The script has no model of corporate actions and no
check that reads a share movement against the position it moves. No run is
affected. Nothing is declared for it anywhere, and nothing should be: this
is a missing check rather than a deferred policy, and a key in `ownership.md`
that the importer does not implement halts the run.

A detector would cover the events a Trading 212 export does not record as
rows of their own: splits, reverse splits, consolidations, share-class
conversions, in-specie transfers in or out, and the ticker or ISIN changes
that follow them. Each moves the share count without a buy or a sell behind
it, so the quantity in the export steps against nothing — and every figure
derived from quantity, net position and FIFO attribution and cost weights
alike, is wrong from that row onward by the ratio of the event.

The concrete case that escapes is a 2:1 split on a holding of 1 share,
recorded by the broker as a buy of 1. Net quantity goes from 1 to 2, which
is exactly what those rows would mean if a share had been bought: the
position stays positive, the running total stays consistent, and no check
has anything to object to. The extra share then enters the weights as though
it were funded, and FIFO dates it at the row's own timestamp, so it counts
as mine even where the split acted on a lot inherited before the cutoff. The
report says 2 shares, which is true, and attributes both to me, which is
not, and prints no marker distinguishing that figure from a measured one.

What exists today is narrower and is not a substitute.
`check_no_negative_quantity` halts when a position nets below zero, which
catches the loud half of this class: `tests/fixtures/quantity_discontinuity.csv`
sells 10 shares of a 1-share position and halts there, naming that check.
But that is a halt on a consequence, not a detection of a cause. It fires
only when an unrecorded event removes more shares than the export accounts
for. An event that leaves net quantity positive — which every forward split
does — passes in silence, and the test that covers the fixture asserts the
check by name precisely so the difference stays visible.

Before the gap could close, the script would need a per-instrument
continuity check — each trade row read against the position standing before
it, flagging a step no row explains — and a declared way to record an event
and its ratio once identified. Without the second half the first halts on
every legitimate transfer in, and a check that cries wolf on ordinary
activity gets switched off, which is worse than the gap it was meant to
close.

## Cost weights across BGN and EUR: restated at the declared fixed rate

**DECIDED 2026-09-28, superseding the refusal of 2026-09-25 below.** The
account owner declared the rate. `ownership.md` now carries
`Fixed rate: 1 EUR = 1.95583 BGN (Council Regulation (EU) 2025/1409 of
8 July 2025, <EUR-Lex URL>)` in its policy block, and
`scripts/t212_holdings.py` honours it: when the surviving lots are costed in
both BGN and EUR, each BGN amount is divided by 1.95583 and the weights are
taken in EUR.

Why this is not the "remembered rate" rule 3 forbids: the BGN/EUR rate is
not an observation. It was the currency-board peg from 1999 and became the
irrevocable conversion rate when Bulgaria joined the euro on 2026-01-01, so
there is no date on which a different rate was the right one for these lots.
A floating rate — USD/EUR for Mode M prices, say — still has to be fetched
with its date, and this key is not the place for it.

What the output owes the reader, and the tests assert:

- the original per-currency `Cost basis` stays in the table, with a
  `Cost basis (EUR)` column beside it that the weights are taken from;
- `CONTEXT` `Currency/units` names the rate and the file that declares it,
  `METHOD` repeats it with its source, and `SOURCES` carries the regulation
  as a row with its URL;
- `PROOF` restates every BGN amount (`41.30 BGN / 1.95583 = 21.12 EUR`) and
  re-adds the EUR column as printed;
- the grammar is strict — `1 EUR = <rate> <CCY> (<source>)`, source
  required — and a malformed value halts at its line;
- a currency the declared rate does not join is still refused, with the
  weights `Not available` and the uncovered currency named;
- a single-currency book never touches the rate.

### Superseded: Not available, no rate declared

**DECIDED 2026-09-25.** `scripts/t212_holdings.py` weights positions on cost
basis — each surviving lot's remaining quantity × its unit cost, FIFO — as
`references/portfolio-sync.md` Step 4 specifies. It replaces the
`Value (last px)` column and the `Actual` and `Drift` columns built on it,
which the spec had already retired and the engine had kept printing: a
last-transacted price dates every row differently, and a drift-from-target
reading is the commentary the module is forbidden to make.

This account's 2025 lots settled in BGN and later lots in EUR. A cost basis
spanning both cannot be summed without a rate, and the module fetches none,
so while a BGN lot survives the weights print `Not available — cost bases
denominated in BGN, EUR, no rate fetched`, with each position's cost shown
per currency. They print in full once every surviving lot is in one
currency; the real-export test asserts whichever of the two holds.

The BGN is fixed to the EUR at 1.95583, so a declared conversion would be
defensible. It is not declared here, deliberately: a rate belongs in a
policy block with its source and date, and adding one is a decision for the
account owner, not a default the engine should assume. Until one is
declared, the refusal is correct behaviour, not a gap.

## Market-wide and Mode B after the live tests of 2026-09-27

**DECIDED 2026-09-27.** In force in `references/market-context.md`,
`references/etf-brief.md`, `RULES.md` v7 and `SKILL.md`. Nothing here is
read by code; `tests/contract.py` checks the parts a parser can check.

Five live runs on 2026-09-27, across Market-wide and Mode B, routed
correctly and got the arithmetic right. They also surfaced ten defects, and
each decision below answers one of them. The runs' text is not reproduced
here, and nothing below quotes it (rule 15); the defects are described as
the fix request stated them.

### 1. Contribution is opt-in

The Contribution table printed empty in the live runs, on requests that
had not asked for it. It now runs only when the request asks what moved
an index ("which stocks drove the S&P"), the same pattern as
`portfolio-sync.md` → Mode M: explicit, never the default, and `METHOD`
says `Contribution: on (requested)` or `off (not requested)` on every run.
The formula and the 0.10pp threshold are unchanged.

A request that names no index ("which stocks drove the market") runs the
table for each index in the default set, because the scope rule (5) gives
the default set whenever no index is named.

### 2. Sectors are the provider's own sector indexes

The GICS sector table printed empty in the live runs, and the rule
forbade relabelling any other breakdown as GICS. It is replaced by sector
index closes the providers publish themselves — the S&P 500 sector indices
and the STOXX Europe 600 supersector indices — each an index with its own
closes, so its period % is computed from its own base and end close and
prints in the same Performance row as the Indexes table. The scheme is
printed only as the provider names it, and it moves from a column to a
`METHOD` line because the Performance row format has no column for it.

A sector named without a parent ("how's tech done") is matched to both
providers' sector indexes by the providers' own index names, and `METHOD`
names each match. A phrase no provider index name matches is asked about,
because mapping everyday words to a classification is a judgement.

### 3. Breadth is removed

The advancer and decliner table printed empty in the live runs. It is
removed
from Market-wide, and `Coverage` now counts indexes, sector indexes and
rates & FX rows.

### 4. Times are exact or absent

`Data as of` printed `13:1x EEST` in five of five runs: a time that was
never recorded, printed in the shape of one that was. Every time printed is
now an exact `HH:MM` with zone or is left off in favour of the date. This is
a `RULES.md` Part IV rule, not a Market-wide one, because the failure does
not depend on the module, and it has a self-check line.

### 5. Mode B source ladder, per field

Both methodology PDFs failed to read. Index facts now walk a ladder per
field — methodology PDF, then the provider's HTML methodology or index page,
then the factsheet's Quick Facts — so an unreadable PDF sends each field
down a rung instead of leaving the table empty. Each row names the document
it came from in a `Source` column, and a field from a document over 12
months old flags `stale` on its own row, because one note for the whole
brief hid which fields were old. The `Stale` column follows the usual
suppression rule.

### 6. The tracked-version field leaves Mode B

The Index facts field for which return version funds track was
`Not available` in every run, and has to be: it can be answered only from
fund documents, and Mode B uses provider documents only. Mode B now lists
the return versions the provider publishes. The fund's tracked version is
stated in Mode A, from the KID, where the Mandate field now says so
explicitly.

### 7. Scope: named indexes only

A request that names one or more indexes reports only those, and `METHOD`
says `Scope: named indexes only`. The full default set, the sector indexes
and Rates & FX run only when no index is named ("the market", "markets").
Under the named scope the Sectors and Rates & FX tables do not print at all;
`METHOD` names them under `Tables not run`, so a table left out by scope is
distinguishable from one a module forgot. This differs from Mode C, which
prints all five tables on a set of one: Mode C's tables answer one question
about one set, while Market-wide's answer different questions, and the
user asked only one.

Named sector indexes, or a named index's sectors, count as named indexes:
they bring the Sectors table back for that parent only. An index outside
the default set ("FTSE 100") prints when named — the rule removes rows the
user did not ask for and never adds any.

### 8. Variant and currency on every index row

The Instrument cell states variant and currency: `MSCI World (price, USD)`.
A source that does not state the variant gives `variant not stated`, listed
in `Not available`. Two sources more than 0.5% apart on the same date and
variant are a conflict: `PROOF` prints both with the gap, marked
`CONFLICT`, and the row's Level and Period % print `Not available — sources
conflict`. Withholding the row was chosen over printing the higher-ranked
figure. Rule 4 permits neither silent choice, and a figure in `RESULT` with
its conflict only in `PROOF` would be read without the conflict. The gap is
measured against the higher-ranked source.

### 9. Mode B mixed dates

The dated factsheet wins for every table it covers. An undated live list
may add only depth the factsheet lacks, and does so as **its own table**,
headed `(undated)`, never as rows merged into a dated table. Mixing the two
would give one table two as-of dates, one of them unknown, and would invite
splitting the factsheet's `Other` line with undated figures. An undated
table is summed on its own in `PROOF` and reconciled against nothing dated.
`METHOD` names which table came from which document.

### 10. Nothing outside the six sections

A run printed a loose note after `SOURCES`. `RULES.md` Part IV now says
nothing prints outside the six sections, such notes go in `METHOD`, and the
self-check carries it. One exception is kept: Mode A's subject line above
`STATUS`, which its reference specifies as identity and which carries no
note. Removing it was out of scope for this fix and would take away the
share class from the first line a reader sees. `SKILL.md`'s instruction to
flag a stale `portfolio.md` "at the top of the output" was text outside the
sections under the new rule, and it now rides on `CONTEXT` → `Latest
period`.

### 11. Base dates and single sources in PROOF

`PROOF` prints one line per row of every table, Rates & FX included, with
the base date on each and the sources of each close in brackets. A close
confirmed by only one source ends the row `single source`, never `PASS`.
The rule applies to the **end** close as well as the base close. The fix
request named the base close, but the period % depends on both, and a
`PASS` over an unconfirmed end close makes the same unsupported claim.

### 12. Reused fetches

A close fetched earlier in the session may be reused only if no new session
has closed on that instrument's exchange since. `METHOD` names each reused
figure and its fetch time. A reused figure keeps its original retrieval
timestamp in `SOURCES`. When the fetch time is not known to the minute, the
figure is re-fetched, because the reuse note would otherwise need exactly
the placeholder time that decision 4 forbids.

### Left open

The contribution formula measures a constituent's share of the index's
**session** move. A request over a period ("which stocks drove the S&P this
week") needs a rule for which weight date and which move to use across
several sessions. No such rule is decided here. Until one is, the table
keeps its session definition: over a longer period it covers the period's
last session only, and `METHOD` says so.

## Follow-ups to 8a94eba: conflicts, multi-day contribution, run journal

**DECIDED 2026-09-27.** In force in `references/market-context.md` and
`references/run-journal.md`. These amend decision 8 and the open item of
the entry above. Neither is edited: the reasoning there is what was decided
at the time.

### Conflicts are within one instrument

Decision 8 compared any two sources "on the same date and variant". It
also noted that a gap over 0.5% between two closes of "the same" index is
usually two variants, and left that as an observation instead of a rule.
It is now a rule. Closes are compared, for confirmation or for conflict,
only when both are for the same index, variant, currency and session. A
price close against a net total return close is two instruments. The figure
that is not the row's variant is not a source for that row: it neither
confirms the row nor conflicts with it. A source that does not state its
variant cannot be matched, so it cannot confirm either. That can leave a
row `single source` where it would otherwise have been `PASS`, and that is
the honest result.

A row withheld from `RESULT` on a conflict is not withheld from the output.
`PROOF` prints both figures, each as `date figure (variant, currency)
[source]`, and the gap. Rule 5 requires every figure to be declared with
its date. A conflict whose figures appear nowhere cannot be told apart from
a failed fetch. The per-figure variant tag is what lets `tests/contract.py`
check that the two figures were the same instrument.

### Multi-day contribution is flagged in CONTEXT

The open item above stays open: no rule attributes a multi-session move.
Until one is decided, a Contribution table over a period longer than one
session covers the last session only. Saying so in `METHOD` was not
enough. A reader who stops at `CONTEXT` sees a table under a week-long
`Latest period` and reads it as the week's attribution. `CONTEXT` →
`Not available` now carries `contribution for multi-day periods; last
session shown`. It rides on `Not available` and not on `Latest period`:
the missing figure is a multi-day attribution, while the period itself is
correctly bounded.

### Run journal: five CONTEXT fields

`references/run-journal.md` still told the journal to copy "all six
fields" of `CONTEXT`, two versions after v5 reduced them to five. It now
says five. The stale-reference test in `tests/test_market_contract.py`
fails on "six fields" in any reference, `SKILL.md` or `RULES.md`, so the
count cannot drift again unnoticed. `references/portfolio-sync.md`'s "on
top of Part IV's six" referred to the same count and now reads "Part IV's
own".

## From the first v7 live run: variant convention, SOURCES links, Period % cells

**DECIDED 2026-09-27.** In force in `references/market-context.md` and
`RULES.md` v8. This entry follows the first live run under v7 (S&P 500
since Monday). That run's text is not quoted here (rule 15).

### Headline convention for unlabelled levels

This amends the entry above, which said a source that states no variant
cannot confirm a close. For S&P 500, Dow Jones Industrial Average, Nasdaq
Composite and STOXX Europe 600, the level quoted without qualification is
the price index, and treating every unlabelled quote as unmatched turned
ordinary confirmations into `single source`. For those four, a source
quoting a headline level without naming a variant now counts as the price
version, for confirmation and for conflict. Only a source that explicitly
states net or total return is a different instrument.

MSCI keeps the strict rule. Its price and net levels are both widely quoted
without a label, so an unlabelled MSCI level could be either. The
convention names the four and nothing else: their sector indexes and any
named index outside the default set ("FTSE 100") stay strict. Extending it
to another index is a decision to add to this list, not a judgement made
during a run.

Three limits keep the convention visible:

- **It settles confirmation only.** The Instrument cell still states the
  variant a source actually named, and reads `variant not stated` when none
  did. The convention decides whether two figures are the same
  instrument. It does not decide what a source said.
- **It is marked where it was used.** A source it matched carries
  `(variant not stated)` in its `PROOF` source list, so a reader can see
  which `PASS` rests on the convention, and `METHOD` has a `Variant rule`
  line.
- **It confirms price only.** On a net or gross row an unlabelled headline
  level is still the price index, so it matches nothing there.

### URLs live on SOURCES rows

The run printed its links as a separate list after `SOURCES`. Each
`SOURCES` row now carries its own URL, and nothing follows the section.
`RULES.md` Part IV's outside-sections rule names the trailing link list
explicitly. A separate list duplicates the section without the dates, and
a link that is not on the row with its publication and retrieval dates
cannot be matched back to them. A local file carries its name or path in
place of a URL. The importer prints file names, which satisfies this as
written.

### Period % cells are bare signed numbers

The cell prints `+1.21`, `-0.40`, or `0.00` for no move. It carries no `%`
sign, because the `Period %` header carries the unit. Positive moves are
signed so that a column of moves reads the same way down its length. Zero
is unsigned, because it has no direction. Withheld cells still read
`Not available — …` and are not numbers.

## Sector and STOXX closes: a reachability table, a staleness check

**DECIDED 2026-09-28.** In force in `references/market-context.md` →
Where the closes come from. Nothing here is read by code.

The live runs of 2026-09-27 printed every S&P 500 sector and STOXX 600
supersector row `Not available`: the S&P DJI pages load their data by
script, and nothing else had been tried. A source check on 2026-09-28 found
that `stoxx.com/index/<symbol>/` (without `www`) serves every supersector
page, and Investing.com history pages serve both families — the STOXX ones
with `PR` in the name, the S&P ones with no variant stated, so those rows
fall under the strict rule and print `single source`. That is a weaker row
than a checked one, and a better one than `Not available` when the close
exists.

Investing.com also served snapshots up to thirteen days old, so the module
now requires the page's latest row to be the latest complete session before
it supplies an end close. The ~0.5% STOXX 600 gap of 2026-09-27 came from
comparing a close backed out of `last − change` with a fetched one; backed-out
closes are now named as derived and never compared.

### Amended 2026-09-28, after the first live sector run

The live run the same evening read both providers' own data through the
built-in browser on the user's computer: the S&P DJI index-data endpoint
(variant and currency stated per index) and the daily series behind each
`stoxx.com/index/<symbol>/` page. Those are rank-1 sources and now head the
table; Investing.com is the fallback when the computer is not reachable.
Where both were read they agreed exactly (S&P 500 IT 7074.89 / 7295.25,
STOXX 600 Banks 424.64).

The run reported `19 of 20` STOXX supersectors. It had found all of them:
STOXX still calculates the legacy supersector indexes on the pre-2019 ICB
names — 19, `SX…P` — beside the ICB 2019 set of 20, and every index page,
legacy included, carries the "20 Supersectors" boilerplate. The module now
names the family, defaults to the legacy 19, and counts coverage against
the family's own total. It also stops calling a post-close, pre-publication
point `in progress`, and requires the whole URL on every `SOURCES` row —
the run had written `…?indexId=` and `[a|b|c]` patterns in their place.

## PROOF on request

**DECIDED 2026-09-28.** In force in `RULES.md` v9 and every module
reference; `scripts/t212_holdings.py` takes `--proof`.

The user reads `RESULT` and does not use `PROOF` on a completed run, and
said so. A section printed on every run that its reader skips is length
without a reader, so it now prints on request and on every halt — a halt
is the one output whose answer is its working.

What stays unconditional is the checking. Every validation runs every time
and a failing one halts exactly as before; `--proof` changes what prints,
not what is verified, and a test asserts that the other five sections are
byte-identical with and without it. The three things `PROOF` used to be the
only home for, and that a reader needs whether or not they asked for the
working — a conflict's two figures, which rows rest on one source, and any
fallback or stale source — move to `METHOD` on a run without `PROOF`. A
figure withheld for a conflict with its evidence hidden would be the
undeclared data rule 5 exists to prevent.

### Amended again 2026-09-28: the ICB 2019 twenty are the default

**DECIDED 2026-09-28, by the user, superseding the legacy-19 default
above.** A second live run found all twenty current supersector indexes
through STOXX's own index search, including the four with new symbols
(`S600FOP`, `S600ENP`, `S600CPP`, `S600PDP`). The "legacy 19" of the v9
run was not a clean older scheme either: sixteen of its indexes are the
current ones, and three (`SX3P`, `SXEP`, `SXQP`) are the indexes STOXX still
publishes under pre-2019 names. The twenty are now written into
`market-context.md` with their symbols; the three old-name indexes print
only when named. The same pass made Investing.com's `PR` history a second
source that confirms STOXX closes, stopped Coverage counting tables that
did not run (`0 of 0`), and required each `SOURCES` row to carry its own
dates rather than inherit them from a heading.

## Full account history, and what the importer prints of it

**DECIDED 2026-09-28.** A one-year export ended one position's history
mid-stream: an inherited lot was sold soon after the cutoff, the window saw
more sold than bought, and that position's quantity was a floor — which
turned every other weight into an upper bound. The user added exports back
to the account's first trade. FIFO now settles every cutoff-spanning
position exactly: that one with no floor, and three others at zero shares
of the user's.

Three output changes follow from the wider window:

- A spanning position FIFO settles at exactly zero is **known**, not a gap.
  It no longer prints under `Not available` as an unknown owner split, and
  the `METHOD` line claiming every weight is larger than its share of the
  account no longer fires for it — that claim was false, since those
  positions hold nothing of the user's. It gets its own `METHOD` line.
- The **Pre-cutoff only** table — the account holder's instruments, dozens of
  them over the full history — moves from `RESULT` to `PROOF`. It answers
  no question the user asks; its count stays on `Coverage` and a `METHOD`
  line says where it is.
- The **cash-flow table** lists only instruments with activity on or after
  the cutoff, instead of a row of zeros for each of those.

The report shrank to under a third of its length on the full history, with nothing
the user's weights depend on removed. `ownership.md`'s evidence column was
rewritten against the full history.

## ETF prices: the listing from the export, and a route per listing

**DECIDED 2026-09-28.** In force in `references/etf-brief.md` → Where fund
prices come from, and `SKILL.md`.

A Mode C run printed every held ETF's Performance row `Not available`:
Yahoo Finance returned 404s and stale pages for the four UCITS lines, and
the run had resolved MEUD to Euronext Paris when the export prices it in
GBX on London. A source check the same evening, through the built-in
browser, found a working route for each listing's latest close:
Deutsche Börse's dated Xetra history for SPPW (confirmed by SSGA's own
closing price, 47.17 on 2026-09-25), and the LSE's instrument data —
last close with its date, and the exchange's previous reference price —
for VUSA, EIMI and MEUD. Vanguard publishes VUSA's full price history.

Longer periods for EIMI and MEUD are left open rather than filled: the
only series found for them, justETF's, states no venue, converts
currencies on request and was up to ~0.5% off Xetra closes, so it is
recorded as not a close. An issuer NAV history is the candidate, printed
as a NAV row if used.

Two routing and format fixes ride along. An attached Trading 212 export is
always read, whatever the question (a "what do I own?" run with exports
went to Mode C alone). And `STATUS` opens every output while a next-step
offer is a `METHOD` line, after live runs opened at `CONTEXT` and printed a
question below `SOURCES`.

### Amended 2026-09-28: exchange first, Yahoo's chart data to confirm

A second Mode C run filled all four Performance rows from Yahoo's chart
data (`query1.finance.yahoo.com/v8/finance/chart/…`, through the built-in
browser), skipping the exchange routes above. Checked against them the same
evening, Yahoo's figures matched to the last digit — SPPW on seven Xetra
sessions, EIMI, MEUD and VUSA on the LSE's and Vanguard's closes. So the
chart data is kept, as the confirming source behind each exchange, and as
the only dated history for EIMI and MEUD, which closes the gap left open
above. The same check showed the Deutsche Börse overview's
`Schlusspreis des letzten Handelstages` is the latest session's close, not
a figure that fails to reconcile; the earlier note said otherwise and is
corrected. That run also took VUSA's and MEUD's facts from justETF where
the previous run had read the factsheets, printing VUSA's AUM as a
different measure in a different currency; factsheets now come first and
AUM names what it measures.

## Distributions inside the period

A distributing fund's price falls by the payout on its ex-date, and
`Period %` printed that fall as a move. VUSA, the one distributing fund
held, pays quarterly (ex-date in the third week of March, June, September,
December), so any period that crosses one understated it by about 0.2 pp —
and "last month" or "YTD" always does. The stocks pay too.

`Period %` stays the price move, because that is what the listing's closes
say and what every other row prints. Beside it, only when some row's period
holds an ex-date, `Incl. dist %` adds the distribution back, and a
`METHOD` line names the ex-date and amount. Rejected: replacing `Period %`
with a total-return figure (the column would then mean two things across
rows), and a METHOD line alone (the table would still read as a loss).

Issuer first for dates and amounts. Yahoo's `&events=div` confirms the date
and supplies the amount in the listing's currency, which the issuer does
not when it declares in another (VUSA: USD declared, GBP traded). Two
things the 2026-09-28 run took as evidence are ruled out: the LSE's `XD`
flag, which was still up eleven days after VUSA's ex-date, and third-party
dividend tables, one of which had a quarter's amount wrong against
Vanguard's.

## Without the computer, the run goes on and the closes stay empty

On 2026-09-29 a session that could not reach the user's computer answered
"how did my ETFs do since 2026-09-16?" outside the skill. It priced all four
funds from their Xetra EUR listings through an aggregator, measured from
the wrong base close, and left VUSA's distribution as a maybe. Against the
held listings the same period read EIMI +1.56 where it printed +3.15, and
MEUD +1.05 where it printed +0.30 — right-looking numbers for instruments
the user does not own.

The skill's files travel with it, so the computer's absence is a missing
route, not a missing skill. The rows the browser would have filled print
`Not available`, the rest of Mode C runs, and `METHOD` says what to reopen.
No cloud-reachable page was found that carries the held listings' closes,
so there is no fallback to name.

The same check found two gaps in Yahoo's chart data — a `null` for a
completed session and an intraday row for the open one — and that the
LSE endpoint works when fetched from a page on the LSE's own site. The end
close now comes from the exchange; Yahoo confirms where it has a number.

## Stocks table in Mode C: earnings dates and newest filings

**DECIDED 2026-10-01.** In force in `references/etf-brief.md` → Mode C →
Stocks table, checked by `tests/contract.py` → `stocks_table_problems` and
`tests/test_stocks_table.py`.

Mode C's Performance table already prints a row for each stock in the set,
and the earnings calendar already existed in `references/market-context.md`,
but neither answered "what is about to happen to the stocks I own, and what
have they filed". Mode C gains a sixth table, one row per individual stock in
the set: next earnings date, latest 10-K or 10-Q, and the 8-Ks filed in the
last 30 days.

- **A sixth table, not more columns on Performance.** Performance is a
  question about price (Part IV: one table per question). Dates and filings
  are a different question with different sources.
- **Company-announced earnings dates only.** A date only a data provider
  shows is `Not available — not confirmed by the company`; a date inferred
  from last year's pattern is a forecast (rule 8). A date before `Data as of`
  is the last report, so it is never printed as the next.
- **Newest filings, facts only.** Form, period and filing date for the latest
  periodic report, and a count with dates for 8-Ks. Item numbers and what an
  8-K announces are left in the filing: summarising them is the causal story
  rule 7 forbids, and a count cannot be wrong in that way. Figure deltas
  (revenue, EPS against the prior period) and insider transactions were
  offered and not chosen; either can be a later column or table.
- **A fixed 30-day window, not "since the last run".** "Since last run" makes
  the table depend on the journal and not reproducible from the data date.
- **A set with no stocks prints `none`**, like the overlap tables, so a reader
  can tell the table ran. `Coverage` never counts it then.
- **The CIK is resolved from the ticker through SEC's own ticker file and the
  entity name must match `portfolio.md`.** No CIK or ISIN is written into the
  spec from memory; the run fetches it and prints the match in `PROOF`.

**Checked live 2026-10-01.** EDGAR's submissions record answers only from a
browser tab on `data.sec.gov`; both shells are refused at the proxy, and
WebFetch summarised the JSON wrongly (a Form 4 offered as the latest periodic
report), so it is ruled out as a route. All three company pages loaded and none
had announced its next date. The route table is in
`references/etf-brief.md` → Stocks table.

## STATUS is `Complete.` alone; the Stocks table names its METHOD lines

The first live Mode C run with the Stocks table (2026-10-03) filled every
table, with two contract slips that no check caught.

- **A tally on the STATUS line.** It printed `STATUS: Complete - 4 of 6
  Performance rows rest on a single source…` over a Performance table of seven
  rows. The tally was already on METHOD's `Confirmation:` line, correctly; the
  copy on STATUS disagreed with it. RULES.md Part IV now says `Complete.` is
  the whole line, and `contract.status_problems` holds it there. A halt line
  may still wrap, as RULES.md's own example does.
- **The parser missed the one-line form.** `split_sections` matched only a
  bare `STATUS` header, so `STATUS: …` on one line — a form RULES.md allows —
  fell outside every section and nothing looked at it. Both forms now parse.
- **`8-K window:` in METHOD.** The `Stocks window:` and `Earnings dates:`
  labels were listed only in Mode A's METHOD template, so the run fell back
  to the PROOF check's name. The Stocks table section now prints both lines
  as `stocks_table_problems` reads them.

## BuffettBot checks its own draft; overlap rules tightened

The second live Mode C run of 2026-10-03 passed STATUS and still broke the
contract in four places, one of them a wrong fact.

- **MEUD · EIMI printed `disjoint`.** The spec said a developed and an
  emerging index never intersect. That holds inside one provider's
  classification only: the STOXX Europe 600 includes Poland, which MSCI
  classifies as emerging. Across providers the country lists decide, and a
  list not fetched makes the row `Not available`. The run before had it right
  for that reason. `structural_problems` checks the wording.
- **Fund facts came from WebFetch summaries.** Two runs were given two
  different, unprinted SPDR top-10 totals. Factsheet figures now come from the
  PDF's text only, as EDGAR's do.
- **Shared weight had no definition**, so one run printed one figure and the
  next printed one per fund. It is now one figure: the sum of the smaller
  weight in each shared name. `holdings_problems` checks it.
- **The METHOD labels were missed again** with the spec naming them. The
  checks existed but only the tests ran them. SKILL.md now has the run write
  its draft to a file and run `scripts/check_output.py` on it, fixing what it
  lists before printing. `contract.py` ships in the zip as
  `scripts/contract.py`; `scripts/build_zip.py` holds the file list, which
  until now lived only in one-off build commands.

**Follow-up, same evening.** The third live run carried none of the rules
above, and no `Self-check:` line, most likely an older zip still installed;
nothing in an output said which build made it. Each zip now carries a `BUILD`
file (commit hash and date, written by `build_zip.py`), and `METHOD` opens with
`Build:` and that text; the checker requires the line. The same run joined its
pairs with `×`, which `structural_problems` did not split on, so the check
missed three wrong `disjoint` rows. It reads `×` now.

## MSCI country lists come from the factsheet footnote

The 2026-10-03 scheduled test run printed VUSA · EIMI and MEUD · EIMI as
`Not available` with `MSCI Emerging Markets IMI country list not fetched`,
though the browser was up. The spec said a missing list makes the row
`Not available` but never said where the list comes from, and the country
weights on a factsheet stop at the top five and `Other`.

- **Source.** MSCI's index factsheets carry the full list in a footnote
  (`* EM countries include: …`, `* DM countries include: …`). The EM IMI
  net factsheet 404s; the gross one (dated SEP 30, 2026) carries the same
  list, which belongs to the index, not the return variant. Read in the
  built-in browser with pdf.js; msci.com refuses both shells. Checked
  2026-10-05: 24 EM countries (United States not among them, Poland among
  them), 23 DM countries.
- **What it settles.** VUSA · EIMI is `disjoint` (the United States is not
  in MSCI EM's list); MEUD · EIMI is `overlapping` (Poland is in both).
- **Check.** A Structural `Not available` must say `(browser route down)`
  or which document returned which status. `structural_problems` flags any
  other wording; the saved 2026-10-03 brief now fails the self-check on
  exactly those two rows.

## Allocation table: market weight vs target, numbers only

Mode C now prints an Allocation table: each pie holding's value in EUR at
the brief's own closes, its market weight, its `pies.md` target, and
`Diff (pp)` = Weight − Target. The look-through takes its weights from it,
so it is computed instead of `Not available`.

- **Reverses part of the 2026-09-25 decision.** That decision dropped the
  `Actual` and `Drift` columns for two reasons. The first, last-transacted
  pricing that dated every row differently, still holds and is why the
  table prices every holding at one close date with ECB rates for that same
  date. The second called any drift-from-target reading commentary. The
  user chose (2026-10-05) to see the difference as a number: a signed figure in
  pp is arithmetic; a word about it ("overweight", "rebalance") is still
  forbidden, and `allocation_problems` checks the column.
- **One engine for quantities.** `scripts/market_weights.py` imports
  `t212_holdings` rather than re-reading the CSVs, so the cutoff and FIFO
  split are the sync's. It fetches nothing: closes and ECB rates come in a
  JSON the run writes from what it already fetched. It runs in the repo
  through the device shell; the ECB is reachable only from the built-in
  browser (both shells refused, checked 2026-10-05).
- **Quantities are as of the last export.** A user who buys manually gets
  a table as current as their last T212 export; `METHOD` names the last
  trade the exports contain.

## Whole-skill review, 2026-10-05

A read of every module after the Allocation table landed. The code was clean
(pyflakes, 314 tests); the defects were in the spec, where newer rules had not
reached older text.

- **Look-through still asked the user for weights.** Mode C told a run to ask
  for portfolio weights and to say "not computed" when none were given. Its
  weights are now Allocation's `Weight (market)`; a named set still asks.
  `lookthrough_problems` checks each Total against its cells and that no
  `via <fund>` cell exceeds that fund's own weight.
- **Allocation's as-of was the Performance end, always.** That date can lack
  a close (Monday evening, Nasdaq still open) or ECB rates (TARGET
  holidays). It is now the latest date with all closes and the rates; the
  2026-10-05 live run already did this unprompted.
- **stock-brief had no EDGAR route rule.** The browser-only rule and the
  WebFetch Form-4 misread lived only in etf-brief's Stocks table, so a stock
  brief could still WebFetch `data.sec.gov`. stock-brief now carries it.
- **"No target language" in RULES' checklist** meant price targets. With a
  `Target` column from `pies.md` in every Mode C run it read as a ban on the
  user's own allocation; the line now says price-target.
- **SKILL.md called portfolio.md "holdings and weights".** They are targets.
  portfolio.md's own 2026-09-16 look-through, computed on targets, is marked
  superseded rather than deleted (it is the record of that day).
- **The scheduled run logged outside the journal's rules**: bare output,
  `*-weekly-brief.md`, written over any same-day file. It now appends a
  run-journal entry to `log/<date>-etf-brief.md`. The two earlier files stay.

## Full holdings files for overlap and look-through, 2026-10-09

Holdings overlap and look-through ran on factsheet top 10s, so both were
floors: MEUD · EIMI read `0` although MEUD holds the Polish and Greek banks
EIMI holds, and a company outside a fund's top 10 vanished from the
look-through.

- **`scripts/fund_holdings.py` reads every row.** SSGA's daily xlsx (1,263
  rows on 2026-10-08), Amundi's product API (614), iShares' UK CSV (~3,000)
  and Vanguard's holdings API (512). All four were confirmed in the built-in
  browser on 2026-10-09 before any code was written.
- **The script fetches, not the browser.** ~5,000 rows a run cannot go
  through the conversation and stay checkable, so the four hosts go in the
  shell's allowed domains. Until they are, `fetch` names each refused host;
  on 2026-10-09 all four still returned 403 from the PC's shell, so the
  parsers are tested on fixtures in each file's observed shape and the first
  live `fetch` is the check that they read the real files. Raw files are saved unchanged under
  `data/holdings/`, which `.gitignore` already keeps out of the repo.
- **One company per issuer.** US/CA ISINs group by the CUSIP's first six
  characters (Alphabet A + C); other ISINs exactly. iShares publishes no
  ISINs, so EIMI matches MEUD through ticker + exchange mapped to the
  Bloomberg code MEUD's file carries. Name matching across issuers was
  rejected: the same company is spelled differently by each.
- **Look-through re-uses `market_weights`** on the same `prices.json`, so its
  fund weights are Allocation's printed `Weight (market)`, to the cent.
  Total is the sum of printed cells, so `lookthrough_problems` re-adds every
  row exactly.
- **Vanguard is month-end.** No daily file exists for VUSA; the heading
  prints each fund's as-of instead of pretending the files share one date.
- **stdlib only.** The xlsx is read with `zipfile` + `ElementTree`, so the
  script needs nothing installed on the PC.

## Holdings files fetched by GitHub Actions, 2026-10-10

The allowlist route above cannot work on a Claude Pro plan: Pro has only a
network on/off switch, and "on" reaches package registries and GitHub. Adding
domains is a Team/Enterprise owner setting. Both the PC shell and Claude's
workspace got a policy 403 from all four issuers on 2026-10-10.

- **A GitHub Actions job fetches instead.** `.github/workflows/holdings.yml`
  runs `fund_holdings.py fetch` daily on a GitHub runner, which has open
  internet, and force-pushes the raw files plus `fetch.log` to the
  `holdings-data` branch. One commit, replaced each run, so the repo does not
  grow by ~1 MB a day. A fund that fails makes the run fail, and GitHub
  emails the owner.
- **First live run (1514ec0) read all four.** SPPW 1,255 rows, MEUD 614, EIMI
  2,995, VUSA 512; every file passed the checks, so the parsers built on
  fixtures read the real files. No issuer blocked GitHub's servers.
- **The brief carries the files across as files.** Claude clones the branch
  in its workspace and `device_commit_files` them into `data/holdings/` on
  the PC, where `report` runs with the T212 data and `prices.json`. The PC's
  git cannot pull the private repo, so it is not asked to.
- **Real files showed one matching fault.** `name_key` dropped "Holdings",
  folding PSK Inc into PSK Holdings and Youngone into Youngone Holdings —
  different companies. It now drops legal-form words only. EIMI's 0.01
  rounding leaves 1,227 of 2,957 equity rows at `0.00`; METHOD now counts
  them.

- **A failed fund keeps its last good file (2026-10-10).** The branch is one
  commit replaced each run, so a single issuer being down used to erase that
  fund's previous file and push the brief back to top-10 depth. The job now
  copies the last good file across from the previous branch and logs
  `carried over` in `fetch.log`; the run still fails, so GitHub still emails.

## Country look-through, 2026-10-10

`portfolio.md` carried "US exposure, all sources: ~62%" from 2026-09-16:
target weights, a June factsheet, top 10s. With full holdings files and
market weights the figure can be measured.

- **A Countries table from the same `report` run.** Every holding in the four
  issuer files carries a country; via cell = fund weight × the fund's % in
  that country ÷ 100. Direct stocks take the country the fund files give the
  same company, so no country is looked up anywhere else. First live run:
  United States 64.25 of 99.82 (2026-10-09 market weights).
- **The four country fields are not the same measurement.** SSGA: trading
  country; Amundi: country of risk; iShares: location; Vanguard: Bloomberg
  ISO. Spellings are aligned (`Korea (South)` → South Korea, `UAE`, ISO
  codes); the difference in basis is printed in METHOD, not normalised away.
- **Fold small countries, keep the sums.** Countries under 0.50 total fold
  into one Other row cell by cell, and a Total row closes the columns, so the
  table re-adds across and down. `contract.countries_problems` checks both.
- **Half-up rounding in both scripts.** `fund_holdings` used Python's default
  half-even; `market_weights` rounds half up. They now agree, so a 0.045
  cell is 0.05 in both. Today's Look-through printed the same either way.

## Any broker, and setup without GitHub, 2026-10-13

Before launch, setup took six steps and a GitHub repo, and "my portfolio"
worked only from Trading 212 exports. Most people who would try BuffettBot use
another app, and many have never made a repo.

- **One broker-neutral file, `me/holdings.csv`.** ISIN, quantity, kind
  (fund or stock), optional group and target %. Every broker can produce
  what it needs: a positions export, a buy/sell history, a screenshot, or a
  typed list. `scripts/import_holdings.py` writes it; Allocation,
  Look-through and Stocks read it, and it wins over a Trading 212 sync when
  both exist. Trading 212's full sync stays for cutoff and FIFO.
- **Columns by header, ISINs by check digit.** Headers are matched in
  several languages; an ISIN is also found in any cell when its check digit
  passes, so a `Symbol/ISIN` or `Product` column still yields it. A wrong
  check digit is refused, including one the run supplies.
- **Ask, don't guess, where a guess would be a wrong number.** A row without
  an ISIN, a file without a quantity column, a history with splits or
  transfers, or sells exceeding buys stops the write with what is needed. A
  quantity is never value ÷ price. `kind` is the one guess, from the name,
  and the summary marks it for the user to confirm.
- **Re-import keeps decisions.** Kind, group and target come from the
  existing file by ISIN, so a fresh export only moves quantities.
- **Any ECB currency.** Prices in CHF, PLN, SEK and so on are valued when the
  run supplies that ECB rate, not refused.
- **No targets is a valid portfolio.** Target and Diff print `-`, and the
  contract checks a `-` target carries a `-` diff.
- **GitHub is optional.** Files live in a folder on the user's computer, in
  their own repo, or nowhere (attach each time). Only the repo brings full
  holdings files; without it a fund falls back to its factsheet top 10, as
  before when the branch could not be read.
- **Setup is one screen.** Disclaimer, where files live, how to add holdings.
  Currency, length, lenses and circle of competence default and are changed
  on request. Briefs never wait for setup.
- **Any-broker scripts run in Claude's workspace**, from the skill's own
  `scripts/`, so they no longer need the computer's shell; the zip now
  carries `import_holdings`, `market_weights` and `fund_holdings`.

## Demo portfolio and quick briefs, 2026-10-15

Both for the 1 November launch: a newcomer should see a full report before
they set anything up, and a brief should not spend a large part of a Pro
plan's usage when the user only wants the scorecard.

- **The demo is frozen data, not a live run.** A live demo needs the
  desktop browser for fund closes and GitHub for full holdings files, which
  a newcomer on the web or a phone has neither of, and it would spend the
  most usage at the moment a user is deciding whether to keep the skill.
  `scripts/demo.py` reads a snapshot shipped in the zip and fetches
  nothing. `Data as of` is the snapshot's date with `frozen — not today's
  prices` beside it, so rule 5 holds: stale is acceptable when labelled.
- **The snapshot is fetched on GitHub's runners**, the same reason as the
  holdings files (2026-10-10): `.github/workflows/demo-data.yml` runs
  `scripts/demo_snapshot.py` monthly and commits `demo/data/`, and each
  release ships the latest. The runner reaches SSGA, the London Stock
  Exchange, Nasdaq, Yahoo, the ECB and EDGAR directly (checked 2026-10-15);
  Actions logs are not readable from Claude's session, so a failed run
  leaves its output on the `demo-data-log` branch.
- **Two SSGA funds and two US stocks.** SSGA's files carry an ISIN, country,
  sector and currency on every row, so the demo's look-through, overlap,
  sector and currency tables come out complete; an iShares file has no ISINs
  and would only match through a third fund, and Vanguard's carries no
  sector. ACWI IMI and the S&P 500 overlap by most of the latter, and
  Amazon and Coca-Cola sit in both, so Look-through shows a company owned
  three ways. The portfolio is synthetic and none of it is the author's.
- **Closes from the exchange, checked against Yahoo.** Yahoo's chart data
  leaves some completed LSE sessions null (2026-10-14 for both funds); such
  a close is used from the exchange alone and said so on the Confirmation
  line, never filled from another day. Two sources that disagree by more
  than 0.10% stop the refresh.
- **Earnings dates only from the company's page.** Coca-Cola's events page
  lists dated event links; Amazon's renders its events by script, which the
  runner does not run, so its cell says that rather than `not announced`.
- **A quick brief is a mode, not a shorter render.** `Mode: Stock brief
  (quick)` and `Mode: Fund brief (Mode A, quick)` print the scorecard and
  any named lenses, and the references list the only documents they open,
  because the saving is in fetches, not in printed rows. The scorecard is
  the same scorecard, so a quick `Met` is a full `Met`. The contract checks
  the layout and that `METHOD` names what was skipped and offers the rest.
  `Report length: quick` in the profile makes it the default.
- **The issuers' holdings files are not shipped (same day, before v1.2.0).**
  SSGA's files say no part may be reproduced or passed to third parties
  without its written consent, and the first version committed them to the
  repo and the zip. The snapshot job now reads them on the runner, runs
  `fund_holdings.py report` on the demo portfolio there, and keeps only its
  output (`demo/data/fund_report.txt`) — the weights of the largest
  companies and the country, sector and currency splits, the depth a
  factsheet publishes — plus each file's as-of and row counts. `demo.py`
  pastes that report and refuses it if `demo/holdings.csv` or `prices.json`
  changed since it was computed. Tests fail if an `.xlsx` is tracked under
  `demo/` or reaches the zip. A check on 2026-10-18 found no issuer file in
  any commit on any branch or tag, no force pushes, and no pull requests left
  in the repo, so nothing remains to purge before it goes public.

## Hidden bets and the portfolio card, 2026-10-18

**DECIDED 2026-10-18.** Two features for the 1 November launch, chosen
because they rest on what no other free tool has — every holding of every
fund — and because a card people post is how others find the skill.

- **Hidden bets is read from every company the cells reach**, not the rows
  Look-through prints, so `--top` never changes it. A company counts when it
  is reached through two or more holdings (a direct stock and a fund, or two
  funds) and its Total is 1.00 or more. The columns are arithmetic only:
  each route, the largest, the Total, and `Added by the others` = Total −
  Largest part — the exposure a single holding's page never shows. The name
  says what the table finds; no word of judgement goes beside it (rule 6).
- **The demo reads it back from its snapshot's Look-through table** until
  the next Demo data run prints the table itself. That is complete only when
  1.00 is above the smallest fund-only Total printed there (0.57 in the
  2026-10-15 snapshot), and `demo.py` prints `Not available` rather than a
  partial list otherwise.
- **The card draws a checked draft, nothing else.** `scripts/card.py` runs
  the output contract first, then lays out cells of the draft's tables as a
  1080×1350 image (LinkedIn, X and Instagram show that shape whole). One
  layout is written two ways — SVG always, PNG through Pillow when installed —
  so long names are cut identically in both.
- **Percentages only.** No quantity, close, value or currency amount is
  drawn, so a card can be posted without saying what anyone has; a test
  checks every bare number on the demo card is a count or the date. A demo
  card says `DEMO · SYNTHETIC PORTFOLIO`.
- **The card's look is an annual letter** (revised the same day, at the
  user's ask): cream paper, ink, hairline rules, Fraunces for the title and
  the large figures, Inter for labels, one green and one ochre. The
  signature is a split bar under the hero figure: in ink, what a single
  holding shows; in ochre, what the others add. The two faces ship in
  `assets/fonts/`, subset to Latin (about 140 KB, SIL OFL 1.1, licence
  beside them), so the PNG and the SVG look the same wherever the skill
  runs; the SVG carries them inline.
- **The hero is the bet with the most `Added by the others`**, not the
  largest Total: the largest Total is usually a stock bought on purpose,
  while the most added is what the user did not see.
