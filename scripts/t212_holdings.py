#!/usr/bin/env python3
"""Derive current holdings from Trading 212 CSV exports.

Follow RULES.md.

Reads every ``*.csv`` in a data directory (default ``data/t212``), deduplicates
transactions across overlapping exports, aggregates net quantity per ISIN, and
prints a report in the RULES.md Part IV shape.

Design notes that are not obvious from the code:

* Quantity is the only figure that can be aggregated across the whole history
  without an FX rate. Cash amounts are grouped by currency and never summed
  across currencies (RULES.md rule 3). This account's ``Total`` currency
  changes from BGN to EUR partway through the real export, so this matters.
  The one exception is a *fixed* rate declared in ``ownership.md`` (the
  BGN/EUR conversion rate, locked by law): cost weights restate BGN in EUR
  through it, and print the restated column, its arithmetic and its source.
* Dividend rows carry a ``No. of shares`` value -- the shares the dividend was
  paid on, not a share movement. They must never touch net quantity.
* Everything numeric is ``Decimal``. Floats make the "negative net quantity"
  check unreliable: a closed position that should be exactly zero comes out as
  -1e-18 and trips a halt that is really a rounding artifact.
* The account is shared. Only transactions on or after the ownership cutoff
  (``ownership.md``) count toward the user's holdings. A position that
  already existed at the cutoff is split FIFO by default -- sells consume
  the inherited lot first -- and the convention is labelled in the output,
  including a floor marker where the export cannot reach the opening.
  ``--attribute none`` claims nothing for those positions instead.

Exit codes: 0 report produced, 1 a validation halted the run. A halt is a
defined output shape, not an absence of output: it prints on stdout like any
other run, with every section but ``RESULT`` and a ``Withheld:`` line naming
what it declined to compute.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

# --------------------------------------------------------------------------
# Schema (derived from a real export -- see docs/t212-csv-schema.md)
# --------------------------------------------------------------------------

# Columns this module reads. A missing one halts the run rather than silently
# producing a zero.
REQUIRED_COLUMNS = (
    "Action",
    "Time (UTC)",
    "ISIN",
    "Ticker",
    "Name",
    "No. of shares",
    "Price / share",
    "Currency (Price / share)",
    "Exchange rate",
    "Total",
    "Currency (Total)",
)

# Required only of a file that has a row which carries one: a buy, sell or
# cash row. Trading 212 leaves a column out of an export when no row in it has
# a value there, and dividend rows have no ID, so an export whose window holds
# only dividends has no ID column at all (2026-09-28 to 2026-10-10). Those rows
# dedupe on the fallback key either way.
ID_COLUMN = "ID"

# Present in the observed export but not read, plus columns seen in older or
# other-account exports. Listed so a genuinely new column shows up as schema
# drift instead of hiding in the noise.
OPTIONAL_KNOWN_COLUMNS = (
    "Notes",
    "Result",
    "Currency (Result)",
    "Withholding tax",
    "Currency (Withholding tax)",
    "Currency conversion from amount",
    "Currency (Currency conversion from amount)",
    "Currency conversion to amount",
    "Currency (Currency conversion to amount)",
    "Currency conversion fee",
    "Currency (Currency conversion fee)",
    "Stamp duty reserve tax",
    "Currency (Stamp duty reserve tax)",
    "Transaction fee",
    "Currency (Transaction fee)",
    "Finra fee",
    "Currency (Finra fee)",
    "French transaction tax",
    "Currency (French transaction tax)",
    "Deposit fee",
    "Currency (Deposit fee)",
    "Merchant name",
    "Merchant category",
    "Time",
)

# Fee columns are summed per currency for reporting only; they never enter a
# cost basis, because the export's Total already includes them.
FEE_COLUMNS = (
    ("Currency conversion fee", "Currency (Currency conversion fee)"),
    ("Transaction fee", "Currency (Transaction fee)"),
    ("Finra fee", "Currency (Finra fee)"),
    ("Stamp duty reserve tax", "Currency (Stamp duty reserve tax)"),
    ("French transaction tax", "Currency (French transaction tax)"),
    ("Deposit fee", "Currency (Deposit fee)"),
)

# Non-instrument actions. Anything that is not a buy, sell or dividend and is
# not listed here is treated as unknown.
CASH_ACTIONS = frozenset(
    {
        "deposit",
        "withdrawal",
        "interest on cash",
        "currency conversion",
        "card debit",
        "card credit",
        "card cashback",
        "spending",
        "lending interest",
        "share lending interest",
        "result adjustment",
        "new card cost",
    }
)

WEIGHT_TOLERANCE_PP = Decimal("0.1")  # percentage points


# Ownership states a position can be in, given the cutoff.
MINE = "mine"  # opened after the cutoff: fully attributable
SPANS_CUTOFF = "spans_cutoff"  # existed at the cutoff: not attributable
PRE_CUTOFF_ONLY = "pre_cutoff_only"  # no activity at all after the cutoff

NOT_ATTRIBUTABLE = "Not available - position opened before cutoff"

# Attribution modes for positions that span the cutoff. FIFO is the
# default: excluding those positions instead leaves the measured weights
# covering a subset of the account, which distorts every other weight in
# the table. A labelled convention beats a silently partial denominator.
ATTRIBUTE_FIFO = "fifo"  # sells consume the oldest lot first: the default
ATTRIBUTE_NONE = "none"  # claim nothing for a position spanning the cutoff
ATTRIBUTION_MODES = (ATTRIBUTE_FIFO, ATTRIBUTE_NONE)

# Keys each policy file may declare. Membership means this build reads the
# key and acts on it -- not that the key is merely tolerated. A key in a file
# and absent from its set halts the run: these files are policy, and a policy
# the importer silently ignores is worse than one it never had, because the
# file reads as though the run honoured it.
OWNERSHIP_KEYS = frozenset({"CUTOFF", "FIXED RATE", "LAST UPDATED"})
PIES_KEYS = frozenset({"LAST UPDATED"})

# Declarations live in a frontmatter block at the top of the file, between
# two `---` fences, and nowhere else. Scoping them by location rather than by
# the shape of the key is what makes the unhandled-key halt trustworthy: a
# pattern narrow enough to spare prose is also narrow enough to skip a real
# key that happens not to match it, and skipping one is indistinguishable
# from there being none to skip. Inside the block the shape is greedy, so no
# key can slip past by looking unusual; outside it, nothing is policy.
POLICY_FENCE = "---"


# What a halt says when the user's files are missing or still the blank
# templates: the way forward, not only what is wrong.
SETUP_HINT = 'say "set up Holdnote" to fill it in (references/setup.md)'
PLACEHOLDER = "YYYY-MM-DD"


class Halt(Exception):
    """A validation that must stop the run. The message names the cause.

    ``Halted`` alone is not a status: several checks can stop a run and which
    one stopped it is the first thing anyone asks. The check is the function
    that raised -- taken from the calling frame, so no raise site has to
    repeat its own name and none can get it wrong. ``figure`` is the measured
    value that fired the check, or the short fact that identifies what fired
    it -- a key, a file, a locator. It is not the reason: the reason is the
    message, which PROOF prints in full. A raise site that passes no figure
    falls back to the first line of that message, which is a poor figure and
    a long one, so a check worth halting on passes its own.
    """

    def __init__(self, message: str, figure: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.check = sys._getframe(1).f_code.co_name
        self.figure = figure or message.strip().splitlines()[0].rstrip(":")

    def status(self) -> str:
        return f"HALTED - {self.check}, {self.figure}"


# --------------------------------------------------------------------------
# Parsing helpers
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Source:
    """Where a row came from, for error messages."""

    path: Path
    line: int

    def __str__(self) -> str:
        return f"{self.path.name}:{self.line}"


def _q_str(value: Decimal | None) -> str:
    """Normalized text form of a Decimal, so 1.10 and 1.1 compare equal."""
    if value is None:
        return ""
    return str(value.normalize())


@dataclass(frozen=True)
class Tx:
    action: str
    kind: str  # buy | sell | dividend | cash | unknown
    time: datetime
    isin: str
    ticker: str
    name: str
    tx_id: str
    qty: Decimal | None
    price: Decimal | None
    price_ccy: str
    fx: Decimal | None
    total: Decimal | None
    total_ccy: str
    fees: tuple[tuple[Decimal, str], ...]
    source: Source

    @property
    def signed_qty(self) -> Decimal:
        """Share movement. Zero for anything that is not a trade."""
        if self.qty is None:
            return Decimal(0)
        if self.kind == "buy":
            return self.qty
        if self.kind == "sell":
            return -self.qty
        return Decimal(0)

    @property
    def dedup_key(self) -> tuple:
        """ID when present; otherwise timestamp + ISIN + quantity + price.

        The fallback is needed because dividend rows are exported with an empty
        ID. The full timestamp is used rather than the calendar date: two
        same-day dividend rows for one ISIN would otherwise collapse into one.
        """
        if self.tx_id:
            return ("id", self.tx_id)
        return (
            "fallback",
            self.time.isoformat(),
            self.isin,
            _q_str(self.qty),
            _q_str(self.price),
        )

    @property
    def identity(self) -> tuple:
        """Fields two rows sharing a dedup key must agree on."""
        return (
            self.action,
            self.time,
            self.isin,
            _q_str(self.qty),
            _q_str(self.price),
            self.price_ccy,
            _q_str(self.total),
            self.total_ccy,
        )


def parse_decimal(raw: str | None, column: str, source: Source) -> Decimal | None:
    """Parse a numeric cell. Empty means absent, not zero."""
    if raw is None:
        return None
    text = raw.strip().replace("\u00a0", "")  # non-breaking space
    if text in ("", "-", "N/A", "n/a"):
        return None
    text = text.replace(",", "")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise Halt(f"{source}: column {column!r} is not a number: {raw!r}") from exc


def parse_time(raw: str | None, source: Source) -> datetime:
    text = (raw or "").strip()
    if not text:
        raise Halt(f"{source}: empty 'Time (UTC)'")
    try:
        stamp = datetime.fromisoformat(text)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                stamp = datetime.strptime(text, fmt)
                break
            except ValueError:
                continue
        else:
            raise Halt(f"{source}: unparseable timestamp {raw!r}")
    if stamp.tzinfo is None:
        # The column is documented as UTC; an offsetless export is still UTC.
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc)


def classify_action(action: str) -> str:
    """Map a raw Action string onto a kind.

    Handles the parenthesised dividend subtypes ("Dividend (Dividend)",
    "Dividend (Dividends paid by us corporations)") and the order-type prefixes
    ("Market buy", "Limit sell", "Stop limit buy").
    """
    base = action.strip().lower().split("(")[0].strip()
    if base.startswith("dividend"):
        return "dividend"
    if base == "buy" or base.endswith(" buy"):
        return "buy"
    if base == "sell" or base.endswith(" sell"):
        return "sell"
    if base in CASH_ACTIONS:
        return "cash"
    return "unknown"


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


@dataclass
class Ledger:
    txs: list[Tx] = field(default_factory=list)
    files: list[Path] = field(default_factory=list)
    empty_files: list[Path] = field(default_factory=list)
    rows_read: int = 0
    duplicates: list[tuple[Tx, Tx]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    schema_notes: list[str] = field(default_factory=list)


def read_csv_file(path: Path, ledger: Ledger) -> list[Tx]:
    text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        # A one-day export covering a window with no activity is a zero-byte
        # file: no header at all. That is empty, not malformed.
        ledger.empty_files.append(path)
        return []

    reader = csv.DictReader(text.splitlines())
    header = reader.fieldnames or []
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise Halt(
            f"{path.name}: export is missing required column(s) "
            f"{', '.join(missing)}. Columns found: {', '.join(header)}",
            # The names of the columns found are the reason, and there can
            # be twenty of them. The figure names the first one missing.
            figure=f"{path.name}, no {missing[0]!r}"
            + (f" (+{len(missing) - 1} more)" if len(missing) > 1 else ""),
        )
    known = set(REQUIRED_COLUMNS) | {ID_COLUMN} | set(OPTIONAL_KNOWN_COLUMNS)
    unknown = [c for c in header if c and c not in known]
    if unknown:
        ledger.schema_notes.append(
            f"{path.name}: {len(unknown)} column(s) not in the recorded schema: "
            f"{', '.join(unknown)} - check docs/t212-csv-schema.md is current"
        )

    out: list[Tx] = []
    for offset, row in enumerate(reader, start=2):  # line 1 is the header
        source = Source(path, offset)
        action = (row.get("Action") or "").strip()
        # csv.DictReader yields None for short rows and a list for overlong
        # ones; only the string cells say whether the line has any content.
        cells = [v for v in row.values() if isinstance(v, str)]
        if not action and not any(v.strip() for v in cells):
            continue  # trailing blank line
        kind = classify_action(action)
        isin = (row.get("ISIN") or "").strip().upper()
        qty = parse_decimal(row.get("No. of shares"), "No. of shares", source)

        if kind == "unknown":
            if isin and qty is not None:
                raise Halt(
                    f"{source}: unrecognised Action {action!r} carries ISIN {isin} "
                    f"and {qty} shares, so it may move quantity. Add it to "
                    f"classify_action() before trusting this run."
                )
            ledger.warnings.append(
                f"{source}: Action {action!r} not recognised; ignored "
                f"(no ISIN or share count, so it cannot affect quantity)"
            )

        fees: list[tuple[Decimal, str]] = []
        for amount_col, ccy_col in FEE_COLUMNS:
            if amount_col not in row:
                continue
            amount = parse_decimal(row.get(amount_col), amount_col, source)
            if amount is None or amount == 0:
                continue
            fees.append((amount, (row.get(ccy_col) or "").strip().upper()))

        out.append(
            Tx(
                action=action,
                kind=kind,
                time=parse_time(row.get("Time (UTC)") or row.get("Time"), source),
                isin=isin,
                ticker=(row.get("Ticker") or "").strip(),
                name=(row.get("Name") or "").strip(),
                tx_id=(row.get("ID") or "").strip(),
                qty=qty,
                price=parse_decimal(row.get("Price / share"), "Price / share", source),
                price_ccy=(row.get("Currency (Price / share)") or "").strip().upper(),
                fx=parse_decimal(row.get("Exchange rate"), "Exchange rate", source),
                total=parse_decimal(row.get("Total"), "Total", source),
                total_ccy=(row.get("Currency (Total)") or "").strip().upper(),
                fees=tuple(fees),
                source=source,
            )
        )
    if ID_COLUMN not in header:
        needing = [tx for tx in out if tx.kind != "dividend"]
        if needing:
            first = needing[0]
            raise Halt(
                f"{path.name}: export is missing required column(s) ID, and "
                f"{len(needing)} row(s) need it to be told apart across "
                f"overlapping exports - first {first.source}: {first.action!r}. "
                f"Columns found: {', '.join(header)}",
                figure=f"{path.name}, no 'ID'",
            )
    return out


def _missing_data_message(data_dir: Path) -> str:
    msg = (f"no CSV exports found in {data_dir}/ - export your history from "
           f"Trading 212 (History -> Export, all columns) into it")
    # This project has been seen with a space where the path separator belongs
    # ("data t212"), which is easy to miss when nothing parses.
    sibling = data_dir.parent.parent / f"{data_dir.parent.name} {data_dir.name}"
    candidates = [
        sibling,
        Path("trading212"),
    ]
    found = [c for c in candidates if c.is_dir() and any(c.glob("*.csv"))]
    if found:
        msg += (
            " - but CSVs exist in "
            + ", ".join(f"{c}/" for c in found)
            + f". Move them into {data_dir}/ or pass --data-dir."
        )
    return msg


def load_transactions(data_dir: Path) -> Ledger:
    ledger = Ledger()
    # The tail of the path, not the whole of it: an absolute path run
    # through STATUS is most of the line and none of the fact. The full
    # path, and where else CSVs were found, stay in the message.
    where = f"{data_dir.parent.name}/{data_dir.name}"
    if not data_dir.is_dir():
        raise Halt(_missing_data_message(data_dir), figure=f"{where} not a directory")

    paths = sorted(p for p in data_dir.glob("*.csv") if p.is_file())
    if not paths:
        raise Halt(_missing_data_message(data_dir), figure=f"{where} holds no CSV")

    collected: list[Tx] = []
    for path in paths:
        rows = read_csv_file(path, ledger)
        ledger.files.append(path)
        ledger.rows_read += len(rows)
        collected.extend(rows)

    ledger.txs = dedup(collected, ledger)
    return ledger


def dedup(txs: list[Tx], ledger: Ledger) -> list[Tx]:
    """Keep the first occurrence of each dedup key.

    Two rows sharing a key must agree on every significant field. If they do
    not, the key is not identifying the row, and the run halts rather than
    picking a winner (RULES.md rule 4: do not silently resolve a conflict).
    """
    seen: dict[tuple, Tx] = {}
    kept: list[Tx] = []
    for tx in sorted(txs, key=lambda t: (t.time, t.source.path.name, t.source.line)):
        key = tx.dedup_key
        first = seen.get(key)
        if first is None:
            seen[key] = tx
            kept.append(tx)
            continue
        if first.identity != tx.identity:
            label = (
                f"ID {tx.tx_id}"
                if tx.tx_id
                else (
                    f"timestamp+ISIN+quantity+price ({tx.time.isoformat()}, "
                    f"{tx.isin or 'no ISIN'})"
                )
            )
            raise Halt(
                # The separator before an Action value is " - " everywhere a
                # halt prints one, as in check_no_negative_quantity. It is
                # the boundary that says the next token is a value out of
                # the export rather than a word in the sentence.
                f"two different transactions share the same dedup key - {label}.\n"
                f"  {first.source} - {first.action} {_q_str(first.qty)} @ "
                f"{_q_str(first.price)} {first.price_ccy}, total "
                f"{_q_str(first.total)} {first.total_ccy}\n"
                f"  {tx.source} - {tx.action} {_q_str(tx.qty)} @ "
                f"{_q_str(tx.price)} {tx.price_ccy}, total "
                f"{_q_str(tx.total)} {tx.total_ccy}\n"
                f"  Resolve by hand: one of these rows is not what it claims.",
                figure=label,
            )
        ledger.duplicates.append((first, tx))
    return kept


# --------------------------------------------------------------------------
# Aggregation
# --------------------------------------------------------------------------


@dataclass
class Position:
    """One instrument. Every field except the ``pre_*`` ones counts only rows
    on or after the ownership cutoff -- that is, the user's own activity."""

    isin: str
    tickers: set[str] = field(default_factory=set)
    names: set[str] = field(default_factory=set)
    net_qty: Decimal = Decimal(0)
    bought_qty: Decimal = Decimal(0)
    sold_qty: Decimal = Decimal(0)
    buy_cost: dict[str, Decimal] = field(default_factory=lambda: defaultdict(Decimal))
    sell_proceeds: dict[str, Decimal] = field(
        default_factory=lambda: defaultdict(Decimal)
    )
    dividends: dict[str, Decimal] = field(default_factory=lambda: defaultdict(Decimal))
    fees: dict[str, Decimal] = field(default_factory=lambda: defaultdict(Decimal))
    trades: int = 0
    first_trade: datetime | None = None
    first_trade_kind: str | None = None
    last_trade: Tx | None = None
    negative_at: Tx | None = None  # first row that drove net quantity below zero
    # Surviving lots bought on or after the cutoff: [qty, unit cost, currency],
    # consumed FIFO by sells on or after the cutoff.
    lots: list[list] = field(default_factory=list)

    # Rows before the cutoff: the account holder's, kept only as evidence of
    # what the position looked like when it became partly the user's.
    pre_net_qty: Decimal = Decimal(0)
    pre_rows: int = 0
    pre_first: datetime | None = None
    pre_last: datetime | None = None

    @property
    def ticker(self) -> str:
        return "/".join(sorted(self.tickers)) if self.tickers else "?"

    @property
    def name(self) -> str:
        return sorted(self.names, key=len)[-1] if self.names else "?"

    @property
    def is_open(self) -> bool:
        return self.net_qty > 0

    def cost_basis(self) -> dict[str, Decimal] | None:
        """Cost of the quantity still held, per currency, FIFO.

        Built from rows on or after the cutoff only: each surviving lot's
        remaining quantity x its unit cost, where unit cost is the buy row's
        Total / its quantity (portfolio-sync.md Step 3). Grouped by the Total
        currency and never summed across currencies. None when a surviving
        lot has no Total to cost it from.

        There is deliberately no market or last-transacted valuation here.
        A last-transacted price dates every position differently, which is
        why portfolio-sync.md Step 4 removed it as a weighting basis.
        """
        return _lots_cost(self.lots)


def _unit_cost(tx: "Tx") -> Decimal | None:
    """Cost per share of one buy row, from its own Total."""
    if tx.total is None or not tx.qty:
        return None
    return abs(tx.total) / tx.qty


def _lots_cost(lots: list[list]) -> dict[str, Decimal] | None:
    """Sum surviving lots [qty, unit cost, currency] by currency."""
    cost: dict[str, Decimal] = defaultdict(Decimal)
    for qty, unit, ccy in lots:
        if qty <= 0:
            continue
        if unit is None:
            return None
        cost[ccy] += qty * unit
    return dict(cost)


def aggregate(txs: list[Tx], cutoff: date) -> dict[str, Position]:
    """Aggregate per ISIN, splitting each instrument at the ownership cutoff.

    A transaction counts toward the user's holdings when its UTC date is on or
    after ``cutoff``. Earlier rows only populate the ``pre_*`` fields.
    """
    positions: dict[str, Position] = {}
    for tx in sorted(txs, key=lambda t: (t.time, t.source.line)):
        if tx.kind not in ("buy", "sell", "dividend"):
            continue
        if not tx.isin:
            continue
        pos = positions.setdefault(tx.isin, Position(isin=tx.isin))
        if tx.ticker:
            pos.tickers.add(tx.ticker)
        if tx.name:
            pos.names.add(tx.name)

        if tx.time.date() < cutoff:
            pos.pre_rows += 1
            pos.pre_net_qty += tx.signed_qty
            if pos.pre_first is None:
                pos.pre_first = tx.time
            pos.pre_last = tx.time
            continue

        for amount, ccy in tx.fees:
            pos.fees[ccy] += amount

        if tx.kind == "dividend":
            # 'No. of shares' here is the holding the dividend was paid on.
            if tx.total is not None:
                pos.dividends[tx.total_ccy] += tx.total
            continue

        pos.trades += 1
        pos.net_qty += tx.signed_qty
        if pos.first_trade is None:
            pos.first_trade = tx.time
            pos.first_trade_kind = tx.kind
        pos.last_trade = tx
        if tx.kind == "buy":
            pos.bought_qty += tx.qty or Decimal(0)
            if tx.total is not None:
                pos.buy_cost[tx.total_ccy] += tx.total
            if tx.qty:
                pos.lots.append([tx.qty, _unit_cost(tx), tx.total_ccy])
        else:
            pos.sold_qty += tx.qty or Decimal(0)
            if tx.total is not None:
                pos.sell_proceeds[tx.total_ccy] += tx.total
            remaining = tx.qty or Decimal(0)
            while remaining > 0 and pos.lots:
                taken = min(pos.lots[0][0], remaining)
                pos.lots[0][0] -= taken
                remaining -= taken
                if pos.lots[0][0] == 0:
                    pos.lots.pop(0)
        if pos.net_qty < 0 and pos.negative_at is None:
            pos.negative_at = tx
    return positions


# --------------------------------------------------------------------------
# pies.md
# --------------------------------------------------------------------------


@dataclass
class PieHolding:
    isin: str
    ticker: str
    name: str
    target_in_pie: Decimal


@dataclass
class Pies:
    path: Path
    shares: dict[str, Decimal] = field(default_factory=dict)  # pie -> % of total
    holdings: dict[str, list[PieHolding]] = field(default_factory=dict)
    excluded: dict[str, str] = field(default_factory=dict)  # isin -> status
    updated: str = ""

    def pie_of(self, isin: str) -> str | None:
        for pie, rows in self.holdings.items():
            if any(h.isin == isin for h in rows):
                return pie
        return None

    def holding(self, isin: str) -> PieHolding | None:
        for rows in self.holdings.values():
            for h in rows:
                if h.isin == isin:
                    return h
        return None

    def target_of_portfolio(self, isin: str) -> Decimal | None:
        pie = self.pie_of(isin)
        h = self.holding(isin)
        if pie is None or h is None:
            return None
        return self.shares[pie] * h.target_in_pie / Decimal(100)


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _parse_percent(text: str, where: str) -> Decimal:
    cleaned = text.strip().rstrip("%").strip()
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise Halt(f"{where}: {text!r} is not a percentage") from exc


def read_policy_block(
    path: Path, lines: list[str], handled: frozenset[str]
) -> tuple[dict[str, tuple[str, int]], int]:
    """Parse the frontmatter declarations and say where the prose starts.

    Declarations are valid only between the two fences. Everything after
    them is prose -- a colon in a sentence, a documented example of a key, a
    fenced code sample -- and none of it is read as policy or can fire the
    unhandled-key halt.

    Inside the block the shape is deliberately greedy: anything up to the
    first colon is the key, whatever it looks like. A key this build does not
    implement halts here, and cannot escape by failing to match a pattern.
    """
    if not lines or lines[0].strip() != POLICY_FENCE:
        raise Halt(
            f"{path.name}: no policy block. The file must open with a "
            f"{POLICY_FENCE!r} fence, hold one 'Key: value' per line, and "
            f"close with a second {POLICY_FENCE!r}. Declarations anywhere "
            f"else in the file are not read.",
            figure=path.name,
        )

    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == POLICY_FENCE:
            end = index
            break
    if end is None:
        raise Halt(
            f"{path.name}: policy block opens on line 1 but is never closed; "
            f"expected a second {POLICY_FENCE!r} fence.",
            figure=f"{path.name}:1",
        )

    declarations: dict[str, tuple[str, int]] = {}
    for offset in range(1, end):
        lineno = offset + 1
        line = lines[offset].strip()
        if not line:
            continue
        if ":" not in line:
            raise Halt(
                f"{path.name}:{lineno}: {line!r} is not a 'Key: value' "
                f"declaration, and the policy block holds nothing else.",
                figure=f"{path.name}:{lineno}",
            )
        raw_key, value = line.split(":", 1)
        key = " ".join(raw_key.split()).upper()
        if key not in handled:
            raise Halt(
                f"{path.name} declares {raw_key.strip()}: {value.strip()}; "
                f"this build does not implement it. Remove the line or "
                f"implement the policy. (line {lineno})",
                figure=key,
            )
        declarations[key] = (value.strip(), lineno)

    return declarations, end + 1


def load_pies(path: Path) -> Pies:
    if not path.is_file():
        raise Halt(f"mapping file not found: {path} - {SETUP_HINT}", figure=path.name)
    pies = Pies(path=path)
    section: str | None = None
    pie_name: str | None = None

    lines = path.read_text(encoding="utf-8").splitlines()
    declarations, body_start = read_policy_block(path, lines, PIES_KEYS)
    pies.updated = declarations.get("LAST UPDATED", ("", 0))[0]

    for lineno, raw in enumerate(lines[body_start:], body_start + 1):
        line = raw.strip()
        where = f"{path.name}:{lineno}"

        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            low = heading.lower()
            if low.startswith("pie shares"):
                section, pie_name = "shares", None
            elif low.startswith("pie:"):
                section = "holdings"
                pie_name = heading.split(":", 1)[1].strip()
                pies.holdings.setdefault(pie_name, [])
            elif low.startswith("not in a pie"):
                section, pie_name = "excluded", None
            else:
                section, pie_name = None, None
            continue
        if not line.startswith("|") or section is None:
            continue

        cells = _split_row(line)
        if not cells or not cells[0]:
            continue
        if cells[0].lower() in ("pie", "isin") or set(cells[0]) <= {"-", ":", " "}:
            continue  # header or separator row

        if section == "shares":
            if len(cells) < 2:
                raise Halt(f"{where}: pie share row needs 2 columns")
            pies.shares[cells[0]] = _parse_percent(cells[1], where)
        elif section == "holdings" and pie_name:
            if len(cells) < 4:
                raise Halt(f"{where}: holding row needs 4 columns")
            pies.holdings[pie_name].append(
                PieHolding(
                    isin=cells[0].upper(),
                    ticker=cells[1],
                    name=cells[2],
                    target_in_pie=_parse_percent(cells[3], where),
                )
            )
        elif section == "excluded":
            pies.excluded[cells[0].upper()] = cells[-1] if len(cells) > 1 else ""

    if not pies.shares:
        raise Halt(f"{path.name}: no '## Pie shares' table found")
    unknown = set(pies.holdings) - set(pies.shares)
    if unknown:
        raise Halt(
            f"{path.name}: pie(s) {', '.join(sorted(unknown))} have holdings but "
            f"no share of portfolio in the 'Pie shares' table"
        )
    missing = set(pies.shares) - set(pies.holdings)
    if missing:
        raise Halt(
            f"{path.name}: pie(s) {', '.join(sorted(missing))} have a share of "
            f"portfolio but no holdings table"
        )
    seen: dict[str, str] = {}
    for pie, rows in pies.holdings.items():
        for h in rows:
            if h.isin in seen:
                raise Halt(
                    f"{path.name}: {h.isin} appears in both {seen[h.isin]} and {pie}"
                )
            seen[h.isin] = pie
    return pies


# --------------------------------------------------------------------------
# ownership.md
# --------------------------------------------------------------------------


# `1 EUR = 1.95583 BGN (source)`. The source is part of the grammar, not a
# courtesy: a rate with no source is a remembered number, which RULES.md
# rule 3 forbids, and the parser refuses it rather than trusting it.
_FIXED_RATE = re.compile(
    r"^1\s+([A-Z]{3})\s*=\s*(\d+(?:\.\d+)?)\s+([A-Z]{3})\s*\((.+)\)\s*$"
)


@dataclass(frozen=True)
class FixedRate:
    """A legally fixed conversion, declared in ownership.md, never fetched.

    ``1 base = rate quote``. Only an irrevocably fixed rate belongs here --
    the BGN was locked to the EUR at 1.95583 by Council Regulation (EU)
    2025/1409. A floating rate is an observation with a date, and this
    module fetches none (DECISIONS.md, "Cost weights across BGN and EUR").
    """

    base: str
    quote: str
    rate: Decimal
    source: str

    def to_base(self, ccy: str, amount: Decimal) -> Decimal | None:
        """``amount`` in ``ccy`` restated in the base; None if not covered."""
        if ccy == self.base:
            return amount
        if ccy == self.quote:
            return amount / self.rate
        return None

    def pair(self) -> str:
        return f"1 {self.base} = {_fmt_num(self.rate)} {self.quote}"

    def describe(self) -> str:
        return f"{self.pair()} ({self.source})"


def parse_fixed_rate(text: str, where: str) -> FixedRate:
    match = _FIXED_RATE.match(text.strip())
    if not match:
        raise Halt(
            f"{where}: fixed rate {text!r} is not '1 EUR = 1.95583 BGN "
            f"(source)'. The source is required: a rate without one is a "
            f"remembered number, not a declaration.",
            figure=where,
        )
    base, rate_text, quote, source = match.groups()
    rate = Decimal(rate_text)
    if base == quote or rate <= 0:
        raise Halt(
            f"{where}: fixed rate {text!r} converts {base} to {quote} at "
            f"{rate_text}; it must join two different currencies at a "
            f"positive rate.",
            figure=where,
        )
    return FixedRate(base=base, quote=quote, rate=rate, source=source.strip())


@dataclass
class Ownership:
    path: Path
    cutoff: date
    declared: dict[str, str] = field(default_factory=dict)  # isin -> evidence
    cutoff_source: str = ""
    updated: str = ""
    fixed_rate: FixedRate | None = None

    def describe(self) -> str:
        return f"{self.cutoff.isoformat()} ({self.cutoff_source})"


def load_ownership(
    path: Path, cutoff_override: date | None = None
) -> Ownership:
    """Read the cutoff date and the declared pre-cutoff ISINs.

    The cutoff is never hardcoded into a run: it comes from this file, or from
    an explicit ``--cutoff``. With neither, the run halts rather than assume a
    date that decides which transactions are the user's.
    """
    if not path.is_file():
        if cutoff_override is None:
            raise Halt(
                f"ownership file not found: {path}\n"
                f"  It records the ownership cutoff -- the date from which "
                f"transactions are yours rather than the account holder's.\n"
                f"  {SETUP_HINT[0].upper()}{SETUP_HINT[1:]}, "
                f"or pass --cutoff YYYY-MM-DD.",
                # The name, not the path: an absolute path run through
                # STATUS is most of the line and none of the fact.
                figure=path.name,
            )
        return Ownership(
            path=path,
            cutoff=cutoff_override,
            cutoff_source="--cutoff, no ownership file present",
        )

    declared: dict[str, str] = {}
    section: str | None = None

    lines = path.read_text(encoding="utf-8").splitlines()
    declarations, body_start = read_policy_block(path, lines, OWNERSHIP_KEYS)
    updated = declarations.get("LAST UPDATED", ("", 0))[0]

    if "CUTOFF" not in declarations:
        raise Halt(
            f"{path.name}: no 'Cutoff: YYYY-MM-DD' in the policy block. It "
            f"decides which transactions are yours rather than the account "
            f"holder's, so it is not defaulted.",
            # Not the filename alone: the file-not-found halt above is also
            # raised from load_ownership, and two different failures with
            # one STATUS line is the thing STATUS exists to prevent.
            figure=f"{path.name}, no CUTOFF",
        )
    cutoff_text, cutoff_line = declarations["CUTOFF"]
    blank = cutoff_text.strip().upper() == PLACEHOLDER
    if blank and cutoff_override is not None:
        cutoff_text = cutoff_override.isoformat()
    elif blank:
        raise Halt(
            f"{path.name}:{cutoff_line}: still the blank template - the cutoff "
            f"is the date your own transactions start; {SETUP_HINT}, or pass "
            f"--cutoff YYYY-MM-DD",
            figure=f"{path.name}, not set up",
        )
    try:
        cutoff = date.fromisoformat(cutoff_text)
    except ValueError as exc:
        raise Halt(
            f"{path.name}:{cutoff_line}: cutoff {cutoff_text!r} is not an "
            f"ISO date (YYYY-MM-DD)"
        ) from exc

    fixed_rate = None
    if "FIXED RATE" in declarations:
        rate_text, rate_line = declarations["FIXED RATE"]
        fixed_rate = parse_fixed_rate(rate_text, f"{path.name}:{rate_line}")

    for lineno, raw in enumerate(lines[body_start:], body_start + 1):
        line = raw.strip()
        if line.startswith("#"):
            heading = line.lstrip("#").strip().lower()
            section = "declared" if heading.startswith("pre-cutoff isin") else None
            continue

        if section != "declared" or not line.startswith("|"):
            continue
        cells = _split_row(line)
        if not cells or not cells[0] or cells[0].lower() == "isin":
            continue
        if set(cells[0]) <= {"-", ":", " "}:
            continue
        declared[cells[0].upper()] = cells[-1] if len(cells) > 1 else ""

    if blank:
        return Ownership(
            path=path,
            cutoff=cutoff,
            declared=declared,
            cutoff_source=f"--cutoff; {path.name} still the blank template",
            updated=updated,
            fixed_rate=fixed_rate,
        )
    if cutoff_override is not None and cutoff_override != cutoff:
        return Ownership(
            path=path,
            cutoff=cutoff_override,
            declared=declared,
            cutoff_source=f"--cutoff, overriding {cutoff.isoformat()} in {path.name}",
            updated=updated,
            fixed_rate=fixed_rate,
        )
    return Ownership(
        path=path,
        cutoff=cutoff,
        declared=declared,
        cutoff_source=path.name,
        updated=updated,
        fixed_rate=fixed_rate,
    )


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def check_no_negative_quantity(
    positions: dict[str, Position], states: dict[str, str]
) -> None:
    """Halt on a negative net quantity that the cutoff cannot explain.

    A position that existed at the cutoff goes negative for a legitimate
    reason -- inherited shares were sold -- and is reported, not halted. A
    position opened after the cutoff going negative is still missing data.
    """
    offenders = [
        p
        for isin, p in positions.items()
        if p.net_qty < 0 and states[isin] == MINE
    ]
    if not offenders:
        return
    lines = [
        "negative net quantity - more shares sold than the exports account for.",
        "These positions opened after the ownership cutoff, so inherited shares",
        "do not explain it. Rows are missing from the exports.",
        "",
    ]
    for pos in sorted(offenders, key=lambda p: p.net_qty):
        lines.append(
            f"  {pos.isin}  {pos.ticker:<6} net {pos.net_qty:+.10f}  "
            f"(bought {pos.bought_qty:.10f}, sold {pos.sold_qty:.10f})"
        )
        if pos.negative_at is not None:
            tx = pos.negative_at
            lines.append(
                f"      first went negative at {tx.source} - "
                f"{tx.action} {_q_str(tx.qty)} on {tx.time.date()}"
            )
    lines.append("")
    lines.append("Re-export the full account history and re-run.")
    worst = min(offenders, key=lambda p: p.net_qty)
    raise Halt(
        "\n".join(lines),
        figure=(
            f"{worst.isin} net {_fmt_num(worst.net_qty, sign=True)} sh "
            f"(bought {_fmt_num(worst.bought_qty)}, "
            f"sold {_fmt_num(worst.sold_qty)})"
        ),
    )


def check_mapping_covers_holdings(pies: Pies, positions: dict[str, Position]) -> None:
    """Halt if an ISIN is still held but has no pie and no exclusion."""
    unmapped = [
        p
        for p in positions.values()
        if p.is_open and pies.pie_of(p.isin) is None and p.isin not in pies.excluded
    ]
    if unmapped:
        lines = [f"held ISIN(s) missing from {pies.path.name}:"]
        for pos in sorted(unmapped, key=lambda p: p.isin):
            lines.append(
                f"  {pos.isin}  {pos.ticker:<6} {pos.name}  net {pos.net_qty:.10f}"
            )
        lines.append("Add each to a pie table, or to 'Not in a pie' with a status.")
        raise Halt(
            "\n".join(lines),
            figure=(
                f"{len(unmapped)} held ISIN(s) not in {pies.path.name}: "
                + ", ".join(sorted(p.isin for p in unmapped))
            ),
        )


def classify_ownership(
    positions: dict[str, Position], ownership: Ownership
) -> dict[str, str]:
    """Label each ISIN ``MINE``, ``SPANS_CUTOFF`` or ``PRE_CUTOFF_ONLY``.

    A position is taken to have existed at the cutoff when any of these holds:

    * it has pre-cutoff buys still outstanding (``pre_net_qty > 0``);
    * its first row on or after the cutoff is a sell -- shares were there to
      sell, even when the export window is too short to show them arriving;
    * ``ownership.md`` declares it pre-cutoff. The declaration is additive and
      never overridden by the arithmetic: it carries what the user knows about
      the account that the CSV cannot express.

    Only ``MINE`` positions are attributable, so only they carry a weight.
    """
    states: dict[str, str] = {}
    for isin, pos in positions.items():
        if pos.trades == 0 and not pos.dividends:
            states[isin] = PRE_CUTOFF_ONLY
        elif pos.trades == 0:
            # Dividends but no trades: shares were held across the cutoff and
            # never traded since, so nothing here is attributable.
            states[isin] = SPANS_CUTOFF
        elif (
            pos.pre_net_qty > 0
            or pos.first_trade_kind == "sell"
            or isin in ownership.declared
        ):
            states[isin] = SPANS_CUTOFF
        else:
            states[isin] = MINE
    return states


@dataclass
class Attribution:
    """FIFO split of one instrument between the account holder and the user.

    Lots are consumed oldest first, so a sell after the cutoff eats the
    inherited shares before it touches anything the user bought.
    """

    isin: str
    inherited_at_cutoff: Decimal = Decimal(0)  # visible pre-cutoff net quantity
    mine_qty: Decimal = Decimal(0)  # remaining lots bought on/after the cutoff
    holder_qty: Decimal = Decimal(0)  # remaining pre-cutoff lots
    unbacked_sold: Decimal = Decimal(0)  # sold with no lot in the export
    mine_proceeds: dict[str, Decimal] = field(
        default_factory=lambda: defaultdict(Decimal)
    )
    holder_proceeds: dict[str, Decimal] = field(
        default_factory=lambda: defaultdict(Decimal)
    )
    # Surviving 'mine' lots: [qty, unit cost, currency].
    mine_lots: list[list] = field(default_factory=list)

    def cost_basis(self) -> dict[str, Decimal] | None:
        """Cost of the attributed quantity, per currency (see Position).

        On a floor this is a floor too: a larger inherited lot would have
        absorbed more of the sells, leaving more of the user's lots alive.
        """
        return _lots_cost(self.mine_lots)

    @property
    def is_floor(self) -> bool:
        """True when shares were sold that no visible lot backs.

        The export window then opens after the position did, so the inherited
        lot is understated. Understating it makes more sells fall against the
        user's own lots, so ``mine_qty`` is a lower bound, not a figure.
        """
        return self.unbacked_sold > 0

    def describe_qty(self) -> str:
        if self.is_floor:
            return f">= {self.mine_qty:.10f} (FIFO, floor)"
        return f"{self.mine_qty:.10f} (FIFO)"


def fifo_attribution(txs: list[Tx], cutoff: date) -> dict[str, Attribution]:
    """Walk every instrument's trades in time order, consuming lots FIFO.

    Sells are allocated against the oldest surviving lot first, and each
    sell row's Total is split between owners in proportion to the quantity
    taken from each -- exact within a row, since one row has one price.
    """
    by_isin: dict[str, list[Tx]] = defaultdict(list)
    for tx in txs:
        if tx.kind in ("buy", "sell") and tx.isin:
            by_isin[tx.isin].append(tx)

    out: dict[str, Attribution] = {}
    for isin, rows in by_isin.items():
        attribution = Attribution(isin=isin)
        lots: list[list] = []  # [remaining qty, owner, unit cost, currency]
        for tx in sorted(rows, key=lambda t: (t.time, t.source.line)):
            qty = tx.qty or Decimal(0)
            owner = "mine" if tx.time.date() >= cutoff else "holder"
            if tx.kind == "buy":
                if tx.time.date() < cutoff:
                    attribution.inherited_at_cutoff += qty
                if qty:
                    lots.append([qty, owner, _unit_cost(tx), tx.total_ccy])
                continue

            # Sell: consume oldest lots first, splitting the row's Total.
            remaining = qty
            total = abs(tx.total) if tx.total is not None else Decimal(0)
            while remaining > 0 and lots:
                lot = lots[0]
                taken = min(lot[0], remaining)
                if qty > 0 and total:
                    share = total * taken / qty
                    if lot[1] == "mine":
                        attribution.mine_proceeds[tx.total_ccy] += share
                    else:
                        attribution.holder_proceeds[tx.total_ccy] += share
                lot[0] -= taken
                remaining -= taken
                if lot[0] == 0:
                    lots.pop(0)
            if remaining > 0:
                # Sold shares that no lot in the export accounts for: they were
                # acquired before the window opened, so they are the holder's.
                attribution.unbacked_sold += remaining
                if qty > 0 and total:
                    attribution.holder_proceeds[tx.total_ccy] += (
                        total * remaining / qty
                    )
                if tx.time.date() < cutoff:
                    attribution.inherited_at_cutoff -= remaining

        for qty_left, owner, unit, ccy in lots:
            if owner == "mine":
                attribution.mine_qty += qty_left
                attribution.mine_lots.append([qty_left, unit, ccy])
            else:
                attribution.holder_qty += qty_left
        out[isin] = attribution
    return out


def effective_quantity(
    pos: Position,
    state: str,
    attribution: Attribution | None,
) -> Decimal | None:
    """The quantity to weight for this position, or None to exclude it."""
    if state == PRE_CUTOFF_ONLY:
        return None
    if state == SPANS_CUTOFF:
        if attribution is None or attribution.mine_qty <= 0:
            return None
        return attribution.mine_qty
    return pos.net_qty if pos.net_qty > 0 else None


def known_zero(pos: Position, attribution: Attribution | None) -> bool:
    """True when FIFO settles a cutoff-spanning position at exactly nothing.

    Such a position is not a gap: its owner split is known, and the answer
    is zero shares of it are the user's. That holds when the attribution is
    exact, or when it is a floor over a position with no post-cutoff buys,
    since the user's shares can only come from those.
    """
    return (
        attribution is not None
        and attribution.mine_qty == 0
        and (not attribution.is_floor or pos.bought_qty == 0)
    )


def positions_in(
    positions: dict[str, Position], states: dict[str, str], state: str
) -> list[Position]:
    return sorted(
        (p for isin, p in positions.items() if states[isin] == state),
        key=lambda p: p.isin,
    )


def reconcile_ownership(
    positions: dict[str, Position], states: dict[str, str], ownership: Ownership
) -> list[str]:
    """Notes where the export and ownership.md disagree about a position.

    Neither direction is an error: the file may be ahead of the export window,
    or the export may have revealed something the file has not recorded yet.
    """
    notes: list[str] = []
    detected = {
        isin
        for isin, pos in positions.items()
        if states[isin] == SPANS_CUTOFF and isin not in ownership.declared
    }
    for isin in sorted(detected):
        pos = positions[isin]
        reason = (
            f"pre-cutoff buys outstanding ({pos.pre_net_qty:+.10f})"
            if pos.pre_net_qty > 0
            else (
                "first row on or after the cutoff is a sell on "
                f"{pos.first_trade.date() if pos.first_trade else '?'}"
            )
        )
        notes.append(
            f"{isin} {pos.ticker} looks pre-cutoff ({reason}) but is not listed "
            f"in {ownership.path.name} - add it, or widen the export to prove "
            f"otherwise"
        )
    for isin in sorted(ownership.declared):
        pos = positions.get(isin)
        if pos is None:
            notes.append(
                f"{isin} is listed in {ownership.path.name} but appears in no "
                f"export - nothing to exclude"
            )
        elif pos.pre_rows == 0 and pos.first_trade_kind == "buy":
            notes.append(
                f"{isin} {pos.ticker} is listed in {ownership.path.name}, but "
                f"the export shows it opening with a buy on "
                f"{pos.first_trade.date() if pos.first_trade else '?'} and no "
                f"pre-cutoff rows. Held as not attributable on the strength of "
                f"the file; remove the line if it was in fact bought after the "
                f"cutoff"
            )
    return notes


def cost_bases(
    positions: dict[str, Position],
    states: dict[str, str] | None = None,
    attributions: dict[str, Attribution] | None = None,
) -> dict[str, dict[str, Decimal] | None]:
    """Cost basis per included ISIN, by currency; None where a lot is uncosted.

    Covers attributable positions only. Without ``attributions``, a position
    that existed at the cutoff holds an unknown mix of the user's shares and
    the account holder's, so costing it would be inventing the split; with
    them, its FIFO share is costed instead.
    """
    out: dict[str, dict[str, Decimal] | None] = {}
    for isin, pos in positions.items():
        state = states[isin] if states else MINE
        attribution = (attributions or {}).get(isin)
        if effective_quantity(pos, state, attribution) is None:
            continue
        if state == SPANS_CUTOFF:
            out[isin] = attribution.cost_basis()
        else:
            out[isin] = pos.cost_basis()
    return out


def cost_currencies(bases: dict[str, dict[str, Decimal] | None]) -> list[str]:
    """Every currency the included cost bases are denominated in."""
    return sorted({ccy for basis in bases.values() if basis for ccy in basis})


def converted_bases(
    bases: dict[str, dict[str, Decimal] | None], fixed_rate: FixedRate | None
) -> dict[str, Decimal] | None:
    """Each cost basis restated in the fixed rate's base currency.

    None unless a rate is declared, every basis is costed, and every
    currency in them is one the declared rate joins. A currency it does not
    cover is still refused, whatever else converts.
    """
    if fixed_rate is None or any(basis is None for basis in bases.values()):
        return None
    out: dict[str, Decimal] = {}
    for isin, basis in bases.items():
        total = Decimal(0)
        for ccy, amount in basis.items():
            restated = fixed_rate.to_base(ccy, amount)
            if restated is None:
                return None
            total += restated
        out[isin] = total
    return out


def cost_weights(
    positions: dict[str, Position],
    states: dict[str, str] | None = None,
    attributions: dict[str, Attribution] | None = None,
    fixed_rate: FixedRate | None = None,
) -> tuple[str, dict[str, Decimal]] | None:
    """Cost-basis weights per ISIN, or None when they cannot be sourced.

    weight = position cost basis / sum of cost bases x 100
    (portfolio-sync.md Step 4). A book costed in one currency is weighted
    as it stands. A mixed book is weighted only through a fixed rate
    declared in ownership.md, restated in that rate's base currency; with
    none declared, or a currency the rate does not join, it is Not available
    rather than converted at a remembered rate (RULES.md rule 3).
    """
    bases = cost_bases(positions, states, attributions)
    if not bases or any(basis is None for basis in bases.values()):
        return None
    currencies = cost_currencies(bases)
    if len(currencies) == 1:
        ccy = currencies[0]
        values = {isin: basis.get(ccy, Decimal(0)) for isin, basis in bases.items()}
    else:
        converted = converted_bases(bases, fixed_rate)
        if converted is None:
            return None
        ccy, values = fixed_rate.base, converted
    total = sum(values.values(), Decimal(0))
    if total <= 0:
        return None
    return ccy, {isin: amount * Decimal(100) / total for isin, amount in values.items()}


def floored_isins(
    weights: dict[str, Decimal], attributions: dict[str, Attribution] | None
) -> set[str]:
    """Weighted ISINs whose quantity, and so whose cost, is a floor."""
    return {
        isin
        for isin in weights
        if attributions and isin in attributions and attributions[isin].is_floor
    }


def check_weights_sum(
    pies: Pies,
    positions: dict[str, Position],
    states: dict[str, str] | None = None,
    attributions: dict[str, Attribution] | None = None,
    fixed_rate: FixedRate | None = None,
) -> list[str]:
    """Halt unless weights sum to 100% per pie and 100% in total, within 0.1pp.

    Also asserts the computed cost weights sum to 100%. That one holds by
    construction, which is exactly why a failure is worth catching.
    """
    notes: list[str] = []
    problems: list[str] = []

    for pie, rows in sorted(pies.holdings.items()):
        total = sum((h.target_in_pie for h in rows), Decimal(0))
        if abs(total - Decimal(100)) > WEIGHT_TOLERANCE_PP:
            problems.append(
                f"  pie {pie!r}: target weights sum to {total}% "
                f"(off by {total - Decimal(100):+}pp, tolerance "
                f"{WEIGHT_TOLERANCE_PP}pp)"
            )
        else:
            notes.append(f"pie {pie!r} target weights sum to {total}%")

    share_total = sum(pies.shares.values(), Decimal(0))
    if abs(share_total - Decimal(100)) > WEIGHT_TOLERANCE_PP:
        problems.append(
            f"  pie shares sum to {share_total}% "
            f"(off by {share_total - Decimal(100):+}pp)"
        )
    else:
        notes.append(f"pie shares sum to {share_total}%")

    of_portfolio = sum(
        (
            pies.shares[pie] * h.target_in_pie / Decimal(100)
            for pie, rows in pies.holdings.items()
            for h in rows
        ),
        Decimal(0),
    )
    if abs(of_portfolio - Decimal(100)) > WEIGHT_TOLERANCE_PP:
        problems.append(
            f"  of-portfolio targets sum to {of_portfolio}% "
            f"(off by {of_portfolio - Decimal(100):+}pp)"
        )
    else:
        notes.append(f"of-portfolio targets sum to {of_portfolio:.2f}%")

    weights = cost_weights(positions, states, attributions, fixed_rate)
    if weights is not None:
        total = sum(weights[1].values(), Decimal(0))
        if abs(total - Decimal(100)) > WEIGHT_TOLERANCE_PP:
            problems.append(f"  computed cost weights sum to {total}%, not 100%")
        else:
            notes.append(
                f"cost weights sum to {total:.4f}% "
                f"across {len(weights[1])} attributable position(s)"
            )

    if problems:
        raise Halt(
            f"weights do not sum to 100% within {WEIGHT_TOLERANCE_PP}pp:\n"
            + "\n".join(problems),
            figure=f"{len(problems)} sum(s) off -{problems[0].rstrip()}",
        )
    return notes


def fx_direction_audit(txs: list[Tx]) -> dict[str, dict[str, int]]:
    """Which arithmetic reproduces Total, per row kind.

    Trade rows satisfy ``total ~= qty * price / fx``; dividend rows satisfy
    ``total ~= qty * price * fx``. The direction of 'Exchange rate' is not
    consistent across row kinds. This audit re-derives it from the data on
    every run instead of trusting the note in docs/.
    """
    audit: dict[str, dict[str, int]] = {}
    for tx in txs:
        if tx.kind not in ("buy", "sell", "dividend"):
            continue
        if None in (tx.qty, tx.price, tx.fx, tx.total) or tx.fx == 0:
            continue
        buckets = audit.setdefault(
            tx.kind, {"divide": 0, "multiply": 0, "ambiguous": 0, "neither": 0}
        )
        gross = tx.qty * tx.price
        fees = sum(
            (amount for amount, ccy in tx.fees if ccy == tx.total_ccy), Decimal(0)
        )
        # Totals are rounded to the cent, and a buy total includes the fee.
        tol = Decimal("0.01") + abs(tx.total) * Decimal("0.005") + abs(fees)
        div_ok = abs(gross / tx.fx - abs(tx.total)) <= tol
        mul_ok = abs(gross * tx.fx - abs(tx.total)) <= tol
        if div_ok and mul_ok:
            buckets["ambiguous"] += 1
        elif div_ok:
            buckets["divide"] += 1
        elif mul_ok:
            buckets["multiply"] += 1
        else:
            buckets["neither"] += 1
    return audit


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def _money(mapping: dict[str, Decimal]) -> str:
    parts = [f"{amount:.2f} {ccy}" for ccy, amount in sorted(mapping.items()) if amount]
    return ", ".join(parts) if parts else "-"


# --------------------------------------------------------------------------
# Table rendering
#
# Two RULES.md Part IV rules live here. Precision is per column rather than
# per output, with trailing zeros dropped: a quantity column at ten decimals
# does not force a percentage column to ten, and digits the source never
# supplied read as measurement. And a column that is zero or empty on every
# row is suppressed -- then named in METHOD, so a column that disappeared
# because it was empty stays distinguishable from one a module forgot.
# --------------------------------------------------------------------------

QTY_PLACES = 10  # the export quotes share quantities to ten decimals
BLANK_CELLS = ("", "-")

# CONTEXT prints the same units line whether the run completes or halts, so
# it lives here rather than in either branch, where the two could drift.
CURRENCY_UNITS = (
    "share quantities are unitless; cash is grouped by the currency the "
    "export states and never summed across currencies"
)

# A field a halt could not populate. An empty field is a statement; a missing
# one is a gap the reader has to notice on their own.
NOT_REACHED = "not reached"

# Every file this module reads is a local file with no publication date.
# Writing that out beats leaving the field blank: a later reader can tell
# "none exists" from "not recorded".
LOCAL_FILE = " - published n/a - local file"


@dataclass(frozen=True)
class Num:
    """A numeric cell, printed at the precision of the column it lands in."""

    value: Decimal
    prefix: str = ""
    suffix: str = ""
    places: int | None = None  # None: take the column's own precision
    sign: bool = False


def _decimals(value: Decimal, cap: int = QTY_PLACES) -> int:
    """Decimal places this value needs once trailing zeros are dropped."""
    return len(f"{value:.{cap}f}".rstrip("0").partition(".")[2])


def _fmt_num(value: Decimal, places: int = QTY_PLACES, sign: bool = False) -> str:
    text = f"{value:{'+' if sign else ''}.{places}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _cell(value: object, places: int) -> str:
    if not isinstance(value, Num):
        return str(value)
    digits = places if value.places is None else value.places
    return f"{value.prefix}{_fmt_num(value.value, digits, value.sign)}{value.suffix}"


def _is_blank(cell: str) -> bool:
    """True for a cell carrying no information: empty, a dash, or a zero."""
    text = cell.strip()
    if text in BLANK_CELLS:
        return True
    try:
        return Decimal(text.removesuffix("pp").removesuffix("%")) == 0
    except InvalidOperation:
        return False


def _table(headers: list[str], rows: list[list]) -> tuple[list[str], list[str]]:
    """Render one markdown table. Returns its lines and the columns dropped."""
    places = [
        max((_decimals(r[i].value) for r in rows if isinstance(r[i], Num)), default=0)
        for i in range(len(headers))
    ]
    body = [[_cell(cell, places[i]) for i, cell in enumerate(row)] for row in rows]
    keep = [
        i
        for i in range(len(headers))
        if not body or not all(_is_blank(row[i]) for row in body)
    ]
    dropped = [h for i, h in enumerate(headers) if i not in keep]
    lines = [
        "| " + " | ".join(headers[i] for i in keep) + " |",
        "|" + "---|" * len(keep),
    ]
    lines.extend("| " + " | ".join(row[i] for i in keep) + " |" for row in body)
    return lines, dropped


def _period_line(period: str, ownership: Ownership | None, pies: Pies | None) -> str:
    """The measured window, with the policy that bounds it.

    RULES.md Part IV: an ownership cutoff bounds the measured period, so it
    rides on this line as a clause rather than adding a sixth CONTEXT
    field. The date the policy files were last updated rides with it -- the
    same cutoff read from a file updated a year ago is a different fact from
    one updated last week, and both are needed to read the numbers rather
    than merely to trust them. Which files carry them is SOURCES' business.
    """
    if ownership is None:
        return f"{period}; ownership cutoff {NOT_REACHED}"
    dates = {ownership.path.name: ownership.updated}
    if pies is not None:
        dates[pies.path.name] = pies.updated
    stated = set(dates.values())
    if len(stated) == 1 and all(dates.values()):
        policy = f"policy as of {stated.pop()}"
    else:
        # The files disagree, or one states no date. Name them: a single
        # date here would claim an agreement that does not exist.
        policy = "policy as of " + ", ".join(
            f"{name} {value or '?'}" for name, value in dates.items()
        )
    return (
        f"{period}; ownership cutoff {ownership.cutoff.isoformat()}, {policy}"
    )


def _addends(values: list[Decimal], places: int = 2) -> str:
    """A sum re-added from the figures as printed, with its drift from 100%.

    The addends are rounded first and the total is their sum, so the line can
    be re-added by hand at the precision it prints (RULES.md Part IV, PROOF).
    """
    rounded = [Decimal(_fmt_num(v, places)) for v in values]
    total = sum(rounded, Decimal(0))
    return (
        " + ".join(_fmt_num(v, places) for v in rounded)
        + f" = {_fmt_num(total, places)}%, drift "
        + f"{_fmt_num(total - Decimal(100), places, sign=True)}pp "
        + f"(tol {WEIGHT_TOLERANCE_PP}pp)"
    )


def build_report(
    ledger: Ledger,
    pies: Pies,
    ownership: Ownership,
    positions: dict[str, Position],
    states: dict[str, str],
    weight_notes: list[str],
    attributions: dict[str, Attribution] | None = None,
    proof: bool = False,
) -> str:
    trades = [t for t in ledger.txs if t.kind in ("buy", "sell")]
    as_of = max((t.time for t in ledger.txs), default=None)
    mine = positions_in(positions, states, MINE)
    spanning = positions_in(positions, states, SPANS_CUTOFF)
    pre_only = positions_in(positions, states, PRE_CUTOFF_ONLY)
    open_positions = sorted(
        (p for p in mine if p.is_open),
        key=lambda p: (pies.pie_of(p.isin) or "~", p.isin),
    )
    closed = sorted((p for p in mine if not p.is_open), key=lambda p: p.isin)
    fixed_rate = ownership.fixed_rate
    weights = cost_weights(positions, states, attributions, fixed_rate)
    bases = cost_bases(positions, states, attributions)
    # Set only when the weights needed the declared rate to exist at all.
    converted = (
        converted_bases(bases, fixed_rate)
        if weights and len(cost_currencies(bases)) > 1
        else None
    )
    floors = floored_isins(weights[1], attributions) if weights else set()
    attributed = [
        p
        for p in spanning
        if attributions is not None
        and effective_quantity(p, SPANS_CUTOFF, attributions.get(p.isin))
        is not None
    ]

    # RESULT carries tables only, so the conventions and suppressed columns it
    # would otherwise trail are collected here and printed under METHOD.
    method: list[str] = []
    suppressed: list[str] = []
    out: list[str] = []

    # ---- STATUS ----------------------------------------------------------
    out.append("STATUS")
    out.append("")
    out.append("Complete.")
    out.append("")

    # ---- CONTEXT ---------------------------------------------------------
    out.append("CONTEXT")
    out.append("")
    out.append("```")
    out.append(
        "Data as of:      "
        + (
            f"{as_of.date().isoformat()} (last transaction in the exports)"
            if as_of
            else "no rows"
        )
    )
    out.append(
        "Latest period:   "
        + _period_line(
            f"{as_of.isoformat()} UTC" if as_of else "-", ownership, pies
        )
    )
    units = f"Currency/units:  {CURRENCY_UNITS}; weights on cost basis"
    if converted is not None:
        units += (
            f" ({weights[0]}, {fixed_rate.quote} restated at the fixed "
            f"{fixed_rate.pair()} declared in {ownership.path.name})"
        )
    elif weights:
        units += f" ({weights[0]})"
    out.append(units)
    not_available = [
        "market prices - the default mode fetches nothing (market weights are "
        "Mode M, opt-in)"
    ]
    settled = [
        p for p in spanning if known_zero(p, (attributions or {}).get(p.isin))
    ]
    unclaimed = [p for p in spanning if p not in attributed and p not in settled]
    if unclaimed:
        not_available.append(
            f"quantity and weight for {len(unclaimed)} position(s) that existed "
            "at the cutoff - the owner split of those shares is not in the export"
        )
    if weights is None:
        uncosted = sorted(isin for isin, basis in bases.items() if basis is None)
        currencies = cost_currencies(bases)
        if uncosted:
            reason = "no Total on a surviving lot of " + ", ".join(uncosted)
        elif len(currencies) > 1 and fixed_rate is None:
            reason = (
                f"cost bases denominated in {', '.join(currencies)}, no rate "
                f"declared in {ownership.path.name}"
            )
        elif len(currencies) > 1:
            uncovered = [
                c for c in currencies if c not in (fixed_rate.base, fixed_rate.quote)
            ]
            reason = (
                f"cost bases denominated in {', '.join(currencies)}; the "
                f"declared {fixed_rate.pair()} does not cover "
                f"{', '.join(uncovered)}"
            )
        else:
            reason = "no attributable position carries a cost basis"
        not_available.append(f"cost-basis weights - {reason}")
    out.append("Not available:   " + "; ".join(not_available))
    # An ignored row changes what the numbers include, so it is read-critical
    # and folds into the mandated field it qualifies rather than a Notes list.
    for warning in ledger.warnings:
        out.append(f"                 {warning}")
    out.append(
        f"Coverage:        {len(open_positions) + len(attributed)} open "
        f"position(s) attributable, {len(closed)} closed, {len(spanning)} "
        f"spanning the cutoff ({len(attributed)} attributed), "
        f"{len(pre_only)} pre-cutoff only, {len(trades)} trade row(s)"
    )
    out.append("```")
    out.append("")

    # ---- RESULT ----------------------------------------------------------
    out.append("RESULT")
    out.append("")

    heading = "## Open positions (mine, opened after the cutoff)"
    if attributed:
        heading = (
            "## Open positions (mine, FIFO-attributed where they span the cutoff)"
        )
    out.append(heading)
    out.append("")
    rows: list[tuple[Position, Decimal, Attribution | None]] = [
        (pos, pos.net_qty, None) for pos in open_positions
    ]
    for pos in attributed:
        rows.append((pos, attributions[pos.isin].mine_qty, attributions[pos.isin]))
    rows.sort(key=lambda r: (pies.pie_of(r[0].isin) or "~", r[0].isin))
    if not rows:
        out.append("None.")
    else:
        headers = [
            "Pie",
            "ISIN",
            "Ticker",
            "My quantity",
            "Cost basis",
            "Weight (cost)",
            "Target",
        ]
        if converted is not None:
            headers.insert(headers.index("Cost basis") + 1, f"Cost basis ({weights[0]})")
        table: list[list] = []
        for pos, qty, attribution in rows:
            pie = pies.pie_of(pos.isin) or "-"
            basis = bases.get(pos.isin)
            floor = attribution is not None and attribution.is_floor
            if basis is None:
                cost_text = "Not available"
            else:
                cost_text = ", ".join(
                    f"{amount:.2f} {ccy}" for ccy, amount in sorted(basis.items())
                ) + (" (floor)" if floor else "")
            weight = weights[1].get(pos.isin) if weights else None
            if weight is None:
                weight_cell: object = "Not available"
            elif pos.isin in floors:
                weight_cell = Num(weight, prefix=">= ", suffix="%", places=1)
            elif floors:
                weight_cell = Num(weight, prefix="<= ", suffix="%", places=1)
            else:
                weight_cell = Num(weight, suffix="%", places=1)
            target = pies.target_of_portfolio(pos.isin)
            if attribution is None:
                qty_cell: object = Num(qty)
            elif attribution.is_floor:
                qty_cell = Num(qty, prefix=">= ", suffix=" (FIFO, floor)")
            else:
                qty_cell = Num(qty, suffix=" (FIFO)")
            row = [
                pie,
                pos.isin,
                pos.ticker,
                qty_cell,
                cost_text,
                weight_cell,
                Num(target, suffix="%", places=2) if target is not None else "-",
            ]
            if converted is not None:
                restated = converted.get(pos.isin)
                row.insert(
                    5,
                    "Not available"
                    if restated is None
                    # A string, not a Num: currency amounts print at 2 dp
                    # whatever the column, and Num would drop a trailing zero.
                    else f"{restated:.2f} {weights[0]}"
                    + (" (floor)" if floor else ""),
                )
            table.append(row)
        lines, dropped = _table(headers, table)
        out.extend(lines)
        suppressed.extend(dropped)
        method.append(
            "Weight basis: cost - the remaining quantity of each surviving lot "
            "x that lot's unit cost (buy row Total / its quantity), FIFO, in "
            "the Total currency (portfolio-sync.md Step 4). Weights are shares "
            "of contributed capital, not of current value; there is no "
            "last-transacted or market valuation in this mode."
        )
        if converted is not None:
            method.append(
                f"Currency: cost bases span {', '.join(cost_currencies(bases))}; "
                f"{fixed_rate.quote} amounts are restated in {fixed_rate.base} "
                f"at the fixed {fixed_rate.describe()}, declared in "
                f"{ownership.path.name}. Weights are taken from the "
                f"Cost basis ({fixed_rate.base}) column."
            )
        if floors:
            method.append(
                "Weight bounds: a floored position's cost is a lower bound, so "
                "its weight is a lower bound (>=) and every other weight an "
                "upper bound (<=)."
            )
        excluded = [p for p in spanning if p not in attributed and p not in settled]
        if weights and excluded:
            method.append(
                f"Cost weights are shares of these {len(weights[1])} "
                f"attributable position(s) only. {len(excluded)} position(s) "
                "existed at the cutoff and carry no quantity, so every weight "
                "above is larger than its share of the whole account."
            )
        if attributed:
            method.append(
                f"{len(attributed)} position(s) marked (FIFO) span the cutoff: "
                "sells were allocated against the inherited lot before any lot "
                "bought on or after it, and the remainder is counted as mine."
                + (
                    " A (floor) marker means shares were sold that no lot in "
                    "the export backs, so the inherited lot is understated and "
                    "the quantity is a lower bound."
                    if any(attributions[p.isin].is_floor for p in attributed)
                    else ""
                )
            )
        if settled:
            method.append(
                f"{len(settled)} position(s) that existed at the cutoff resolve "
                "to zero shares of mine ("
                + ", ".join(p.ticker for p in settled)
                + "): known, not missing, and outside the weights for that "
                "reason alone."
            )
    out.append("")

    if spanning:
        out.append("## Positions that existed at the cutoff")
        out.append("")
        if attributions is None:
            out.append(
                "Inherited shares and bought shares are indistinguishable in "
                "this export, so no quantity is claimed. Excluded from the "
                "weights above. Re-run with --attribute fifo to allocate them."
            )
        else:
            out.append(
                "Split FIFO: the oldest lot is sold first. Quantities that "
                "resolve to more than zero appear in the table above as well."
            )
        out.append("")
        headers = [
            "ISIN",
            "Ticker",
            "Name",
            "My quantity",
            "Holder quantity",
            "Post-cutoff buys",
            "Post-cutoff sells",
            "Evidence",
        ]
        table = []
        for pos in spanning:
            if pos.pre_net_qty > 0:
                evidence = (
                    f"pre-cutoff net {pos.pre_net_qty:+.10f} over {pos.pre_rows} row(s) "
                    f"to {pos.pre_last.date() if pos.pre_last else '?'}"
                )
            elif pos.first_trade_kind == "sell":
                evidence = (
                    "first row on or after cutoff is a sell on "
                    f"{pos.first_trade.date() if pos.first_trade else '?'}"
                )
            else:
                evidence = f"declared in {ownership.path.name}"
            if pos.isin in ownership.declared and ownership.declared[pos.isin]:
                evidence += f"; {ownership.path.name}: {ownership.declared[pos.isin]}"
            attribution = (attributions or {}).get(pos.isin)
            if attribution is None:
                mine_cell: object = NOT_ATTRIBUTABLE
                holder_cell: object = "-"
            elif attribution.is_floor:
                mine_cell = Num(
                    attribution.mine_qty, prefix=">= ", suffix=" (FIFO, floor)"
                )
            else:
                mine_cell = Num(attribution.mine_qty, suffix=" (FIFO)")
            if attribution is not None:
                holder_cell = Num(
                    attribution.holder_qty,
                    suffix=(
                        f" (+{_fmt_num(attribution.unbacked_sold)} sold unbacked)"
                        if attribution.unbacked_sold
                        else ""
                    ),
                )
            table.append(
                [
                    pos.isin,
                    pos.ticker,
                    pos.name,
                    mine_cell,
                    holder_cell,
                    Num(pos.bought_qty),
                    Num(pos.sold_qty),
                    evidence,
                ]
            )
        lines, dropped = _table(headers, table)
        out.extend(lines)
        suppressed.extend(dropped)
        out.append("")

    # The account holder's instruments answer no question the user asked --
    # the table can run to dozens of rows -- so it is built here and printed
    # as a diagnostic in PROOF, with its count on Coverage and a METHOD line.
    pre_only_lines: list[str] = []
    if pre_only:
        method.append(
            f"{len(pre_only)} instrument(s) have no rows on or after the "
            "cutoff: the account holder's alone, outside every table above, "
            "and listed in PROOF."
        )
        headers = ["ISIN", "Ticker", "Name", "Rows before cutoff", "Last row"]
        table = [
            [
                pos.isin,
                pos.ticker,
                pos.name,
                Num(Decimal(pos.pre_rows), places=0),
                pos.pre_last.date() if pos.pre_last else "-",
            ]
            for pos in pre_only
        ]
        lines, _ = _table(headers, table)
        pre_only_lines = [
            "## Pre-cutoff only (the account holder's, not mine)",
            "",
            *lines,
            "",
        ]

    out.append("## Cash flows per instrument, by currency")
    out.append("")
    out.append(
        f"Rows on or after {ownership.cutoff.isoformat()} only. Pre-cutoff "
        "activity is the account holder's and is not totalled here."
    )
    out.append("")
    headers = [
        "ISIN",
        "Ticker",
        "Bought",
        "Sold",
        "Buy cost",
        "Sell proceeds",
        "Dividends",
        "Fees",
    ]
    table = [
        [
            pos.isin,
            pos.ticker,
            Num(pos.bought_qty),
            Num(pos.sold_qty),
            _money(pos.buy_cost),
            _money(pos.sell_proceeds),
            _money(pos.dividends),
            _money(pos.fees),
        ]
        for pos in sorted(positions.values(), key=lambda p: p.isin)
        # Only instruments with activity on or after the cutoff: a row of
        # zeros for each of the account holder's instruments is not a flow.
        if pos.bought_qty or pos.sold_qty or any(pos.dividends.values())
        or any(pos.fees.values())
    ]
    lines, dropped = _table(headers, table)
    out.extend(lines)
    suppressed.extend(dropped)
    out.append("")

    if closed:
        out.append("## Closed positions (net quantity zero)")
        out.append("")
        headers = ["ISIN", "Ticker", "Name", "Last traded", "Status in pies.md"]
        table = []
        for pos in closed:
            status = pies.excluded.get(pos.isin) or (
                f"in pie {pies.pie_of(pos.isin)}" if pies.pie_of(pos.isin) else "-"
            )
            table.append(
                [
                    pos.isin,
                    pos.ticker,
                    pos.name,
                    pos.last_trade.time.date() if pos.last_trade else "-",
                    status,
                ]
            )
        lines, dropped = _table(headers, table)
        out.extend(lines)
        suppressed.extend(dropped)
        out.append("")

    # ---- METHOD ----------------------------------------------------------
    out.append("METHOD")
    out.append("")
    policies = [
        "Attribution: "
        + (
            "FIFO - sells consume the inherited lot first"
            if attributions is not None
            else "none - positions that existed at the cutoff carry no quantity"
        ),
        "Ownership: shared account; only transactions on or after "
        f"{ownership.cutoff.isoformat()} count as mine",
        f"Cutoff: {ownership.describe()}",
    ]
    for line in policies + method:
        out.append(f"- {line}")
    audit = fx_direction_audit(ledger.txs)
    if audit:
        summary = "; ".join(
            f"{kind}: "
            + ", ".join(
                f"{count} {bucket}" for bucket, count in buckets.items() if count
            )
            for kind, buckets in sorted(audit.items())
        )
        out.append(f"- Exchange-rate direction re-derived from Total - {summary}")
        bad = [kind for kind, b in audit.items() if b["neither"]]
        if bad:
            out.append(
                f"  - **{', '.join(bad)} row(s) where neither direction reproduces "
                "Total - the schema may have changed**"
            )
    if suppressed:
        out.append(
            "- Columns suppressed (zero or empty on every row): "
            + ", ".join(dict.fromkeys(suppressed))
        )
    notes = list(ledger.schema_notes)
    notes.extend(reconcile_ownership(positions, states, ownership))
    if ledger.empty_files:
        notes.append(
            "empty export(s) skipped: "
            + ", ".join(p.name for p in ledger.empty_files)
            + " (zero-byte file, no header - a window with no activity)"
        )
    if ledger.duplicates:
        shown = ledger.duplicates[:5]
        notes.append(
            f"{len(ledger.duplicates)} duplicate row(s) dropped across overlapping "
            "exports, e.g. "
            + "; ".join(f"{dup.source} = {first.source}" for first, dup in shown)
        )
    for note in notes:
        out.append(f"- {note}")
    out.append("")

    # ---- PROOF -----------------------------------------------------------
    # Built on every run and printed only with --proof (RULES.md Part IV,
    # v9). The checks it reports have already run by now -- a failed one
    # halted before this report was reached -- so dropping the section
    # drops the working, never the verdict.
    proof_start = len(out)
    out.append("PROOF")
    out.append("")
    out.append("## Validation")
    out.append("")
    out.append(
        "- No attributable position has negative net quantity (a position that "
        "existed at the cutoff may, and is reported above instead)"
    )
    for note in weight_notes:
        out.append(f"- {note}")
    out.append("- Re-added from the figures as printed:")
    for pie, holdings in sorted(pies.holdings.items()):
        out.append(
            f"  - pie {pie!r} targets: "
            + _addends([h.target_in_pie for h in holdings])
        )
    if pies.shares:
        out.append(
            "  - pie shares: "
            + _addends([share for _, share in sorted(pies.shares.items())])
        )
    if weights:
        out.append(
            f"  - cost weights across {len(weights[1])} attributable "
            "position(s): "
            + _addends([w for _, w in sorted(weights[1].items())], places=1)
        )
    if converted is not None:
        out.append(
            f"- {fixed_rate.quote} cost restated at {fixed_rate.pair()}:"
        )
        for isin in sorted(converted):
            parts = []
            for ccy, amount in sorted(bases[isin].items()):
                if ccy == fixed_rate.quote:
                    parts.append(
                        f"{amount:.2f} {ccy} / {_fmt_num(fixed_rate.rate)} = "
                        f"{amount / fixed_rate.rate:.2f} {fixed_rate.base}"
                    )
                else:
                    parts.append(f"{amount:.2f} {ccy}")
            ticker = positions[isin].ticker
            out.append(
                f"  - {ticker}: " + " + ".join(parts)
                + f" -> {converted[isin]:.2f} {fixed_rate.base}"
            )
        # Re-added from the column as printed, so the line can be checked by
        # hand; the weights themselves are taken from the unrounded figures,
        # which cannot move a 1 dp weight by more than the rounding shown.
        printed = [Decimal(f"{v:.2f}") for _, v in sorted(converted.items())]
        total = sum(printed, Decimal(0))
        out.append(
            f"  - Cost basis ({fixed_rate.base}) column: "
            + " + ".join(f"{v:.2f}" for v in printed)
            + f" = {total:.2f} {fixed_rate.base}; each weight = its row / "
            f"{total:.2f} x 100"
        )
    out.append(f"- Every open position is mapped in {pies.path.name}")
    if pre_only_lines:
        out.append("")
        out.extend(pre_only_lines)
    if spanning:
        out.append(f"- {len(spanning)} position(s) existed at the cutoff:")
        for pos in spanning:
            attribution = (attributions or {}).get(pos.isin)
            if attribution is None:
                verdict = "reported as not attributable"
            else:
                verdict = (
                    f"FIFO mine {attribution.mine_qty:.10f}, holder "
                    f"{attribution.holder_qty:.10f}"
                    + (" (floor)" if attribution.is_floor else "")
                )
            out.append(
                f"  - {pos.isin} {pos.ticker} - post-cutoff net "
                f"{pos.net_qty:+.10f}, {verdict}"
            )
    else:
        out.append("- No position existed at the ownership cutoff")
    out.append("")
    if not proof:
        del out[proof_start:]

    # ---- SOURCES ---------------------------------------------------------
    out.append("SOURCES")
    out.append("")
    if ledger.files:
        out.append(
            "- "
            + ", ".join(p.name for p in ledger.files)
            + f" ({ledger.rows_read} rows read, {len(ledger.duplicates)} "
            f"duplicate(s) dropped, {len(ledger.txs)} kept)" + LOCAL_FILE
        )
    else:
        out.append("- no export read")
    out.append(
        f"- {pies.path.name} (updated {pies.updated or '?'})" + LOCAL_FILE
    )
    out.append(
        f"- {ownership.path.name} (cutoff {ownership.cutoff.isoformat()}, "
        f"updated {ownership.updated or '?'})" + LOCAL_FILE
    )
    if converted is not None:
        out.append(
            f"- {fixed_rate.source} - fixed {fixed_rate.pair()}, declared in "
            f"{ownership.path.name}"
        )

    return "\n".join(out)


@dataclass
class RunState:
    """What the run had established by the time it stopped.

    A halt prints every section but RESULT, and those sections read fields
    the run produces as it goes. Collecting them here is what lets a halt
    inside ``load_pies`` still print the exports it had already read, instead
    of printing nothing because the locals that held them never existed.
    """

    attribute: str = ATTRIBUTE_FIFO
    ownership: Ownership | None = None
    ledger: Ledger | None = None
    pies: Pies | None = None
    positions: dict[str, Position] | None = None
    states: dict[str, str] | None = None
    attributions: dict[str, Attribution] | None = None


def build_halt_report(
    state: RunState, halt: Halt, withheld: list[str] | None = None
) -> str:
    """The halt output shape: every section but RESULT.

    RESULT is omitted deliberately -- the run declined to reach the
    conclusion it states -- and STATUS names what did not print, so a halt is
    never confused with a run that produced nothing. METHOD prints because
    the measured value that fired the check was produced by the policies in
    it, and a halt nobody can reproduce is an assertion.
    """
    ledger = state.ledger
    out: list[str] = []

    # ---- STATUS ----------------------------------------------------------
    out.append("STATUS")
    out.append("")
    out.append(halt.status())
    out.append(
        "Withheld: "
        + "; ".join(
            (withheld or [])
            + [
                "RESULT - open positions, positions that existed at the "
                "cutoff, pre-cutoff only, cash flows per instrument, closed "
                "positions",
                "every quantity, cost, weight and share figure derived from "
                "them",
            ]
        )
        + "."
    )
    out.append("")

    # ---- CONTEXT ---------------------------------------------------------
    as_of = max((t.time for t in ledger.txs), default=None) if ledger else None
    out.append("CONTEXT")
    out.append("")
    out.append("```")
    out.append(
        "Data as of:      "
        + (
            f"{as_of.date().isoformat()} (last transaction in the exports)"
            if as_of
            else ("no rows" if ledger else NOT_REACHED)
        )
    )
    out.append(
        "Latest period:   "
        + _period_line(
            f"{as_of.isoformat()} UTC" if as_of else NOT_REACHED,
            state.ownership,
            state.pies,
        )
    )
    out.append(f"Currency/units:  {CURRENCY_UNITS}")
    out.append(
        f"Not available:   every figure RESULT would have carried - the run "
        f"halted at {halt.check}"
    )
    if state.positions is not None and state.states is not None:
        counts = defaultdict(int)
        for isin in state.positions:
            counts[state.states.get(isin, MINE)] += 1
        out.append(
            f"Coverage:        0 of {len(state.positions)} position(s) "
            f"reported ({counts[MINE]} mine, {counts[SPANS_CUTOFF]} spanning "
            f"the cutoff, {counts[PRE_CUTOFF_ONLY]} pre-cutoff only)"
        )
    else:
        out.append(f"Coverage:        {NOT_REACHED}")
    out.append("```")
    out.append("")

    # ---- METHOD ----------------------------------------------------------
    out.append("METHOD")
    out.append("")
    out.append(
        "- Attribution: "
        + (
            "FIFO - sells consume the inherited lot first"
            if state.attribute == ATTRIBUTE_FIFO
            else "none - positions that existed at the cutoff carry no quantity"
        )
    )
    if state.ownership:
        out.append(
            "- Ownership: shared account; only transactions on or after "
            f"{state.ownership.cutoff.isoformat()} count as mine"
        )
        out.append(f"- Cutoff: {state.ownership.describe()}")
    else:
        out.append(f"- Ownership: {NOT_REACHED}")
        out.append(f"- Cutoff: {NOT_REACHED}")
    if ledger:
        audit = fx_direction_audit(ledger.txs)
        if audit:
            summary = "; ".join(
                f"{kind}: "
                + ", ".join(
                    f"{count} {bucket}" for bucket, count in buckets.items() if count
                )
                for kind, buckets in sorted(audit.items())
            )
            out.append(f"- Exchange-rate direction re-derived from Total - {summary}")
        for note in ledger.schema_notes:
            out.append(f"- {note}")
        for warning in ledger.warnings:
            out.append(f"- {warning}")
    out.append("- Columns suppressed: none - no table was printed")
    out.append("")

    # ---- PROOF -----------------------------------------------------------
    out.append("PROOF")
    out.append("")
    out.append(f"## {halt.check} failed")
    out.append("")
    for line in halt.message.splitlines():
        out.append(line)
    out.append("")

    # ---- SOURCES ---------------------------------------------------------
    out.append("SOURCES")
    out.append("")
    if ledger and ledger.files:
        out.append(
            "- "
            + ", ".join(p.name for p in ledger.files)
            + f" ({ledger.rows_read} rows read, {len(ledger.duplicates)} "
            f"duplicate(s) dropped, {len(ledger.txs)} kept)" + LOCAL_FILE
        )
    else:
        out.append(f"- exports: {NOT_REACHED}")
    out.append(
        f"- {state.pies.path.name} (updated {state.pies.updated or '?'})"
        + LOCAL_FILE
        if state.pies
        else f"- pie mapping: {NOT_REACHED}"
    )
    out.append(
        f"- {state.ownership.path.name} "
        f"(cutoff {state.ownership.cutoff.isoformat()}, "
        f"updated {state.ownership.updated or '?'})" + LOCAL_FILE
        if state.ownership
        else f"- ownership file: {NOT_REACHED}"
    )

    return "\n".join(out)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def run(
    data_dir: Path,
    pies_path: Path,
    ownership_path: Path = Path("me/ownership.md"),
    cutoff: date | None = None,
    attribute: str = ATTRIBUTE_FIFO,
    state: RunState | None = None,
    proof: bool = False,
) -> str:
    # Each step records itself in ``state`` as it lands, so a halt further
    # down can still print what had been established when it fired.
    state = state if state is not None else RunState()
    state.attribute = attribute
    if attribute not in ATTRIBUTION_MODES:
        raise Halt(
            f"unknown attribution mode {attribute!r}; "
            f"expected one of {', '.join(ATTRIBUTION_MODES)}",
            figure=f"--attribute {attribute}",
        )
    ownership = state.ownership = load_ownership(ownership_path, cutoff)
    ledger = state.ledger = load_transactions(data_dir)
    positions = state.positions = aggregate(ledger.txs, ownership.cutoff)
    pies = state.pies = load_pies(pies_path)
    states = state.states = classify_ownership(positions, ownership)
    attributions = state.attributions = (
        fifo_attribution(ledger.txs, ownership.cutoff)
        if attribute == ATTRIBUTE_FIFO
        else None
    )

    check_no_negative_quantity(positions, states)
    check_mapping_covers_holdings(pies, positions)
    weight_notes = check_weights_sum(
        pies, positions, states, attributions, ownership.fixed_rate
    )

    return build_report(
        ledger, pies, ownership, positions, states, weight_notes, attributions,
        proof=proof,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive current holdings from Trading 212 CSV exports."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data/t212"),
        help="directory of Trading 212 CSV exports (default: data/t212)",
    )
    parser.add_argument(
        "--pies",
        type=Path,
        default=Path("me/pies.md"),
        help="pie mapping file (default: me/pies.md)",
    )
    parser.add_argument(
        "--ownership",
        type=Path,
        default=Path("me/ownership.md"),
        help="ownership cutoff and pre-cutoff ISINs (default: me/ownership.md)",
    )
    parser.add_argument(
        "--cutoff",
        type=date.fromisoformat,
        default=None,
        metavar="YYYY-MM-DD",
        help="override the cutoff date recorded in the ownership file",
    )
    parser.add_argument(
        "--attribute",
        choices=ATTRIBUTION_MODES,
        default=ATTRIBUTE_FIFO,
        help=(
            "how to treat positions that existed at the cutoff: 'fifo' "
            "(default) consumes the inherited lot first and attributes what "
            "is left; 'none' claims no quantity for them at all"
        ),
    )
    parser.add_argument(
        "--proof",
        action="store_true",
        help="print the PROOF section on a completed run (a halt always "
        "prints it); the checks run either way",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=None,
        help="write the report here instead of stdout",
    )
    args = parser.parse_args(argv)

    state = RunState(attribute=args.attribute)
    try:
        report = run(
            args.data_dir,
            args.pies,
            args.ownership,
            args.cutoff,
            args.attribute,
            state,
            proof=args.proof,
        )
    except Halt as exc:
        # A halt is a defined output shape, not an absence of output: it
        # prints on stdout like any other run, minus RESULT.
        withheld = [f"{args.out} (not written)"] if args.out else []
        print(build_halt_report(state, exc, withheld))
        return 1

    if args.out:
        args.out.write_text(report + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
