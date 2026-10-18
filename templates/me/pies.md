---
Last updated: YYYY-MM-DD
---

# Pies — ISIN to pie mapping

The block above is the only part of this file the importer reads as policy.

Target weights are your chosen allocation, not measured values. They are the
only numbers in Holdnote allowed to be unsourced, because they are a
decision rather than an observation. Pie membership is not in a Trading 212
export, so this file is the mapping. `scripts/t212_holdings.py` halts if it
finds a held ISIN listed nowhere below.

## Pie shares

| Pie | Target share of portfolio |
|---|---|
| ETF | 75% |
| Stock | 25% |

## Pie: ETF

| ISIN | Ticker | Name | Target in pie |
|---|---|---|---|

## Pie: Stock

| ISIN | Ticker | Name | Target in pie |
|---|---|---|---|

## Not in a pie

Instruments the export contains that no pie holds. Each needs a status, or
the run halts on an unmapped holding.

| ISIN | Ticker | Name | Status |
|---|---|---|---|
