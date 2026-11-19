"""Tests for scripts/mirror.py: the Decision Mirror (references/decision-mirror.md)."""

from __future__ import annotations

import json
import random
import re
import subprocess
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO / "tests"))

import mirror as mi  # noqa: E402
from test_fund_holdings import make_xlsx  # noqa: E402
from test_t212_holdings import buy, dividend, row, sell, write_export, write_ownership  # noqa: E402

D = Decimal
AS_OF = "2026-11-18"


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


def write_nav(path: Path, points: dict[str, object], currency="EUR", isin="IE000XZSV718",
              ticker="SPYL") -> Path:
    lines = [f"# isin: {isin}", f"# ticker: {ticker}", f"# currency: {currency}",
             "# source: synthetic test file", "date,nav"]
    lines += [f"{d},{v}" for d, v in sorted(points.items())]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def daily(start: str, end: str, f) -> dict[str, object]:
    """A NAV on every weekday from start to end, valued by f(day index)."""
    out, day, i = {}, date.fromisoformat(start), 0
    while day <= date.fromisoformat(end):
        if day.weekday() < 5:
            out[day.isoformat()] = f(i)
        day += timedelta(days=1)
        i += 1
    return out


def write_prices(path: Path, prices: dict[str, tuple[str, str]], fx=None, as_of=AS_OF) -> Path:
    spec = {"as_of": as_of,
            "prices": {k: {"price": p, "currency": c, "date": as_of} for k, (p, c) in prices.items()},
            "fx": fx or {}}
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


def write_tx(path: Path, rows: list[str]) -> Path:
    path.write_text("date,type,isin,ticker,quantity,amount,currency\n" + "\n".join(rows) + "\n",
                    encoding="utf-8")
    return path


def run(args: list[str], cwd: Path) -> tuple[int, str]:
    proc = subprocess.run([sys.executable, str(REPO / "scripts" / "mirror.py"), *args],
                          cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


HAND_NAV = {"2026-01-05": 100, "2026-02-02": 110, "2026-03-02": 120, AS_OF: 150}
HAND_TX = [
    "2026-01-05,deposit,,,,1000,EUR",
    "2026-01-05,buy,AAAAAAAAAAA1,AAA,5,500,EUR",
    "2026-02-02,buy,BBBBBBBBBBB2,BBB,3,300,EUR",
    "2026-03-02,sell,AAAAAAAAAAA1,AAA,2.5,400,EUR",
    "2026-03-02,dividend,BBBBBBBBBBB2,BBB,,10,EUR",
]
HAND_PRICES = {"AAAAAAAAAAA1": ("200", "EUR"), "BBBBBBBBBBB2": ("90", "EUR")}


@pytest.fixture
def hand(tmp_path):
    write_nav(tmp_path / "nav.csv", HAND_NAV)
    write_tx(tmp_path / "tx.csv", HAND_TX)
    write_prices(tmp_path / "prices.json", HAND_PRICES)
    return tmp_path


def hand_args(extra=()):
    return ["report", "--nav", "nav.csv", "--prices", "prices.json", "--transactions", "tx.csv",
            "--json", "s.json", *extra]


# --------------------------------------------------------------------------
# The worked example, every figure derived by hand
# --------------------------------------------------------------------------


def test_hand_example_every_figure(hand):
    code, out = run(hand_args(), hand)
    assert code == 0, out
    # AAA: you 2.5*200 + 400 = 900; twin 5 units, half sold at 120 -> 2.5*150 + 300 = 675
    assert "| AAA | none | 500.00 | 900.00 | 675.00 | +225.00 |" in out
    # BBB: you 3*90 + 10 = 280; twin 300/110 units * 150 = 409.09
    assert "| BBB | none | 300.00 | 280.00 | 409.09 | -129.09 |" in out
    # account: holdings 500 + 270, cash 1000 - 800 + 400 + 10 = 610 -> 1380; twin 10 * 150
    assert "| Account today: holdings + cash | 1380.00 | 1500.00 | -120.00 |" in out
    assert "| What you picked: the picks twin's gap | +95.91 |" in out
    assert "| Cash waiting: never invested, or not reinvested after a sale | -215.91 |" in out
    assert "| Total | -120.00 |" in out
    assert "| 2026-03-02 | AAA | 2.5 | 400.00 | 500.00 | +100.00 |" in out
    summary = json.loads((hand / "s.json").read_text())
    assert summary["twin"] == "lazy" and summary["gap_pct"] == "-12.00%"


def test_one_headline_percentage(hand):
    """The share line carries the lazy-twin gap, never the picks-twin one."""
    _, out = run(hand_args(), hand)
    share = next(line for line in out.splitlines() if line.startswith("Share line:"))
    assert "-12.00% of money deposited" in share
    assert "+11.99%" not in share


def test_short_history_is_said(hand):
    _, out = run(hand_args(), hand)
    assert "History: 10 months, 3 trades. This much history says little about skill." in out


# --------------------------------------------------------------------------
# An independent re-derivation: a day-by-day simulation that shares no code
# --------------------------------------------------------------------------


def simulate(flows, nav: dict[date, Decimal], prices: dict[str, Decimal], today: date):
    """Hold two books day by day, the slow way, and value them today."""
    def navon(d):
        return nav[max(k for k in nav if k <= d)]

    shares, twin_units, cash, lazy_units = {}, {}, D(0), D(0)
    twin_cash, per = D(0), {}
    for f in sorted(flows, key=lambda x: x[0]):
        d, kind, isin, qty, eur = f
        if kind == "deposit":
            cash += eur
            lazy_units += eur / navon(d)
            twin_cash += eur
        elif kind == "buy":
            cash -= eur
            twin_cash -= eur
            shares[isin] = shares.get(isin, D(0)) + qty
            twin_units[isin] = twin_units.get(isin, D(0)) + eur / navon(d)
        elif kind == "sell":
            frac = qty / shares[isin]
            cash += eur
            sold = twin_units[isin] * frac
            twin_units[isin] -= sold
            twin_cash += sold * navon(d)
            shares[isin] -= qty
        elif kind == "dividend":
            cash += eur
    you = cash + sum(shares[i] * prices[i] for i in shares)
    twin = twin_cash + sum(u * navon(today) for u in twin_units.values())
    lazy = lazy_units * navon(today)
    return you, twin, lazy


def test_random_histories_match_an_independent_simulation(tmp_path):
    rng = random.Random(20261119)
    for trial in range(25):
        start = date(2025, 1, 6)
        nav = {}
        level = D(100)
        for i in range(400):
            d = start + timedelta(days=i)
            if d.weekday() < 5:
                level = (level * (1 + D(rng.randint(-200, 220)) / 10000)).quantize(D("0.0001"))
                nav[d] = level
        days = sorted(nav)
        isins = ["AAAAAAAAAAA1", "BBBBBBBBBBB2", "CCCCCCCCCCC3"]
        held = {i: D(0) for i in isins}
        flows, rows, cash = [], [], D(0)
        for d in sorted(rng.sample(days[:-5], 30)):
            pick = rng.random()
            isin = rng.choice(isins)
            if pick < 0.25 or cash < 50:
                eur = D(rng.randint(100, 900))
                flows.append((d, "deposit", "", D(0), eur))
                rows.append(f"{d},deposit,,,,{eur},EUR")
                cash += eur
            elif pick < 0.7:
                eur = D(rng.randint(20, int(cash)))
                qty = (eur / D(rng.randint(10, 60))).quantize(D("0.0001"))
                flows.append((d, "buy", isin, qty, eur))
                rows.append(f"{d},buy,{isin},{isin[:3]},{qty},{eur},EUR")
                held[isin] += qty
                cash -= eur
            elif held[isin] > 0:
                qty = (held[isin] * D(rng.randint(10, 100)) / 100).quantize(D("0.0001"))
                qty = min(qty, held[isin])
                eur = (qty * D(rng.randint(10, 70))).quantize(D("0.01"))
                flows.append((d, "sell", isin, qty, eur))
                rows.append(f"{d},sell,{isin},{isin[:3]},{qty},{eur},EUR")
                held[isin] -= qty
                cash += eur
            else:
                eur = D(rng.randint(1, 20))
                if held[isin] > 0:
                    flows.append((d, "dividend", isin, D(0), eur))
                    rows.append(f"{d},dividend,{isin},{isin[:3]},,{eur},EUR")
                    cash += eur
        if not flows or flows[0][1] != "deposit":
            continue
        today = days[-1]
        prices = {i: D(rng.randint(5, 90)) for i in isins}
        d = tmp_path / f"t{trial}"
        d.mkdir()
        write_nav(d / "nav.csv", {k.isoformat(): v for k, v in nav.items()})
        write_tx(d / "tx.csv", rows)
        write_prices(d / "prices.json", {i: (str(p), "EUR") for i, p in prices.items()},
                     as_of=today.isoformat())
        code, out = run(["report", "--nav", "nav.csv", "--prices", "prices.json",
                         "--transactions", "tx.csv", "--json", "s.json"], d)
        assert code == 0, out
        you, twin, lazy = simulate(flows, nav, prices, today)
        s = json.loads((d / "s.json").read_text())
        # each holding's value is rounded to the cent before it is added: <= 1 cent per holding
        cents = D("0.01") * (len(isins) + 1)
        assert abs(D(s["picks_eur"]) - (you - twin)) <= cents, (trial, out)
        assert abs(D(s["waiting_eur"]) - (twin - lazy)) <= cents, (trial, out)
        total = re.search(r"\| Total \| ([+-][\d,.]+|0\.00) \|", out).group(1).replace(",", "")
        assert abs(D(total) - (you - lazy)) <= cents, (trial, out)
        assert D(total) == D(s["picks_eur"]) + D(s["waiting_eur"]), (trial, out)
        # the holdings add up to the picks gap
        assert sum(D(v) for v in s["holdings"].values()) == D(s["picks_eur"])


# --------------------------------------------------------------------------
# Trading 212: shared account, FIFO, BGN, dividends
# --------------------------------------------------------------------------

CUT = "2025-10-12"


def t212_workspace(tmp_path, rows, fixed=True):
    data = tmp_path / "data" / "t212"
    write_export(data, "export.csv", rows)
    write_ownership(tmp_path / "ownership.md", cutoff=CUT,
                    fixed_rate="1 EUR = 1.95583 BGN (Council Regulation (EU) 2025/1409)"
                    if fixed else None)
    write_nav(tmp_path / "nav.csv", daily("2025-01-01", AS_OF, lambda i: 100 + i // 10))
    return tmp_path


def t212_args(prices="prices.json"):
    return ["report", "--nav", "nav.csv", "--prices", prices, "--data-dir", "data/t212",
            "--ownership", "ownership.md", "--json", "s.json"]


def deposit(total, time, total_ccy="EUR", tx_id="DEP1"):
    return row(action="Deposit", time=time, total=total, total_ccy=total_ccy, tx_id=tx_id,
               notes="Bank Transfer")


def test_shared_account_sells_holder_shares_first_and_has_no_lazy_twin(tmp_path):
    ws = t212_workspace(tmp_path, [
        buy(isin="US0378331005", ticker="AAPL", qty="2", total="391.17", total_ccy="BGN",
            time="2025-06-02 10:00:00+00:00", tx_id="H1"),  # the holder's
        buy(isin="US0378331005", ticker="AAPL", qty="1", total="200.00", total_ccy="BGN",
            time="2025-11-03 10:00:00+00:00", tx_id="M1"),  # mine, BGN: 102.26 EUR
        sell(isin="US0378331005", ticker="AAPL", qty="2", total="400.00", total_ccy="EUR",
             time="2026-02-02 10:00:00+00:00", tx_id="S1"),  # all holder lots
    ])
    write_prices(ws / "prices.json", {"US0378331005": ("250", "EUR")})
    code, out = run(t212_args(), ws)
    assert code == 0, out
    assert "| AAPL | none | 102.26 | 250.00 |" in out  # 200 BGN / 1.95583
    assert "Sold on" not in out  # the sell was the holder's, not mine
    assert "Lazy twin: Not available - the account is shared" in out
    assert json.loads((ws / "s.json").read_text())["twin"] == "picks"


def test_a_sell_split_between_holder_and_mine(tmp_path):
    ws = t212_workspace(tmp_path, [
        buy(isin="US0378331005", ticker="AAPL", qty="1", total="100", time="2025-06-02 10:00:00+00:00", tx_id="H1"),
        buy(isin="US0378331005", ticker="AAPL", qty="3", total="300", time="2025-11-03 10:00:00+00:00", tx_id="M1"),
        sell(isin="US0378331005", ticker="AAPL", qty="2", total="240", time="2026-02-02 10:00:00+00:00", tx_id="S1"),
    ])
    write_prices(ws / "prices.json", {"US0378331005": ("150", "EUR")})
    code, out = run(t212_args(), ws)
    assert code == 0, out
    # 1 of the 2 sold was mine: half the proceeds
    assert "| 2026-02-02 | AAPL | 1 | 120.00 | 150.00 | +30.00 |" in out
    assert "| AAPL | none | 300.00 | 420.00 |" in out  # 2 left * 150 + 120


def test_dividend_split_by_my_share_of_the_holding(tmp_path):
    ws = t212_workspace(tmp_path, [
        buy(isin="IE00B3XXRP09", ticker="VUSA", qty="1", total="100", time="2025-06-02 10:00:00+00:00", tx_id="H1"),
        buy(isin="IE00B3XXRP09", ticker="VUSA", qty="3", total="300", time="2025-11-03 10:00:00+00:00", tx_id="M1"),
        dividend(isin="IE00B3XXRP09", ticker="VUSA", qty="4", total="2.00", total_ccy="EUR",
                 time="2026-03-25 10:00:00+00:00"),
    ])
    write_prices(ws / "prices.json", {"IE00B3XXRP09": ("100", "EUR")})
    code, out = run(t212_args(), ws)
    assert code == 0, out
    assert "| VUSA | none | 300.00 | 301.50 |" in out  # 3 * 100 + 3/4 of 2.00


def test_unsettled_fifo_split_is_left_out_and_named(tmp_path):
    ws = t212_workspace(tmp_path, [
        sell(isin="US67066G1040", ticker="NVDA", qty="2", total="200", time="2025-06-02 10:00:00+00:00", tx_id="H1"),
        buy(isin="US67066G1040", ticker="NVDA", qty="3", total="300", time="2025-11-03 10:00:00+00:00", tx_id="M1"),
        sell(isin="US67066G1040", ticker="NVDA", qty="1", total="120", time="2026-02-02 10:00:00+00:00", tx_id="S1"),
        buy(isin="US0378331005", ticker="AAPL", qty="1", total="100", time="2025-11-04 10:00:00+00:00", tx_id="M2"),
    ])
    write_prices(ws / "prices.json", {"US0378331005": ("150", "EUR"), "US67066G1040": ("150", "EUR")})
    code, out = run(t212_args(), ws)
    assert code == 0, out
    assert "Not included: NVDA (" in out
    assert "| NVDA |" not in out
    assert "| AAPL |" in out


def test_bgn_without_a_declared_fixed_rate_refuses(tmp_path):
    ws = t212_workspace(tmp_path, [
        buy(isin="US0378331005", ticker="AAPL", qty="1", total="200", total_ccy="BGN",
            time="2025-11-03 10:00:00+00:00", tx_id="M1"),
    ], fixed=False)
    write_prices(ws / "prices.json", {"US0378331005": ("250", "EUR")})
    code, out = run(t212_args(), ws)
    assert code == 1 and "Fixed rate in ownership.md" in out


def test_sole_t212_account_gets_the_lazy_twin(tmp_path):
    ws = t212_workspace(tmp_path, [
        deposit("500", "2025-10-13 09:00:00+00:00"),
        buy(isin="US0378331005", ticker="AAPL", qty="1", total="200", time="2025-11-03 10:00:00+00:00", tx_id="M1"),
        row(action="Interest on cash", time="2025-12-01 00:00:00+00:00", total="0.50",
            total_ccy="EUR", tx_id="INT1"),
    ])
    write_prices(ws / "prices.json", {"US0378331005": ("250", "EUR")})
    code, out = run(t212_args(), ws)
    assert code == 0, out
    assert "Lazy twin (EUR," in out
    # account: 250 held + cash 500 - 200 + 0.50
    assert "| Account today: holdings + cash | 550.50 |" in out


# --------------------------------------------------------------------------
# Refusals and partial coverage
# --------------------------------------------------------------------------


def test_first_trade_before_the_benchmark_existed_refuses(tmp_path):
    write_nav(tmp_path / "nav.csv", {"2026-02-02": 100, AS_OF: 120})
    write_tx(tmp_path / "tx.csv", HAND_TX)
    write_prices(tmp_path / "prices.json", HAND_PRICES)
    code, out = run(hand_args(), tmp_path)
    assert code == 1 and "before SPYL's NAV history starts" in out


def test_a_gap_in_the_nav_file_refuses_rather_than_reaching_back(tmp_path):
    write_nav(tmp_path / "nav.csv", {"2026-01-05": 100, AS_OF: 150})
    write_tx(tmp_path / "tx.csv", HAND_TX)
    write_prices(tmp_path / "prices.json", HAND_PRICES)
    code, out = run(hand_args(), tmp_path)
    assert code == 1 and "the file has a gap there" in out


def test_selling_more_than_was_bought_refuses(tmp_path):
    write_nav(tmp_path / "nav.csv", daily("2026-01-01", AS_OF, lambda i: 100))
    write_tx(tmp_path / "tx.csv", ["2026-01-05,deposit,,,,100,EUR",
                                    "2026-01-06,sell,AAAAAAAAAAA1,AAA,1,50,EUR"])
    write_prices(tmp_path / "prices.json", {})
    code, out = run(hand_args(), tmp_path)
    assert code == 1 and "does not reach back to the first buy" in out


def test_a_missing_price_keeps_the_rest_and_drops_the_lazy_twin(hand):
    write_prices(hand / "prices.json", {"AAAAAAAAAAA1": ("200", "EUR")})
    code, out = run(hand_args(), hand)
    assert code == 0, out
    assert "Totals cover 1 of 2 holdings; no figure for BBB." in out
    assert "Lazy twin: Not available - a holding has no price today." in out
    assert json.loads((hand / "s.json").read_text())["complete"] is False


def test_locked_benchmark_must_match_the_nav_file(hand):
    code, out = run(hand_args(["--benchmark", "CSPX"]), hand)
    assert code == 1 and "never switches benchmark" in out
    code, out = run(hand_args(["--benchmark", "IE000XZSV718"]), hand)
    assert code == 0, out


def test_a_withdrawal_larger_than_the_twin_empties_it(tmp_path):
    write_nav(tmp_path / "nav.csv", daily("2026-01-01", AS_OF, lambda i: 100 if i < 30 else 50))
    write_tx(tmp_path / "tx.csv", ["2026-01-05,deposit,,,,100,EUR",
                                    "2026-02-10,withdrawal,,,,80,EUR"])
    write_prices(tmp_path / "prices.json", {})
    code, out = run(hand_args(), tmp_path)
    assert code == 0, out
    assert "the twin was emptied, not taken below zero" in out


def test_rows_that_leave_the_account_negative_drop_the_lazy_twin(tmp_path):
    write_nav(tmp_path / "nav.csv", daily("2026-01-01", AS_OF, lambda i: 100))
    write_tx(tmp_path / "tx.csv", ["2026-01-05,deposit,,,,100,EUR",
                                    "2026-01-06,buy,AAAAAAAAAAA1,AAA,3,300,EUR"])
    write_prices(tmp_path / "prices.json", {"AAAAAAAAAAA1": ("100", "EUR")})
    code, out = run(hand_args(), tmp_path)
    assert code == 0, out
    assert "below zero, so some rows are missing" in out


# --------------------------------------------------------------------------
# Currencies
# --------------------------------------------------------------------------


def write_ecb(path: Path, rows: dict[str, str]) -> Path:
    lines = ["Date,USD,JPY,"] + [f"{d},{usd},N/A," for d, usd in sorted(rows.items(), reverse=True)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_usd_nav_is_restated_at_the_ecb_rate_of_its_day(tmp_path):
    write_nav(tmp_path / "nav.csv", {"2026-01-05": 110, AS_OF: 132}, currency="USD")
    write_ecb(tmp_path / "ecb.csv", {"2026-01-05": "1.1000", AS_OF: "1.2000"})
    write_tx(tmp_path / "tx.csv", ["2026-01-05,deposit,,,,100,EUR",
                                    "2026-01-05,buy,AAAAAAAAAAA1,AAA,1,100,EUR"])
    write_prices(tmp_path / "prices.json", {"AAAAAAAAAAA1": ("100", "EUR")})
    code, out = run(hand_args(["--fx", "ecb.csv"]), tmp_path)
    assert code == 0, out
    # twin: 100 EUR / (110/1.1) = 1 unit; today 132/1.2 = 110 EUR
    assert "| AAA | none | 100.00 | 100.00 | 110.00 | -10.00 |" in out


def test_usd_nav_without_rates_refuses(tmp_path):
    write_nav(tmp_path / "nav.csv", HAND_NAV, currency="USD")
    write_tx(tmp_path / "tx.csv", HAND_TX)
    write_prices(tmp_path / "prices.json", HAND_PRICES)
    code, out = run(hand_args(), tmp_path)
    assert code == 1 and "pass --fx" in out


# --------------------------------------------------------------------------
# Wording (rules 6, 8, 11)
# --------------------------------------------------------------------------

LOADED = re.compile(r"\b(cost you|mistake|should|beat|lost|won|better|worse|regret|wrong|"
                    r"underperform|outperform|recommend|consider)\b", re.I)


def test_no_loaded_words_in_the_output(hand):
    _, out = run(hand_args(), hand)
    assert not LOADED.search(out), LOADED.search(out)


# --------------------------------------------------------------------------
# NAV import
# --------------------------------------------------------------------------


def test_nav_import_reads_an_issuer_sheet(tmp_path):
    rows = [["Fund Name:", "SPDR S&P 500 UCITS ETF (Acc)"], ["ISIN:", "IE000XZSV718"],
            ["Currency:", "USD"], [], ["Date", "NAV", "Shares Outstanding", "Total Net Assets"],
            ["18-Nov-2026", "12.3456", "1", "1"], ["17-Nov-2026", "12.2", "1", "1"],
            ["The information contained above is for illustration only."]]
    (tmp_path / "nav.xlsx").write_bytes(make_xlsx(rows))
    code, out = run(["nav-import", "nav.xlsx", "--isin", "IE000XZSV718", "--ticker", "SPYL",
                     "--source", "SSGA NAV history"], tmp_path)
    assert code == 0, out
    assert out.splitlines()[2] == "# currency: USD"
    assert out.strip().endswith("2026-11-17,12.2\n2026-11-18,12.3456".split("\n")[-1])
    (tmp_path / "nav.csv").write_text(out, encoding="utf-8")
    nav = mi.read_nav_csv(tmp_path / "nav.csv")
    assert nav.series.points[date(2026, 11, 18)] == D("12.3456")


def test_nav_import_refuses_another_funds_file(tmp_path):
    rows = [["ISIN:", "IE00B5BMR087"], ["Currency:", "USD"], ["Date", "NAV"],
            ["18-Nov-2026", "600"], ["17-Nov-2026", "601"]]
    (tmp_path / "nav.xlsx").write_bytes(make_xlsx(rows))
    code, out = run(["nav-import", "nav.xlsx", "--isin", "IE000XZSV718", "--ticker", "SPYL",
                     "--source", "x"], tmp_path)
    assert code == 1 and "not IE000XZSV718" in out


def test_tables_add_up_exactly(hand):
    _, out = run(hand_args(), hand)
    rows = [l for l in out.splitlines() if l.startswith("| AAA |") or l.startswith("| BBB |")]
    gaps = [D(r.split("|")[-2].strip().replace(",", "")) for r in rows]
    picks = re.search(r"What you picked: the picks twin's gap \| ([+-][\d.,]+)", out).group(1)
    assert sum(gaps) == D(picks)


def test_a_buy_listed_before_its_same_day_deposit_still_gets_the_lazy_twin(tmp_path):
    write_nav(tmp_path / "nav.csv", HAND_NAV)
    write_tx(tmp_path / "tx.csv", [HAND_TX[1], HAND_TX[0], *HAND_TX[2:]])
    write_prices(tmp_path / "prices.json", HAND_PRICES)
    code, out = run(hand_args(), tmp_path)
    assert code == 0 and "| Total | -120.00 |" in out, out


def test_an_out_of_date_nav_file_says_so(tmp_path):
    write_nav(tmp_path / "nav.csv", {"2026-01-05": 100, "2026-02-02": 110, "2026-03-02": 120})
    write_tx(tmp_path / "tx.csv", HAND_TX)
    write_prices(tmp_path / "prices.json", HAND_PRICES)
    code, out = run(hand_args(), tmp_path)
    assert code == 1 and "it needs fetching again" in out


def test_a_split_row_stops_the_run_rather_than_valuing_wrong_shares(tmp_path):
    ws = t212_workspace(tmp_path, [
        buy(isin="US67066G1040", ticker="NVDA", qty="1", total="1000", time="2025-11-03 10:00:00+00:00", tx_id="M1"),
        row(action="Stock split open", isin="US67066G1040", ticker="NVDA", qty="10",
            time="2026-01-10 10:00:00+00:00", tx_id="SP1"),
        buy(isin="US0378331005", ticker="AAPL", qty="1", total="100", time="2025-11-04 10:00:00+00:00", tx_id="M2"),
    ])
    write_prices(ws / "prices.json", {"US0378331005": ("150", "EUR"), "US67066G1040": ("120", "EUR")})
    code, out = run(t212_args(), ws)
    assert code == 1 and "Stock split open" in out and "Not available" in out


def test_a_price_in_the_wrong_unit_is_caught(hand):
    write_prices(hand / "prices.json", {"AAAAAAAAAAA1": ("20000", "EUR"), "BBBBBBBBBBB2": ("90", "EUR")})
    _, out = run(hand_args(), hand)
    assert "Not available (value EUR" in out and "check the close's unit" in out


def test_a_weekend_deposit_buys_at_mondays_nav_not_fridays(tmp_path):
    # Friday 2026-01-09 NAV 100, Monday 2026-01-12 NAV 200
    write_tx(tmp_path / "tx.csv", ["2026-01-10,deposit,,,,1000,EUR"])
    write_prices(tmp_path / "prices.json", {})
    write_nav(tmp_path / "nav.csv", daily("2026-01-12", AS_OF, lambda i: 200) | {"2026-01-09": 100})
    code, out = run(hand_args(), tmp_path)
    assert code == 0, out
    # 1000 at Monday's 200 = 5 units * 200 = 1000: no gap. At Friday's 100 it would be +1000.
    assert "| Account today: holdings + cash | 1000.00 | 1000.00 | 0.00 |" in out
    assert "2026-01-10 filled at the 2026-01-12 NAV, the first after it" in out


@pytest.mark.parametrize("dates,expect", [
    (["18/11/2026", "17/11/2026"], date(2026, 11, 18)),   # day first: 18 > 12
    (["11/18/2026", "11/17/2026"], date(2026, 11, 18)),   # month first: 18 > 12
])
def test_nav_import_settles_slashed_dates_from_the_column(tmp_path, dates, expect):
    rows = [["Currency:", "USD"], ["Date", "NAV/Share"], [dates[0], "12.5"], [dates[1], "12.4"]]
    (tmp_path / "n.xlsx").write_bytes(make_xlsx(rows))
    code, out = run(["nav-import", "n.xlsx", "--isin", "IE000XZSV718", "--ticker", "SPYL",
                     "--source", "x"], tmp_path)
    assert code == 0, out
    assert f"{expect},12.5" in out


def test_nav_import_refuses_ambiguous_dates(tmp_path):
    rows = [["Currency:", "USD"], ["Date", "NAV"], ["03/04/2026", "12.5"], ["02/04/2026", "12.4"]]
    (tmp_path / "n.xlsx").write_bytes(make_xlsx(rows))
    code, out = run(["nav-import", "n.xlsx", "--isin", "IE000XZSV718", "--ticker", "SPYL",
                     "--source", "x"], tmp_path)
    assert code == 1 and "day or month first" in out


def test_nav_import_refuses_a_jump_that_is_a_misread(tmp_path):
    rows = [["Currency:", "USD"], ["Date", "NAV"], ["18-Nov-2026", "1250"], ["17-Nov-2026", "12.4"]]
    (tmp_path / "n.xlsx").write_bytes(make_xlsx(rows))
    code, out = run(["nav-import", "n.xlsx", "--isin", "IE000XZSV718", "--ticker", "SPYL",
                     "--source", "x"], tmp_path)
    assert code == 1 and "misread column" in out


def test_nav_import_refuses_a_currency_that_contradicts_the_file(tmp_path):
    rows = [["Currency:", "EUR"], ["Date", "NAV"], ["18-Nov-2026", "12.5"], ["17-Nov-2026", "12.4"]]
    (tmp_path / "n.xlsx").write_bytes(make_xlsx(rows))
    code, out = run(["nav-import", "n.xlsx", "--isin", "IE000XZSV718", "--ticker", "SPYL",
                     "--source", "x", "--currency", "USD"], tmp_path)
    assert code == 1 and "says its NAV is in EUR, not USD" in out


def test_a_dividend_with_nothing_held_refuses(tmp_path):
    write_nav(tmp_path / "nav.csv", daily("2026-01-01", AS_OF, lambda i: 100))
    write_tx(tmp_path / "tx.csv", ["2026-01-05,deposit,,,,100,EUR",
                                    "2026-01-06,dividend,AAAAAAAAAAA1,AAA,,5,EUR"])
    write_prices(tmp_path / "prices.json", {})
    code, out = run(hand_args(), tmp_path)
    assert code == 1 and "no shares of it held" in out


def test_a_sole_t212_account_runs_with_cutoff_and_no_ownership_file(tmp_path):
    ws = t212_workspace(tmp_path, [
        deposit("500", "2025-10-13 09:00:00+00:00"),
        buy(isin="US0378331005", ticker="AAPL", qty="1", total="200", time="2025-11-03 10:00:00+00:00", tx_id="M1"),
    ])
    (ws / "ownership.md").unlink()
    write_prices(ws / "prices.json", {"US0378331005": ("250", "EUR")})
    code, out = run(["report", "--nav", "nav.csv", "--prices", "prices.json", "--data-dir",
                     "data/t212", "--ownership", "ownership.md", "--cutoff", "2025-10-13"], ws)
    assert code == 0, out
    assert "Lazy twin (EUR," in out
