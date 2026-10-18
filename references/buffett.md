# Buffett

Reference for Holdnote (`holdnote`). Follow `RULES.md`.

What Holdnote takes from Warren Buffett, where each idea comes from, and
which feature uses it. Three things it never does with his name: speak as
him ("Buffett would buy this"), say what he thinks of an instrument he has
not written about, or quote him from memory. Holdnote is not affiliated
with or endorsed by Warren Buffett or Berkshire Hathaway.

## Principles

Each is a paraphrase of a Berkshire Hathaway shareholder letter, linked so
the user can read the original. A quotation in an output is fetched from
the linked letter in that session and kept under 15 words; otherwise the
paraphrase below is used as written.

| Principle | The idea, paraphrased | Letter | Used by |
|---|---|---|---|
| Four filters | Buy only a business you understand, with favourable long-term economics, run by able and trustworthy managers, at a sensible price | [2007](https://www.berkshirehathaway.com/letters/2007ltr.pdf) | Thesis journal, Buffett checklist |
| Moat | A great business has a lasting advantage that protects high returns on the capital it uses | [2007](https://www.berkshirehathaway.com/letters/2007ltr.pdf) | Scorecard: Moat, Capital efficiency |
| Owner earnings | What a business really earns for its owners: reported earnings plus depreciation and amortization, less the capital spending it needs to keep its position | [1986](https://www.berkshirehathaway.com/letters/1986.html) | Scorecard: Owner earnings, Margin of safety |
| Price is an offer | A price quote is an offer you may take or ignore, never an instruction; a low one can be an opportunity, a high one a reason to do nothing | [2013](https://www.berkshirehathaway.com/letters/2013ltr.pdf) | Buffett note: Mr. Market |
| Circle of competence | Know where your understanding ends and stay well inside that line | [2013](https://www.berkshirehathaway.com/letters/2013ltr.pdf) | Profile, Buffett note, checklist filter 1 |
| Ignore forecasts | Other people's predictions about the economy or the market are a waste of time | [2013](https://www.berkshirehathaway.com/letters/2013ltr.pdf) | Rule 8: no forecasts anywhere |
| Index funds | For most people who don't study businesses, a very low-cost S&P 500 index fund held for the long term does the job | [2013](https://www.berkshirehathaway.com/letters/2013ltr.pdf) | Fund scorecard, Buffett note: Index fund |

The Low debt row follows the acquisition criteria Berkshire prints in its
annual reports: businesses earning good returns on equity while using little
or no debt.

## Buffett notes

A brief or a checklist adds a `Buffett notes` table after `Red flags` when,
and only when, one of the triggers below fires on a figure the output
already prints. At most two notes, in this table's order; none fired → no
table. A note states a principle beside the finding that matched it. It is
never advice, never a prediction, and never says what to do (rules 6 and
11).

```
| Principle | Why it's here | Letter |
```

| Principle | Fires when | Why it's here (fill the brackets from the output) |
|---|---|---|
| Circle of competence | the company's GICS sector, as an issuer holdings file states it, is not in `me/profile.md` → Circle of competence, and that list is not empty | `[Sector] is not in the circle of competence in your profile` |
| Mr. Market | the close moved 15% or more, either way, over the 30 days to the price date, from the same daily close history the price came from | `The price moved [x]% in 30 days; the filings behind the scorecard are the same` |
| Moat | the scorecard's Moat or Capital efficiency row is `Not met` | `[Row] is not met: [value] against [threshold]` |
| Index funds | a fund brief whose Low cost and Broad rows are both `Met` | `[Ticker] is a broad fund at [TER]: the kind of fund the 2013 letter describes` |

`Letter` is the year as a link, from the Principles table. A note whose
figure is `Not available` does not fire.

## Words to avoid around his name

"Buffett-approved", "Buffett would", "Buffett's pick", "a Buffett stock",
and any wording that makes a scorecard result sound like his opinion. The
scorecard is the user's chosen tests, named after the man whose letters
describe them.
