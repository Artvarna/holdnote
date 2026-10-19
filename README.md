# Holdnote

A Claude skill that researches ETFs, stocks and your own portfolio, from
**any broker**, using **primary sources**: SEC filings, issuer factsheets,
KIDs and full fund holdings files. It reports what they say, with every
number traceable.

> Holdnote is a research tool, not a financial adviser. It describes what
> filings and fund documents say; it never says buy, sell or hold. It can be
> wrong — check anything important in the original documents. It is not
> affiliated with or endorsed by Warren Buffett or Berkshire Hathaway.
> See [DISCLAIMER.md](DISCLAIMER.md).

## What it does

| Ask | You get |
|---|---|
| `Show me a demo` | A full portfolio report on a sample portfolio, in seconds, with no setup |
| `Quick brief on KO` | Just the Buffett scorecard: the fastest brief, and the lightest on your plan's limits |
| `Brief me on NVDA` | A Buffett scorecard (moat, returns on capital, debt, owner earnings, margin of safety), key numbers, what changed since your last run, and red flags from the filings |
| `Brief me on VWCE with the Graham and Lynch lenses` | The same for a fund or stock, plus any of 7 investor lenses: Graham, Lynch, Greenblatt, Piotroski, Terry Smith, Munger, Bogle |
| `What do I own?` + your broker export or a screenshot | Weights for every holding, from any app or website. On the web or your phone they come from the values in your export, with nothing to set up |
| `What do I actually own by sector and currency?` | Look-through of every company inside your funds, not just their top 10 (full holdings files with the free GitHub option: 23 popular ETFs such as VWCE, IWDA and CSPX are set up for you, and any other SSGA, iShares, Vanguard UK or Amundi fund in one step; the factsheet top 10 otherwise) |
| `How much do my ETFs overlap?` | Shared companies and shared weight for each pair of funds |
| `What am I really betting on?` | **Hidden bets:** every company you own through two or more holdings, and how much more of it you own than any one of them shows |
| `Make a card` | A shareable image of what your portfolio looks through to: biggest hidden bet, top 10 companies, countries, sectors. Percentages only, never amounts |
| `Should I buy AAPL?` | Buffett's four filters, answered from the scorecard and two questions to you — never a recommendation |
| `Write a thesis for GOOGL` | A dated thesis in your words, checked against later reports |

Every report ends with one line of sources; say **"show proof"** for the
full evidence: every source, its date, and the arithmetic behind each figure.

## How it works

- **Any broker.** Give it your app's export (CSV or Excel, positions or a
  buy/sell history), a screenshot of your holdings, or just type them. It
  finds the columns in most languages, checks every ISIN, and asks rather
  than guesses when something is missing. Its tests cover exports in the
  formats of Degiro, Interactive Brokers, Trading 212, Revolut, Scalable
  Capital, Comdirect, Hargreaves Lansdown, XTB, Schwab and Fidelity, among
  others.
- **Your data stays yours.** Your holdings, targets and theses live in a
  `me/` folder **you** choose: a folder on your computer, your own private
  GitHub repo, or nowhere (attach your file when you ask). The skill itself
  ships with no personal data.
- **Fund holdings come from the issuers.** With the GitHub option, a daily
  Action in your copy downloads each fund's full holdings file (SSGA,
  iShares, Vanguard UK and Amundi are supported) and keeps a weekly history
  so Holdnote can say what changed. Without it, funds are looked through
  from their factsheet top 10.
- **Trading 212 history exports get a full sync**, including shared accounts
  (an ownership cutoff, FIFO across it) and the 2026 BGN → EUR switch.
- **A checker holds every report to its rules** before you see it: no
  recommendations, no forecasts, no number without a source and a date.

## Get started

1. Get `holdnote.zip` from the [latest release](../../releases/latest)
   and add it to Claude as a skill (needs a paid Claude plan, see below).
2. Say **"show me a demo"** to see a full report on a sample portfolio.
   Then ask anything: **"Brief me on NVDA"** works straight away, with no
   setup.
   For your portfolio, attach your broker's export (or a screenshot) and ask
   **"What do I own?"**
3. To keep your portfolio for next time, say **"set up Holdnote"**: one
   screen of taps, and you choose where your files live.

**Want full fund look-through?** Pick GitHub at setup. Setup walks you
through **Use this template** → a private repo; full look-through starts
after its Action's first run, and week-on-week changes a week after that.

**Needs:**
- **A paid Claude plan (Pro or higher).** Skills need code execution, and
  one report makes dozens of searches and fetches, which the Free plan's
  limits won't cover.
- **Skills enabled:** turn on *Code execution and file creation*, then
  upload the zip under Skills.
- **The Claude desktop app, for today's prices.** Live closes from the
  London Stock Exchange, Deutsche Börse and the ECB are read through the
  desktop app's built-in browser. Without it (on the web or a phone), the
  portfolio view uses the values in your export, as of its date.
- GitHub is optional.

## Repo layout

```
SKILL.md, RULES.md      what the skill does and the rules every report follows
references/             one file per mode (stock brief, fund brief, portfolio, ...)
scripts/                any-broker importer, Trading 212 sync, market weights, fund holdings, checker, renderer
templates/me/           the blank files setup copies into me/
tests/                  pytest suite (python3 -m pytest -q)
DECISIONS.md            why things are the way they are
```

Build the skill from a checkout with `python3 scripts/build_zip.py`.

## License

[MIT](LICENSE)
