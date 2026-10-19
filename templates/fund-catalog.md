# Fund catalogue

Popular ETFs whose holdings file Holdnote already knows how to fetch. When a
fund in someone's holdings is listed here (by its ISIN, or one in `Also`),
setup writes its `me/funds.md` row with no lookup, and `fund_holdings.py`
takes the link from here. Each user's own copy fetches the files for their
own use; nothing here is a holdings file.

`Also` lists other share classes of the same fund (same portfolio, another
dividend policy or listing): their holders are looked through with this
fund's file. Only physically replicated funds are listed: a swap-based fund's
file is a substitute basket, not what its holders are exposed to.

`Tickers` lists common exchange tickers (London, Xetra) for each ISIN.
`import_holdings.py` uses it to fill in the ISIN of an export row that has
only one of these tickers and no ISIN, and lists every ISIN it filled in for
the user to confirm. A ticker that is also the US listing of something else
(SPYD, SPXL) is left out, and so is any ticker not certain for that ISIN.

To add a fund, its issuer must be SSGA, iShares, Vanguard UK or Amundi (as
in `templates/me/funds.md`); open a pull request with its row.

## Funds

| Ticker | ISIN | Issuer | Holdings file | Also | Tickers | Fund |
|---|---|---|---|---|---|---|
| VWCE | IE00BK5BQT80 | vanguard | 9679 | IE00B3RBWM25 | VWCE, VWRA = IE00BK5BQT80; VWRL, VWRD = IE00B3RBWM25 | Vanguard FTSE All-World (Acc; VWRL is the Dist class) |
| VUSA | IE00B3XXRP09 | vanguard | 9503 | IE00BFMXXD54 | VUSA, VUSD = IE00B3XXRP09; VUAA, VUAG = IE00BFMXXD54 | Vanguard S&P 500 (Dist; VUAA is the Acc class) |
| VHVG | IE00BK5BQV03 | vanguard | 9675 | IE00BKX55T58 | VHVG = IE00BK5BQV03; VEVE = IE00BKX55T58 | Vanguard FTSE Developed World (Acc; VEVE is the Dist class) |
| VHYL | IE00B8GKDB10 | vanguard | 9677 | IE00BK5BR626 | VHYL = IE00B8GKDB10; VHYA = IE00BK5BR626 | Vanguard FTSE All-World High Dividend Yield (Dist; VHYA is the Acc class) |
| SWDA | IE00B4L5Y983 | ishares | 251882 |  | SWDA, IWDA, EUNL = IE00B4L5Y983 | iShares Core MSCI World (IWDA, EUNL) |
| CSPX | IE00B5BMR087 | ishares | 253743 |  | CSPX, CSP1, SXR8 = IE00B5BMR087 | iShares Core S&P 500 (Acc; SXR8) |
| IUSA | IE0031442068 | ishares | 251900 |  | IUSA = IE0031442068 | iShares Core S&P 500 (Dist) |
| SSAC | IE00B6R52259 | ishares | 251850 |  | SSAC, ISAC, IUSQ = IE00B6R52259 | iShares MSCI ACWI (ISAC, IUSQ) |
| CNDX | IE00B53SZB19 | ishares | 253741 |  | CNDX, SXRV = IE00B53SZB19 | iShares NASDAQ 100 (SXRV) |
| EIMI | IE00BKM4GZ66 | ishares | 264659 |  | EIMI, EMIM, IS3N = IE00BKM4GZ66 | iShares Core MSCI EM IMI (EMIM, IS3N) |
| SMEA | IE00B4K48X80 | ishares | 251861 |  | SMEA = IE00B4K48X80 | iShares Core MSCI Europe (IMEU) |
| WSML | IE00BF4RFH31 | ishares | 296576 |  | WSML, IUSN = IE00BF4RFH31 | iShares MSCI World Small Cap (IUSN) |
| ISF | IE0005042456 | ishares | 251795 |  | ISF = IE0005042456 | iShares Core FTSE 100 |
| IUIT | IE00B3WJKG14 | ishares | 280510 |  | IUIT, QDVE = IE00B3WJKG14 | iShares S&P 500 Information Technology Sector (QDVE) |
| INRG | IE00B1XNHC34 | ishares | 251911 |  | INRG, IQQH = IE00B1XNHC34 | iShares Global Clean Energy Transition |
| SPPW | IE00BFY0GT14 | ssga | https://www.ssga.com/ie/en_gb/intermediary/library-content/products/fund-data/etfs/emea/holdings-daily-emea-en-sppw-gy.xlsx |  | SPPW = IE00BFY0GT14 | SPDR MSCI World |
| SPYI | IE00B3YLTY66 | ssga | https://www.ssga.com/ie/en_gb/intermediary/library-content/products/fund-data/etfs/emea/holdings-daily-emea-en-spyi-gy.xlsx |  | SPYI, IMID = IE00B3YLTY66 | SPDR MSCI ACWI IMI |
| SPY5 | IE00B6YX5C33 | ssga | https://www.ssga.com/ie/en_gb/intermediary/library-content/products/fund-data/etfs/emea/holdings-daily-emea-en-spy5-gy.xlsx |  | SPY5 = IE00B6YX5C33 | SPDR S&P 500 |
| SPYD | IE00B6YX5D40 | ssga | https://www.ssga.com/ie/en_gb/intermediary/library-content/products/fund-data/etfs/emea/holdings-daily-emea-en-spyd-gy.xlsx |  | USDV = IE00B6YX5D40 | SPDR S&P US Dividend Aristocrats (USDV) |
| SPYW | IE00B5M1WJ87 | ssga | https://www.ssga.com/ie/en_gb/intermediary/library-content/products/fund-data/etfs/emea/holdings-daily-emea-en-spyw-gy.xlsx |  | SPYW = IE00B5M1WJ87 | SPDR S&P Euro Dividend Aristocrats |
| MEUD | LU0908500753 | amundi |  |  | MEUD = LU0908500753 | Amundi Core Stoxx Europe 600 |
| MWRD | IE000BI8OT95 | amundi |  |  |  | Amundi Core MSCI World |
| PRAW | IE0003XJA0J9 | amundi |  |  |  | Amundi Prime All Country World |
