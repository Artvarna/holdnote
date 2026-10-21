# Price Move

Reference for Holdnote (`holdnote`). Follow `RULES.md`.

"Why did NVDA drop today?" "Is there a reason VUSA is down this week?" A
quick, sourced answer to one question about one stock or ETF: how far it
moved, what happened to it in that window, and what named sources said the
reason was. Not a news feed, and not an explanation of Holdnote's own.

This is the one module allowed to print reported reasons (`RULES.md` rule
7, second paragraph). Everything below exists to keep that allowance
narrow: a reason is always somebody's, with a name and a date on it, and the
line from an event to the move is still the user's to draw.

## Trigger

A request that asks **why** a named stock or ETF moved, or whether there is
a reason for it: "why did X fall", "why is X up today", "what's behind X's
drop", "any reason X jumped this week", "is there news on X".

- **One instrument per output.** A request naming two or more gets one
  output per instrument, each checked on its own.
- **The possessive changes nothing.** "Why did my Apple shares fall" is a
  Price move for AAPL. This mode never opens `portfolio.md`,
  `holdings.csv` or `pies.md`: no position size, no weight, no "you lost".
  The question is about the instrument, and a reason answered in units of
  the user's money is the prompt to act rule 11 forbids.
- **Not here:** a "why" about the whole portfolio ("why is my portfolio
  down") is Mode C, which reports moves; its `METHOD` `Next:` line offers a
  Price move on its largest mover. A "why" about an index or the market
  ("why did the S&P 500 fall") is Market-wide, which reports the move and
  no reasons (`DECISIONS.md`, Price move). "Which stocks drove the S&P 500"
  is Market-wide's Contribution table, arithmetic only.
- **The period** comes from `references/market-context.md` → Period
  resolution: no period or "today" is the last complete session; "this
  week", "since Monday", "since [date]" as that table says; "lately" or
  "recently" is asked about, never picked.

## The listing

A stock is read on its primary listing. An ETF is the listing the ticker
names (VUSA is the LSE, GBP); a fund named by ISIN or by name with several
listings is asked about once — which exchange or currency — never resolved
from the ticker alone (`references/etf-brief.md` → Where fund prices come
from). Resolve the entity by ISIN or CIK, never by name.

## What it reports

Four tables, in this order. Contribution prints for an ETF only.

### 1. Move

The Performance row of `references/market-context.md`, for the instrument
and its benchmark:

```
Move
| Instrument | Level | Period % | As of |
|---|---|---|---|
| NVIDIA Corporation (NVDA, Nasdaq, USD) | 181.20 USD | -4.31 | 2026-10-20 (Nasdaq close) |
| Benchmark: S&P 500 (price, USD) | 6612.40 | -0.85 | 2026-10-20 (NYSE close) |
```

- The instrument's row is first. Every other row starts `Benchmark: `.
- **The benchmark is fixed, not chosen per run.** A US-listed stock: S&P
  500 (price, USD). A stock listed in Europe: STOXX Europe 600 (price,
  EUR). Any other market: `Benchmark: Not available — no benchmark defined
  for this market`. An ETF: the index its own factsheet or KID names as
  its benchmark, in the variant and currency the document states; where
  that index's closes cannot be fetched the row is `Not available` with the
  reason.
- The benchmark is a comparison, not an attribution. The table does not
  print the gap between the two rows, and nothing in the output says the
  instrument moved "with" or "against" the market.
- `Incl. dist %` prints when an ex-date falls in the period, as
  market-context → Distributions inside the period sets out.

### 2. Contribution (ETF only)

Which of the fund's largest holdings account for how much of its move —
arithmetic, as in market-context → Contribution:

```
Contribution (top 10 holdings, weights as of 2026-09-30)
| Holding | Weight % | Move % | Contribution pp |
|---|---|---|---|
| NVIDIA | 7.91 | -4.31 | -0.34 |
| Microsoft | 6.80 | -1.10 | -0.07 |
| ... | | | |
| Rest of fund | | | -0.44 |
```

```
contribution (pp) = weight (%) × move (%) ÷ 100
Rest of fund (pp) = fund Period % − sum of the contributions above it
```

- **Weights** are the fund's own top 10 from its factsheet or holdings
  file, with the file's as-of date in the heading. They are the weights on
  that date, not on the base session, and `METHOD` says so.
- **Moves** are each holding's own close-to-close move over the same
  sessions, in its own trading currency.
- **Rest of fund** is the residual, printed so the table adds up: it holds
  every other holding, currency movement between the holdings' currencies
  and the fund's, fees and tracking difference. It is never broken down
  further and never described.
- Rows are sorted by the size of their contribution, largest first. That
  is arithmetic; it says which numbers are bigger, not which mattered.
- A holding whose move cannot be fetched is `Not available` in Move % and
  Contribution pp, and Rest of fund is then `Not available` too, because
  the residual would absorb the gap silently.

### 3. Dated events

What happened to the instrument in the window — the same kind of dated
facts market-context reports, scoped to this instrument:

```
Dated events (2026-10-16 to 2026-10-20)
| Date | About | Event | Source |
|---|---|---|---|
| 2026-10-17 | NVDA | Filing: 8-K, Item 2.02 Results of Operations and Financial Condition | SEC EDGAR |
| 2026-10-17 | NVDA | Results release: NVIDIA Announces Financial Results for Third Quarter Fiscal 2027 | NVIDIA newsroom |
| 2026-10-18 | NVDA | Rate decision: Federal Reserve, target range unchanged | federalreserve.gov |
```

- **Window:** the base session's date to the end session's date, both
  inclusive, so results released after the base session's close count.
- **Event** starts with one of these types and a colon, then the document's
  own title or the form's own item label — nothing about what the document
  means:
  - `Results release:` — the company's quarterly or annual results
  - `Filing:` — SEC form and item numbers with their SEC titles, or an
    exchange filing's own title
  - `Company release:` — any other press release on the issuer's own news
    page
  - `Ex-dividend:` — the ex-date and the declared amount and currency
  - `Index change:` — an addition or deletion the index provider
    announced, with its effective date
  - `Rate decision:` — the central bank of the listing's currency (Fed,
    ECB, BoE, BNB), from the bank's own site
  - `Fund notice:` — an ETF issuer's notice for the fund (a distribution, a
    benchmark change, a merger)
- **For an ETF**, the fund's own events plus the results releases and
  filings of the three holdings with the largest contributions; `About`
  says which.
- Nothing in the window: one row, `| — | NVDA | None in window | checked:
  SEC EDGAR, NVIDIA newsroom, federalreserve.gov |`. A quiet week is a
  complete answer (rule 10).
- An event is never placed in this table because a reported reason
  mentions it, and never left out because none does. The two tables are
  built independently.

### 4. Reported reasons

What named sources published as the reason for the move. The heading is
fixed, so the reader cannot mistake the table for Holdnote's view:

```
Reported reasons (as published by the named sources — not Holdnote's view)
| About | Published | Source | Reason as reported | Premise |
|---|---|---|---|---|
| NVDA | 2026-10-17 | Reuters | Reports shares fell after the company's revenue outlook came in below analyst estimates | Matches primary source |
| NVDA | 2026-10-18 | CNBC | Says the drop followed comments on export limits to China in the earnings call | Not checkable |
```

- **About** — the instrument's ticker; for an ETF, the fund or one of the
  three largest contributors.
- **Published** — the article's own publication date, between the base
  session's date and the day after the end session, inclusive. A piece
  about a different window is not used, however relevant it looks.
- **Source** — the outlet or the issuer, by name. Never "analysts",
  "reports", "the market", Holdnote or Claude. The article is a `SOURCES`
  row with its URL and both dates.
- **Reason as reported** — the source's claim in Holdnote's own words,
  under 30 words, starting with `Says`, `Reports` or `Writes` (or
  `States` for the issuer's own release). No quotation. The source's hedge
  stays: "analysts pointed to" is not upgraded to "because".
- **Premise** — whether the **fact** the source cites is in a primary
  document. It checks the fact, never the causation:
  - `Matches primary source` — the cited fact (a results figure, guidance,
    a filing, an index change) is in a document listed in `SOURCES`
  - `Not in primary sources` — the cited fact is the kind a filing or
    release would state, and the run's primary documents do not state it
  - `Not checkable` — the claim is about sentiment, analysts, flows or
    macro, which no primary document of this instrument settles
- **At most five rows per About.** Order: published date, then source rank
  below. Never by plausibility, and never by how well a reason fits an
  event in table 3.
- **Sources disagree:** both rows print. Holdnote does not reconcile them.
- **Nothing found:** one row, `| NVDA | — | — | None found — no named
  source attributed this move | — |`. That is the expected answer for most
  small moves (rule 10), not a failed search.

**Which sources count**, in this order — rule 4's hierarchy applied to
reasons:

1. The issuer itself (a release that states why, which is rare)
2. Wire services: Reuters, AP, Bloomberg, Dow Jones Newswires
3. Named financial media with an editor and a byline: CNBC, Financial
   Times, Wall Street Journal, MarketWatch, Barron's, Handelsblatt, and the
   like

Not sources: social media, forums, video, newsletters with no outlet,
"stock prediction" and AI-written aggregator pages, and any page that
reports a reason without naming who gives it. A syndicated wire story is
one row, credited to the wire, however many sites carry it.

**How reasons are found.** WebSearch, at most four queries per About,
built from the company name, the ticker and the end session's date. A
search snippet is a lead, never a source: every row comes from the article
itself, opened with WebFetch, and a page WebFetch cannot open is not used.
A paywalled article whose open part states the reason may be used; one
whose reason is behind the wall is not.

**Credit what was read.** The Source cell names the outlet whose article
was opened. A syndicated copy (a Yahoo Finance page carrying a 24/7 Wall
St. story) is credited to the original publisher, which the copy names. A
reason the article relays from someone else ("an economist told Reuters")
stays the opened article's row, with the relay in its words — `Reports an
AMP economist told Reuters that…` — and is never promoted to a Reuters row
nobody opened.

**What the search routes did, checked live 2026-10-21** (NVDA, the week
to 2026-10-20). A record of reachability, not a rank:

- **WebSearch without filters** works, and most of what it returns is not
  a source here: stock-prediction pages, AI-written or unsigned
  aggregators, and syndicated copies. Read past them; do not lower the
  bar to fill the table.
- **WebSearch with `allowed_domains`** was refused by the search proxy for
  `reuters.com`, `apnews.com`, `marketwatch.com` and `investopedia.com`,
  and for a list of several domains together. `cnbc.com` alone worked.
  Search plainly with the outlet's name in the query instead.
- **CNBC article pages** failed on WebFetch twice; the search result's
  title and date are a lead only, so a CNBC row needs another route.
- **Yahoo Finance news pages** opened on WebFetch and name the original
  publisher of a syndicated story.
- **A query for "this week" returned an article from November 2025**
  whose headline matched. The Published window caught it; never take a
  piece's date from the query that found it.

## Where the data comes from

The routes the other modules already use; nothing new is fetched for this
mode.

- **Closes** — a fund's listing: `references/etf-brief.md` → Where fund
  prices come from. A US stock: Yahoo's chart data (*browser*), the same
  JSON route; a second source for the close makes the row checked, and
  without one it is `single source` on the `Confirmation` line. Benchmark
  index closes: `references/market-context.md` → Where the closes come
  from (the AP wire route for the S&P 500 works without the browser).
- **Filings** — SEC EDGAR submissions, browser-only
  (`references/stock-brief.md` → Step 1); a European issuer's own news
  page and its exchange's filing portal.
- **Company and fund releases, ex-dates** — the issuer's own pages, as
  `references/etf-brief.md` → Stocks table and Distributions describe.
- **Rate decisions** — the central bank's own statement page.
- **Reported reasons** — WebSearch and WebFetch, which work everywhere,
  the web and the phone included.

**Without the built-in browser** the run goes on. Move and Contribution
rows whose closes need the browser print `Not available (browser route
down)`; Dated events loses EDGAR and says so in its `none` row or on a
`Fallbacks:` line; Reported reasons runs in full. A reason table beside an
empty Move table is still an honest output: the reasons are dated, and the
move is marked as not fetched rather than guessed.

## Output

The sections of `RULES.md` Part IV, with a subject line above `STATUS`:

```
=== NVDA — NVIDIA Corporation · price move ===
```

`CONTEXT`, with this mode's placements:

```
Data as of:       the run's retrieval date
Latest period:    YYYY-MM-DD close to YYYY-MM-DD close ("the phrase") —
                  the base and end sessions, which every window below uses
Currency / units: listing currency; Period % and Move % in %; contributions
                  in pp
Not available:    rows and cells not fetched, with the reason
Coverage:         Move n of m rows · Dated events n of m sources checked ·
                  Reported reasons from n of m articles read
```

`RESULT` opens with `Mode: Price move`, then the four tables, nothing
between them.

`METHOD`, on every run:

```
Build:             [text of BUILD]
Period:            the resolution applied, from market-context → Period
                   resolution
Benchmark:         the fixed rule above, and which row it produced
Contribution:      weight × move ÷ 100, top 10 as of [date], Rest of fund
                   as the residual | not run (not an ETF)
Events window:     [base date] to [end date], both inclusive
Reasons window:    published [base date] to [end date + 1 day]
Reasons rule:      attributed only (RULES.md rule 7); never Holdnote's own;
                   not ranked by plausibility; at most 5 per About
Reasons searched:  n queries, n articles read, n used — and the sources
                   left out and why (not a named source, outside the
                   window, paywalled reason)
Confirmation:      all rows checked | single source: [rows]
Conflict:          one line per conflict, or none
Fallbacks:         any fallback used and why, or none
Columns suppressed: [named, or none]
Next:              say "brief on NVDA" for the filings behind these dates
```

`PROOF`, when asked for: each close with its base and end and sources, as
market-context prints them; each contribution re-derived from its weight
and move; the Rest of fund subtraction with its addends; for each Premise
cell, the document and the line it was checked against.

## Self-check

`RULES.md` Part IV checklist, plus:

- [ ] One instrument; `portfolio.md`, `holdings.csv` and `pies.md` not
      opened, and no position size or weight of the user's anywhere
- [ ] Tables in order: Move, Contribution (ETF only), Dated events,
      Reported reasons — no other table
- [ ] Move's first row is the instrument; the benchmark follows the fixed
      rule and starts `Benchmark: `
- [ ] Every contribution re-derives from its weight and move; Rest of fund
      is the fund's Period % minus their sum
- [ ] Every event is dated inside the events window and starts with one of
      the event types
- [ ] Every reported reason names its source and publication date, sits
      inside the reasons window, starts with `Says`, `Reports`, `Writes`
      or `States`, is under 30 words, and is a `SOURCES` row
- [ ] No reason of Holdnote's own, anywhere: no "because", "due to",
      "driven by" or "on fears" outside the Reported reasons table
- [ ] Reported reasons ordered by date and source rank, never by fit;
      disagreeing sources both printed
- [ ] Premise judges the cited fact, never whether it caused the move

## Frequency

On request only, like market-context. Never scheduled, never offered after
a move the user did not ask about: a tool that explains every wiggle is a
tool that makes every wiggle feel like news.
