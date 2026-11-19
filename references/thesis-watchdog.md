# Thesis Watchdog

Reference for Holdnote (`holdnote`). Follow `RULES.md`.

When the user buys something, they have a reason, and a picture of what
would prove them wrong. The Watchdog keeps that picture and checks it every
week against the newest filing or fund document. Most weeks it says nothing.
When a condition the user wrote comes true, it says so once, in their own
words, with the figure, its source and its date — and stops there.

It never says sell, hold, trim, add or revisit (rules 6, 11). "A condition
you wrote has been met" is the whole message; the decision is the user's.

## Trigger

- **Add:** "watch AAPL", "tell me if VUSA's fee goes up", "set a tripwire",
  "warn me if Apple's margins drop below 40%", a thesis just written
  (`references/thesis-journal.md` → Make it watchable), or the Mirror's and
  the portfolio sync's `Next:` line taken up.
- **Check:** the scheduled weekly brief (below), or "check my tripwires",
  "anything I'm watching changed?".
- **List:** "what am I watching?" → `watchdog.py list`.
- **Not here:** "is my AAPL thesis still holding?" with no tripwire on file
  is the thesis check (`references/thesis-journal.md` → Checking a thesis).
  A price alert ("tell me when NVDA hits 100") is not a tripwire: say in one
  line that Holdnote watches the business and the fund, not the price, and
  offer a valuation tripwire (`pe_ratio`) instead.

## Where tripwires live

`me/watch.md`, one row per tripwire, written only by `scripts/watchdog.py`
so every row stays one a document can answer. The template is
`templates/me/watch.md`. Unlike a thesis, the file is state: `check --write`
updates each row's `State` and `Last evidence`, and is committed
`Watch: weekly check [date]`. The user's words are never edited — a changed
view is a new tripwire, and the old one stays.

Without a saved `me/` folder there is nowhere to keep a tripwire: say so,
print the row it would have been, and offer setup (`references/setup.md`).
GitHub storage is the one that works for the weekly check, because the
scheduled run cannot reach a computer that is asleep.

## Adding a tripwire

**1. The words are the user's.** From a thesis: each line of `What has to
be true` and `What would prove me wrong`, verbatim. Quick: ask one question
— `What would you want to know about [TICKER]? Say it your way.` — and take
the answer verbatim. Never draft the words for them; a tripwire Holdnote
wrote checks Holdnote's thesis, not theirs.

**2. Holdnote proposes the measurable version; the user confirms it.**
Map the words to one metric from the table below, its exact definition, a
test and today's value (fetched now, sourced and dated: rule 1). Show it in
one `AskUserQuestion`:

- Question: `You wrote: "[words]". I'd check: [definition] [test] — today it is [value] ([source], [date]). Watch it like that?`
- Options: `Yes, watch it` · `Change the number` · `No document can show this`

`Change the number` asks for their number and asks again. `No document can
show this` adds the row as `--not-watchable`: words that name nothing a
filing could show ("if management gets worse") are worth knowing about too,
and the Mirror's Thesis column says `noted, not watchable`.

**3. Write it** with `watchdog.py add`; it refuses a metric it cannot
watch, a test of the wrong kind, a stock metric on a fund, or a row with no
baseline source:

```
python3 <skill>/scripts/watchdog.py add --watch me/watch.md \
  --holding AAPL --isin US0378331005 --kind stock --origin AAPL-2026-03-12.md \
  --words "If services stop growing, the story is over" \
  --metric filing_figure --definition "Services net sales, quarter, year on year %, 10-Q" \
  --test "< 5" --baseline 11.9 --baseline-date 2026-08-01 \
  --baseline-source "Apple 10-Q filed 2026-08-01, p. 12"
```

Then one line: `Watching AAPL: you'll hear about it only if that changes.`

### What can be watched

| Metric | Unit | Kind | Read from |
|---|---|---|---|
| `revenue_growth`, `gross_margin`, `operating_margin`, `net_margin`, `fcf_margin`, `return_on_equity`, `share_count_change` | % | stock | SEC companyfacts, the tags and formulas of `references/stock-brief.md` → Margins, Returns, Growth |
| `free_cash_flow` | USD m | stock | as above |
| `net_debt_to_ebitda`, `pe_ratio` | x | stock | as above; P/E on the brief's own close |
| `filing_figure` | as stated | stock | a figure the filing states that companyfacts does not carry — a segment's sales or margin, a customer count. Its passage is quoted in the values file, or the check refuses |
| `ter`, `tracking_difference` | %, pp | fund | the KID or factsheet |
| `top10_weight`, `largest_holding_weight`, `holdings_count` | %, x | fund | the full holdings file (`fund_holdings.py report`) |
| `fund_size` | EUR m | fund | the factsheet |
| `index`, `distribution_policy`, `domicile`, `fund_status` | text | fund | the factsheet, KID, or the issuer's shareholder notices (a merger, a closure, a change of index); tested with `changes` |

The **definition** is the like-for-like guarantee: period (quarter, TTM,
fiscal year), formula or tag, document. A later value with a different
definition is `not compared`, never compared anyway. Price alone is not in
the table on purpose (above).

A European stock has no companyfacts: its tripwires are `filing_figure`
rows read from its own reports. Coverage is said, not assumed (rule 9).

## Checking

**1. Fetch a value for every `armed` or `met` row** into a values file —
the newest figure under the row's exact definition:

```
{"as_of": "2026-11-21",
 "values": {"AAPL-1": {"value": "4.2", "unit": "as stated",
                       "definition": "Services net sales, quarter, year on year %, 10-Q",
                       "date": "2026-10-31", "source": "Apple 10-Q filed 2026-10-31, p. 12",
                       "evidence": "0000320193-26-000101",
                       "quote": "Services net sales increased 4.2% ..."}}}
```

`evidence` is what makes "no new information" true: the filing's accession
number, the KID's or factsheet's own date, the holdings file's date. A row
whose newest document is the one already checked is not fetched again. A
value that cannot be fetched is left out of the file; the row prints
`not available` and keeps its state.

**2. Run the check, then commit the watch file:**

```
python3 <skill>/scripts/watchdog.py check --watch me/watch.md \
  --values values.json --theses me/theses --write
```

The script, not the model, compares. Its outcomes:

| Outcome | Means | Alerts |
|---|---|---|
| `met` | crossed this week; the state becomes `met [date]` | **yes, once** |
| `still met` | met before, still true | no |
| `no longer met` | crossed back; re-armed, so a later crossing alerts again | no |
| `not met` | watching, nothing crossed | no |
| `no new information` | the newest document is the one already checked | no |
| `not compared` | different unit or definition, or a 50x jump from the baseline (a fraction read as a percentage) | no — the reason prints |
| `not available` | no value fetched this run | no |

A met tripwire with a newer thesis for the same holding, dated after it was
met, carries `Note: a newer thesis was written on [date], after this was
met` — the history stays visible (rule 12).

## The output

`Mode: Thesis Watchdog`, then the script's output exactly as printed: the
alert block for each `met` row (the user's words in quotes, the check, the
baseline, the new figure with source and date, the passage for a filing
figure), the table of every row checked, the not-watchable line, and the
`Subject:` line. Nothing is added after an alert: no "you may want to",
no "consider", no reading of what it means.

## The weekly run

The scheduled weekly brief (Mode C, `references/etf-brief.md`, all tables)
runs the Watchdog after it, in the same email. The email is the script's,
not the model's: `check ... --write --email watchdog-email.json` writes the
exact subject and plain-text body, and the run sends that subject as it is
and puts that body first, above the portfolio summary. When the files
cannot be reached, `watchdog.py skipped --reason "<why>" --as-of <date>
--email watchdog-email.json` writes the email instead.

- The email's subject is the script's subject —
  `Holdnote weekly: 1 condition you wrote met`,
  `Holdnote weekly: nothing new met (1 still met)` while an earlier alert
  is still true, or `Holdnote weekly: no condition you wrote was met`. A run that could not
  check some tripwires says how many (`(2 of 5 not checked)`), and one that
  could check none says exactly that: a Watchdog that failed must never
  read as an all-clear.
- The alert blocks go first in the email body, above the portfolio report.
- When the run cannot reach the user's files (a computer folder on a
  sleeping computer, a repo it cannot clone), it still sends the email,
  with the subject `Holdnote weekly: Watchdog skipped - couldn't reach your
  files` and the reason. Silence would read as "nothing met".
- A run with no `me/watch.md` or no rows in it skips the Watchdog without a
  line, and Mode C's `Next:` offers a quick tripwire on the largest holding
  that has none.

## Demo

On the Mirror demo's files, without `--write` (the skill folder is
read-only):

```
python3 <skill>/scripts/watchdog.py check --watch <skill>/demo/mirror/watch.md \
  --values <skill>/demo/mirror/values.json
```

Its `Method` line in the reply: `Demo: synthetic tripwires and values, to
show how the Watchdog reads.`
