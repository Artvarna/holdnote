# BuffettBot

A Claude skill that researches ETFs, stocks and your own portfolio from
**primary sources** — SEC filings, issuer factsheets, KIDs and full fund
holdings files — and reports what they say, with every number traceable.

> BuffettBot is a research tool, not a financial adviser. It describes what
> filings and fund documents say; it never says buy, sell or hold. It can be
> wrong — check anything important in the original documents. It is not
> affiliated with or endorsed by Warren Buffett or Berkshire Hathaway.
> See [DISCLAIMER.md](DISCLAIMER.md).

## What it does

| Ask | You get |
|---|---|
| `Brief me on NVDA` | A Buffett scorecard (moat, returns on capital, debt, owner earnings, margin of safety), key numbers, what changed since your last run, and red flags from the filings |
| `Brief me on VWCE with the Graham and Lynch lenses` | The same for a fund or stock, plus any of 7 investor lenses: Graham, Lynch, Greenblatt, Piotroski, Terry Smith, Munger, Bogle |
| `What do I actually own by sector and currency?` | Look-through of every company in every fund you hold, not just the top 10 |
| `How much do my ETFs overlap?` | Shared companies and shared weight for each pair of funds |
| `Should I buy AAPL?` | Buffett's four filters, answered from the scorecard and two questions to you — never a recommendation |
| `Write a thesis for GOOGL` | A dated thesis in your words, checked against later reports |

Every report ends with one line of sources; say **"show proof"** for the
full evidence: every source, its date, and the arithmetic behind each figure.

## How it works

- **Your data stays yours.** Your holdings, targets and theses live in a
  `me/` folder in **your own private copy** of this repo. The skill itself
  ships with blank templates only.
- **Fund holdings come from the issuers.** A daily GitHub Action in your
  copy downloads each fund's full holdings file (SSGA, iShares, Vanguard UK
  and Amundi are supported) to a `holdings-data` branch, and keeps a weekly
  history so BuffettBot can say what changed.
- **Trading 212 exports are read directly**, including shared accounts
  (an ownership cutoff, FIFO across it) and the 2026 BGN → EUR switch.
- **A checker holds every report to its rules** before you see it: no
  recommendations, no forecasts, no number without a source and a date.

## Get started

1. Click **Use this template** → **Create a new repository**. Name it
   `buffettbot` and choose **Private**.
2. In your new repo, open **Actions** and enable workflows if GitHub asks.
   Setup will ask you to run **Fund holdings** once after your funds are in.
3. Get `buffettbot.zip` from the [latest release](../../releases/latest)
   and add it to Claude as a skill.
4. Connect GitHub in Claude, then say **"set up BuffettBot"**. A short
   conversation fills in your `me/` folder: currency, broker, holdings,
   targets, funds and the industries you understand.

The first brief works right away. Fund look-through starts after the Action's
first run, and week-on-week holdings changes a week after that.

**Needs:** Claude with skills enabled and GitHub connected. Live prices from
the London Stock Exchange, Deutsche Börse and the ECB are read through the
browser built into the Claude desktop app, so the full portfolio view needs
the desktop app open on your computer.

## Repo layout

```
SKILL.md, RULES.md      what the skill does and the rules every report follows
references/             one file per mode (stock brief, fund brief, portfolio, ...)
scripts/                importer, market weights, fund holdings, checker, renderer
templates/me/           the blank files setup copies into me/
tests/                  pytest suite (python3 -m pytest -q)
DECISIONS.md            why things are the way they are
```

Build the skill from a checkout with `python3 scripts/build_zip.py`.

## License

[MIT](LICENSE)
