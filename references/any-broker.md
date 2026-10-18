# Any broker

Reference for Holdnote (`holdnote`). Follow `RULES.md`.

Turns what the user owns, from **any** investment app or website, into
`holdings.csv`: the one broker-neutral file the Allocation, Look-through and
Stocks tables read. Trading 212 users with a full history export keep
Portfolio sync (`references/portfolio-sync.md`), which this does not replace;
the importer sends a Trading 212 history there itself.

`<skill>` below is the folder this skill's `SKILL.md` is in. Every command
runs in **Claude's workspace**, on files there; nothing needs the user's
computer except reading or saving their files (`SKILL.md` → Your files).

## What the user can give

Whichever is easiest for them — never insist on one:

1. **An export file** — a positions / portfolio / holdings export is best; a
   transaction history of buys and sells also works. CSV, TSV, TXT or Excel
   (`.xlsx`). Where to find it: the app's portfolio, holdings or statements
   page, under Export, Download or CSV. Do not recite a broker's menu path
   from memory — menus change; if the user can't find it, look it up in that
   broker's own help pages.
2. **A screenshot** of the holdings screen.
3. **A typed list** — `VWCE 12, AAPL 3.5`.

Several files at once are fine (two brokers, two accounts): the importer sums
them by ISIN.

## Steps

1. **Into a file.** An attached export is used as it is. A screenshot or a
   typed list is written by the run into `holdings-input.csv` with the header
   `ticker,name,isin,quantity`, one row per line the user showed, copying
   exactly what is there and leaving a cell empty when it is not shown. A
   screenshot that shows values but no quantities: ask for the quantities.
   **A quantity is never derived from value ÷ price.**
2. **Import.**
   ```
   python3 <skill>/scripts/import_holdings.py <file> [<file> ...] -o <holdings.csv>
   ```
   `-o` is the user's saved `me/holdings.csv` when one exists (copy it into
   the workspace first), so a re-import keeps their kinds, groups and
   targets; otherwise `me/holdings.csv` in the workspace.
3. **Exit 2 — needs input.** Do exactly what the message names, then run
   again with the same files:
   - `no ISIN for …`: find each in a primary source — the issuer's fund page
     for an ETF, the exchange's listing page or the broker's own instrument
     page for a stock. One ticker can be several listings; when the source
     shows more than one, ask the user which exchange or currency theirs
     trades in. Pass `--isin TICKER=ISIN`. The script rejects an ISIN whose
     check digit is wrong.
   - `no quantity column`: the message lists the headers. Pick the one that
     counts shares or units, or ask the user when two could; pass
     `--map quantity="<header>"`.
4. **Exit 1 — refused.** Print the reason in one line. A Trading 212 history
   goes to Portfolio sync; a history with splits or transfers needs a
   positions export instead, as the message says.
5. **Exit 0 — confirm.** Show the script's table as it printed it, then one
   `AskUserQuestion`: `Looks right` · `Fix something`. Every `(guessed)` kind
   and any `Check:` line is named in the question. A fix goes back through
   the script (`--kind TICKER=fund|stock`, `--isin`, `--map`), never by hand.
6. **Targets, only if they want them.** Ask once whether they want target
   weights next to the market weights. If yes, they give a % per holding (or
   per group); write them into `target_pct` (and `group`). Targets are
   theirs: never propose one, a split or a fund. No targets is a complete
   answer; the Allocation table then prints `-` in Target and Diff.
7. **Save** where the user keeps their files, when they asked for it or at
   setup (`SKILL.md` → Writing). With nowhere to save, send `holdings.csv`
   with `SendUserFile` and say they can attach it next time.

## The file

```
# as_of: 2026-10-13
# source: Portfolio.csv (positions)
isin,ticker,name,kind,quantity,group,target_pct
IE00BK5BQT80,VWCE,Vanguard FTSE All-World UCITS ETF,fund,12,Portfolio,
```

- `quantity` is what the user holds, as their export or their own words
  state it: a sourced figure, named in `METHOD` with the file and its
  `as_of`. A holding fully sold leaves the file on the next import.
- `kind` decides which table a holding feeds: `fund` rows are looked
  through; `stock` rows are the Stocks table and the direct column of
  Look-through.
- `group` is optional (`Portfolio` by default); with more than one, the
  Allocation table prints a total row per group.
- An `as_of` over three months old is said once, as a clause on `CONTEXT` →
  `Latest period`, exactly as `portfolio.md`'s `Last updated` is.

## How the portfolio view uses it

- **Allocation**, in the workspace, with the `prices.json` etf-brief →
  Allocation table describes — one price per ISIN in `holdings.csv`, and an
  ECB rate for every currency those prices are in:
  ```
  python3 <skill>/scripts/market_weights.py --prices prices.json --holdings <holdings.csv>
  ```
- **Look-through** with a GitHub copy: clone its `holdings-data` branch in the
  workspace (etf-brief → Holdings and Look-through tables, step 1) and run
  `report` there on the same files, with no copying to the computer:
  ```
  python3 <skill>/scripts/fund_holdings.py report --funds <me/funds.md> \
      --holdings-dir "$SCRATCH/holdings" --prices prices.json --holdings <holdings.csv>
  ```
  Without GitHub, each fund falls back to its factsheet top 10, labelled
  partial, as that section says.
- **Stocks**: the `stock` rows, in the file's order.
