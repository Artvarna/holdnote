# Run Journal

Reference for Holdnote (`holdnote`). Follow `RULES.md`.

The record of what this system actually printed. Rule 15 says a claim about
a previous run requires that run's text and never a reconstruction; this
module is where the text lives, and without it rule 15 has nothing to point
at and degrades into "cannot verify" for everything.

It is a record, not a report. It asserts nothing, checks nothing, re-runs
nothing, and adds no validation of its own — the validation already happened
in the module being journalled, and the journal's only job is to preserve
what that module printed, exactly as printed.

## When an entry is written

**After the output, never before.** The run completes, the output goes to
the user, and only then is the entry appended.

Writing the entry first is the one failure that makes this module worse than
not having it. Rule 15 treats the journal as authoritative — that is the
whole point of it — so an entry describing a run that then halted, errored,
or was abandoned mid-way is not an incomplete record. It is a false one,
carrying the authority of a file, and it will be quoted back later as
evidence of something that never happened. A missing entry costs a "cannot
verify". A wrong entry costs the thing the journal exists to protect.

**A halted run is a completed run** and gets an entry. A halt is a defined
output shape, not a failure to produce output — `references/portfolio-sync.md`
specifies what a halt prints and what it withholds — so it is journalled
like any other run, with the halt recorded.

**An abandoned run gets no entry.** A run interrupted before its output was
delivered leaves no trace, and that is correct: the journal records what was
printed, and nothing was.

## Where entries are stored

**Not in this skill.** The skill package is read-only — a session can read it
but cannot write back into it, so nothing saved there would survive.

Entries are written to the user's own folder:

```
<owner>/<name>               (the user's own repo — SKILL.md → Your files)
└── me/log/
    ├── 2026-09-19-portfolio-sync.md
    ├── 2026-09-19-etf-brief.md
    └── 2026-09-22-portfolio-sync.md
```

Filename is `[YYYY-MM-DD]-[module].md`, dated by the day the run completed,
named for the module that ran — `etf-brief` for a Mode C run, scheduled or
not. Several runs of one module on one day append to the same file, in
order; a write never replaces a file that already exists.

In Cowork, this requires folder access — ask for it once if the folder is not
already available, then write directly. In chat without folder access, output
the entry as a code block and tell the user plainly that it has not been
saved and needs pasting into their file. Never imply an entry was stored when
it was not: a run the user believes is journalled, and is not, is exactly the
gap rule 15 will later fall into without knowing it.

## Append only

**Never edit an entry. Never delete one. Never reorder them.**

A corrected run is a **new entry**, appended below the old one, with its own
timestamp. The superseded entry stays exactly as written. If the correction
should be findable from the original, the new entry names it in
`Supersedes:` — the pointer goes forward in time, and the old entry is not
touched to add a pointer back.

This is the same discipline as `references/thesis-journal.md`, for the same
reason. A journal that can be tidied after the fact records what the system
wishes it had printed. The value of the file is precisely that it cannot be
brought into line with a later view.

That includes flaws. If the run printed a typo, a mis-labelled column, a
figure later found to be wrong, or a header missing a field, **the entry
carries it verbatim**. Fixing it in the journal destroys the only evidence
that the defect occurred, which is usually the moment someone is trying to
establish exactly that.

## What an entry contains

**The draft, verbatim** — the six-section text the checker passed, which
`scripts/render.py` turned into the report the user read. The report is
not stored: it is rebuilt from the draft by the same script, so the draft
is the whole record. Where this file says what the run printed, it means
the draft.

**The sections the run printed, verbatim, in order.** `RULES.md` Part IV
fixes the shape of every output — `STATUS`, `CONTEXT`, `RESULT`, `METHOD`,
`PROOF`, `SOURCES` — and an entry is a copy of that output, not a digest of
it. A run that did not print `PROOF` records the heading with
`not requested` under it, so a later reader can tell a hidden section from
a lost one. A run that printed `SOURCES` as its summary line records that
line verbatim and, under it, the full listing from the run's draft, headed
`full listing (not printed)` — the draft is the run's own text, so this is
a quotation, not a reconstruction, and it is what a later "show proof"
reads. Same text, same spacing, same wording, same rounding.

An entry that reorganises the run's output into the journal's own preferred
blocks is a condensation, and condensation is the failure mode rule 15
names: a faithful summary of a section reads exactly like the section. The
journal copies; it does not re-format.

### Section by section

**`STATUS`** — the line as printed, including the withheld-items line on a
halt. `Halted` alone does not say which of several checks stopped the run,
and that is the first thing anyone asks.

**`CONTEXT`** — all five fields as printed, including the clauses that ride
on them. A field that was missing from the output is missing from the entry
too. Its absence is a fact about that run, and it is the fact most likely to
be disputed later.

**`RESULT`** — the tables as printed, at the precision printed, with the
columns that were printed. A column suppressed on that run stays suppressed
in the entry; re-adding it to make two entries comparable destroys the
evidence that it was suppressed. On a halt, `RESULT` is absent from the
output and absent from the entry — recorded as:

```
RESULT: withheld (halt)
```

**`METHOD`** — every policy as printed. This is what makes two entries
comparable at all: the same export under different policies produces
different tables, and an entry whose `METHOD` was trimmed cannot be diffed
against anything.

**`PROOF`** — verbatim, **with its addends.** A line recorded as:

```
printed combined table      99.9%   PASS
```

cannot be rechecked by anyone reading it later. The same line recorded as
printed:

```
printed combined table    47.8+38.6+13.5 = 99.9%, drift -0.1pp   PASS (tol 0.1pp)
```

can be re-added by hand, and a transcription error in it is visible. The
addends are what make the entry auditable rather than merely testimonial;
dropping them to save space converts evidence into a claim. This applies to
every sum, split, reconciliation and decomposition — weights, pie shares,
cash provenance, owner splits, FX tallies.

**`SOURCES`** — every source the run retrieved, one row each:

| Field | Note |
|---|---|
| URL or path | the actual location fetched or read |
| Document title | as the document names itself, not as the module refers to it |
| Publication date | the document's own date — when the issuer published it |
| Retrieval timestamp | when this run fetched it, UTC |

**Publication date and retrieval timestamp are different facts and both are
required.** A factsheet published 2026-06-30 and fetched 2026-09-19 is three
months stale, and only the pair shows it. Recording one is how a stale
figure later reads as fresh (`RULES.md` rule 5).

For a local file — a CSV export, `pies.md`, `ownership.md` — record the path,
its identifying facts (row count, export window, whatever the module printed
to identify it), and the retrieval timestamp. There is no publication date;
write `n/a — local file` rather than leaving the field blank, so a later
reader can tell the difference between "no publication date exists" and "not
recorded".

A run that fetched nothing records what the module printed — `export only`,
with the file it read. For a module whose default mode fetches nothing, that
line is the evidence it behaved correctly.

## Entry template

```
## Run [n] — [YYYY-MM-DD HH:MM UTC]
Module: [module]
[Supersedes: run [n] of [YYYY-MM-DD], reason]

### STATUS
[verbatim]

### CONTEXT
[verbatim, all five fields]

### RESULT
[verbatim tables, or: withheld (halt)]

### METHOD
[verbatim]

### PROOF
[verbatim, with addends — or `not requested`]

### SOURCES
[verbatim — the summary line, then `full listing (not printed)` and the
draft's rows; or the full rows, if they printed]

---
```

The entry carries no seventh block. A halt is recorded by its `STATUS` line
and its withheld-items line, both of which the module printed — there is no
separate halt field, because inventing one would mean the journal holds a
statement the output never made.

## Reading the journal — the rule 15 path

When asked what a previous run printed, showed, or contained:

1. **Read the journal file** for that date and module.
2. If the entry exists, **quote it.** Quoting the file is quoting the text,
   which is what rule 15 requires. Say which entry it came from.
3. If there is no entry, or no folder access, the answer is:

```
Cannot verify — no journal entry for [module] on [date].
```

**Not a reconstruction.** The temptation is strongest here, because the
module's specification is at hand and the data may still be in context, so a
faithful-looking rebuild is easy and will usually be close to right. Rule 15
exists because "close to right" and "what was printed" are different claims,
and only one of them can be checked.

The journal is authoritative about what was printed. It is not authoritative
about whether what was printed was correct — an entry faithfully records a
wrong figure as a wrong figure. "The run printed X" and "X is true" are
separate statements, and the journal only ever supports the first.

## What never goes in an entry

- **Commentary.** No note on what changed since the last run, whether the
  allocation drifted, or what a figure implies. The entry is a copy of the
  output, and the output already stopped where it was supposed to.
- **Summary or tidying.** Not a condensed header, not rounded-off validation
  lines, not "all checks passed". Condensation is the failure mode rule 15
  names: a faithful summary of a header reads exactly like the header, and
  once it is in the file nothing distinguishes them.
- **Anything not printed.** A figure computed during the run but withheld
  from the output does not appear. The journal records the output, not the
  working.
- **Retroactive annotation.** A later discovery about an earlier run is a
  note in the *later* entry, never an addition to the earlier one.
