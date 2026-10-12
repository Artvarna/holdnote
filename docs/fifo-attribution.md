# FIFO attribution of a shared account

Follow RULES.md.

```
Data as of:      2026-09-17
Source:          a real Trading 212 export and its ownership.md cutoff;
                 the rows are not reproduced here, and the worked example
                 below is synthetic with the same shape
Currency/units:  share quantities, unitless; proceeds in the currency the row states
Not available:   the true opening quantity of any position the export window
                 does not reach
Coverage:        5 positions spanning the cutoff, 2 of them attributable
```

Off by default. `--attribute fifo` turns it on; `--attribute none` is the
behaviour described in `ownership.md`, where a position spanning the cutoff
carries no quantity at all.

## The rule

Every trade row for an ISIN is walked in timestamp order, maintaining a list of
open lots. A buy appends a lot, tagged `holder` if it is dated before the
cutoff and `mine` if on or after it. A sell consumes lots **oldest first**, so
inherited shares go before anything bought later. What remains tagged `mine` at
the end is my quantity.

Each sell row's `Total` is split between owners in proportion to the quantity
taken from each lot. That is exact within a row, because one row has one price.

## Why it is not a formula

An obvious closed form —
`mine = post_cutoff_buys - max(0, post_cutoff_sells - inherited)` — is wrong,
because a sell cannot consume a lot bought after it. The worked example below
is the counterexample: the closed form gives 1.5, the row-by-row walk gives
3.5. The walk is right; the difference is a sell that lands before every one
of the user's buys.

## Worked example (synthetic)

Cutoff 2026-01-10. The shape is the one a real export produced: a sell soon
after the cutoff, larger than anything the export shows was held.

| Date | Side | Quantity | Owner | Mine after | Unbacked |
|---|---|---|---|---|---|
| 2026-01-05 | buy | 1.0 | holder | 0.0 | 0.0 |
| 2026-01-12 | sell | 3.0 | mine | 0.0 | **2.0** |
| 2026-01-15 | buy | 2.5 | mine | 2.5 | 2.0 |
| 2026-02-01 | buy | 1.5 | mine | 4.0 | 2.0 |
| 2026-03-01 | sell | 1.0 | mine | 3.0 | 2.0 |
| 2026-04-01 | buy | 0.5 | mine | **3.5** | 2.0 |

Row 2 is the finding. A sell of 3.0 arrives when the only open lot is the
inherited 1.0, so 2.0 shares were sold that nothing in this export accounts
for. **The position was therefore held before the export starts**, and the
export does not reach its opening.

## Floors, and what bounds them

When `unbacked_sold > 0` the inherited lot is understated. Understating it
sends more selling against my own lots, so my quantity comes out too low:
the figure is a lower bound, printed as `>= x (FIFO, floor)`.

The upper bound is everything bought on or after the cutoff — reached if the
inherited lot had been large enough to absorb every later sell. For the
example:

```
mine is in [3.5, 4.5]
```

That range can be wide, and only a wider export narrows it. A position with
no unbacked sells has an exact figure, not a floor.

## Verifying a figure by hand

`fifo_attribution()` is the whole rule and takes no configuration. To re-derive
a position's numbers independently, walk its rows as the table above does; the
trace script used to produce that table is a twenty-line loop over
`ledger.txs`, deliberately written not to import the module's own walk.

## What FIFO does not decide

It allocates quantity and sale proceeds. It does **not** claim that the split
is legally or morally yours — it is one convention, chosen because it is the
one an export of dated rows can actually support. LIFO or average-cost would
give different answers from the same file, and none of them is a fact about who
paid for which share.
