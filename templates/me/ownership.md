---
Last updated: YYYY-MM-DD
Cutoff: YYYY-MM-DD
---

# Ownership

The block above is the only part of this file the importer reads as policy.

`Cutoff` is the date your own transactions start. For an account that is
only yours, the day you opened it: every transaction then counts as yours.
For a shared account, the date of your first deposit; earlier transactions
belong to the account holder and never enter your weights.
`docs/fifo-attribution.md` explains how a position that spans the cutoff is
split.

## Pre-cutoff ISINs

Positions you know existed before the cutoff and are not yours. Leave the
table empty for an account that is only yours.

| ISIN | Ticker | Name | Evidence |
|---|---|---|---|
