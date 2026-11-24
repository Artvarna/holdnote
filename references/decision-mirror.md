# Decision Mirror

Reference for Holdnote (`holdnote`). Follow `RULES.md`.

"Did my choices help, or would I have done better doing nothing clever?"
The Mirror answers it with a **lazy twin**: someone who put the same money
in on the same days, bought one boring fund, and never touched it. It
compares the user with the twin today, then shows which holdings and which
waiting cash made the gap.

It describes the past only. It never says what to do next, never forecasts
and never annualises: a gap is arithmetic, and what it means is the user's
(rules 6, 8, 11).

## Trigger

"Did my trades beat the market / the S&P 500?", "me vs my lazy twin",
"would I have done better just buying the index?", "how good are my
picks?", "decision mirror", "how did my decisions do?". The possessive and
the user's own trades are the point: it is the one module built on the
user's transaction history rather than on a holdings snapshot.

- **Not here:** how the portfolio moved this week (Mode C → Performance);
  why one instrument moved (Price move); two funds compared (Head-to-head).
- **One portfolio per output.** Two accounts are two runs.

## The two twins

Both twins buy the locked benchmark at its NAV of the day the money moved,
or the newest NAV before it on a day with none. Neither pays fees.

| Twin | What it does | What its gap shows | When |
|---|---|---|---|
| **Lazy twin** (the headline) | Every deposit goes into the benchmark at once; a withdrawal takes the same EUR out | Everything: what was picked, and cash left waiting | The account is the user's alone, and the export reaches its first deposit |
| **Picks twin** | Every buy of a holding puts the same EUR into the benchmark that day; selling N% of a holding sells N% of that holding's twin | What was picked, holding by holding; the holdings add up to it exactly | Always |

`Lazy-twin gap = what you picked + cash waiting`, exactly: the breakdown
table adds up to its own total to the cent.

A **shared account** (a Trading 212 account with an ownership cutoff) gets
the picks twin only: its cash pool mixes the holder's money with the user's,
so a deposit twin would credit the user with money that is not theirs, or
miss money they spent. The output says so in one line.

## The benchmark is locked before the result

`profile.md` → Settings → `Mirror benchmark`. The default is **SPYL**
(SPDR S&P 500 UCITS ETF (Acc), IE000XZSV718, TER 0.03%): accumulating, so
its dividends are already in its NAV, and bought in EUR on Xetra, so the
twin pays no currency fee.

The lock exists because a benchmark picked after seeing the result is the
one the user beat. On the first Mirror run with the setting blank, before
anything is computed, ask once (`AskUserQuestion`):

- Question: `Your lazy twin needs one fund to buy. Lock it now, before you see a result, so the comparison stays honest.`
- Options: `S&P 500 (SPYL)` · `I'll pick another`

Write the answer into `profile.md` with today's date
(`SPYL (IE000XZSV718), set 2026-11-19`), commit `Profile: Mirror benchmark`,
and say so in one line. Another fund needs its NAV history attached (below).
A later change is a new value with a new date, and the run journal notes the
old one; the Mirror passes the locked ticker as `--benchmark` and refuses a
NAV file for any other fund.

The NAV history must start before the user's first transaction. SPYL's
starts in 2023: a history older than that gets `Not available` with the
date, never a different fund swapped in.

## Inputs

| Input | From | Notes |
|---|---|---|
| Trades | Trading 212 exports + `ownership.md` (`--data-dir`, `--ownership`), the same engine and FIFO split as the portfolio sync; or `me/transactions.csv` (`--transactions`) | A holdings snapshot (`holdings.csv`, a screenshot) cannot be mirrored: it has no dates. Say so and offer the template |
| Benchmark NAV | The GitHub Action's `holdings-data` branch: `bench-SPYL-YYYY-MM-DD.csv`, written by `mirror.py nav-import` from SSGA's own NAV history file. Without GitHub, the user attaches that file: SSGA's SPYL page → Performance → NAV history (xlsx) | Issuer data, tier 2 (rule 4). Run `nav-import` on an attached file |
| ECB rates | Same branch: `ecb-YYYY-MM-DD.zip`; without GitHub, the user attaches `eurofxref-hist.zip` from the ECB's reference-rates page | SPYL's NAV is in USD; every NAV is restated at the rate of its own day |
| Today's closes | The closes JSON of `references/portfolio-sync.md` → Mode M, fetched the same way, for every holding still held | One `as_of` date for all of them |

**`me/transactions.csv`**, for any broker: the template is
`templates/me/transactions.csv`. One row per buy, sell, dividend, deposit,
withdrawal or interest payment; `amount` is the cash that moved, fees
included. Converting another broker's transaction export into it is allowed
only as a mapping the user sees: print the first five mapped rows beside the
originals and ask once before running. Never fill a row from memory.

## Run it

In the user's repo (or Claude's workspace with the files copied in):

```
python3 <skill>/scripts/mirror.py report \
  --nav bench-SPYL-2026-11-19.csv --fx ecb-2026-11-19.zip --prices closes.json \
  --data-dir data/t212 --ownership me/ownership.md \
  --benchmark SPYL --label "the S&P 500 (SPYL)" \
  --theses me/theses --watch me/watch.md --json mirror.json
```

`--transactions me/transactions.csv` replaces `--data-dir`/`--ownership`. A
Trading 212 account that is the user's alone has no `ownership.md`: pass
`--cutoff` with the date of its first deposit instead.
Exit 1 prints `Decision Mirror: Not available - <reason>`: that is the whole
`RESULT`, under `STATUS: Halted`, and the reason is never worked around.

## The output

`Mode: Decision Mirror`, then the script's tables exactly as printed: the
Lazy twin table and its breakdown (when there is a lazy twin), the Picks
twin table, the per-holding table, the sells table, and its closing lines.
Its `Method` lines go into `METHOD` as they are. No figure is recomputed,
rounded again or restated in prose; a TL;DR may quote the headline gap and
nothing the tables do not print.

| Table | Read it as |
|---|---|
| Lazy twin | Account today (holdings + cash) against the twin's; gap as % of money deposited |
| Where the gap comes from | Picks + cash waiting = total, to the cent |
| Picks twin | Your buys, and what they are worth today held, sold or paid out, against the same buys in the benchmark |
| Per holding | Each holding's share of the picks gap, and its **Thesis** column: `none`, `on file (date)`, `watched`, `tripwire met (date)` |
| Sells | Each sale's proceeds against the same shares at today's price: a hindsight figure, labelled as one, never "cost" or "mistake" |

The closing lines always print, and are never trimmed:

- `Largest single holding gap:` the one holding the picks gap rests on most.
  It is the check on luck: a gap carried by one holding is one holding's
  story, not a pattern.
- `History: N months, M trades.` — with `This much history says little
  about skill.` under 36 months or 20 trades.
- `Not included:` a holding whose FIFO split the export cannot settle, named
  with the reason (rule 9: partial coverage is stated, not estimated).
- `Share line:` the one sentence the user may post: the headline gap as a
  percentage only. **No EUR figure goes on a card or a share line** unless
  the user asks for one by name.

### Wording

The gap has a sign and nothing else. Never "cost you", "lost", "won",
"beat", "mistake", "should have", "better", "worse", "regret" — in the
tables, the TL;DR or the reply around them. "Kept instead of sold" is a
fact about today's price; whether selling was right is not a fact. Never
annualise: a percentage of ten months is not a yearly rate.

### Next line

`METHOD`'s `Next:` offers one thing: a quick tripwire for the largest
holding whose Thesis is `none` (`references/thesis-watchdog.md`), worded
`Next: say "watch [TICKER]" to get told when something you'd worry about
changes.`

## Card

"Make a card" after a Mirror: `scripts/card.py --mirror mirror.json`,
percentages only, the benchmark and both dates on it, and the
`This much history says little about skill` line when the run printed it.
It writes two sizes: `mirror-card.png` (1080 x 1350, for Instagram and
LinkedIn) and `mirror-card-wide.png` (1200 x 675, the shape X shows in full
in a timeline). Give the user both PNGs as files, with one line saying which
is for where.

## Demo

"Show me the Mirror", "demo the lazy twin": the same script on the shipped
synthetic files, with `--demo`, which prints the line saying every figure is
made up:

```
python3 <skill>/scripts/mirror.py report --demo \
  --nav <skill>/demo/mirror/nav.csv --prices <skill>/demo/mirror/prices.json \
  --transactions <skill>/demo/mirror/transactions.csv \
  --watch <skill>/demo/mirror/watch.md --label "a demo index fund (synthetic)"
```

Print it as it is, then one line: `Want yours? Attach your Trading 212
export, or fill in the transactions template, and ask "me vs my lazy twin".`

## Halts

| Halt | Says |
|---|---|
| First transaction before the NAV history starts | the date it starts; no other fund is swapped in |
| NAV or rate file ends more than 5 days before a date it must price | "needs fetching again" |
| A gap of more than 5 days inside the NAV file | the dates around the gap |
| Locked benchmark ≠ NAV file | both names |
| A sell larger than the holding before it (transactions.csv) | the row; the file does not reach the first buy |
| A Trading 212 row the engine does not know that moves shares (a split) | the row; from `t212_holdings.py` |
| BGN totals without the fixed rate in `ownership.md` | the line to add |
