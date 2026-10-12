# Trading 212 CSV export — schema as actually observed

Follow RULES.md.

```
Data as of:      2026-09-17
Source:          two real Trading 212 exports (History -> Export, all
                 columns): one full-history file of 89 data rows with no
                 trailing newline, so wc -l undercounts by one; one
                 single-day export of 0 bytes. Figures below are kept to
                 the mechanism; the rows themselves are not reproduced.
Currency/units:  as stated per column below
Not available:   column semantics Trading 212 does not document; anything this
                 one account never produced (withdrawals, stock splits,
                 mergers, share lending, card transactions, limit/stop orders)
Coverage:        23 of 23 columns, 6 of 6 Action values present in the export
```

Everything below was re-derived from the file, not from documentation. Where a
claim is arithmetic, the worked figures are given so it can be rechecked.

## Columns, in file order

23 columns, header row 1:

```
Action, Time (UTC), ISIN, Ticker, Name, Notes, ID, No. of shares,
Price / share, Currency (Price / share), Exchange rate, Result,
Currency (Result), Total, Currency (Total), Withholding tax,
Currency (Withholding tax), Currency conversion from amount,
Currency (Currency conversion from amount), Currency conversion to amount,
Currency (Currency conversion to amount), Currency conversion fee,
Currency (Currency conversion fee)
```

## Action values present

| Action | Rows | ISIN | ID | No. of shares |
|---|---|---|---|---|
| `Market buy` | 49 | yes | `EOF…` | shares transacted |
| `Market sell` | 25 | yes | `EOF…` | shares transacted |
| `Dividend (Dividend)` | 9 | yes | **empty** | shares *held*, not moved |
| `Deposit` | 3 | no | UUID v4 / v7 | empty |
| `Interest on cash` | 2 | no | UUID v7 | empty |
| `Currency conversion` | 1 | no | `1D5HL07ZEWEOV7VP` | empty |

## Where the provisional schema was wrong

The schema in the approved plan came from a blog post and a forum thread, and I
no longer have its text in context, so this lists the points where the file
contradicts how that export is usually described. Paste the original column
list and I will diff it line by line.

**1. `Exchange rate` changes direction between row kinds.** This is the one
that would have produced wrong numbers silently.

On trade rows the rate is quoted in price-currency per Total-currency, so the
Total is reconstructed by **dividing**:

- a GBP-priced ETF buy — `shares × price GBP ÷ rate` matches the reported
  EUR Total to the cent once the conversion fee is added. ✅

On dividend rows it is quoted the other way round, so the Total is
reconstructed by **multiplying**:

- a GBP dividend — multiplying matches the reported Total; dividing is
  about 25% too low and prints the wrong cent. ❌
- a USD dividend — the same, the other way: dividing rounds to a cent the
  export does not report. ❌

`scripts/t212_holdings.py` does not hard-code this. `fx_direction_audit()`
re-tests both directions against the reported Total on every run and reports
the tally, so a future export that changes the convention shows up as a
`neither` count instead of a wrong number.

**2. Dividend rows have no `ID` at all.** Not a different ID format — the field
is empty on all 9 dividend rows. Any dedup keyed on `ID` alone collapses every
dividend in the file onto one row. This is why the fallback key exists.
An export whose window holds only dividends has no `ID` **column** either:
Trading 212 drops any column no row uses (2026-09-28 to 2026-10-10 came with
13 of the usual 23). The importer accepts that file, and halts only when a
file without the column has a buy, sell or cash row.

**3. `No. of shares` on a dividend row is the holding, not a movement.**
A stock dividend row shows the position size and the per-share dividend. Adding it to quantity would inflate the
position by roughly a whole extra share across the file.

**4. The action label is `Dividend (Dividend)`, not `Dividend`.** Parenthesised
subtype, and Trading 212 uses several (`Dividend (Dividends paid by us
corporations)`, `Dividend (Dividend manufactured payment)`). An equality test
on `"Dividend"` matches nothing. `classify_action()` matches the prefix before
the bracket.

**5. The timestamp column is `Time (UTC)`, not `Time`**, and the value carries
an explicit offset: `2025-10-15 07:20:26+00:00`, not `2025-10-15 07:20:26`.
A `strptime("%Y-%m-%d %H:%M:%S")` parse raises on every row. The parser tries
`fromisoformat` first and falls back to the offsetless formats.

**6. `Price / share` can be quoted in `GBX` (pence), not just GBP/EUR/USD.**
An LSE listing priced in GBX carries an `Exchange rate` quoted per GBX, so
**no ÷100 rescale is needed** — and applying one would divide the position
value by 100: `shares × price GBX ÷ rate` matches the reported EUR Total
once its fee is added. ✅

**7. The only fee column present is `Currency conversion fee`.** No
`Transaction fee`, `Finra fee`, `Stamp duty reserve tax`, `French transaction
tax` or `Deposit fee` column exists in this export. Code that reads them by
name gets a `KeyError`; code that reads them with `.get()` silently books zero
fees. They are kept in `OPTIONAL_KNOWN_COLUMNS` so they parse if they appear,
and their absence is not an error.

**8. `Withholding tax` can be `-0.00`.** Two VUSA dividend rows carry negative
zero. Harmless in `Decimal`, and worth knowing before it is read as a signal.

**9. `Result` is populated on sells only** — blank on buys, dividends and cash
rows. It is realised result in the Total currency, and it is **not** derivable
from the other columns on the row, since it depends on the cost basis of the
lots sold.

**10. `Total` currency changes mid-history.** BGN for 2025 rows, EUR from
2026-01-01, when Bulgaria joined the euro (a `Currency conversion` row
carries the switch, as `<amount> BGN -> <amount> EUR`).
Any sum of `Total` over the full history mixes two currencies. The script
groups every cash figure by currency and refuses to add across them.

**11. An export for a window with no activity is a zero-byte file** — no
header, not even column names: a one-day export with nothing in it is
0 bytes. A header check that runs before an emptiness
check reports it as a corrupt export.

**12. `Notes` is not free-text-empty.** It carries `Bank Transfer` on deposits,
`Interest on cash` on interest rows, and the conversion legs as
`<amount> BGN -> <amount> EUR` on the conversion row. Empty on every trade row.

## Things this export cannot tell us

- **Pie membership.** There is no pie column. One flat transaction list, no
  link to either pie. Hence `pies.md`.
- **Market prices.** Only transacted prices. Any valuation here is
  quantity × last transacted price, dated to that trade.
- **Positions opened before the window.** Some instruments appear as
  sells with no matching buys, so their net quantity is negative — the reason
  the negative-quantity check names the ISIN and stops.
