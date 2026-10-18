# Setup

Reference for Holdnote (`holdnote`). Follow `RULES.md`.

Runs on "set up Holdnote", "get started", or "save my portfolio". The goal
is the user's first portfolio report in about two minutes: **one screen of
taps, one file or screenshot, done.** Everything else has a default and is
changed later only if they want to (Settings, later).

Setup is never a gate. A stock or fund brief needs no setup at all, and a
user who attaches any broker export and asks "what do I own?" gets the answer
straight away (`references/any-broker.md`); setup is only how they keep it.

## 1. One screen

A single `AskUserQuestion` call with three questions. Where that tool is not
available, ask the same three in one plain message.

1. **Disclaimer** — the question text is these four lines:
   ```
   Holdnote is a research tool, not a financial adviser.
   It describes what filings and fund documents say; it never says buy, sell or hold.
   It can be wrong. Check anything important in the original documents.
   It is not affiliated with or endorsed by Warren Buffett or Berkshire Hathaway.
   ```
   Options: `I understand` · `Stop`. On `Stop`, end setup politely and save
   nothing.
2. **Where should your files live?**
   - `On this computer` — a folder on their computer, through the Claude
     desktop app. Nothing to create anywhere.
   - `GitHub` — a private repo of their own. Adds every fund's full holdings
     (not just a top 10) and week-on-week holdings changes, fetched daily.
   - `Don't save` — they attach their export or holdings file when they ask.
3. **How do you want to add what you own?** — `Upload an export` ·
   `Screenshot` · `Type it` · `Later`.

The disclaimer's date goes into `me/profile.md` as `Disclaimer seen:` and the
question is never asked again.

## 2. What they own

Unless they chose `Later`, ask for the file, the screenshot or the list in one
line, then follow `references/any-broker.md`. A Trading 212 user who uploads
a full **history** export is routed to Portfolio sync instead
(`references/portfolio-sync.md`), which keeps a shared account's cutoff: only
then ask whether the account is only theirs, and if not, the date of their
first deposit (`me/ownership.md` → `Cutoff`).

The import's confirm step is the only other question setup asks. Targets are
offered once, as any-broker step 6 says, and skipping them is fine.

## 3. Save

Write only what the conversation gave: `me/profile.md` (from
`templates/me/profile.md`, with the defaults and `Disclaimer seen:`) and
`me/holdings.csv`. Never copy blank templates the user has no use for yet;
`me/theses/` and `me/log/` are created the first time something is written to
them. Never overwrite a file that already has content: show the difference
and ask first.

- **On this computer.** Ask for a folder in one line (suggest
  `Documents/Holdnote`), request access to it
  (`device_request_folder_access`), and write the files into its `me/`.
  If the computer is not linked, say how to link it (open this chat in the
  Claude desktop app on that computer, then send a message) and send the
  files with `SendUserFile` meanwhile.
- **GitHub.** Give these steps and wait for the repo's `owner/name`:
  1. Open https://github.com/Artvarna/holdnote and click **Use this
     template** → **Create a new repository**.
  2. Name it `holdnote`, choose **Private**, click **Create repository**.
  3. In the new repo, open **Actions** and enable workflows if GitHub asks.

  Attach it with push access (`add_repo`, `access: "push"`) and clone it;
  if attaching is refused, relay the tool's reason (most often: connect
  GitHub in Claude's settings) and fall back to `On this computer` or
  `Don't save`. Then fill `me/funds.md` (below), commit as
  `Set up Holdnote`, push, and — when `funds.md` got any rows — ask them to
  run the Action once: their repo → **Actions** → **Fund holdings** → **Run
  workflow**. Before the push it would find no funds and fetch nothing.
- **Don't save.** Send `holdings.csv` with `SendUserFile`: attaching it next
  time gives the same portfolio view. Saving can be set up any time.

### Their funds (GitHub only)

For each `fund` row, find its issuer from its ISIN. For SSGA, iShares,
Vanguard UK or Amundi, find the one thing `me/funds.md` needs (the holdings
file link, the port ID, or nothing) from the issuer's own fund page in the
browser, and write the row. A fund from any other issuer gets no row and is
briefed from its factsheet; say so in one line.

## 4. The first report

End with one line saying where the files are, then three things to try with
their own holdings:

```
What do I own by sector?
Brief me on [their largest stock or fund]
Should I buy [any ticker]?
```

With GitHub, add one line: full look-through starts after the Action's first
run, and week-on-week changes a week after that.

## Settings, later

Never asked during setup. Each has a default in `templates/me/profile.md` and
is changed when the user says so ("change my settings", "use the Graham lens
every time", "reports in full"), or offered once on a brief's `METHOD`
`Next:` line the first time it would matter:

- **Base currency** — EUR · USD · GBP (any other: typed)
- **Report length** — Quick · Short · Full (Quick: the Buffett scorecard only, fewest fetches)
- **Extra lenses on every brief** — Graham · Lynch · Piotroski · none
- **Circle of competence** — the industries they understand well enough to
  judge a company in. Map the answer to GICS sector names, read them back,
  and write the confirmed list. Until it is set, briefs print no circle
  note (`references/buffett.md`), and the checklist's first filter rests on
  the user's own answer alone.
- **Name** — how reports address them.

One `AskUserQuestion` call carries the first four when they ask to change
settings without naming one.
