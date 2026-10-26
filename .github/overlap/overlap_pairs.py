#!/usr/bin/env python3
"""Temporary: weight overlap of popular ETF pairs, for one X post.

Overlap of two funds = sum over shared companies of the smaller weight
(min(wA, wB)), from each issuer's full holdings file. Rows with an ISIN
match by company (fund_holdings.company_key: Alphabet A + C are one).
iShares files carry no ISIN, so iShares pairs match by the issuer's own
company name (fund_holdings.match_key), which is only used between two
iShares files. Prints aggregates only, never the files' rows.
"""
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, "scripts")
import fund_holdings as fh  # noqa: E402

files = Path(sys.argv[1])
fh.use_funds(Path("templates/fund-catalog.md"))
by_ticker = {s.ticker: s for s in fh.SOURCES.values()}

PAIRS = [
    ("CSPX", "CNDX", "S&P 500 + Nasdaq 100", "name"),
    ("VUSA", "SPPW", "S&P 500 + MSCI World", "isin"),
    ("SPPW", "VWCE", "MSCI World + FTSE All-World", "isin"),
    ("SWDA", "SSAC", "MSCI World + MSCI ACWI", "name"),
    ("VUSA", "VWCE", "S&P 500 + FTSE All-World", "isin"),
    ("SWDA", "EIMI", "MSCI World + MSCI EM IMI", "name"),
    # validation: the same index from two files should be close to 100
    ("VUSA", "SPY5", "CHECK S&P 500 Vanguard vs SPDR", "isin"),
    ("CSPX", "IUSA", "CHECK S&P 500 iShares Acc vs Dist", "name"),
    ("CSPX", "SWDA", "CROSS-CHECK S&P 500 + MSCI World (iShares)", "name"),
]

funds = {}
for t in sorted({p for a, b, *_ in PAIRS for p in (a, b)}):
    path = fh.latest_file(files, t)
    if path is None:
        print(f"{t}: no file")
        continue
    try:
        f = fh.load_fund(by_ticker[t], path)
    except fh.Refused as e:
        print(f"{t}: refused - {e}")
        continue
    funds[t] = f
    eq = [r for r in f.rows if r.equity and r.weight > 0]
    print(f"{t}: as of {f.as_of}, {len(f.rows)} rows, {len(eq)} equity, "
          f"weights sum {sum((r.weight for r in f.rows), Decimal(0)):.2f}, "
          f"equity sum {sum((r.weight for r in eq), Decimal(0)):.2f}")


def weights(f, mode):
    w, names = {}, {}
    for r in f.rows:
        if not r.equity or r.weight <= 0:
            continue
        if mode == "isin":
            if not r.isin:
                continue
            k = fh.company_key(r.isin)
        else:
            k = "nm:" + fh.match_key(r.name)
        w[k] = w.get(k, Decimal(0)) + r.weight
        names.setdefault(k, fh.display_name(r.name))
    return w, names


print()
print("pair | label | shared companies | overlap % (sum of min) | % of A in B | % of B in A | largest shared")
for a, b, label, mode in PAIRS:
    if a not in funds or b not in funds:
        print(f"{a}-{b} | {label} | Not available")
        continue
    wa, na = weights(funds[a], mode)
    wb, nb = weights(funds[b], mode)
    shared = wa.keys() & wb.keys()
    ov = sum((min(wa[k], wb[k]) for k in shared), Decimal(0))
    a_in_b = sum((wa[k] for k in shared), Decimal(0))
    b_in_a = sum((wb[k] for k in shared), Decimal(0))
    top = sorted(shared, key=lambda k: -min(wa[k], wb[k]))[:5]
    tops = ", ".join(f"{na[k]} {min(wa[k], wb[k]):.2f}" for k in top)
    print(f"{a}-{b} | {label} | {len(shared)} of {len(wa)}/{len(wb)} | {ov:.2f} | "
          f"{a_in_b:.2f} | {b_in_a:.2f} | {tops}")
