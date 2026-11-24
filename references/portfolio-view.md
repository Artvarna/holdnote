# Portfolio view (Mode C)

Reference for Holdnote (`holdnote`). Follow `RULES.md`. This is Mode C of
`references/etf-brief.md`, kept in its own file so a fund or index brief does
not read it. Read `references/etf-brief.md` with it: its Three modes, Step 1
(resolve documents), the output skeleton under Mode A → Output, Document
handling, Validation and Self-check all apply here. A pointer of the form
"etf-brief.md → Mode C → X" means section X of this file.

## Mode C — Portfolio view

### Comparison table

One row per fund. Columns: Ticker · Index · Universe (DM/EM/global,
size segments) · TER · Replication · Acc/Dist · Currency · Domicile · AUM ·
Top-10 concentration. AUM is the fund's, in its base currency, from the
factsheet; a cell that can only give a share class's says so
(`EUR 46,776m, share class [justETF]`) — see Fund facts below.

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
Without the browser, WebFetch reads the same PDFs: ask for the countries as
a list, not the footnote as a quote (`references/no-browser.md` → Fund
documents).

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
for: `fund_holdings.py report --factsheets factsheets.csv`, the file written
as `references/any-broker.md` → Look-through without GitHub says. The
table's heading then says `top-10 depth, partial` for that fund and
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
| A portfolio card ("make a card", `references/cards.md`) | Allocation, Holdings, Look-through, Hidden bets, Countries, Sectors |
| Countries · sectors · currencies | Allocation, then Countries · Sectors · Currencies |
| How it performed ("how's my portfolio done this week") | Performance |
| What changed in my funds' holdings | Holdings changes |
| My stocks' earnings dates or filings | Stocks |
| "Full report", "everything", or the scheduled weekly brief | all twelve; the scheduled brief then runs the Thesis Watchdog (`references/thesis-watchdog.md` → The weekly run), whose `Subject:` line is the email's subject |

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

A Performance question that asks why ("what's driving my portfolio",
"why is my portfolio down") still gets moves, not reasons (rule 7). Its
`METHOD` ends with `Next: say "why did <ticker> move" for its dated events
and reported reasons`, naming the row with the largest move by size, which
opens `references/price-move.md` for that one instrument.

A Performance question that names a benchmark over the user's whole
history ("have I beaten the S&P 500 since I started?") gets the
Performance table for the period asked, and `METHOD` ends with
`Next: say "me vs my lazy twin" to see your own trades against it`
(`references/decision-mirror.md`): a period's move is Performance, the
user's decisions against doing nothing are the Mirror.

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
| EIMI | iShares UK product-data JSON (`/varnish-api/.../get-product-data`, `holdings.all`), the CSV addresses as fallback | daily | ISIN (since 2026-11-16); ticker + exchange from a CSV fallback, weights to 0.01 there |
| VUSA | Vanguard UK holdings API (`/gpx/graphql`) | **month-end** | ISIN |

**One company, not one share class.** US and Canadian ISINs contain the
CUSIP, whose first six characters name the issuer, so Alphabet A and C are
one company in every column. Other ISINs match exactly. EIMI's file now
carries ISINs too (iShares' JSON, since 2026-11-16); from its older CSV
fallback, which has none, its rows match MEUD's through ticker and exchange
(`PKO` on Warsaw is `PKO PW`), which is how the Polish and Greek companies
both funds hold are found — at top-10 depth MEUD · EIMI read `0`.

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

**EDGAR's full JSON files are browser-only.** `data.sec.gov` refuses both shells (the cloud
workspace's and the user's computer's) at the proxy, so it is fetched from a
tab on `data.sec.gov`: open one submissions URL with `preview_start`, then one
`fetch()` loop over the three CIKs from that tab, parsing
`filings.recent` (`form`, `filingDate`, `reportDate`, `items`) in the page.
WebFetch reached the file but summarised it: on 2026-10-01 it dropped the form
types and offered a Form 4 dated 2026-09-29 as the latest periodic report. It
is never a route for this table. Without the browser, the filing columns come
from each stock's cover-page shares concept, which lists every 10-K and 10-Q
with its `filed` date and accession number, and 8-Ks from EDGAR full-text
search (`references/no-browser.md` → SEC EDGAR); the CIK from EDGAR company
search, its entity name matching `portfolio.md`'s Company.

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
- Comparison, Structural and Holdings still run from factsheets, KIDs and
  index factsheets over WebFetch, through `references/no-browser.md`'s
  read-back gate.
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

**A factsheet's figures are read from its text, never from an unchecked
WebFetch summary.** Open the PDF in the built-in browser and read its text,
or download it and extract the text in a shell. WebFetch summarises: on
2026-10-03 two runs WebFetched the same SPDR factsheet and were given two
different top-10 totals (30.67% and 31.67%), neither printed in the
document. So with the browser up, a figure WebFetch reports is only a lead.
Without the browser, WebFetch is the route, and a figure prints only once
`references/no-browser.md`'s read-back gate confirms it — the top 10 adding
to the factsheet's printed total, the TER matching the KID — which is the
check that would have caught both 2026-10-03 readings.

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

