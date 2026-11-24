# RULES.md changelog

The history of RULES.md, kept out of the rules themselves so it is not read on every run.

- **v16 (2026-11-19)** — Two modes. Decision Mirror (`Mode: Decision
  Mirror`, `references/decision-mirror.md`) compares the user's own dated
  trades with a lazy twin in one benchmark locked before the first result,
  and splits the gap into what was picked and cash left waiting. Thesis
  Watchdog (`Mode: Thesis Watchdog`, `references/thesis-watchdog.md`)
  checks the conditions the user wrote against each new filing or fund
  document, with the comparison made by a script. Rule 11 gains a paragraph
  on looking backwards at the user's own decisions. The banned-word check
  exempts the user's own quoted words, and only those. Rule numbers are
  untouched.

- **v15 (2026-10-25)** — Two modes. Earnings recap
  (`Mode: Earnings recap`, `references/earnings-recap.md`) reports one
  company's latest quarter from its own release: results against the prior
  and year-ago quarters, estimates with their provider and outlet named,
  the company's outlook as stated, what management said, and the share
  price either side of the release with no reason. Rule 8 gains a second
  paragraph so the company's own guidance can be reported as the company's,
  never as a forecast of the agent's. Head-to-head (`Mode: Head-to-head`,
  `references/head-to-head.md`) compares two funds or two stocks on one
  scorecard and one set of definitions; rule 6 gains a paragraph that a
  comparison never names a winner. Rule numbers are untouched.

- **v14 (2026-10-21)** — Rule 7 gains a second paragraph: a reason a named
  source published for a move may be reported, attributed and dated, the
  way rule 8 reports analyst estimates — never the agent's own reason,
  never one chosen over another, and never linked to an event by the agent.
  Only the new Price move mode (`Mode: Price move`,
  `references/price-move.md`) prints them, in a `Reported reasons` table
  the contract checks. Rule 7's first paragraph is unchanged and still
  binds every other module. Rule numbers are untouched.
  The report's closing disclaimer drops its non-affiliation sentence
  (still stated in `DISCLAIMER.md`, `README.md` and `SKILL.md`).
- **v13 (2026-10-15)** — Two modes. A quick brief
  (`Mode: Stock brief (quick)`, `Mode: Fund brief (Mode A, quick)`) prints
  the `Scorecard:` TL;DR line and the Buffett scorecard, plus lenses only
  when named, and fetches only what the scorecard needs; its `METHOD` says
  what was not built. The demo (`Mode: Demo + Portfolio (Mode C)`) runs
  Mode C on a synthetic portfolio and a frozen, dated snapshot of public
  data shipped with the skill; every figure keeps its source and both
  dates, and `Data as of` is the snapshot's date, never today's. Part IV
  is unnumbered; rules 1–15 are untouched.
- **v12 (2026-10-11)** — The draft and the report. Part IV governs the
  six-section draft, which is checked and journaled; the user reads
  `scripts/render.py`'s rendering of it, which keeps every table and
  warning, adds nothing, and always ends with the disclaimer. "Show proof"
  prints the draft's evidence sections. Brief layout gains an optional
  `Buffett notes` table after `Red flags`; the Buffett checklist mode has
  its own layout (`references/checklist.md`). Part IV is unnumbered;
  rules 1–15 are untouched.
- **v11 (2026-10-11)** — `SOURCES` prints as one summary line — document
  count, publication date range, stale and unverified counts — unless
  `PROOF` prints, in which case both print in full. The full listing is
  still composed and checked on every run and kept in the journal, so
  hiding it hides the rows, never the staleness: each count above zero has
  its `METHOD` line. "Show proof" after a run quotes that run's listing,
  never re-fetches it. Part IV is unnumbered; rules 1–15 are untouched.
- **v10 (2026-10-11)** — A stock or fund brief may open `RESULT` with a
  TL;DR of at most three labelled lines that restate figures from its own
  tables. It is the one summary `RESULT` allows, and it is held to rule 6
  by carrying no figure the tables do not. Brief tables follow a fixed
  order — Buffett scorecard, any extra lenses, Key numbers, What changed,
  Red flags, then detail tables on request — set in `SKILL.md` → Report
  layout and checked by `contract.py`. Red flags are filing risks
  and the user's own thesis criteria only, which rule 6 already allows.
  Part IV is unnumbered; rules 1–15 are untouched.
- **v9 (2026-09-28)** — `PROOF` prints on request and on every halt, not
  on every run. The user reads the answer, not the addends; every check
  still runs, and a failed check still halts. Conflicts, single-source
  marks and fallbacks, which used to be visible only in `PROOF`, move to
  `METHOD` on a run without it, so hiding the working never hides a
  figure that was withheld or unconfirmed. Section rules, the placement
  rule and the self-check updated to match. Part IV is unnumbered; rules
  1–15 are untouched.
- **v8 (2026-09-27)** — Every `SOURCES` row carries its URL, and nothing
  follows `SOURCES`, a separate `Sources:` link list included. Added to the
  outside-sections rule and the self-check after the first v7 live run
  printed its links as a list below the section. The same run prompted two
  module changes in `references/market-context.md`: a headline convention
  under which an unlabelled S&P 500, Dow, Nasdaq Composite or STOXX Europe
  600 level confirms the price version (MSCI stays strict), and Period %
  cells printed as signed numbers without a `%` sign. Reasoning in
  `DECISIONS.md`. Part IV is unnumbered; rules 1–15 are untouched.
- **v7 (2026-09-27)** — Nothing prints outside the six sections; a note
  that wants printing is a `METHOD` line, and the Mode A subject line is
  the one line allowed above `STATUS`. Times are an exact `HH:MM` with zone
  or the date alone, never a placeholder digit. Both added to the
  self-check, after five live market-wide and Mode B runs on 2026-09-27
  printed `13:1x EEST` in every `Data as of` and one printed a loose note
  after `SOURCES`. The module-level fixes from the same runs — market-wide
  scope, opt-in contribution, sector indexes in place of breadth and GICS
  tables, single-source and conflict tags in `PROOF`, reused fetches, and
  Mode B's source ladder — are in `references/market-context.md` and
  `references/etf-brief.md`, with the reasoning in `DECISIONS.md`. Part IV
  is unnumbered; rules 1–15 are untouched.
- **v6 (2026-09-22)** — Added the Mode line as the first line of `RESULT`
  on every run, after market-wide and portfolio questions about the same
  index became distinguishable only by which tables printed. Part IV is
  unnumbered; rules 1–15 are untouched.
- **v5 (2026-09-20)** — Dropped `Sources used` from the mandated `CONTEXT`
  fields, leaving five. Every file a run read belongs in `SOURCES` once,
  with its dates; CONTEXT keeps only the values a reader needs to read the
  numbers, which ride on the mandated line they qualify. A module that
  fetched documents still names them, as an exception it earns by fetching
  rather than as a field every module prints. Fixed the `STATUS` halt
  separator as an ASCII hyphen-minus, because that line is machine-read and
  the code and this file had already disagreed on it unnoticed.
- **v4 (2026-09-19)** — Restructured Part IV from a header block into six
  fixed sections, `STATUS / CONTEXT / RESULT / METHOD / PROOF / SOURCES`,
  after headers, tables, method and validation had been printing at one
  level and the answer was not visually separable from the proof. Added the
  field placement rule, per-column precision, empty-column suppression,
  one-table-per-question, and the halt shape. Part IV is unnumbered, so the
  append-only rule above does not apply to it; rules 1–15 are untouched.
- **v3 (2026-09-19)** — Added rule 15, prior output is quoted never
  reconstructed, after a run defended a dropped header field by quoting
  header lines it had rebuilt rather than read. Declared rule numbers
  append-only so the constitution can grow without invalidating references
  to it.
- **v2 (2026-09-16)** — Added number-type labeling, source hierarchy,
  anti-narrative and anti-forecast rules, personal guardrails, self-check.
- **v1 (2026-09-16)** — Initial four rules.
