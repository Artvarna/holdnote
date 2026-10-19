# Funds

The ETFs whose full holdings files the GitHub Action fetches every day, for
look-through, overlap, sectors, currencies and weekly holdings changes.
`scripts/fund_holdings.py` reads the table below; a fund not listed here is
briefed from its factsheet only.

Four issuers are supported. `Holdings file` is what each one needs:

| Issuer | Holdings file |
|---|---|
| `ssga` | the daily holdings `.xlsx` link from the fund's SSGA page |
| `ishares` | the product ID (the number in its iShares UK page address), or the `latest-holdings.csv` link |
| `vanguard` | the fund's port ID, the number in its vanguard.co.uk page address |
| `amundi` | nothing: the ISIN is enough |

**A fund in `templates/fund-catalog.md`** (23 popular ETFs, and their other
share classes such as VWRL for VWCE or VUAA for VUSA) needs only its ticker
and ISIN here: leave Issuer and Holdings file blank and the catalogue fills
them in. The setup conversation finds the rest for you. Funds from another
issuer: leave them out here; Holdnote still briefs them from their
factsheets, and the look-through says which share of the portfolio it could
not look through.

## Funds

| Ticker | ISIN | Issuer | Holdings file |
|---|---|---|---|
