# Setup

Reference for BuffettBot (`buffettbot`). Follow `RULES.md`.

Runs on "set up BuffettBot", "get started", or the first time a request needs
the user's files (`SKILL.md` → Your files) and none can be found. It takes a
new user from nothing to a first report in about ten minutes, by
conversation, and writes everything into their own private repo. Questions
go through `AskUserQuestion` where it exists, one step at a time. A step the
user skips is left blank and named at the end. Nothing is filled in for
them.

## 1. The disclaimer, once

Before anything else, print these four lines and ask the user to confirm:

```
BuffettBot is a research tool, not a financial adviser.
It describes what filings and fund documents say; it never says buy, sell or hold.
It can be wrong. Check anything important in the original documents.
It is not affiliated with or endorsed by Warren Buffett or Berkshire Hathaway.
```

Options: `I understand` · `Stop`. On `Stop`, end setup politely. On
`I understand`, the date goes into `me/profile.md` as `Disclaimer seen:`
and the question is never asked again.

## 2. Their private copy

BuffettBot keeps each user's files in their own **private** GitHub repo,
copied from the public template. Ask whether they have one.

- **Not yet:** give these steps, then wait for the repo's name:
  1. Open https://github.com/Artvarna/buffettbot and click **Use this
     template** → **Create a new repository**.
  2. Name it `buffettbot`, choose **Private**, click **Create repository**.
  3. In the new repo, open **Actions** and enable workflows if GitHub asks.
- **Already have one:** ask for `owner/name`.

Attach it with push access (`add_repo`, `access: "push"`) and clone it. If
attaching is refused, relay the reason the tool gives; the most common fix
is connecting GitHub in Claude's settings. Without a repo, setup can still
continue: the files are printed at the end for the user to add by hand.

## 3. About them

One `AskUserQuestion` call, four questions:

1. **Base currency** — EUR · USD · GBP (any other: typed)
2. **Broker** — Trading 212 · another broker
3. **Report length** — Short (the rendered report) · Full (every detail table)
4. **Extra lenses on every brief** (multi-select) — Graham · Lynch ·
   Piotroski · none. Buffett always runs; the rest stay available on request.

Then, in plain text: **Which industries do you understand well enough to
judge a company in them?** Map the answer to GICS sector names, read them
back, and write the confirmed list under Circle of competence. "None yet"
is a valid answer and is written as such.

## 4. What they own

- **Trading 212:** ask for a CSV export (History → Export, all columns) and
  run Portfolio sync (`references/portfolio-sync.md`) to fill
  `me/portfolio.md`. Ask whether the account is only theirs. Only theirs →
  `Cutoff` and `OWN_FROM` are the account's first transaction. Shared →
  the date of their first deposit, which they give.
- **Another broker:** ask them to list each holding as `ticker, ISIN if
  they know it, target %`. Write the targets into `me/pies.md` and the
  holdings into `me/portfolio.md`. Quantities stay empty; market weights
  then need a Trading 212 export, and the portfolio view says so.

Targets are theirs. Setup never proposes a target, a split or a fund.

## 5. Their funds

For each ETF they hold, find its issuer from its ISIN. For SSGA, iShares,
Vanguard UK or Amundi, find the one thing `me/funds.md` needs (the holdings
file link, the port ID, or nothing), using the issuer's own fund page in
the browser, and write the row. A fund from any other issuer gets no row
and is briefed from its factsheet; say so in one line.

## 6. Write and save

Copy `templates/me/` into `me/` where a file does not already exist, fill
in what the conversation gave, then show a short summary:

| File | What's in it |
|---|---|
| `me/profile.md` | currency, broker, length, lenses, circle |
| `me/portfolio.md` | holdings |
| `me/pies.md` | targets |
| `me/ownership.md` | cutoff |
| `me/funds.md` | funds the Action fetches |

Commit as `Set up BuffettBot` and push. Never overwrite a file that already
has content: show the difference and ask first.

If `me/funds.md` got any rows, ask the user to run the Action once now:
their repo → **Actions** → **Fund holdings** → **Run workflow**. Running it
before this push would find no funds and fetch nothing.

## 7. The first report

End with three things to try, using their own holdings:

```
Brief me on [largest stock]
What do I own by sector?
Should I buy [something on their watchlist, or any ticker]?
```

and one line: fund look-through starts working after the Action's first
run, and week-on-week holdings changes a week after that.
