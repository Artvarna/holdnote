#!/usr/bin/env python3
"""Decision Mirror: the user's own decisions against a lazy twin.

Follow RULES.md. The module is references/decision-mirror.md.

The lazy twin puts the same money in on the same days, buys one benchmark
fund (the one locked in profile.md), and never sells on its own. Two twins
are computed, and the gap between them and the user splits exactly:

- **Trade twin.** Every buy of a holding puts the same EUR into the
  benchmark that day. Selling N% of a holding sells N% of that holding's
  twin. ``you - trade twin`` per holding is what that holding's picks did,
  and the holdings add up to the total exactly. This is the headline, and
  the only twin for a shared account.
- **Deposit twin.** Every deposit goes straight into the benchmark; a
  withdrawal takes the same EUR out. ``trade twin - deposit twin`` is what
  cash waiting in the account did. Computed only for an account that is the
  user's alone and whose export reaches its first deposit: in a shared
  account, the cash pool is not the user's to split.

Nothing here is fetched and nothing is recalled. Inputs:

- the user's trades: Trading 212 exports (``--data-dir`` + ``--ownership``,
  the same engine and FIFO attribution as the portfolio sync), or the
  broker-neutral ``me/transactions.csv`` (``--transactions``);
- ``--nav``: the benchmark's daily NAV history, in the CSV form ``nav-import``
  writes from the issuer's own file;
- ``--fx``: the ECB's euro reference-rate history (``eurofxref-hist.zip`` or
  the CSV inside it), for a USD NAV and for non-EUR amounts;
- ``--prices``: today's closes, the JSON ``market_weights.py`` reads.

What it prints is arithmetic about the past. It has no word for a gap
beyond its sign -- no "mistake", "cost you", "should", "beat" -- because a
reading of the gap is the user's (rules 6, 8, 11).

    python3 scripts/mirror.py report --nav nav.csv --fx eurofxref-hist.zip \\
        --prices prices.json --data-dir data/t212 --ownership me/ownership.md
    python3 scripts/mirror.py nav-import navhist.xlsx --isin IE000XZSV718 \\
        --ticker SPYL --source "SSGA NAV history file, fetched 2026-11-19" > nav.csv

Exit codes: 0 printed, 1 refused (the reason on stdout), 2 usage.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import t212_holdings as t  # noqa: E402

CENT = Decimal("0.01")
ZERO = Decimal(0)
TINY = Decimal("0.0000001")  # share quantities are exported to 8-10 places

# A NAV or rate older than this, against the day it prices, is a gap in the
# file rather than a weekend or a holiday: the longest market closure in the
# benchmark's history (Easter, Christmas) is four days.
MAX_LAG_DAYS = 5
# History this short says little about skill (DECISIONS.md, Decision Mirror).
SHORT_MONTHS = 36
FEW_TRADES = 20

DEFAULT_BENCHMARK = ("SPYL", "IE000XZSV718", "SPDR S&P 500 UCITS ETF (Acc)")


class Refused(Exception):
    """The run cannot produce a correct figure; the message says why."""


# --------------------------------------------------------------------------
# Numbers
# --------------------------------------------------------------------------


def q(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def money(value: Decimal | None) -> str:
    return "Not available" if value is None else f"{q(value):.2f}"


def signed(value: Decimal | None) -> str:
    if value is None:
        return "Not available"
    v = q(value)
    return "0.00" if v == 0 else f"{v:+.2f}"


def pct(part: Decimal, whole: Decimal) -> str:
    if not whole:
        return "Not available"
    v = (part / whole * 100).quantize(CENT, rounding=ROUND_HALF_UP)
    return "0.00%" if v == 0 else f"{v:+.2f}%"


def dec(raw: object, where: str, positive: bool = True) -> Decimal:
    text = str(raw).strip().replace(" ", "").replace(",", "")
    try:
        value = Decimal(text)
    except (InvalidOperation, ValueError):
        raise Refused(f"{where}: {raw!r} is not a number")
    if not value.is_finite() or (positive and value <= 0):
        raise Refused(f"{where}: {raw!r} is not a positive number")
    return value


# --------------------------------------------------------------------------
# Dated series: the benchmark NAV and the ECB rates
# --------------------------------------------------------------------------


@dataclass
class Series:
    """Values by date, read on or before a day, never interpolated."""

    name: str
    points: dict[date, Decimal]
    source: str = ""
    _days: list[date] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        self._days = sorted(self.points)

    @property
    def first(self) -> date:
        return self._days[0]

    @property
    def last(self) -> date:
        return self._days[-1]

    def on_or_before(self, day: date) -> tuple[date, Decimal]:
        if not self._days or day < self._days[0]:
            start = self._days[0].isoformat() if self._days else "nothing"
            raise Refused(f"{self.name} has no value on or before {day} (the file starts {start})")
        lo, hi = 0, len(self._days) - 1
        while lo < hi:  # last index with _days[i] <= day
            mid = (lo + hi + 1) // 2
            if self._days[mid] <= day:
                lo = mid
            else:
                hi = mid - 1
        found = self._days[lo]
        if found == self._days[-1] and (day - found).days > MAX_LAG_DAYS:
            raise Refused(f"{self.name}: the file ends {found}, {(day - found).days} days before "
                          f"{day} - it needs fetching again")
        if (day - found).days > MAX_LAG_DAYS:
            raise Refused(f"{self.name}: the newest value on or before {day} is from {found}, "
                          f"{(day - found).days} days earlier - the file has a gap there")
        return found, self.points[found]


    def on_or_after(self, day: date) -> tuple[date, Decimal] | None:
        """The first value on or after a day, within the lag; None past the file's end."""
        if not self._days or self._days[-1] < day:
            return None
        lo, hi = 0, len(self._days) - 1
        while lo < hi:  # first index with _days[i] >= day
            mid = (lo + hi) // 2
            if self._days[mid] >= day:
                hi = mid
            else:
                lo = mid + 1
        found = self._days[lo]
        if (found - day).days > MAX_LAG_DAYS:
            raise Refused(f"{self.name}: no value within {MAX_LAG_DAYS} days after {day} "
                          f"(the next is {found}) - the file has a gap there")
        return found, self.points[found]


@dataclass
class Nav:
    isin: str
    ticker: str
    currency: str
    series: Series
    url: str = ""
    retrieved: str = ""


def read_nav_csv(path: Path) -> Nav:
    """The CSV ``nav-import`` writes: ``# key: value`` lines, then date,nav."""
    meta: dict[str, str] = {}
    body: list[str] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.startswith("#"):
            key, _, value = line[1:].partition(":")
            meta[key.strip().lower()] = value.strip()
        elif line.strip():
            body.append(line)
    for key in ("isin", "ticker", "currency", "source"):
        if not meta.get(key):
            raise Refused(f"{path.name}: no '# {key}:' line - write it with "
                          "`mirror.py nav-import`")
    points: dict[date, Decimal] = {}
    reader = csv.DictReader(body)
    if not reader.fieldnames or [f.strip().lower() for f in reader.fieldnames][:2] != ["date", "nav"]:
        raise Refused(f"{path.name}: the header must be 'date,nav'")
    for n, row in enumerate(reader, 2):
        try:
            day = date.fromisoformat(row["date"].strip())
        except (ValueError, AttributeError):
            raise Refused(f"{path.name}: row {n}: {row.get('date')!r} is not YYYY-MM-DD")
        if day in points:
            raise Refused(f"{path.name}: {day} appears twice")
        points[day] = dec(row["nav"], f"{path.name}: {day} NAV")
    if not points:
        raise Refused(f"{path.name}: no NAV rows")
    ccy = meta["currency"].upper()
    if not re.fullmatch(r"[A-Z]{3}", ccy):
        raise Refused(f"{path.name}: currency {meta['currency']!r} is not an ISO code")
    return Nav(meta["isin"].upper(), meta["ticker"].upper(), ccy,
               Series(f"{meta['ticker'].upper()} NAV", points, meta["source"]),
               meta.get("url", ""), meta.get("retrieved", ""))


def read_ecb(path: Path) -> dict[str, Series]:
    """ECB euro reference rates, units per 1 EUR, one series per currency."""
    data = path.read_bytes()
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = [n for n in z.namelist() if n.lower().endswith(".csv")]
            if not names:
                raise Refused(f"{path.name}: the zip holds no CSV")
            data = z.read(names[0])
    rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
    if not rows or rows[0][0].strip() != "Date":
        raise Refused(f"{path.name}: not the ECB reference-rate history (no 'Date' header)")
    header = [h.strip() for h in rows[0]]
    points: dict[str, dict[date, Decimal]] = defaultdict(dict)
    for row in rows[1:]:
        if not row or not row[0].strip():
            continue
        day = date.fromisoformat(row[0].strip())
        for ccy, cell in zip(header[1:], row[1:]):
            cell = cell.strip()
            if ccy and cell and cell.upper() != "N/A":
                points[ccy][day] = dec(cell, f"ECB {ccy} {day}")
    source = "ECB euro foreign exchange reference rates"
    return {ccy: Series(f"ECB {ccy} rate", p, source) for ccy, p in points.items() if p}


@dataclass
class Pricer:
    """EUR value of the benchmark and of non-EUR amounts on a day."""

    nav: Nav
    fx: dict[str, Series]

    def to_eur(self, amount: Decimal, ccy: str, day: date) -> tuple[Decimal, date | None]:
        if ccy == "EUR":
            return amount, None
        series = self.fx.get(ccy)
        if series is None:
            raise Refused(f"no ECB {ccy} rate in the rate file")
        rate_day, per_eur = series.on_or_before(day)
        return amount / per_eur, rate_day

    def bench(self, day: date) -> tuple[Decimal, date, date | None]:
        """Benchmark NAV in EUR to value a holding on a day: the newest on or before it."""
        nav_day, nav = self.nav.series.on_or_before(day)
        eur, rate_day = self.to_eur(nav, self.nav.currency, nav_day)
        return eur, nav_day, rate_day

    def fill(self, day: date) -> tuple[Decimal, date, date | None]:
        """Benchmark NAV in EUR for money that moved on a day: the first NAV it could get.

        Money that arrives on a Saturday buys at Monday's NAV, never Friday's:
        a price from before the money existed is hindsight. Past the end of
        the file (a flow on the newest day, before its NAV is published) it
        is the newest NAV, and the run says so.
        """
        hit = self.nav.series.on_or_after(day)
        if hit is None:
            return self.bench(day)
        nav_day, nav = hit
        eur, rate_day = self.to_eur(nav, self.nav.currency, nav_day)
        return eur, nav_day, rate_day


# --------------------------------------------------------------------------
# The user's money flows
# --------------------------------------------------------------------------

BUY, SELL, DIVIDEND = "buy", "sell", "dividend"
DEPOSIT, WITHDRAWAL, INCOME = "deposit", "withdrawal", "income"
KINDS = {BUY, SELL, DIVIDEND, DEPOSIT, WITHDRAWAL, INCOME}


@dataclass
class Flow:
    day: date
    kind: str
    eur: Decimal  # magnitude, EUR
    isin: str = ""
    ticker: str = ""
    qty: Decimal = ZERO  # the user's shares moved (buy, sell)
    where: str = ""


@dataclass
class Flows:
    flows: list[Flow]
    shared: bool  # the account holds money that is not the user's
    start: date  # from this day every flow is the user's
    uncertain: dict[str, str] = field(default_factory=dict)  # isin -> why left out
    cash_complete: bool = True  # every cash row is understood
    notes: list[str] = field(default_factory=list)
    source: str = ""


def _t212_eur(amount: Decimal, ccy: str, fixed: t.FixedRate | None, where: str) -> Decimal:
    if ccy == "EUR":
        return amount
    if fixed is not None and fixed.base == "EUR":
        converted = fixed.to_base(ccy, amount)
        if converted is not None:
            return converted
    hint = (" - declare '1 EUR = 1.95583 BGN (Council Regulation (EU) 2025/1409)' as "
            "Fixed rate in ownership.md" if ccy == "BGN" else "")
    raise Refused(f"{where}: total in {ccy or 'no currency'}, which is neither EUR nor a "
                  f"declared fixed rate{hint}")


CASH_IN = {"deposit": DEPOSIT, "card credit": INCOME, "card cashback": INCOME,
           "interest on cash": INCOME}
CASH_OUT = {"withdrawal": WITHDRAWAL, "card debit": WITHDRAWAL}


def flows_from_t212(txs: list[t.Tx], ownership: t.Ownership) -> Flows:
    """The user's flows from the exports, FIFO-split at the ownership cutoff.

    The same rule as ``t212_holdings.fifo_attribution``, walked row by row
    because the Mirror needs each sell's own share and date, not totals.
    A holding whose split the export cannot settle -- one of the user's lots
    was sold after the export showed shares sold that no lot backs -- is left
    out whole and named, never estimated.
    """
    cutoff = ownership.cutoff
    fixed = ownership.fixed_rate
    out: list[Flow] = []
    lots: dict[str, list[list]] = defaultdict(list)  # isin -> [[qty, owner]]
    unbacked: set[str] = set()
    uncertain: dict[str, str] = {}
    names: dict[str, str] = {}
    notes: list[str] = []
    shared = any(tx.time.date() < cutoff for tx in txs)
    cash_complete = True

    for tx in sorted(txs, key=lambda x: (x.time, x.source.line)):
        day = tx.time.date()
        mine = day >= cutoff
        where = str(tx.source)
        isin = tx.isin
        if isin and tx.ticker:
            names[isin] = tx.ticker
        total = abs(tx.total) if tx.total is not None else None

        if tx.kind == BUY:
            qty = tx.qty or ZERO
            if qty > 0:
                lots[isin].append([qty, "mine" if mine else "holder"])
            if mine:
                if total is None:
                    raise Refused(f"{where}: a buy with no Total")
                out.append(Flow(day, BUY, _t212_eur(total, tx.total_ccy, fixed, where),
                                isin, tx.ticker, qty, where))
            continue

        if tx.kind == SELL:
            qty = tx.qty or ZERO
            remaining, mine_taken = qty, ZERO
            while remaining > 0 and lots[isin]:
                lot = lots[isin][0]
                taken = min(lot[0], remaining)
                if lot[1] == "mine":
                    mine_taken += taken
                    if isin in unbacked:
                        uncertain[isin] = ("shares were sold before your first buy that the "
                                           "export cannot account for, so which later sells "
                                           "were yours is not settled")
                lot[0] -= taken
                remaining -= taken
                if lot[0] == 0:
                    lots[isin].pop(0)
            if remaining > 0:
                unbacked.add(isin)
            if mine_taken > 0:
                if total is None:
                    raise Refused(f"{where}: a sell with no Total")
                share = _t212_eur(total, tx.total_ccy, fixed, where) * mine_taken / qty
                out.append(Flow(day, SELL, share, isin, tx.ticker, mine_taken, where))
            continue

        if tx.kind == DIVIDEND:
            if not mine or total is None:
                continue
            mine_held = sum((lot[0] for lot in lots[isin] if lot[1] == "mine"), ZERO)
            if mine_held <= 0:
                continue
            held = tx.qty  # a dividend row's quantity is the holding, not a movement
            if held is None or held <= 0:
                if all(lot[1] == "mine" for lot in lots[isin]):
                    fraction = Decimal(1)
                else:
                    uncertain[isin] = "a dividend row does not say how many shares it was paid on"
                    continue
            else:
                fraction = min(Decimal(1), mine_held / held)
            out.append(Flow(day, DIVIDEND, _t212_eur(total, tx.total_ccy, fixed, where) * fraction,
                            isin, tx.ticker, ZERO, where))
            continue

        if tx.kind == "unknown" and isin:
            if any(lot[1] == "mine" for lot in lots[isin]) or mine:
                uncertain[isin] = (f"the export has a {tx.action!r} row for it, which changes "
                                   "shares in a way the Mirror does not model")
            continue
        if not mine:
            continue
        base = tx.action.strip().lower()
        if base == "currency conversion":
            continue  # BGN to EUR at the fixed rate: the same money, restated
        kind = CASH_IN.get(base) or CASH_OUT.get(base)
        if kind is None or total is None:
            cash_complete = False
            notes.append(f"{where}: {tx.action!r} is not a row the Mirror understands; "
                         "the deposit twin is left out")
            continue
        out.append(Flow(day, kind, _t212_eur(total, tx.total_ccy, fixed, where), where=where))

    for flow in out:
        if flow.isin and not flow.ticker:
            flow.ticker = names.get(flow.isin, flow.isin)
    if shared:
        notes.append(f"the account holds money from before {cutoff} that is not yours, so only "
                     "the trade twin is computed")
    return Flows(out, shared, cutoff, uncertain, cash_complete, notes,
                 f"Trading 212 exports, your transactions from {cutoff} ({ownership.cutoff_source})")


TX_COLUMNS = ["date", "type", "isin", "ticker", "quantity", "amount", "currency"]
TX_TYPES = {"buy": BUY, "sell": SELL, "dividend": DIVIDEND, "deposit": DEPOSIT,
            "withdrawal": WITHDRAWAL, "interest": INCOME, "income": INCOME}


def flows_from_csv(path: Path, pricer: Pricer) -> Flows:
    """``me/transactions.csv``: one row per buy, sell, dividend or cash move.

    Amount is the cash that moved, in its currency, fees included: what left
    the account on a buy, what arrived on a sell or a dividend. A non-EUR
    amount is restated at the ECB rate of its day. The file is the user's
    alone: a shared account is a Trading 212 export with an ownership cutoff.
    """
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    header = [h.strip().lower() for h in (reader.fieldnames or [])]
    missing = [c for c in TX_COLUMNS if c not in header]
    if missing:
        raise Refused(f"{path.name}: missing column(s) {', '.join(missing)}; the header is "
                      + ",".join(TX_COLUMNS))
    out: list[Flow] = []
    held: dict[str, Decimal] = defaultdict(Decimal)
    rows = []
    for n, raw in enumerate(reader, 2):
        row = {k.strip().lower(): (v or "").strip() for k, v in raw.items() if k}
        if not any(row.values()):
            continue
        where = f"{path.name}:{n}"
        try:
            day = date.fromisoformat(row["date"])
        except ValueError:
            raise Refused(f"{where}: date {row['date']!r} is not YYYY-MM-DD")
        kind = TX_TYPES.get(row["type"].lower())
        if kind is None:
            raise Refused(f"{where}: type {row['type']!r} is not one of {', '.join(TX_TYPES)}")
        rows.append((day, n, kind, row, where))
    order = {DEPOSIT: 0, INCOME: 1, BUY: 2, SELL: 2, DIVIDEND: 3, WITHDRAWAL: 4}
    for day, _n, kind, row, where in sorted(rows, key=lambda r: (r[0], order[r[2]], r[1])):
        ccy = (row["currency"] or "EUR").upper()
        amount = dec(row["amount"].lstrip("-"), f"{where} amount")
        eur, _ = pricer.to_eur(amount, ccy, day)
        isin = row["isin"].upper()
        qty = ZERO
        if kind in (BUY, SELL, DIVIDEND) and not isin:
            raise Refused(f"{where}: a {kind} needs an ISIN")
        if kind == DIVIDEND and held[isin] <= TINY:
            raise Refused(f"{where}: a dividend on {isin} with no shares of it held before it - "
                          "the file does not reach back to the first buy")
        if kind in (BUY, SELL):
            qty = dec(row["quantity"].lstrip("-"), f"{where} quantity")
            if kind == SELL and qty > held[isin] + TINY:
                raise Refused(f"{where}: sells {qty} {isin} but only {held[isin]} were bought "
                              "before it - the file does not reach back to the first buy")
            held[isin] += qty if kind == BUY else -qty
        out.append(Flow(day, kind, eur, isin, row["ticker"] or isin, qty, where))
    if not out:
        raise Refused(f"{path.name}: no rows")
    has_cash = any(f.kind == DEPOSIT for f in out)
    notes = [] if has_cash else ["the file has no deposit rows, so the deposit twin is left out"]
    return Flows(out, False, out[0].day, {}, has_cash, notes, f"{path.name}")


# --------------------------------------------------------------------------
# The twins
# --------------------------------------------------------------------------


@dataclass
class Leg:
    """One holding: the user's side and its own trade twin."""

    isin: str
    ticker: str
    bought: Decimal = ZERO
    proceeds: Decimal = ZERO
    dividends: Decimal = ZERO
    qty: Decimal = ZERO
    bought_qty: Decimal = ZERO
    twin_units: Decimal = ZERO
    twin_proceeds: Decimal = ZERO
    trades: int = 0
    value: Decimal | None = None  # today's value of qty, EUR
    reason: str = ""  # why value is missing

    # Every figure a table prints is rounded to the cent first, and every total
    # is the sum of the rounded figures, so each printed table adds up exactly.
    @property
    def you(self) -> Decimal | None:
        return None if self.value is None else q(self.value + self.proceeds + self.dividends)

    def twin(self, bench_today: Decimal) -> Decimal:
        return q(self.twin_units * bench_today + self.twin_proceeds)

    def gap(self, bench_today: Decimal) -> Decimal | None:
        you = self.you
        return None if you is None else you - self.twin(bench_today)


@dataclass
class Sale:
    day: date
    isin: str
    ticker: str
    qty: Decimal
    got: Decimal
    today: Decimal | None = None


@dataclass
class Mirror:
    legs: list[Leg]
    sales: list[Sale]
    bench_today: Decimal
    bench_dates: tuple[date, date | None]
    first: date
    as_of: date
    trades: int
    # deposit twin; None when not computed, with the reason
    deposited: Decimal | None = None
    withdrawn: Decimal = ZERO
    cash_now: Decimal | None = None
    dep_units: Decimal | None = None
    deposit_reason: str = ""
    notes: list[str] = field(default_factory=list)
    excluded: dict[str, str] = field(default_factory=dict)  # ticker -> why
    lookups: list[str] = field(default_factory=list)

    # --- totals over the holdings that have a figure
    @property
    def priced(self) -> list[Leg]:
        return [leg for leg in self.legs if leg.you is not None]

    @property
    def bought(self) -> Decimal:
        return sum((q(leg.bought) for leg in self.priced), ZERO)

    @property
    def you(self) -> Decimal:
        return sum((leg.you for leg in self.priced), ZERO)

    @property
    def twin(self) -> Decimal:
        return sum((leg.twin(self.bench_today) for leg in self.priced), ZERO)

    @property
    def picks(self) -> Decimal:
        return self.you - self.twin

    @property
    def complete(self) -> bool:
        return len(self.priced) == len(self.legs)

    # --- deposit twin
    @property
    def has_deposit_twin(self) -> bool:
        return self.dep_units is not None and self.complete

    @property
    def account(self) -> Decimal:
        held = sum((leg.value for leg in self.legs), ZERO)
        return held + q(self.cash_now)

    @property
    def deposit_twin(self) -> Decimal:
        return q(self.dep_units * self.bench_today)

    @property
    def trade_twin_account(self) -> Decimal:
        """The picks twin with the account's cash: the bridge between the two twins."""
        held = sum((leg.twin_units for leg in self.legs), ZERO) * self.bench_today
        cash = (self.cash_now
                - sum((leg.proceeds + leg.dividends for leg in self.legs), ZERO)
                + sum((leg.twin_proceeds for leg in self.legs), ZERO))
        return held + cash

    @property
    def waiting(self) -> Decimal:
        """Cash waiting: the bridge from the picks twin to the lazy twin.

        It equals ``trade_twin_account - deposit_twin`` to within the cents
        of rounding; it is taken as the remainder so the breakdown table adds
        up to its own total exactly.
        """
        return (self.account - self.deposit_twin) - self.picks


def build(flows: Flows, pricer: Pricer, as_of: date, prices: dict, fx_today: dict,
          today_price) -> Mirror:
    """Walk the flows in date order, building each holding and both twins."""
    rows = sorted(flows.flows, key=lambda f: f.day)
    if not rows:
        raise Refused("no transactions of yours to mirror")
    if rows[-1].day > as_of:
        raise Refused(f"a transaction on {rows[-1].day} is after the as-of date {as_of}")
    lookups: set[str] = set()

    def bench(day: date) -> Decimal:
        price, nav_day, rate_day = pricer.fill(day)
        if nav_day > day:
            lookups.add(f"{day} filled at the {nav_day} NAV, the first after it")
        elif nav_day < day:
            lookups.add(f"{day} filled at the {nav_day} NAV, the newest published by the as-of date")
        return price

    legs: dict[str, Leg] = {}
    sales: list[Sale] = []
    dep_units = ZERO
    deposited = withdrawn = cash = ZERO
    clamped = False
    for f in rows:
        if f.isin and f.isin in flows.uncertain:
            continue
        if f.kind in (BUY, SELL, DIVIDEND):
            leg = legs.setdefault(f.isin, Leg(f.isin, f.ticker))
        if f.kind == BUY:
            leg.bought += f.eur
            leg.qty += f.qty
            leg.bought_qty += f.qty
            leg.twin_units += f.eur / bench(f.day)
            leg.trades += 1
            cash -= f.eur
        elif f.kind == SELL:
            if f.qty > leg.qty + TINY:
                raise Refused(f"{f.where}: sells {f.qty} of {f.ticker} with {leg.qty} held")
            fraction = min(Decimal(1), f.qty / leg.qty)
            units = leg.twin_units * fraction
            leg.twin_proceeds += units * bench(f.day)
            leg.twin_units -= units
            leg.qty = max(ZERO, leg.qty - f.qty)
            leg.proceeds += f.eur
            leg.trades += 1
            cash += f.eur
            sales.append(Sale(f.day, f.isin, f.ticker, f.qty, f.eur))
        elif f.kind == DIVIDEND:
            leg.dividends += f.eur
            cash += f.eur
        elif f.kind == DEPOSIT:
            deposited += f.eur
            dep_units += f.eur / bench(f.day)
            cash += f.eur
        elif f.kind == WITHDRAWAL:
            withdrawn += f.eur
            units = f.eur / bench(f.day)
            if units > dep_units:
                clamped = True
                units = dep_units
            dep_units -= units
            cash -= f.eur
        elif f.kind == INCOME:
            cash += f.eur

    bench_today, nav_day, rate_day = pricer.bench(as_of)
    mirror = Mirror(
        legs=sorted(legs.values(), key=lambda leg: -leg.bought),
        sales=sales,
        bench_today=bench_today,
        bench_dates=(nav_day, rate_day),
        first=rows[0].day,
        as_of=as_of,
        trades=sum(leg.trades for leg in legs.values()),
        notes=list(flows.notes),
        excluded={_ticker(flows, isin): why for isin, why in flows.uncertain.items()},
        lookups=sorted(lookups),
    )

    # Today's value of what each holding still has.
    for leg in mirror.legs:
        if leg.qty <= TINY:
            leg.qty, leg.value = ZERO, ZERO
            continue
        cost = leg.bought * leg.qty / leg.bought_qty if leg.bought_qty else None
        leg.value, leg.reason = today_price(leg.isin, leg.ticker, leg.qty, prices, fx_today,
                                            as_of, cost)
    for sale in sales:
        if sale.isin in prices:
            value, _ = today_price(sale.isin, sale.ticker, sale.qty, prices, fx_today, as_of, None)
            sale.today = value

    # The deposit twin, where the cash is the user's and every row is known.
    if flows.shared:
        mirror.deposit_reason = "the account is shared, so its cash is not yours alone to split"
    elif not flows.cash_complete:
        mirror.deposit_reason = "the export has cash rows the Mirror does not understand"
    elif deposited <= 0:
        mirror.deposit_reason = "no deposits in the file"
    elif rows[0].kind != DEPOSIT:
        mirror.deposit_reason = (f"the first row ({rows[0].day}, a {rows[0].kind}) comes before "
                                 "any deposit, so the export does not reach the account's start")
    elif cash < -CENT:
        mirror.deposit_reason = (f"the rows leave the account EUR {money(-cash)} below zero, so "
                                 "some rows are missing from the export")
    elif not mirror.complete:
        mirror.deposit_reason = "a holding has no price today"
    else:
        mirror.deposited, mirror.withdrawn = deposited, withdrawn
        mirror.cash_now, mirror.dep_units = max(cash, ZERO), dep_units
        if clamped:
            mirror.notes.append("a withdrawal took out more than the deposit twin held; "
                                "the twin was emptied, not taken below zero")
    return mirror


def _ticker(flows: Flows, isin: str) -> str:
    for f in flows.flows:
        if f.isin == isin and f.ticker:
            return f.ticker
    return isin


def price_today(isin: str, ticker: str, qty: Decimal, prices: dict, fx: dict, as_of: date,
                cost: Decimal | None = None):
    """(EUR value, "") or (None, reason), through market_weights' own pricing.

    ``cost`` is what the held shares cost on average: a value ten times it or
    a tenth of it is a unit error (pence as pounds) until shown otherwise.
    """
    import market_weights as mw

    try:
        priced = mw.price_rows([mw.Row("", isin, ticker, qty, None, cost_eur=cost)],
                               as_of, prices, fx)[0]
    except mw.Refused as exc:
        return None, str(exc)
    return priced.value, priced.reason


# --------------------------------------------------------------------------
# Thesis column (references/thesis-watchdog.md)
# --------------------------------------------------------------------------


def thesis_status(theses: Path | None, watch: Path | None) -> dict[str, str]:
    """Ticker or ISIN -> what Holdnote holds on it: none, on file, a tripwire."""
    out: dict[str, str] = {}
    if theses and theses.is_dir():
        for p in sorted(theses.glob("*.md")):
            m = re.fullmatch(r"(.+)-(\d{4}-\d{2}-\d{2})\.md", p.name)
            if m:
                out[m.group(1).upper()] = f"on file ({m.group(2)})"
    if watch and watch.is_file():
        import watchdog

        for key, state in watchdog.holding_status(watch).items():
            out[key] = state if state.startswith("tripwire") or key not in out else out[key]
    return out


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(r) + " |" for r in rows]
    return lines


def months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + b.month - a.month - (1 if b.day < a.day else 0)


def headline(m: Mirror) -> tuple[Decimal, Decimal, str]:
    """(gap, basis, twin): the one figure the output leads with."""
    if m.has_deposit_twin:
        return m.account - m.deposit_twin, m.deposited, "lazy"
    return m.picks, m.bought, "picks"


def render(m: Mirror, label: str, theses: dict[str, str], ticker: str = "") -> list[str]:
    out: list[str] = []
    ticker = ticker or label
    gap, basis, twin = headline(m)
    span = f"EUR, {m.first} to {m.as_of}"

    if twin == "lazy":
        out.append(f"Lazy twin ({span}, the same deposits put into {ticker} at once)")
        out += _table(["Line", "You", "Twin", "You - twin"], [
            ["Money deposited", money(m.deposited), money(m.deposited), ""],
        ] + ([["Money withdrawn", money(m.withdrawn), money(m.withdrawn), ""]]
             if m.withdrawn else []) + [
            ["Account today: holdings + cash", money(m.account), money(m.deposit_twin),
             signed(gap)],
            ["Gap, % of money deposited", "", "", pct(gap, m.deposited)],
        ])
        out.append("")
        out.append(f"Where the gap comes from ({span})")
        out += _table(["Part", "You - twin"], [
            ["What you picked: the picks twin's gap", signed(m.picks)],
            ["Cash waiting: never invested, or not reinvested after a sale", signed(m.waiting)],
            ["Total", signed(gap)],
        ])
        out.append("")
    out.append(f"Picks twin ({span}, the same purchases on the same days in {ticker})")
    out += _table(["Line", "You", "Twin", "You - twin"], [
        ["Your purchases", money(m.bought), money(m.bought), ""],
        ["Worth today: held + sold + dividends", money(m.you), money(m.twin), signed(m.picks)],
        ["Gap, % of your purchases", "", "", pct(m.picks, m.bought)],
    ])
    out.append("")

    out.append(f"By holding ({span})")
    rows = []
    for leg in m.legs:
        g = leg.gap(m.bench_today)
        key = theses.get(leg.ticker.upper()) or theses.get(leg.isin) or "none"
        rows.append([
            leg.ticker, key, money(leg.bought),
            money(leg.you) if leg.you is not None else f"Not available ({leg.reason})",
            money(leg.twin(m.bench_today)), signed(g),
        ])
    out += _table(["Holding", "Thesis", "Bought", "You today", "Twin today", "You - twin"], rows)
    out.append("")

    if m.sales:
        out.append(f"Sells (EUR, today's price as of {m.as_of})")
        rows = []
        for s in m.sales:
            diff = None if s.today is None else s.today - s.got
            rows.append([s.day.isoformat(), s.ticker, f"{s.qty.normalize():f}", money(s.got),
                         money(s.today), signed(diff)])
        out += _table(["Sold on", "Holding", "Shares", "Got", "Same shares at today's price",
                       "Difference"], rows)
        out.append("")

    gaps = [(leg.gap(m.bench_today), leg) for leg in m.priced]
    if gaps:
        biggest, leg = max(gaps, key=lambda g: abs(g[0]))
        out.append(f"Largest single holding gap: {leg.ticker} {signed(biggest)}, of a picks-twin "
                   f"gap of {signed(m.picks)}.")
    months = months_between(m.first, m.as_of)
    line = f"History: {months} months, {m.trades} trades."
    if months < SHORT_MONTHS or m.trades < FEW_TRADES:
        line += " This much history says little about skill."
    out.append(line)
    if m.excluded:
        out.append("Not included: " + "; ".join(f"{k} ({v})" for k, v in m.excluded.items()) + ".")
    missing = [leg.ticker for leg in m.legs if leg.you is None]
    if missing:
        out.append(f"Totals cover {len(m.priced)} of {len(m.legs)} holdings; no figure for "
                   + ", ".join(missing) + ".")
    if twin == "picks":
        out.append(f"Lazy twin: Not available - {m.deposit_reason}.")
    what = "money deposited" if twin == "lazy" else "your purchases"
    out.append(f"Share line: Me vs my lazy twin in {label}: {pct(gap, basis)} of {what}, "
               f"{m.first} to {m.as_of}.")
    return out


def method_lines(m: Mirror, flows: Flows, nav: Nav, fx_note: str) -> list[str]:
    nav_day, rate_day = m.bench_dates
    lines = [
        f"Trades: {flows.source}.",
        f"Benchmark: {nav.ticker} ({nav.isin}), daily NAV in {nav.currency} from {nav.series.source}"
        + (f", restated in EUR at the {fx_note} of each NAV's day" if nav.currency != "EUR" else "")
        + ".",
        f"Twin today: the {nav_day} NAV"
        + (f" at the {rate_day} rate" if rate_day else "") + f", for an as-of date of {m.as_of}.",
        "Twin purchases: each purchase's full EUR amount, fees included, goes into the benchmark "
        "at the NAV of its day, or the first NAV after it on a day with none (a weekend deposit "
        "is invested at Monday's NAV, never Friday's); the twin pays no fees, so yours stay on "
        "your side of the gap.",
        "Twin sells: selling a fraction of a holding sells the same fraction of that holding's "
        "twin at that day's NAV. Dividends you were paid count as money you have; the "
        "benchmark is accumulating, so its own are already in its NAV.",
        "Gaps are arithmetic about the past. They change with every day's prices.",
    ]
    lines += [f"Note: {n}." for n in m.notes]
    if m.lookups:
        lines.append(f"Days without a NAV of their own: {len(m.lookups)} (first: {m.lookups[0]}).")
    return lines


def summary_json(m: Mirror, label: str, demo: bool = False) -> dict:
    """The run in figures, for the card. The ``*_pct`` fields are all a card
    may draw: every one is a share of the money put in, never an amount."""
    total, basis, twin = headline(m)

    def share(x: Decimal) -> str:
        return pct(x, basis)

    months = months_between(m.first, m.as_of)
    return {
        "benchmark": label,
        "from": m.first.isoformat(),
        "as_of": m.as_of.isoformat(),
        "twin": twin,
        "basis": "money deposited" if twin == "lazy" else "your purchases",
        "gap_pct": share(total),
        "picks_pct": share(m.picks),
        "waiting_pct": share(m.waiting) if twin == "lazy" else None,
        "holdings_pct": {leg.ticker: share(g) for leg in m.priced
                         if (g := leg.gap(m.bench_today)) is not None},
        "picks_eur": str(q(m.picks)),
        "waiting_eur": str(q(m.waiting)) if twin == "lazy" else None,
        "holdings": {leg.ticker: str(q(g)) for leg in m.priced
                     if (g := leg.gap(m.bench_today)) is not None},
        "complete": m.complete and not m.excluded,
        "months": months,
        "trades": m.trades,
        "short_history": months < SHORT_MONTHS or m.trades < FEW_TRADES,
        "demo": demo,
    }


# --------------------------------------------------------------------------
# The full draft (RULES.md Part IV), checked and rendered
# --------------------------------------------------------------------------

ECB_URL = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip"


def build_stamp() -> str:
    import sys
    here = Path(__file__).resolve().parent
    sys.path.insert(0, str(here))
    from build_info import build_stamp as stamp
    return stamp(here.parent)


def compose(m: Mirror, flows: Flows, nav: Nav, label: str, theses: dict[str, str],
            inputs: list[tuple[str, str]], extra: list[dict], fx_file: Path | None,
            demo: bool, proof: bool, prices: dict | None = None) -> tuple[str, str]:
    """(full draft, report text): the six sections, every figure from ``render``."""
    gap, basis, twin = headline(m)
    nav_day, rate_day = m.bench_dates
    missing = [leg.ticker for leg in m.legs if leg.you is None]
    gaps = []
    if twin != "lazy":
        gaps.append(f"lazy twin ({m.deposit_reason})")
    gaps += [f"{t} today's value" for t in missing]
    gaps += [f"{t} (FIFO split not settled)" for t in m.excluded]
    covered = len(m.priced)
    total = len(m.legs) + len(m.excluded)

    head = [
        "STATUS: Complete.",
        "",
        "CONTEXT",
        f"Data as of:       {m.as_of}" + (" · demo, synthetic - not real prices or anyone's "
                                           "account" if demo else " · closes of that day"),
        f"Latest period:    your transactions {m.first} to {m.as_of}; benchmark NAV {nav_day}"
        + (f", ECB rate {rate_day}" if rate_day else ""),
        "Currency / units: EUR · gaps are You - twin, EUR, and % of money put in",
        f"Not available:    {'; '.join(gaps) if gaps else 'none'}",
        f"Coverage:         {covered} of {total} holdings",
        "",
    ]
    result = ["RESULT", f"Mode: {'Demo + ' if demo else ''}Decision Mirror", ""]
    result += render(m, label, theses, nav.ticker)
    result.append("")
    next_line = ("Next: attach your Trading 212 export, or fill in the transactions template, and "
                 "ask \"me vs my lazy twin\"" if demo else
                 _next_line(m, theses))
    method = ["METHOD", f"Build: {build_stamp()}",
              "Tables: " + ", ".join(t for t in (
                  ["Lazy twin", "Where the gap comes from"] if twin == "lazy" else []) +
                  ["Picks twin", "By holding"] + (["Sells"] if m.sales else [])) + " (Decision Mirror)"]
    if demo:
        method.append("Demo: every figure here is synthetic - made-up trades, prices and benchmark, "
                      "built to show how the Mirror reads. None is a real price or anyone's account.")
    method += method_lines(m, flows, nav, "ECB reference rate")
    method += [confirmation_line(m, prices, demo), next_line, ""]

    rows = ["| URL or path | Document | Published | Retrieved (UTC) |", "|---|---|---|---|"]
    nav_doc = f"{nav.ticker} daily NAV history ({nav.series.source})"
    if nav.url:
        rows.append(f"| {nav.url} | {nav_doc} | {nav.series.last} | {nav.retrieved or 'not recorded'} |")
    for path, doc in inputs:
        rows.append(f"| {path} | {doc} | n/a — local file | n/a — local file |")
    if fx_file is not None and nav.currency != "EUR":
        rows.append(f"| {ECB_URL} | ECB euro foreign exchange reference rates, history "
                    f"(read from {fx_file.name}) | {rate_day} | n/a — local file |")
    for x in extra:
        rows.append(f"| {x['url']} | {x['document']} | {x['published']} | {x['retrieved']} |")
    published = sorted({str(nav.series.last)} | {str(x["published"]) for x in extra
                                                  if re.match(r"^\d{4}-\d{2}-\d{2}$", str(x["published"]))})
    n_docs = len(rows) - 2
    unverified = 0 if demo else sum(
        1 for leg in m.legs if leg.qty > 0 and not (prices or {}).get(leg.isin, {}).get("confirmed_by"))
    summary = (f"{n_docs} documents · published {published[0]} to {published[-1]} · 0 stale · "
               f"{unverified} unverified · full list on \"show proof\"")
    draft = "\n".join(head + result + method + ["SOURCES", *rows]) + "\n"
    report = draft if proof else "\n".join(head + result + method + ["SOURCES", summary]) + "\n"
    return draft, report


def confirmation_line(m: Mirror, prices: dict | None, demo: bool) -> str:
    """Which of today's closes rest on one source (RULES.md Part IV)."""
    if demo:
        return "Confirmation: not applicable - the demo's closes are synthetic"
    used = {leg.isin: leg.ticker for leg in m.legs if leg.qty > 0}
    if not used:
        return "Confirmation: no close used - nothing is still held"
    single = [t for isin, t in used.items() if not (prices or {}).get(isin, {}).get("confirmed_by")]
    if not single:
        return "Confirmation: every close used is confirmed by a second source"
    return "Confirmation: these closes rest on one source: " + ", ".join(single)


def _next_line(m: Mirror, theses: dict[str, str]) -> str:
    bare = [leg for leg in m.legs if leg.qty > 0 and
            (theses.get(leg.ticker.upper()) or theses.get(leg.isin) or "none") == "none"]
    if bare:
        top = max(bare, key=lambda leg: leg.value or ZERO)
        return (f"Next: say \"watch {top.ticker}\" to get told when something you'd worry about "
                "changes")
    return "Next: say \"make a card\" for a picture of the share line"


# --------------------------------------------------------------------------
# NAV import from an issuer file
# --------------------------------------------------------------------------


def _is_nav_header(cell: str) -> bool:
    return cell == "nav" or cell.startswith("nav ") or cell.startswith("nav/") or \
        cell.startswith("nav per") or cell.startswith("net asset value")


SLASHED = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})$")


def _slash_order(texts: list[str], where: str) -> str | None:
    """'dmy' or 'mdy' for a column of n/n/yyyy dates, decided by the column.

    A date like 03/04/2026 is the 3rd of April or the 4th of March depending
    on the issuer; the column settles it when any first part is above 12
    (day first) or any second part is (month first). A column that cannot
    settle it is refused rather than guessed.
    """
    parts = [SLASHED.match(t.strip()) for t in texts]
    parts = [m for m in parts if m]
    if not parts:
        return None
    first = any(int(m.group(1)) > 12 for m in parts)
    second = any(int(m.group(2)) > 12 for m in parts)
    if first and not second:
        return "dmy"
    if second and not first:
        return "mdy"
    raise Refused(f"{where}: dates like {parts[0].group(0)} could be day or month first, and "
                  "the column does not say which")


def nav_from_rows(rows: list[list[str]], where: str) -> tuple[dict[date, Decimal], dict[str, str]]:
    """Find a Date / NAV header in a sheet and read the rows under it."""
    import fund_holdings as fh

    header_at = None
    for i, row in enumerate(rows):
        cells = [c.strip().lower() for c in row]
        if cells and cells[0] in ("date", "as of", "as of date", "nav date") and any(
                _is_nav_header(c) for c in cells[1:]):
            header_at = i
            break
    if header_at is None:
        raise Refused(f"{where}: no header row with Date and NAV")
    cells = [c.strip().lower() for c in rows[header_at]]
    nav_col = next(j for j, c in enumerate(cells) if j and _is_nav_header(c))
    meta = {}
    for row in rows[:header_at]:
        if row and row[0].strip().endswith(":") and len(row) > 1:
            meta[row[0].strip().rstrip(":").lower()] = row[1].strip()
    body = [r for r in rows[header_at + 1:] if r and r[0].strip()]
    order = _slash_order([r[0] for r in body], where)
    points: dict[date, Decimal] = {}
    for row in body:
        text = row[0].strip()
        m = SLASHED.match(text)
        if m and order:
            a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            day = date(y, b, a) if order == "dmy" else date(y, a, b)
        else:
            day = fh._excel_date(text)
        if day is None:
            continue  # a footnote under the table
        raw = row[nav_col] if nav_col < len(row) else ""
        if not raw.strip() or raw.strip() in ("-", "N/A"):
            continue
        if day in points:
            raise Refused(f"{where}: {day} appears twice")
        points[day] = dec(raw, f"{where}: {day} NAV")
    if len(points) < 2:
        raise Refused(f"{where}: fewer than two NAV rows under the header")
    days = sorted(points)
    for prev, cur in zip(days, days[1:]):
        move = abs(points[cur] / points[prev] - 1)
        if move > Decimal("0.25"):
            raise Refused(f"{where}: the NAV moves {move * 100:.0f}% from {prev} to {cur} - a "
                          "misread column or unit, not a day in an index fund")
    return points, meta


def cmd_nav_import(args) -> int:
    import fund_holdings as fh

    data = args.file.read_bytes()
    where = args.file.name
    if data[:2] == b"PK":
        sheet = fh.xlsx_rows(data)
        rows = [sheet[n] for n in sorted(sheet)]
    else:
        rows = list(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
    points, meta = nav_from_rows(rows, where)
    file_isin = next((v for k, v in meta.items() if "isin" in k), "").upper()
    if file_isin and file_isin != args.isin.upper():
        raise Refused(f"{where}: the file is for {file_isin}, not {args.isin}")
    stated = next((v for k, v in meta.items() if "currency" in k), "").strip().upper()
    given = (args.currency or "").strip().upper()
    if stated and given and stated != given:
        raise Refused(f"{where}: the file says its NAV is in {stated}, not {given}")
    ccy = stated or given
    if not re.fullmatch(r"[A-Z]{3}", ccy):
        raise Refused(f"{where}: the file names no NAV currency; pass --currency")
    print(f"# isin: {args.isin.upper()}")
    print(f"# ticker: {args.ticker.upper()}")
    print(f"# currency: {ccy}")
    print(f"# source: {args.source}")
    if args.url:
        print(f"# url: {args.url}")
    if args.retrieved:
        print(f"# retrieved: {args.retrieved}")
    print("date,nav")
    for day in sorted(points):
        print(f"{day.isoformat()},{points[day]}")
    return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def cmd_report(args) -> int:
    nav = read_nav_csv(args.nav)
    if args.benchmark and args.benchmark.upper() not in (nav.isin, nav.ticker):
        raise Refused(f"the locked benchmark is {args.benchmark}, but {args.nav.name} is "
                      f"{nav.ticker} ({nav.isin}); the twin never switches benchmark mid-run")
    fx = read_ecb(args.fx) if args.fx else {}
    if nav.currency != "EUR" and nav.currency not in fx:
        raise Refused(f"the NAV is in {nav.currency}; pass --fx with the ECB rate history")
    pricer = Pricer(nav, fx)
    spec = json.loads(args.prices.read_text(encoding="utf-8"))
    try:
        as_of = date.fromisoformat(spec["as_of"])
    except (KeyError, TypeError, ValueError):
        raise Refused(f"{args.prices.name}: 'as_of' must be a YYYY-MM-DD date")

    if args.transactions:
        flows = flows_from_csv(args.transactions, pricer)
    else:
        ledger = t.load_transactions(args.data_dir)
        ownership = t.load_ownership(args.ownership, args.cutoff)
        flows = flows_from_t212(ledger.txs, ownership)
    first = min(f.day for f in flows.flows) if flows.flows else None
    if first and first < nav.series.first:
        raise Refused(f"your first transaction ({first}) is before {nav.ticker}'s NAV history "
                      f"starts ({nav.series.first}); the twin cannot buy a fund before it existed")

    m = build(flows, pricer, as_of, spec.get("prices", {}), spec.get("fx", {}), price_today)
    label = args.label or f"{nav.ticker}"
    theses = thesis_status(args.theses, args.watch)
    if args.draft:
        inputs = [(str(args.transactions), "Your transactions") if args.transactions else
                  (str(args.data_dir), "Your Trading 212 exports, with " + str(args.ownership)),
                  (str(args.prices), "Closes of " + str(as_of) + " for the holdings still held"),
                  (str(args.nav), "Benchmark NAV history file")]
        extra = json.loads(args.sources.read_text(encoding="utf-8")) if args.sources else []
        draft, report = compose(m, flows, nav, label, theses, inputs, extra, args.fx,
                                args.demo, args.proof, spec.get("prices", {}))
        args.draft.write_text(draft, encoding="utf-8")
        here = Path(__file__).resolve().parent
        for folder in (here, here.parent / "tests"):
            if (folder / "contract.py").exists():
                sys.path.insert(0, str(folder))
                break
        import contract
        import render as renderer

        problems = list(dict.fromkeys(contract.output_problems(draft) +
                                      contract.output_problems(report)))
        if problems:
            print("Decision Mirror: the draft failed its contract check:")
            print("\n".join(problems))
            return 1
        print(renderer.render(report), end="")
    else:
        print("\n".join(render(m, label, theses, nav.ticker)))
        print()
        print("Method")
        if args.demo:
            print("Demo: every figure here is synthetic - made-up trades, prices and benchmark, "
                  "built to show how the Mirror reads. None is a real price or anyone's account.")
        print("\n".join(method_lines(m, flows, nav, "ECB reference rate")))
    if args.json:
        args.json.write_text(json.dumps(summary_json(m, label, args.demo), indent=2) + "\n",
                             encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("report", help="the Mirror tables")
    r.add_argument("--nav", type=Path, required=True)
    r.add_argument("--fx", type=Path, default=None)
    r.add_argument("--prices", type=Path, required=True)
    r.add_argument("--data-dir", type=Path, default=Path("data/t212"))
    r.add_argument("--ownership", type=Path, default=Path("me/ownership.md"))
    r.add_argument("--cutoff", type=date.fromisoformat, default=None,
                   help="the date your own transactions start, for an account with no "
                        "ownership.md (one that is yours alone: its first export date)")
    r.add_argument("--transactions", type=Path, default=None,
                   help="me/transactions.csv, used instead of the Trading 212 exports")
    r.add_argument("--benchmark", default=None, help="the ticker or ISIN locked in profile.md")
    r.add_argument("--label", default=None, help="how the benchmark is named in the output")
    r.add_argument("--theses", type=Path, default=None)
    r.add_argument("--watch", type=Path, default=None)
    r.add_argument("--json", type=Path, default=None, help="also write the summary as JSON")
    r.add_argument("--demo", action="store_true", help="the shipped synthetic demo")
    r.add_argument("--draft", type=Path, default=None,
                   help="write the full RULES.md Part IV draft here, check it, print the report")
    r.add_argument("--sources", type=Path, default=None,
                   help="JSON list of fetched documents (url, document, published, retrieved)")
    r.add_argument("--proof", action="store_true", help="print the full SOURCES in the report")

    n = sub.add_parser("nav-import", help="an issuer's NAV history file as the NAV CSV")
    n.add_argument("file", type=Path)
    n.add_argument("--isin", required=True)
    n.add_argument("--ticker", required=True)
    n.add_argument("--source", required=True)
    n.add_argument("--currency", default=None)
    n.add_argument("--url", default="", help="where the issuer file came from")
    n.add_argument("--retrieved", default="", help="when it was fetched, UTC")

    args = parser.parse_args(argv)
    try:
        return cmd_report(args) if args.cmd == "report" else cmd_nav_import(args)
    except (Refused, t.Halt) as exc:
        print(f"Decision Mirror: Not available - {getattr(exc, 'message', exc)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
