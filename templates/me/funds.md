# Funds

The ETFs whose full holdings files the GitHub Action fetches every day, for
look-through, overlap, sectors, currencies and weekly holdings changes.
`scripts/fund_holdings.py` reads the table below; a fund not listed here is
briefed from its factsheet only.

Four issuers are supported. `Holdings file` is what each one needs:

| Issuer | Holdings file |
|---|---|
| `ssga` | the daily holdings `.xlsx` link from the fund's SSGA page |
| `ishares` | the `latest-holdings.csv` link from the fund's iShares page (UK site, English) |
| `vanguard` | the fund's port ID, the number in its vanguard.co.uk page address |
| `amundi` | nothing: the ISIN is enough |

The setup conversation finds these for you. Funds from another issuer:
leave them out here; BuffettBot still briefs them from their factsheets.

## Funds

| Ticker | ISIN | Issuer | Holdings file |
|---|---|---|---|
