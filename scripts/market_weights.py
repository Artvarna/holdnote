#!/usr/bin/env python3
"""Market weights for the Allocation table (references/portfolio-sync.md -> Mode M).

Follow RULES.md.

Quantities come from one of two places:

- ``me/holdings.csv`` when it exists: the broker-neutral file
  ``import_holdings`` writes from any app's export, a screenshot or a typed
  list. Groups and targets (``target_pct``, % of portfolio) are the user's.
- otherwise the Trading 212 exports, through ``t212_holdings`` -- the same
  engine, the same ownership cutoff, the same FIFO attribution -- so the
  quantity behind a market weight is the quantity the sync prints.

Prices and FX rates come from a JSON file the run writes from what it fetched:

    {
      "as_of": "2026-10-02",
      "prices": {
        "IE00BFY0GT14": {"price": "47.545", "currency": "EUR",
                         "date": "2026-10-02", "source": "Deutsche Boerse, Xetra close"}
      },
      "fx": {
        "USD": {"per_eur": "1.1225", "date": "2026-10-02",
                "source": "ECB euro foreign exchange reference rates"}
      }
    }

``currency`` is the price's own currency: ``EUR``, any ISO code the ``fx``
section carries an ECB rate for (``USD``, ``GBP``, ``CHF``, ``PLN`` ...), or
pence as ``GBX`` or ``GBp`` (Yahoo's spelling), divided by 100 into GBP. Case
matters only there: ``GBp`` is pence, ``GBP`` is pounds. ``per_eur`` is units of that currency per 1 EUR, as the ECB
quotes it. Nothing is fetched here and nothing is recalled: a figure that is
not in the file is ``Not available``.

What it prints is arithmetic only. ``Diff (pp)`` is ``Weight - Target`` in
percentage points, signed. There is no wording on top of it -- no "over",
"under", "rebalance" -- because a reading of the difference is the user's.

Exit codes: 0 table printed, 1 a check refused the run (message on stdout).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import import_holdings as ih  # noqa: E402
import t212_holdings as t  # noqa: E402

CENT = Decimal("0.01")
PENCE = {"GBX", "GBx", "GBp"}
DEFAULT_HOLDINGS = Path("me/holdings.csv")
# A value this many times its cost basis, or this fraction of it, is a unit
# error until shown otherwise: pence read as pounds is 100x, and no lot in
# this account is old enough to have moved 10x.
IMPLAUSIBLE = Decimal(10)


class Refused(Exception):
    """A check that stops the table: nothing is printed but the reason."""


@dataclass
class Row:
    pie: str
    isin: str
    ticker: str
    qty: Decimal | None  # None: quantity is a floor, not a figure
    target: Decimal | None  # % of portfolio, from pies.md or holdings.csv; None: none set
    cost_eur: Decimal | None = None  # FIFO cost basis in EUR, for the unit check
    kind: str = ""  # fund or stock; blank: the Trading 212 pie decides

    @property
    def is_stock(self) -> bool:
        return self.kind == "stock" if self.kind else self.pie == "Stock"


@dataclass
class Priced:
    row: Row
    close: str = ""  # as the source states it, with its currency
    value: Decimal | None = None  # EUR, rounded to the cent
    reason: str = ""  # why value is None


def _q(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _dec(raw: object, where: str) -> Decimal:
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError):
        raise Refused(f"{where}: {raw!r} is not a number")
    if not value.is_finite() or value <= 0:
        raise Refused(f"{where}: {raw!r} is not a positive number")
    return value


def _signed(value: Decimal) -> str:
    return f"{value:+.2f}" if value != 0 else "0.00"


def price_rows(rows: list[Row], as_of: date, prices: dict, fx: dict) -> list[Priced]:
    """Value each row in EUR at ``as_of``, or say why it cannot be valued."""
    out = []
    for row in rows:
        p = Priced(row)
        out.append(p)
        quote = prices.get(row.isin)
        if quote:
            p.close = f"{quote.get('currency', '?')} {quote.get('price', '?')}"
        if row.qty is None:
            p.reason = "quantity is a floor (FIFO), not a figure"
            continue
        if row.qty == 0:
            p.value = Decimal("0.00")
            continue
        if not quote:
            p.reason = "no price supplied"
            continue
        if quote.get("date") != as_of.isoformat():
            p.reason = f"priced only at {quote.get('date')}, table as-of is {as_of}"
            continue
        price = _dec(quote.get("price"), f"{row.ticker} price")
        raw = str(quote.get("currency", "")).strip()
        if raw in PENCE:
            price, ccy = price / 100, "GBP"
        else:
            ccy = raw.upper()
        if not re.fullmatch(r"[A-Z]{3}", ccy):
            p.reason = f"price currency {raw!r} is not an ISO currency code or GBX"
            continue
        if ccy == "EUR":
            value = _q(row.qty * price)
        else:
            rate = fx.get(ccy)
            if not rate:
                p.reason = f"no {ccy} rate supplied"
                continue
            if rate.get("date") != as_of.isoformat():
                p.reason = f"{ccy} rate dated {rate.get('date')}, table as-of is {as_of}"
                continue
            value = _q(row.qty * price / _dec(rate.get("per_eur"), f"{ccy} rate"))
        if row.cost_eur and (
            value > row.cost_eur * IMPLAUSIBLE or value * IMPLAUSIBLE < row.cost_eur
        ):
            p.reason = (
                f"value EUR {value} against cost basis EUR {_q(row.cost_eur)} - "
                f"check the close's unit ({raw})"
            )
            continue
        p.value = value
    return out


def allocation_table(priced: list[Priced], pie_targets: dict[str, Decimal | None],
                     label: str = "Pie") -> list[str]:
    """The Allocation table: one row per holding, one total row per pie.

    ``label`` is ``Pie`` for Trading 212 pies, ``Group`` for holdings.csv,
    whose single default group gets no total row of its own.

    Weights are taken from the printed values, so a reader can re-derive every
    one from the column beside it. A row that cannot be valued withholds every
    weight: a share of a total with a missing position is not a share of the
    portfolio (portfolio-sync.md -> M2).
    """
    complete = all(p.value is not None for p in priced)
    total = sum((p.value for p in priced), Decimal(0)) if complete else None

    def weight_cells(value: Decimal | None, target: Decimal | None) -> list[str]:
        shown = "-" if target is None else f"{target:.2f}"
        if total is None or value is None or total == 0:
            return ["Not available", shown, "Not available"]
        weight = _q(value / total * 100)
        diff = "-" if target is None else _signed(weight - _q(target))
        return [f"{weight:.2f}", shown, diff]

    lines = [
        f"| {label} | Ticker | Quantity | Close | Value (EUR) | Weight (market) | Target | Diff (pp) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    groups = list(dict.fromkeys(p.row.pie for p in priced))
    for pie in groups:
        members = [p for p in priced if p.row.pie == pie]
        for p in members:
            qty = "floor" if p.row.qty is None else t._fmt_num(p.row.qty)
            value = f"{p.value:.2f}" if p.value is not None else f"Not available - {p.reason}"
            lines.append(
                "| " + " | ".join(
                    [pie, p.row.ticker, qty, p.close or "-", value,
                     *weight_cells(p.value, p.row.target)]
                ) + " |"
            )
        if label != "Pie" and len(groups) == 1:
            continue  # one group is the whole portfolio: the total row says it
        pie_value = (
            sum((p.value for p in members), Decimal(0))
            if all(p.value is not None for p in members) else None
        )
        lines.append(
            "| " + " | ".join(
                [f"{pie} pie" if label == "Pie" else pie, "total", "", "",
                 f"{pie_value:.2f}" if pie_value is not None else "Not available",
                 *weight_cells(pie_value, pie_targets.get(pie, Decimal(0) if label == "Pie" else None))]
            ) + " |"
        )
    targets = [p.row.target for p in priced]
    if label == "Pie" or any(t_ is None for t_ in targets):
        set_total = Decimal(100) if label == "Pie" else None
    else:
        set_total = _q(sum(targets, Decimal(0)))
    t_cell = "-" if set_total is None else f"{set_total:.2f}"
    d_cell = "-" if set_total is None else _signed(Decimal(100) - set_total)
    lines.append(
        f"| Portfolio | total | | | {total:.2f} | 100.00 | {t_cell} | {d_cell} |"
        if total is not None else
        f"| Portfolio | total | | | Not available | Not available | {t_cell} | Not available |"
    )
    return lines


def csv_rows(path: Path) -> tuple[list[Row], dict[str, Decimal | None], date | None, str]:
    """Rows from holdings.csv, each group's target (None unless every member
    has one), the file's as-of date and its source line."""
    try:
        f = ih.load_holdings(path)
    except ih.Refused as exc:
        raise Refused(str(exc))
    rows = [Row(h.group, h.isin, h.ticker or h.name[:24] or h.isin, h.quantity, h.target,
                None, h.kind) for h in f.holdings]
    targets: dict[str, Decimal | None] = {}
    for g in dict.fromkeys(r.pie for r in rows):
        members = [r.target for r in rows if r.pie == g]
        targets[g] = None if any(m is None for m in members) else sum(members, Decimal(0))
    return rows, targets, f.as_of, f.source


def holdings_rows(data_dir: Path, pies_path: Path, ownership_path: Path) -> tuple[list[Row], t.Pies, date]:
    """Every pie holding with the user's quantity, and the date of the last trade."""
    ownership = t.load_ownership(ownership_path)
    ledger = t.load_transactions(data_dir)
    positions = t.aggregate(ledger.txs, ownership.cutoff)
    pies = t.load_pies(pies_path)
    states = t.classify_ownership(positions, ownership)
    attributions = t.fifo_attribution(ledger.txs, ownership.cutoff)
    t.check_no_negative_quantity(positions, states)
    t.check_mapping_covers_holdings(pies, positions)

    bases = t.converted_bases(
        t.cost_bases(positions, states, attributions), ownership.fixed_rate
    ) if ownership.fixed_rate is None or ownership.fixed_rate.base == "EUR" else None
    single = t.cost_bases(positions, states, attributions)

    def cost_eur(isin: str) -> Decimal | None:
        if bases is not None:
            return bases.get(isin)
        basis = single.get(isin)
        return basis.get("EUR") if basis and set(basis) == {"EUR"} else None

    rows = []
    for pie, holdings in pies.holdings.items():
        for h in holdings:
            pos = positions.get(h.isin)
            attribution = attributions.get(h.isin)
            if pos is None:
                qty: Decimal | None = Decimal(0)
            elif attribution is not None and attribution.is_floor and not t.known_zero(pos, attribution):
                qty = None
            else:
                qty = t.effective_quantity(pos, states[h.isin], attribution) or Decimal(0)
            rows.append(Row(pie, h.isin, h.ticker, qty, pies.target_of_portfolio(h.isin),
                            cost_eur(h.isin)))
    trades = [tx.time for tx in ledger.txs if tx.kind in ("buy", "sell")]
    if not trades:
        raise Refused(f"no trades in the exports in {data_dir}")
    last_trade = max(trades).date()
    return rows, pies, last_trade


def csv_method_lines(path: Path, snapshot: date | None, source: str, as_of: date,
                     fx: dict, any_target: bool) -> list[str]:
    rates = ", ".join(f"{ccy} {r['per_eur']}" for ccy, r in sorted(fx.items())) or "none supplied"
    when = f"positions as of {snapshot}" if snapshot else "positions undated"
    return [
        f"Allocation quantities: {path.as_posix()}, {when}"
        + (f", from {source}" if source else "") + "; import_holdings",
        f"Allocation prices: the Performance closes of {as_of}; FX ECB euro reference rates "
        f"{as_of} ({rates} per EUR)",
        "Allocation arithmetic: Value = quantity x close / rate (GBX / 100 into GBP), to the cent; "
        "Weight = Value / portfolio total x 100"
        + ("; Diff = Weight - Target, pp; Target is target_pct from holdings.csv"
           if any_target else "; no targets set in holdings.csv, so no Diff"),
    ]


def method_lines(rows: list[Row], last_trade: date, as_of: date, fx: dict, data_dir: Path) -> list[str]:
    rates = ", ".join(
        f"{ccy} {r['per_eur']}" for ccy, r in sorted(fx.items())
    ) or "none supplied"
    return [
        f"Allocation quantities: {data_dir.as_posix()} exports, last trade {last_trade}; "
        "t212_holdings, FIFO, ownership cutoff per ownership.md",
        f"Allocation prices: the Performance closes of {as_of}; FX ECB euro reference rates "
        f"{as_of} ({rates} per EUR)",
        "Allocation arithmetic: Value = quantity x close / rate (GBX / 100 into GBP), to the cent; "
        "Weight = Value / portfolio total x 100; Diff = Weight - Target, pp; Target from pies.md; "
        "a value over 10x or under 1/10 of its cost basis is withheld as a likely unit error",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prices", type=Path, required=True,
                        help="JSON of closes and FX rates, as in this module's docstring")
    parser.add_argument("--data-dir", type=Path, default=Path("data/t212"))
    parser.add_argument("--pies", type=Path, default=Path("me/pies.md"))
    parser.add_argument("--ownership", type=Path, default=Path("me/ownership.md"))
    parser.add_argument("--holdings", type=Path, default=DEFAULT_HOLDINGS,
                        help="broker-neutral holdings file; used instead of the Trading 212 "
                             "exports whenever it exists")
    args = parser.parse_args(argv)

    try:
        spec = json.loads(args.prices.read_text(encoding="utf-8"))
        try:
            as_of = date.fromisoformat(spec["as_of"])
        except (KeyError, TypeError, ValueError):
            raise Refused(f"{args.prices}: 'as_of' must be a YYYY-MM-DD date")
        if args.holdings.exists():
            rows, targets, snapshot, source = csv_rows(args.holdings)
            priced = price_rows(rows, as_of, spec.get("prices", {}), spec.get("fx", {}))
            print(f"Allocation (market weights, EUR, as of {as_of})")
            print("\n".join(allocation_table(priced, targets, label="Group")))
            print()
            print("\n".join(csv_method_lines(args.holdings, snapshot, source, as_of,
                                             spec.get("fx", {}),
                                             any(r.target is not None for r in rows))))
            return 0
        rows, pies, last_trade = holdings_rows(args.data_dir, args.pies, args.ownership)
        if as_of < last_trade:
            raise Refused(
                f"as-of {as_of} precedes the last trade in the exports ({last_trade}); "
                "quantities after that trade would be priced at a close from before they were held"
            )
        priced = price_rows(rows, as_of, spec.get("prices", {}), spec.get("fx", {}))
    except (Refused, t.Halt) as exc:
        print(f"Allocation: Not available - {exc}")
        return 1

    print(f"Allocation (market weights, EUR, as of {as_of})")
    print("\n".join(allocation_table(priced, pies.shares)))
    print()
    print("\n".join(method_lines(rows, last_trade, as_of, spec.get("fx", {}), args.data_dir)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
