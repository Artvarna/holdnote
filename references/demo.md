# Demo

Reference for Holdnote (`holdnote`). Follow `RULES.md`.

Shows what Holdnote does before the user has set anything up: a full
portfolio report (Mode C, `references/etf-brief.md`) on a **synthetic**
portfolio and a **frozen snapshot** of public data, both shipped inside the
skill. Nothing is fetched, so it runs the same everywhere — web, phone or
desktop, with or without the user's computer — in seconds, and costs the
user almost none of their plan's usage.

## When

"Show me a demo", "try it", "example report", "what does Holdnote do?",
"what would my report look like?" — when the user has attached no holdings
of their own. With an export or screenshot attached, the user's own
portfolio runs instead (`references/any-broker.md`); the demo is never
mixed with real holdings.

## The portfolio

`<skill>/demo/holdings.csv` — four holdings, synthetic quantities, targets
summing to 100:

| Ticker | What | Kind | Target |
|---|---|---|---|
| SPYI | SPDR MSCI ACWI IMI UCITS ETF | fund | 60% |
| SPY5 | SPDR S&P 500 UCITS ETF (Dist) | fund | 25% |
| KO | The Coca-Cola Company | stock | 8% |
| AMZN | Amazon.com Inc. | stock | 7% |

It is built to show the features that set Holdnote apart: two funds that
overlap heavily, and two stocks the funds also hold, so Look-through shows a
company owned three ways. It is nobody's real account and never a
suggestion of what to hold — say so if asked.

## Run it

`<skill>` is the folder this skill's `SKILL.md` is in, and `<scratch>` any
folder the run can write to (the skill's own folder is read-only). In
Claude's workspace:

```
python3 <skill>/scripts/demo.py --draft <scratch>/demo-draft.md --share <scratch>/share
```

It writes the full draft (RULES.md Part IV, with `PROOF` and every
`SOURCES` row) to `--draft`, checks it against the same contract as
`scripts/check_output.py`, makes the demo's share images in `--share`
(their paths are printed to stderr as `share image: ...`), and prints the
rendered report.

The answer is in this order, because the first thing a new user sees decides
whether they read on:

1. **The two stories, as files**: `story.png` ("I bought 4 things. I own
   5,965 companies") and `mirror-story.png` ("My lazy twin beat me by
   5.70%"), sent the way this environment hands files to the user (its
   file-sending tool, else its outputs folder). One line with them:
   `This is a made-up demo portfolio. Here's what Holdnote found, and how it did against a lazy twin who just bought an index fund:`
2. **The report**: print the script's output as it is.
3. **One closing line**:
   `Want yours? Attach your broker's export or a screenshot and ask "what do I own?" or "me vs my lazy twin". Say "make a card" to get these images for your own portfolio.`

The other four images (`wide.png` and `mirror-wide.png` for X, and the two
detailed cards) are sent only when asked for. Without a way to send files,
skip step 1 and say in the closing line that "make a card" makes the images.

Follow-up questions about the demo pick tables with `--tables`
(comma-separated: `Allocation`, `Holdings`, `Look-through`, `Hidden bets`,
`Countries`, `Sectors`, `Currencies`, `Stocks`, or `all`; quote the list, since
`Hidden bets` has a space), the same way Mode C's Which
tables a question gets picks them:

| Asked about the demo | `--tables` |
|---|---|
| "how much do these ETFs overlap?" | `Holdings` |
| "how much Amazon is in there really?" | `Allocation,Look-through,Hidden bets` |
| "what is this portfolio really betting on?" | `Allocation,Look-through,Hidden bets` |
| "make a card" | `Allocation,Holdings,Look-through,Hidden bets,Countries,Sectors`, then `references/cards.md` on the draft |
| "currencies?" | `Allocation,Currencies` |
| "everything" | `all` |
| "show proof" | the same tables, plus `--proof` |

Exit 1 means a contract check failed or the shipped data does not fit
together: print what it says, say the demo could not be shown, and offer a
stock brief instead. Never build the
demo's tables by hand or from memory.

## The Mirror and the Watchdog

"Demo the Mirror", "show me the lazy twin", "demo the Watchdog": those two
have their own synthetic demo, made-up trades in made-up instruments against
a made-up benchmark, because they need a year of dated trades the portfolio
demo does not have. `references/decision-mirror.md` → Demo and
`references/thesis-watchdog.md` → Demo say how to run them. A plain "show me
a demo" stays the portfolio demo; it shows the Mirror only as its
`mirror-story.png` share image, and "demo the Mirror" gives the full Mirror report.

## What the demo cannot show

Its `METHOD` says so on the `Demo:` line: Performance, Comparison,
Structural and Holdings changes need live closes, factsheets or a week of
history. Stock and fund briefs are not part of the demo — a real brief is
one question away ("Quick brief on KO").

## The snapshot

`demo/data/` holds, for one session date: `fund_report.txt`, the output of
`fund_holdings.py report` on the demo portfolio, computed from each fund's
full SSGA holdings file on the runner (the files themselves are not kept:
SSGA does not allow them to be passed on), the closes (London Stock Exchange or Nasdaq, checked against Yahoo
Finance), the ECB rate, each stock's EDGAR filings and its earnings date
from the company's own events page, and `sources.json`, every document with
its URL and both dates. `scripts/demo_snapshot.py` fetches it on GitHub's
runners (`.github/workflows/demo-data.yml`, monthly), because neither
Claude's workspace nor the user's computer can reach those sites; each
release ships the latest one. `Data as of` is the snapshot's date and says
it is frozen: the demo's figures are never presented as today's.
