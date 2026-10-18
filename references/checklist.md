# Buffett Checklist

Reference for Holdnote (`holdnote`). Follow `RULES.md`.

Runs when someone is thinking about owning something: "should I buy X",
"I'm thinking of adding X", "checklist for X". It answers with the evidence
Buffett's four filters ask for, the user's own answers beside it, and what
the position would add to what they already own. It never answers the
question it was asked. The decision is the user's (rules 6 and 11), and the
output says so in its footer.

`Mode: Buffett checklist`

## Before anything is fetched: two questions

Two of the four filters are judgements no filing can make. Ask them first,
in one `AskUserQuestion` call (plain text where that tool is absent), and
print the answers verbatim:

1. **Do you understand how [company or fund] makes money?** Yes · Not sure · No
2. **Do you trust the people running it?** Yes · Not sure · No — for a fund:
   **Do you understand what the index holds?**

The user's answers are theirs. Holdnote never changes them, scores them,
or suggests a better one.

## Then the brief

Run the stock or fund brief as usual (its scorecard, Key numbers and Red
flags), then answer the four filters from it.

## RESULT

TL;DR, then these tables, in this order:

```
Four filters      the four rows below
Buffett scorecard as in the brief
Key numbers       as in the brief
Your position     what owning it would add to what you already own
Red flags         as in the brief
Buffett notes     when a trigger fires (references/buffett.md)
```

TL;DR lines for this mode:

```
Filters:   2 yes · 1 not sure · scorecard 4 of 6 met
Position:  12.50% of your portfolio is already Apple, across 3 lines
Thesis:    none on file
```

### Four filters

| Filter | Evidence | Answer |
|---|---|---|
| 1. Understand it | the user's answer; whether the sector is inside the circle of competence in `me/profile.md` | the user's answer |
| 2. Lasting economics | the scorecard's Moat and Capital efficiency rows (fund: Low cost and Broad) | `Met` when both are met, `Not met` when either is not, `Not available` otherwise |
| 3. Able, trustworthy management | the user's answer; the Munger lens's Clean accounts row (restatements, auditor changes, material weaknesses) as a filing fact | the user's answer |
| 4. Sensible price | the scorecard's Margin of safety row (fund: Low cost) | that row's result |

`Answer` is `Yes`, `Not sure` or `No` for the user's two, and `Met`,
`Not met` or `Not available` for the two the scorecard answers. Nothing
else, and no total.

### Your position

From the portfolio's Mode C look-through, on today's market weights:

| Line | Now |
|---|---|
| [Company] already held, all routes | [Total from Look-through, or 0] |
| Held directly | [weight, or none] |
| Held through funds | [the funds holding it, each with its weight] |
| Thesis on file | [file name and date, or `none`] |

Without portfolio access (no vault, no computer for market weights), the
table carries one row: `Not available — <reason>`. Holdnote never
calculates a position size to buy, and never says how the weights *would*
change by a stated amount: that is a proposal, and proposals are the user's.

## After RESULT

`METHOD` ends with `Next: say "write a thesis for [TICKER]" to answer the
four filters in your own words before deciding`, when no thesis is on
file. That line is an offer, not advice; it is the user's own rule 12.
