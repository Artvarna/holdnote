# Thesis Journal

Reference for BuffettBot (`buffettbot`). Follow `RULES.md`.

The only module that improves decisions rather than describing instruments.
Everything else answers "what is this". This one answers "what did I think,
and was I right".

## Writing a thesis

Triggered before a purchase, by a Buffett checklist that finds no thesis on
file, or retroactively for something already owned. A thesis is written
**before** the position (rule 12).

Ask the questions below in order, one at a time, in the user's own words.
Never draft an answer for them: a thesis written by the system is worthless,
because the point is to capture what *they* believed. A blank answer is
recorded as `not answered`, which is itself worth knowing later.

The first four are Buffett's four filters (`references/buffett.md`, 2007
letter). The last three make the thesis checkable.

1. **Do I understand this business?** What it sells, to whom, and how it
   makes money, in two or three sentences.
2. **Will it still be strong in ten years?** What protects it from
   competitors (its moat), and what would wear that down.
3. **Do I trust the people running it?** Why, or why not.
4. **Is the price sensible?** What the user is paying against what they get.
   BuffettBot adds, as a fact under the answer, the scorecard's Margin of
   safety row from a brief run that day: value, threshold, result, date.
5. **What has to be true:** two or three specific, checkable conditions.
6. **What would prove me wrong:** the falsifier, as something a filing or a
   price could show. If nothing could, say so; an unfalsifiable thesis is a
   fact worth recording. These lines are what `Red flags` checks on every
   later brief.
7. **How long do I intend to hold it, and how big is the position?**

## Where theses are stored

**In the user's vault, never in the skill.** The installed skill is
read-only. Theses go to the user's private BuffettBot repo
(`SKILL.md` → Your files):

```
me/theses/AAPL-2026-03-12.md
me/theses/NVDA-2026-04-02.md
```

Filename `[TICKER]-[YYYY-MM-DD].md`, dated by the day it was written. Write
the file, commit it with the message `Thesis: [TICKER] [date]`, and push,
then tell the user in one line that it is saved. Without write access to the
repo, print the thesis as a code block and say plainly that it is not saved
and needs adding to `me/theses/`. Never imply a thesis was stored when it was
not.

**Never edit a stored thesis.** A changed view is a new dated entry beside the
old one. The old file stays exactly as written; that is the point of the
module.

Template:

```
# [TICKER] — thesis
Written: [date]      Price: [close, date]      Position size at entry: [%]
Intended holding period: [x]

## 1. Do I understand this business?
[user's words, verbatim]

## 2. Will it still be strong in ten years?
[user's words, verbatim]

## 3. Do I trust the people running it?
[user's words, verbatim]

## 4. Is the price sensible?
[user's words, verbatim]
Scorecard on [date]: Margin of safety [value] vs [threshold], [Met | Not met | Not available]

## What has to be true
1. [condition]
2. [condition]
3. [condition]

## What would prove me wrong
[falsifier, or "nothing specified"]
```

## Checking a thesis

Triggered on request, or when the user runs a brief on something they hold.

1. Load the original thesis
2. Load the newest filing or fund document
3. For each stated condition, report: **supported / contradicted / no new
   information**, with the sourced figure or passage behind the verdict

Quote the original wording verbatim. Never paraphrase a thesis when checking
it — paraphrase is exactly where hindsight edits the past.

```
=== [TICKER] thesis check ===
Thesis written:  [date]     Checked against: [filing, date]

Condition 1: "[verbatim]"
  → Contradicted. [sourced figure and what it shows]

Condition 2: "[verbatim]"
  → No new information since the thesis was written.

Falsifier: "[verbatim]"
  → [triggered / not triggered], [evidence]
```

Then stop. Do not recommend selling, holding, adding, or revisiting. Report
the state of the conditions; the decision is the user's.

## Why verbatim matters

Memory rewrites theses to match outcomes. A position that fell will be
remembered as a smaller conviction than it was; one that rose will be
remembered as more foreseen. The file is the defense against that, and it
only works if nothing in the system is allowed to soften, summarize or
retroactively improve the original words.

## Position sizing is recorded, not advised

Record the size at entry so the user can later see whether conviction and
sizing matched. Never suggest a size.
