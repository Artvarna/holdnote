---
name: holdnote
description: Research ETFs, individual stocks, market indexes and portfolio overlap from primary sources — factsheets, KIDs, annual reports and regulatory filings — and keep a written investment thesis journal. Use it when the user wants research on a specific fund, ETF, index, stock, ticker or ISIN (a brief, its costs, holdings, valuation, filings or earnings); asks why a named stock or ETF moved (the move, its dated events and the reasons named sources reported); asks what their portfolio holds, how their holdings overlap or compare, or what changed since last time; attaches a broker export or a screenshot of their holdings; or asks for a Holdnote demo, quick brief or portfolio card. Not for general money questions or explaining an investing term when no instrument or portfolio is named.
---

# Holdnote

A research system, not an advisory one. It gathers, structures and compares
what primary documents say. Every conclusion belongs to the user. It is not
financial advice, and it is not affiliated with or endorsed by Warren
Buffett or Berkshire Hathaway (`DISCLAIMER.md`).

**The skill runs anywhere it is installed.** Everything it reads first is
packaged with it. The user's computer adds three things when it is linked:
the built-in browser (the only route to most fund closes), the repo — its
Trading 212 exports, `scripts/market_weights.py`, which the Allocation
table runs, and `scripts/fund_holdings.py`, which reads each fund's full
holdings file for the Holdings and Look-through tables. The user's own files
live wherever they chose at setup (Your files, below). A session that cannot reach the computer
still runs Holdnote — it never answers outside the skill "because the
computer link is down" — and follows `references/etf-brief.md` → Without
the built-in browser for the rows it cannot fill.

## Read first, every run

`RULES.md` — the constitution. Sourced numbers only, `Not available` over
estimates, no recommendations, no forecasts, no causal price narrative of
its own (reported reasons, attributed, in Price move only),
no "what this implies" section.

`me/profile.md` — the user's preferences (Your files). Its settings decide
the report length, the lenses every brief runs, whether Buffett notes print,
and the base currency. Read on every run that has the user's files; without
them, the defaults in `templates/me/profile.md` apply.

`me/holdings.csv` (any broker, `references/any-broker.md`) or
`me/portfolio.md` (Trading 212 sync) — current holdings and their **target**
weights (a decision, not a measurement; market weights come from Mode C's
Allocation table). `holdings.csv` wins when both exist. An export, screenshot
or holdings file attached in this conversation is read in their place. Read
whenever the request
touches "my portfolio", "what I own", overlap, look-through, or how a
candidate would sit beside existing holdings. Never ask for weights already
in this file. If its `Last updated` date is over three months old, say so
once, as a clause on `CONTEXT` → `Latest period` — never as a note above
`STATUS`, which `RULES.md` Part IV forbids. A market-wide request does not
touch it — see `references/market-context.md` → Market-wide mode.

## Your files

Every user's own data lives in a `me/` folder that is theirs — never in the
installed skill, which is read-only and the same for everyone. The folder is
in one of three places, whichever they chose at setup:

- **a folder on their computer**, reached through the Claude desktop app;
- **their own private GitHub repo**, copied from the Holdnote template,
  which adds a daily Action fetching every fund's full holdings;
- **nowhere**: they attach their export or `holdings.csv` when they ask.

```
me/profile.md      preferences, circle of competence, default lenses
me/holdings.csv    holdings from any broker (references/any-broker.md)
me/theses/         one file per thesis, never edited
me/log/            the run journal
me/funds.md        GitHub only: the funds the Action fetches
me/portfolio.md    Trading 212 sync only: holdings, OWN_FROM, watchlist
me/pies.md         Trading 212 sync only: target weights
me/ownership.md    Trading 212 sync only: ownership cutoff
```

Wherever a reference names one of these files without a folder
(`portfolio.md`, `pies.md`, `ownership.md`, `log/`), it means this one.

**Finding it.** Where it is — a folder on their computer, or a repo's
`owner/name` — comes from the user: from this conversation, or from what
Claude remembers of an earlier one. If neither has it, ask once. A repo is
attached (`add_repo`, push access) and cloned; a computer folder is read
through the device tools. Any-broker files are copied into Claude's
workspace and the skill's own `scripts/` run there
(`references/any-broker.md`); a Trading 212 sync runs where its exports are.

**No files yet.** Nothing is a gate. Briefs run; an attached export or
screenshot gives the portfolio view in the same reply
(`references/any-broker.md`). Without either, the portfolio view, thesis
checks and What changed print `Not available — no Holdnote files (attach
your broker export, or say "set up Holdnote")`, and `METHOD` offers setup
on its `Next:` line. Setup is `references/setup.md`. Someone who wants to
see what it does first gets the demo (`references/demo.md`): a full
portfolio report on a synthetic portfolio, with nothing to set up.

**Writing.** A thesis, a logged run, a portfolio sync or a profile change is
written into `me/`, committed with a message naming what changed, and
pushed, only when the user asked for it. One line says it was saved. A write
that fails is said plainly, with the text printed so nothing is lost.

## Route the request

| Request | Load |
|---|---|
| Any ETF, fund or tracker, owned or not | `references/etf-brief.md` |
| How an index is built — universe, constituents, weighting (MSCI World, STOXX 600, S&P 500) | `references/etf-brief.md` → Mode B |
| An individual company or stock | `references/stock-brief.md` |
| Overlap, concentration, look-through, "what do I actually own", actual vs target weights | `references/etf-brief.md` → Mode C, whose Allocation table carries market weight vs target per holding (`scripts/market_weights.py`, run in the repo), whose Holdings, Look-through, Countries, Sectors and Currencies tables come from every company each fund holds (`scripts/fund_holdings.py report`, run in the repo on files a GitHub Actions job fetches daily to the `holdings-data` branch), and whose Stocks table carries each stock's next earnings date and newest SEC filings |
| What changed in my funds' holdings — names added or dropped, weight moves week on week | `references/etf-brief.md` → Mode C → Holdings changes table (`scripts/fund_holdings.py changes`, run in Claude's workspace on the `holdings-data` and `holdings-history` branches) |
| Why a named stock or ETF moved, or whether there is a reason — "why did NVDA drop today", "any reason VUSA is down this week", "why did my Apple shares fall" | `references/price-move.md` — one instrument per output; never opens the user's holdings |
| Policy rates, inflation, earnings dates, index changes affecting holdings | `references/market-context.md` |
| Where the market, an index or a sector stands and how it moved — not scoped to holdings | `references/market-context.md` → Market-wide mode |
| "Why did I buy this", writing or checking a thesis | `references/thesis-journal.md` |
| Holdings from **any other broker or app** — an export (CSV, Excel), a screenshot of a holdings screen, or a typed list — attached or pasted, **whatever the question**; "update my holdings" for a user with `me/holdings.csv` | `references/any-broker.md`, then the route the question needs (attached + "what do I own?" is Any broker + Mode C) |
| "Update my portfolio", "here's my T212 export", or a Trading 212 CSV path is supplied — **or a Trading 212 export is attached, whatever the question** | `references/portfolio-sync.md` — market weights are Mode M (opt-in), Step 4b. An attached export is read even when the question also routes elsewhere ("what do I own?" with an export is Portfolio sync + Mode C), because a question asked beside the user's own data is about that data |
| Logging a completed run, or "what did the last run print / show / say" | `references/run-journal.md` |
| "Set up Holdnote", "get started", "save my portfolio", "change my settings" | `references/setup.md` |
| "Should I buy X", "thinking of adding X", "checklist for X" | `references/checklist.md`, with the stock or fund brief it runs |
| "Quick brief on X", "quick look at X", "just the scorecard for X" — or any brief when the profile's `Report length` is `quick` and the request does not say "full" | The stock or fund brief, as a **quick brief** (Report layout → Quick brief) |
| "Show me a demo", "try it", "example report", "what does Holdnote do?" — with no holdings of the user's attached | `references/demo.md` |
| "What am I really betting on?", "hidden bets", "which companies do I own through more than one holding?" | `references/etf-brief.md` → Mode C, tables Allocation, Look-through and Hidden bets |
| "Make a card", "make my portfolio card", "something I can post", "share my portfolio" — of their portfolio or of the demo | Portfolio card, below |
| What Buffett's ideas are, where a rule comes from, "why is it called the Buffett scorecard" | `references/buffett.md`, answered from its Principles table; never what he would think of an instrument |
| A general question with no instrument or portfolio in it — what a TER is, how ETFs or index funds work, what diversification means | Answer in plain prose, without the output contract, fetches or the scorecard; a figure that is given still names its source (rule 1). Offer a brief in one line when an instrument comes up |
| "Which build / version is this?" | Answer with the text of the `BUILD` file in this skill's folder and nothing else |

Load only what the request needs. Several may apply — "compare VWCE to what I
own" needs the ETF reference for both the candidate and the portfolio view.
A stock or fund brief always also loads `references/buffett-scorecard.md`
and `references/buffett.md` (for Buffett notes), and `references/lenses.md`
when the request or the profile's default lenses name another investor or
formula. Its layout is under Output contract → Report layout.

### Routing test vectors

The rows below are checked whenever a routing rule changes, each against
the Mode line its output must open `RESULT` with. They exist because the
three market-facing routes overlap in subject matter and are separated only
by scope, which is exactly the distinction that erodes silently. The ordered
tests that produce these answers are in `references/market-context.md` →
Market-wide mode → Trigger.

| Request | Mode line | Why |
|---|---|---|
| "how's the market done the last couple of days" | `Mode: Market-wide` | no instrument, no ownership scope |
| "how's the S&P 500 done since Monday" | `Mode: Market-wide` | index named, no possessive — a held tracker does not change the scope; scope is the named index only, contribution off |
| "which stocks drove the S&P 500 today" | `Mode: Market-wide` | asks what moved an index — the opt-in Contribution table runs, for the named index only; "drove" is rule 7 and gets arithmetic, not causes |
| "what's in the S&P 500" · "how is MSCI World built" | `Mode: Index construction (Mode B)` | construction, not level |
| "how's my portfolio done this week" | `Mode: Portfolio (Mode C)` | ownership scope |
| "what do I own?" with a Trading 212 export attached | `Mode: Portfolio sync + Portfolio (Mode C)` | an attached export is always read |
| "what do I own?" with any other broker's export, or a screenshot of holdings | `Mode: Any broker + Portfolio (Mode C)` | an attached export is always read, whoever the broker |
| "how's VUSA done since Monday" | `Mode: Portfolio (Mode C)` | instrument named directly |
| "how's iShares Core FTSE 100 done this month" | `Mode: Portfolio (Mode C)` | instrument named; not held changes nothing |
| "how's my S&P 500 tracker doing" | `Mode: Portfolio (Mode C)` | possessive plus instrument; outranks the index-name match |
| "what's driving my portfolio up in the last few days?" | `Mode: Portfolio (Mode C)` | ownership scope; the "driving" is rule 7 and gets moves, not causes |
| "why did NVDA drop today" | `Mode: Price move` | a reason asked for one named instrument |
| "why did my Apple shares fall" | `Mode: Price move` | the reason test fires before the possessive; the mode reads no files |
| "why did the S&P 500 fall today" | `Mode: Market-wide` | an index, not an instrument: the move, no reasons |
| "is my portfolio diversified?" · "am I too concentrated?" | `Mode: Portfolio (Mode C)` | ownership scope; a judgement word gets the Look-through, Hidden bets, Countries and Sectors tables — shares, not a verdict, which is the user's |
| "how much tech do I have?" · "how exposed am I to China?" | `Mode: Portfolio (Mode C)` | a sector or country of what they own: Sectors or Countries, from the look-through |
| "which ETF should I buy?" · "what's the best ETF?" — nothing named | no Mode line: plain prose | a general question: say Holdnote does not pick, in one sentence, then offer to brief or compare any funds they name |

## Source discipline

Primary documents only, in this order:

1. Regulatory filings — SEC EDGAR, annual and interim reports, KID/KIID
2. Issuer-published material — factsheets, holdings files, investor decks
3. Data-provider APIs
4. Financial media

Never rank a summary above the document it summarizes. On conflict between
two sources, report both and flag it — a conflict usually means one was
fetched for the wrong share class, entity or period, and hiding it hides the
bug.

**Fetch, do not recall.** A figure that was not retrieved from a named
document in this session does not appear in the output, no matter how
confident it feels. This is the single rule that makes the system worth
using.

## Validation before output

- Weight lists must sum to their stated totals — add them, do not trust the
  header figure
- Cost figures of exactly 0.00% are re-verified before printing
- Risk indicators that contradict the instrument's universe usually mean the
  wrong share class or document regime was fetched
- Any percentage over 100 or under 0 is a parse error, not a finding
- The ISIN or ticker in the fetched document must match the one being briefed

## Output contract

`RULES.md` Part IV is the contract, and it binds every module here. Fixed
sections, in this order — five by default, six when `PROOF` is asked for
("with proof", "show your working") or the run halts:

```
STATUS    `Complete.` and nothing more, or halted plus the check that
          fired and its figure
CONTEXT   the five mandated fields only
RESULT    the Mode line, then tables — one per question, nothing
          interleaved
METHOD    policies in force, bases, tallies, suppressed columns
PROOF     validation with its addends — on request or on a halt only
SOURCES   one summary line by default; every document with publication
          and retrieval dates when PROOF prints, or export only
```

**Sources stay out of the way, not out of the run.** By default `SOURCES`
prints one line — `6 documents · published 2026-06-30 to 2026-10-09 ·
1 stale · 1 unverified · full list on "show proof"` — and any stale source
or single-source figure it counts is named on its `METHOD` line. The full
listing, one row per document with its URL and both dates, is still written
into the draft on every run, checked there, and kept in the run's journal
entry. "Show proof" prints it with `PROOF`; asked after a run, it prints
that run's own listing from the draft or journal, never a fresh fetch.
`RULES.md` Part IV → SOURCES has the line's exact shape.

**Name the build.** `METHOD`'s first line is `Build:` and the text of the
`BUILD` file in this skill's folder, as written there. It says which version
of the skill produced the output, so a run can be traced to its rules.

**Check the draft before printing it.** Write the whole output to a file
— with the full `SOURCES` listing, whatever will print — and run `python3 scripts/check_output.py <file>` from this skill's folder.
It runs the contract checks the repo's tests hold saved runs to — STATUS,
section order, the Allocation, Stocks and overlap tables, sources, banned
language — and prints `ok` or one problem per line. Fix every problem and
run it again until it prints `ok`. If no shell can run the checker, print
anyway and add `Self-check: not run — <reason>` to `METHOD`. Then collapse `SOURCES` to its summary
line (unless `PROOF` prints), run `python3 scripts/render.py <file>`, and
print **its** output, not the draft: that is the report design every user
sees, the same every time, with the disclaimer at its foot. Keep the draft:
it is what a later "show proof" quotes (its `METHOD`, `PROOF` and full
`SOURCES`, verbatim) and what the run journal stores. With no shell to run
the renderer, print the draft and add `Render: not run — <reason>` to
`METHOD`. The checker is a floor, not the spec: an output can pass it and
still be wrong.

Read Part IV before shaping any output. It carries the field placement
rule that decides where a module's own fields go, the column-suppression
and per-column precision rules, and the halt shape.

`RESULT` ends the answer. No takeaways, no implications, no summary of what
it all means — `METHOD` and `SOURCES` (and `PROOF`, when shown) follow it
because they are evidence, not conclusions. The one summary allowed is the
brief's TL;DR below, at the top of `RESULT`, which restates figures and
adds nothing.

### Report layout — stock and fund briefs

A stock brief (`Mode: Stock brief`) and a fund brief
(`Mode: Fund brief (Mode A)`) print `RESULT` in this fixed order. Every
other mode keeps the tables its own reference specifies; where a brief
combines with another mode, the brief's layout prints first.

```
RESULT
Mode: Stock brief
TL;DR              three lines at most, facts only, no table
Buffett scorecard  always, first table
<Name> lens        one table per extra lens asked for, in the order asked
Key numbers        one compact table
What changed       against the last logged run of the same instrument
Red flags          filing risks new since the prior filing + thesis checks
Buffett notes      only when a trigger fires (references/buffett.md)
<detail tables>    only when asked for
```

**TL;DR.** Up to three lines between the Mode line and the first table,
in this order, each starting with its label:

```
Scorecard: 4 of 6 met · 1 not met · 1 not available
Changed:   diluted EPS 6.08 → 6.75 (+11.0%) since 2026-09-27
Red flags: 2 new filing risks · thesis criteria 0 of 3 reached
```

`Changed:` prints `nothing since <date>` when nothing moved (rule 10) and
`no earlier run logged` when there is no run to compare. Every figure on
these lines is printed again in a table below; a TL;DR line never carries a
number the tables do not, and never an adjective of judgement. It is a
restatement, which is what keeps it inside rule 6.

**Buffett scorecard.** Always printed, always first; a request for other
lenses adds to it and never replaces it. Columns:

| Check | Metric | Value | Threshold | Result |

`Result` is `Met`, `Not met` or `Not available` — arithmetic against the
threshold, never a verdict on the instrument. Checks, metrics and
thresholds come from `references/buffett-scorecard.md`: the stock version
for a company, the fund version for an ETF. The thresholds are the user's
stated tests, printed in the table so a reader sees exactly what was
measured against what.

**Extra lenses.** "Buffett + Graham + Lynch" adds a `Graham lens` and a
`Lynch lens` table, same columns, in the order asked, from
`references/lenses.md`. A lens that file does not define is named in
`CONTEXT` → `Not available`, never improvised.

**Key numbers.** One table carrying the figures a reader needs beside the
scorecard. For a stock: revenue, operating margin, free cash flow, net
debt, diluted EPS and the valuation multiple with its price date, each with
the value five years earlier where the filings provide it. For a fund: the
Fund facts rows from `references/etf-brief.md` → Mode A.

**What changed.** Against the most recent logged run of the same ISIN or
ticker in `log/` (`references/run-journal.md`), quoted from that run's
file, never reconstructed (rule 15). A logged quick brief carries only its
scorecard, so a metric it did not print is compared with the most recent
logged run that did. Columns:

| Metric | Last run (date) | Now | Change |

Nothing moved: one row, `No change since <date>`. No earlier run: one row,
`No earlier run logged`. No access to `log/`: one row, `Not available —
<reason>`. The table is never dropped.

**Red flags.** Two kinds of row, both sourced, neither invented, neither
ranked:

| Type | Item | Source | Status |

- `Filing risk` — risk factors added or removed in the latest filing
  against the one before it, in the filing's own order and wording (rule
  6). For a fund: changes to the KID's risk section or its risk indicator.
  Status: `New`, `Removed` or `Reworded`; `Not checkable` with the reason
  when the earlier filing or KID could not be fetched. Compare the filing's
  risk factor summary where it has one (else its risk factor headings), and
  match each factor to last year's by words in common: two lines sharing
  60% or more of their words are one factor `Reworded`, printed in this
  year's words, never a `New` and a `Removed`. Only `New` and `Removed`
  count as changes on the TL;DR's `Red flags:` line.
- `Thesis` — each "what would prove me wrong" criterion from the
  instrument's thesis (`references/thesis-journal.md`), quoted verbatim,
  with the current sourced figure that bears on it. Status: `Reached`,
  `Not reached` or `Not checkable`.

A filing with nothing added or removed gets one `Filing risk` row with
status `None`; an instrument with no thesis on file gets one `Thesis` row
with status `None on file`, so an empty side is a statement, not a gap.
Holdnote never writes failure scenarios of its own: a red flag is
something a filing states or a criterion the user wrote.

**Detail tables.** The module's other tables — for a stock, Business,
Segments, Geography, Financials, Balance sheet, Valuation, Peers, Capital
return and Risks stated; for a fund, Top 10, Sectors and Countries — are
still built on every run, because the scorecard and Key numbers draw on
them. They print after `Red flags` only when asked for: "full detail",
"show everything", a question about one of them ("what are Apple's
segments?" prints Segments), or the profile's `Report length` set to `full`. `METHOD` names the ones held back on a
`Detail tables:` line.

`scripts/check_output.py` holds a brief to this order.

### Quick brief

"Quick brief on NVDA" — or any brief when the profile's `Report length` is
`quick` — prints the TL;DR's `Scorecard:` line and the Buffett scorecard,
plus a lens table only when the request names one. Nothing else: no Key
numbers, What changed, Red flags, Buffett notes or detail tables. The Mode
line says so: `Mode: Stock brief (quick)` or `Mode: Fund brief (Mode A,
quick)`.

**It fetches only what the scorecard needs**, which is what makes it quick
and light on the user's plan limits. `references/stock-brief.md` → Quick
brief and `references/etf-brief.md` → Mode A → Quick brief list those
documents; a document not on the list is not opened. The run journal is not
read, because What changed is not printed.

The scorecard itself is unchanged: the same checks, thresholds, sources and
`Not available` rules as a full brief, so a quick `Met` is the same `Met`.

`METHOD` carries one line naming what was skipped, and its `Next:` line
offers the rest:

```
Quick brief:       Key numbers, What changed, Red flags and detail tables not built
Next:              say "full brief on NVDA" for the rest
```

"Full brief", "full report" or "everything" in the request overrides a
`quick` profile setting. A checklist ("should I buy X") always runs the full
brief, because its tables need Key numbers and Red flags.

Two slips the live runs of 2026-09-28 made, which the contract already
forbids: an output that opened at `CONTEXT` with no `STATUS`, and a
question ("Want me to write this into portfolio.md?") printed after the
last `SOURCES` row. `STATUS` is the first line of every output. An offer of
a next step — writing a file, logging the run — is a `METHOD` line,
`Next: …`, and the output still ends on a `SOURCES` row. The checks behind `PROOF` run
every time; with it hidden, any conflict, single-source figure or fallback
is a `METHOD` line, so nothing withheld or unconfirmed goes unsaid.

## Portfolio card

One image of what a portfolio looks through to, set like an issuer's fund
factsheet and made to be posted: its composition, three key figures, the top
10 companies across every holding with each fund's part, the company reached
through most holdings, countries and sectors, with the Holdnote link at its
foot.

1. **Get a checked Mode C draft** with the tables Allocation, Holdings,
   Look-through, Hidden bets, Countries and Sectors — the user's portfolio
   (`references/etf-brief.md` → Mode C), or the demo with
   `--tables "Allocation,Holdings,Look-through,Hidden bets,Countries,Sectors"`
   (`references/demo.md`). A draft from earlier in the conversation is used
   when it has them; never rebuild one from the rendered report.
2. Run `python3 <skill>/scripts/card.py <draft> --out <scratch>/card`. It
   checks the draft against the contract first and writes `card.svg`, plus
   `card.png` when Pillow is installed.
3. **Give the user the PNG as a file** (the SVG when no PNG was made), the
   way this environment hands files to the user: its file-sending tool when
   it has one, else its outputs folder (`/mnt/user-data/outputs/` where that
   exists). Never a bare path or a description of the image instead. Add one
   line: what it shows and that it carries percentages only.

**Percentages only.** The card draws cells of the draft's tables — shares of
the portfolio's market value — and never a quantity, close, value or amount,
so the user can post it without showing what they have. It says nothing the
tables do not: no rating, no verdict. A demo card is labelled `DEMO ·
SYNTHETIC PORTFOLIO`. Without GitHub the card is made from a look-through
at factsheet top-10 depth (`references/any-broker.md` → Look-through without
GitHub) and says `PARTIAL · TOP-10 DEPTH`. Exit 1 means the draft cannot
make a card (most often Look-through is `Not available`): say why in one
line and offer what would fix it — attach an export, or run the demo card.

## Scope

Not financial advice. Built by a non-professional for personal research. Its
output carries no authority beyond the documents it cites, and the decisions
are the user's alone.
