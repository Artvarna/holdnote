#!/usr/bin/env python3
"""Any broker's export -> me/holdings.csv (references/any-broker.md).

Follow RULES.md.

Reads what an investment app or website lets its users download -- a
positions / portfolio export, or a transaction history of buys and sells --
as CSV, TSV, TXT or Excel (.xlsx), and writes the one broker-neutral file the
portfolio view reads:

    # Holdnote holdings. quantity is what you hold; target_pct is your
    # chosen % of the whole portfolio (optional).
    # as_of: 2026-10-13
    # source: Portfolio.csv (positions)
    isin,ticker,name,kind,quantity,group,target_pct
    IE00BFY0GT14,SPPW,SPDR MSCI World UCITS ETF,fund,12.5,Portfolio,60

A screenshot or a typed list is first written by the run as a two-column CSV
(``isin,quantity`` or ``ticker,quantity``) and imported the same way, so
every route ends in the same checks.

Columns are found by their header (English, German, French, Spanish,
Italian, Dutch, Polish, Bulgarian, Russian spellings), and ISINs also by
their check digit in any cell, so a "Symbol/ISIN" or "Product" column still
yields them. ``--map quantity="No. of units"`` overrides a header.

Nothing is guessed silently. A row with no ISIN stops the write until the run
supplies one (``--isin AAPL=US0378331005``, from a primary source); a history
with splits or transfers stops it too, because net buys and sells are then
not the holding. ``kind`` (fund or stock) is guessed from the name only for a
new holding, and the summary marks every guess for the user to confirm.

Re-importing keeps what the user decided -- kind, group, target_pct -- from
the existing file, by ISIN.

Exit codes: 0 written (or printed, with --dry-run); 1 refused, reason on
stdout; 2 needs input (an ISIN, or which column holds the quantity), named on
stdout.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

FIELDS = ["isin", "ticker", "name", "kind", "quantity", "group", "target_pct"]
KINDS = {"fund", "stock"}
DEFAULT_GROUP = "Portfolio"
DEFAULT_OUT = Path("me/holdings.csv")
HEADER_SCAN = 40  # rows searched for the header line

ISIN_RE = re.compile(r"\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b")

# Normalised header -> field. Earlier entries win when two columns match the
# same field. "amount" is last for quantity: some apps mean shares by it,
# others money, so a quantity read from it is flagged.
SYNONYMS: dict[str, list[str]] = {
    "isin": ["isin", "isin code", "symbol isin", "isin symbol", "product isin",
             "security isin", "instrument isin", "isin wkn", "wkn isin", "isin number"],
    "ticker": ["ticker", "symbol", "ticker symbol", "instrument symbol", "trading symbol",
               "code", "instrument code", "epic", "kurzel", "kuerzel", "simbolo",
               "symbole", "тикер", "символ"],
    "name": ["name", "instrument name", "security name", "security", "product", "produkt",
             "instrument", "security description", "description", "asset", "asset name",
             "company", "company name", "fund", "fund name", "holding", "bezeichnung",
             "wertpapier", "titel", "nom", "nombre", "nome", "titolo", "naam", "nazwa",
             "наименование", "название", "име", "инструмент"],
    "quantity": ["quantity", "qty", "shares", "no of shares", "number of shares",
                 "share quantity", "units", "no of units", "number of units", "position",
                 "open quantity", "volume", "anzahl", "stuck", "stueck", "stuckzahl",
                 "menge", "bestand", "nominal", "quantite", "nombre de parts", "cantidad",
                 "titulos", "quantita", "aantal", "ilosc", "liczba", "количество",
                 "брой", "количество акции", "amount"],
    "currency": ["currency", "ccy", "currency code", "wahrung", "waehrung", "devise",
                 "moneda", "divisa", "valuta", "waluta", "валюта", "валута"],
    "type": ["type", "action", "side", "transaction type", "trade type", "buy sell",
             "operation", "direction", "transaction", "order type", "art", "typ",
             "transaktionstyp", "transaktionsart", "tipo", "sens", "тип", "операция"],
    "date": ["date", "time", "datetime", "trade date", "execution date", "execution time",
             "trade time", "settlement date", "datum", "fecha", "data", "дата"],
}

BUY = re.compile(r"\b(buy|bought|purchase|kauf|achat|compra|acquisto|koop|kupno|"
                 r"покупка|купить|subscription|sparplan|savings plan|reinvest\w*)\b", re.I)
SELL = re.compile(r"\b(sell|sold|sale|verkauf|vente|venta|vendita|verkoop|sprzedaz|"
                  r"продажба|продажа|redemption)\b", re.I)
# Rows that move a holding without being a buy or a sell: the history alone
# then cannot rebuild the quantity.
MOVES = re.compile(r"(split|transfer|einbuchung|ausbuchung|spin.?off|merger|"
                   r"corporate action|conversion|stock dividend|bonus|delivery)", re.I)
NOT_A_HOLDING = re.compile(r"^(cash|total|totals|sum|summe|gesamt|subtotal|free funds|"
                           r"available|balance|guthaben|saldo|liquidity|eur|usd|gbp|bgn|chf)\b",
                           re.I)
FUND_WORDS = re.compile(r"\b(etf|etc|etn|ucits|fund|fonds|index|tracker|ishares|vanguard|spdr|"
                        r"xtrackers|amundi|lyxor|invesco|wisdomtree|vaneck|hsbc msci|"
                        r"msci|s&p 500|ftse|stoxx|acc|dist)\b", re.I)


class Refused(Exception):
    """A check that stops the import: nothing is written but the reason."""


class NeedsInput(Exception):
    """The run must supply something (an ISIN, a column) before a write."""


@dataclass
class Holding:
    isin: str
    ticker: str
    name: str
    kind: str
    quantity: Decimal
    group: str = DEFAULT_GROUP
    target: Decimal | None = None  # % of the whole portfolio


@dataclass
class HoldingsFile:
    holdings: list[Holding]
    as_of: date | None
    source: str


# --- small parsers ----------------------------------------------------------

def norm_header(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text or ""))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^\w]+", " ", text).split())


def isin_valid(code: str) -> bool:
    """The ISO 6166 check digit: letters to numbers, then Luhn."""
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", code or ""):
        return False
    digits = "".join(str(int(c, 36)) for c in code)
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def find_isin(text: str) -> str:
    for m in ISIN_RE.finditer(str(text or "").upper()):
        if isin_valid(m.group(1)):
            return m.group(1)
    return ""


def _clean_number(raw: str) -> str:
    s = str(raw or "").strip().replace("−", "-").replace(" ", "").replace(" ", "")
    s = s.replace(" ", "").replace("'", "")
    negative = s.startswith("(") and s.endswith(")")
    s = re.sub(r"[^\d,.\-+]", "", s.strip("()"))
    if negative and not s.startswith("-"):
        s = "-" + s
    return s


# One separator followed by exactly three digits, as in 1,250 or 12.500: a
# thousands separator or a decimal one, and nothing in the value says which.
AMBIGUOUS_NUMBER = re.compile(r"[-+]?[1-9]\d{0,2}[,.]\d{3}")


def decimal_mode(values: list[str], delimiter: str) -> tuple[bool, list[str]]:
    """Whether a column writes 12,5 for twelve and a half, and the values whose
    reading rests only on the file's delimiter (the caller asks about those).

    Evidence, in order: a value with both separators; a value starting 0, or
    0. (never a thousands separator); a separator followed by one, two, or four
    or more digits; one separator repeated (1.250.000). Only when none is
    present does the delimiter decide (semicolon files write decimal commas),
    and then every value like 1,250 is returned as a guess.
    """
    cleaned = [_clean_number(v) for v in values if _clean_number(v)]
    for s in cleaned:
        if "," in s and "." in s:
            return s.rfind(",") > s.rfind("."), []
    for s in cleaned:
        m = re.fullmatch(r"[-+]?0([,.])\d+", s)
        if m:
            return m.group(1) == ",", []
    if any(re.fullmatch(r"[-+]?\d+,(\d{1,2}|\d{4,})", s) for s in cleaned):
        return True, []
    if any(re.fullmatch(r"[-+]?\d+\.(\d{1,2}|\d{4,})", s) for s in cleaned):
        return False, []
    if any(re.fullmatch(r"[-+]?\d{1,3}(\.\d{3}){2,}", s) for s in cleaned):
        return True, []
    if any(re.fullmatch(r"[-+]?\d{1,3}(,\d{3}){2,}", s) for s in cleaned):
        return False, []
    return delimiter == ";", [s for s in cleaned if AMBIGUOUS_NUMBER.fullmatch(s)]


def decimal_comma(values: list[str], delimiter: str) -> bool:
    """Whether a column writes 12,5 for twelve and a half (decimal_mode's guess)."""
    return decimal_mode(values, delimiter)[0]


def parse_number(raw: str, comma: bool) -> Decimal | None:
    s = _clean_number(raw)
    if not s or s in "-+":
        return None
    s = s.replace(".", "").replace(",", ".") if comma else s.replace(",", "")
    try:
        value = Decimal(s)
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


# --- reading any export -----------------------------------------------------

def _decode(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "cp1252"):
        try:
            text = data.decode(enc)
            if enc == "utf-16" and not data[:2] in (b"\xff\xfe", b"\xfe\xff"):
                continue
            return text
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def _delimiter(text: str) -> str:
    sample = "\n".join(text.splitlines()[:HEADER_SCAN])
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except csv.Error:
        counts = {d: sample.count(d) for d in (";", ",", "\t", "|")}
        return max(counts, key=counts.get)


def _cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return format(Decimal(repr(value)).normalize(), "f")
    if isinstance(value, (date,)):
        return value.isoformat()[:10]
    return str(value)


def read_tables(path: Path) -> list[tuple[str, list[list[str]], str]]:
    """(label, rows, delimiter) for each sheet or the one text table."""
    if path.suffix.lower() in (".xlsx", ".xlsm"):
        try:
            import openpyxl
        except ImportError:
            raise Refused(f"{path.name}: reading Excel needs openpyxl; save the sheet as CSV")
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        out = []
        for ws in wb.worksheets:
            rows = [[_cell(v) for v in r] for r in ws.iter_rows(values_only=True)]
            out.append((f"{path.name} [{ws.title}]", rows, ","))
        return out
    if path.suffix.lower() == ".xls":
        raise Refused(f"{path.name}: old .xls files can't be read here; save it as .xlsx or CSV")
    text = _decode(path.read_bytes())
    delim = _delimiter(text)
    rows = list(csv.reader(io.StringIO(text), delimiter=delim))
    return [(path.name, rows, delim)]


def map_columns(header: list[str], overrides: dict[str, str]) -> tuple[dict[str, int], dict[str, str]]:
    """Field -> column index, and field -> the header text it came from."""
    normed = [norm_header(h) for h in header]
    cols: dict[str, int] = {}
    for field, wanted in overrides.items():
        target = norm_header(wanted)
        if target not in normed:
            raise NeedsInput(f'--map {field}="{wanted}": no such column. Columns: '
                             + ", ".join(f'"{h}"' for h in header if h))
        cols[field] = normed.index(target)
    for field, names in SYNONYMS.items():
        if field in cols:
            continue
        for name in names:
            if name in normed and normed.index(name) not in cols.values():
                cols[field] = normed.index(name)
                break
    return cols, {f: header[i] for f, i in cols.items()}


def _header_score(row: list[str]) -> int:
    known = {n for names in SYNONYMS.values() for n in names}
    return sum(1 for c in row if norm_header(c) in known)


def pick_table(tables, overrides):
    """The sheet and header row that look most like a holdings table."""
    best = None
    for label, rows, delim in tables:
        for i, row in enumerate(rows[:HEADER_SCAN]):
            score = _header_score(row)
            if overrides:
                normed = {norm_header(c) for c in row}
                score += 10 * sum(norm_header(v) in normed for v in overrides.values())
            if score >= 2 and (best is None or score > best[0]):
                best = (score, label, rows, delim, i)
    if best is None:
        first = next((r for _, rows, _ in tables for r in rows if any(c.strip() for c in r)), [])
        raise NeedsInput("no header row with a quantity or ISIN column found. First row: "
                         + ", ".join(f'"{c}"' for c in first if c)
                         + '. Say which column holds what, e.g. --map quantity="Units"')
    _, label, rows, delim, i = best
    return label, rows[i], rows[i + 1:], delim, i + 1


def _is_trading212(normed: set[str]) -> bool:
    return {"action", "time", "isin", "no of shares"} <= normed


@dataclass
class Parsed:
    key: str  # ISIN, else ticker, else name
    isin: str
    ticker: str
    name: str
    quantity: Decimal
    bad_isin: str = ""  # an ISIN-shaped cell that failed the check digit


def parse_export(path: Path, overrides: dict[str, str],
                 decimal: str | None = None) -> tuple[list[Parsed], dict]:
    tables = read_tables(path)
    label, header, body, delim, header_line = pick_table(tables, overrides)
    normed = {norm_header(h) for h in header}
    if _is_trading212(normed):
        raise Refused(f"{path.name} is a Trading 212 history export. Portfolio sync reads it "
                      "directly (t212_holdings.py, references/portfolio-sync.md), keeping "
                      "the ownership cutoff and FIFO.")
    cols, came_from = map_columns(header, overrides)
    if "quantity" not in cols:
        raise NeedsInput(f"{label}: no quantity column. Columns: "
                         + ", ".join(f'"{h}"' for h in header if h)
                         + '. Say which holds the number of shares, e.g. --map quantity="Units"')

    def get(row: list[str], field: str) -> str:
        i = cols.get(field)
        return row[i].strip() if i is not None and i < len(row) else ""

    quantities = [get(r, "quantity") for r in body]
    if decimal:
        comma, unsure = decimal == "comma", []
    else:
        comma, unsure = decimal_mode(quantities, delim)
    history = False
    if "type" in cols:
        kinds = [get(r, "type") for r in body]
        history = any(BUY.search(k) or SELL.search(k) for k in kinds)
    info = {"label": label, "header_line": header_line, "came_from": came_from,
            "mode": "history" if history else "positions", "skipped": 0, "ignored_types": {},
            "dates": [], "warnings": []}
    if unsure:
        raw = unsure[0]
        now, alt = parse_number(raw, comma), parse_number(raw, not comma)
        info["warnings"].append(
            f"{len(unsure)} quantit{'y' if len(unsure) == 1 else 'ies'} like {raw} read as "
            f"{_fmt(now)}, not {_fmt(alt)}: the file does not say which separator is the "
            f"decimal one. Confirm, or pass --decimal {'dot' if comma else 'comma'} to read "
            f"{raw} as {_fmt(alt)}")
    bad_isins: list[str] = []
    if came_from.get("quantity") and norm_header(came_from["quantity"]) == "amount":
        info["warnings"].append(f'quantity read from the "{came_from["quantity"]}" column: '
                                "confirm these are share counts, not money")

    moves: list[str] = []
    out: dict[str, Parsed] = {}
    for row in body:
        if not any(c.strip() for c in row):
            continue
        isin = get(row, "isin").upper()
        isin = isin if isin_valid(isin) else find_isin(get(row, "isin"))
        if not isin:
            isin = next((find_isin(c) for c in row if find_isin(c)), "")
        bad = ""
        if not isin:
            bad = next((m.group(1) for c in (get(row, "isin"), get(row, "ticker"))
                        for m in ISIN_RE.finditer(c.upper())), "")
        ticker = get(row, "ticker")
        if find_isin(ticker) == ticker.upper() and ticker:
            ticker = ""  # a "Symbol/ISIN" cell holding the ISIN is not a ticker
        name = get(row, "name")
        qty = parse_number(get(row, "quantity"), comma)
        label_text = name or ticker
        if not (isin or ticker or name) or (not isin and NOT_A_HOLDING.match(label_text)):
            if bad:
                bad_isins.append(bad)
            info["skipped"] += 1
            continue
        if history:
            kind = get(row, "type")
            if MOVES.search(kind):
                moves.append(f"{kind} {label_text or isin}")
                continue
            if BUY.search(kind):
                sign = Decimal(1)
            elif SELL.search(kind):
                sign = Decimal(-1)
            else:
                info["ignored_types"][kind or "(blank)"] = info["ignored_types"].get(kind or "(blank)", 0) + 1
                continue
            if qty is None:
                raise Refused(f"{label}: a {kind} of {label_text or isin} has no quantity")
            qty = sign * abs(qty)
            if get(row, "date"):
                info["dates"].append(get(row, "date"))
        elif qty is None:
            info["skipped"] += 1
            continue
        key = isin or (ticker.upper() if ticker else name.lower())
        p = out.get(key)
        if p is None:
            out[key] = Parsed(key, isin, ticker, name, qty, bad)
        else:
            p.quantity += qty
            p.ticker = p.ticker or ticker
            p.name = p.name or name
    if bad_isins:
        raise NeedsInput(f"{label}: not a valid ISIN (check digit): " + ", ".join(bad_isins)
                         + ". Check the export for a typo, or pass the right one with "
                           "--isin NAME_OR_TICKER=ISIN")
    if moves:
        raise Refused(f"{label}: {len(moves)} rows move holdings without a buy or sell ("
                      + "; ".join(moves[:5]) + (" ..." if len(moves) > 5 else "")
                      + "). Buys minus sells are then not what you hold: export your current "
                      "positions (portfolio / holdings page) instead.")
    rows = [p for p in out.values() if p.quantity != 0]
    short = [p for p in rows if p.quantity < 0]
    if short:
        what = "sells exceed buys" if history else "negative quantity"
        raise Refused(f"{label}: {what} for " + ", ".join(p.ticker or p.name or p.isin for p in short)
                      + (" - the history may not start at the account's first trade; "
                         "export your current positions instead" if history else
                         " - short positions are not supported"))
    if not rows:
        raise Refused(f"{label}: no holdings found ({info['skipped']} rows skipped)")
    return rows, info


# --- the holdings file ------------------------------------------------------

def load_holdings(path: Path) -> HoldingsFile:
    """Read and check me/holdings.csv. Raises Refused with the reason."""
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise Refused(f"{path}: {exc}")
    as_of = None
    source = ""
    data = []
    for line in lines:
        if line.lstrip().startswith("#"):
            m = re.match(r"#\s*as_of:\s*(\d{4}-\d{2}-\d{2})", line.strip())
            if m:
                as_of = date.fromisoformat(m.group(1))
            m = re.match(r"#\s*source:\s*(.+)", line.strip())
            if m:
                source = m.group(1).strip()
            continue
        if line.strip():
            data.append(line)
    reader = csv.DictReader(data)
    missing = {"isin", "quantity", "kind"} - set(reader.fieldnames or [])
    if missing:
        raise Refused(f"{path}: missing column(s) " + ", ".join(sorted(missing)))
    holdings: list[Holding] = []
    seen = set()
    for n, r in enumerate(reader, start=2):
        where = f"{path.name} row {n}"
        isin = (r.get("isin") or "").strip().upper()
        if not isin_valid(isin):
            raise Refused(f"{where}: {isin!r} is not a valid ISIN")
        if isin in seen:
            raise Refused(f"{where}: {isin} appears twice")
        seen.add(isin)
        try:
            qty = Decimal((r.get("quantity") or "").strip())
        except InvalidOperation:
            raise Refused(f"{where}: quantity {r.get('quantity')!r} is not a number")
        if not qty.is_finite() or qty < 0:
            raise Refused(f"{where}: quantity {r.get('quantity')!r} is not zero or more")
        kind = (r.get("kind") or "").strip().lower()
        if kind not in KINDS:
            raise Refused(f"{where}: kind {kind!r} must be fund or stock")
        raw_t = (r.get("target_pct") or "").strip().rstrip("%")
        target = None
        if raw_t:
            try:
                target = Decimal(raw_t.replace(",", "."))
            except InvalidOperation:
                raise Refused(f"{where}: target_pct {raw_t!r} is not a number")
            if not (0 <= target <= 100):
                raise Refused(f"{where}: target_pct {raw_t} is outside 0-100")
        holdings.append(Holding(isin, (r.get("ticker") or "").strip(), (r.get("name") or "").strip(),
                                kind, qty, (r.get("group") or "").strip() or DEFAULT_GROUP, target))
    if not holdings:
        raise Refused(f"{path}: no holdings")
    return HoldingsFile(holdings, as_of, source)


def _fmt(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    return text


def write_holdings(path: Path, holdings: list[Holding], as_of: date, source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    buf.write("# Holdnote holdings. quantity is what you hold; target_pct is your\n"
              "# chosen % of the whole portfolio (optional). Edit freely.\n")
    buf.write(f"# as_of: {as_of.isoformat()}\n# source: {source}\n")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(FIELDS)
    for h in holdings:
        w.writerow([h.isin, h.ticker, h.name, h.kind, _fmt(h.quantity), h.group,
                    "" if h.target is None else _fmt(h.target)])
    path.write_text(buf.getvalue(), encoding="utf-8")


def guess_kind(name: str, ticker: str) -> str:
    return "fund" if FUND_WORDS.search(f"{name} {ticker}") else "stock"


def _pairs(values: list[str], flag: str) -> dict[str, str]:
    out = {}
    for v in values:
        if "=" not in v:
            raise SystemExit(f"{flag} {v!r}: expected KEY=VALUE")
        k, val = v.split("=", 1)
        out[k.strip()] = val.strip()
    return out


def build(parsed: list[Parsed], existing: HoldingsFile | None, isins: dict[str, str],
          kinds: dict[str, str]) -> tuple[list[Holding], list[str], list[str]]:
    """Holdings to write, the ISINs whose kind was guessed, and dropped names."""
    lookup = {k.upper(): v.strip().upper() for k, v in isins.items()}
    need = []
    for p in parsed:
        if p.isin:
            continue
        code = lookup.get(p.ticker.upper()) or lookup.get(p.name.upper())
        if code:
            if not isin_valid(code):
                raise Refused(f"--isin {p.ticker or p.name}={code}: not a valid ISIN (check digit)")
            p.isin = code
        else:
            need.append(p.ticker or p.name)
    if need:
        typos = [f"{p.ticker or p.name} ({p.bad_isin})" for p in parsed if not p.isin and p.bad_isin]
        raise NeedsInput("no ISIN for " + ", ".join(need) + ". "
                         + ("Not a valid ISIN (check digit), likely a typo in the export: "
                            + ", ".join(typos) + ". " if typos else "")
                         + "Find each one in a primary source (issuer page, exchange listing, "
                           "the broker's instrument page) and pass it: "
                         + " ".join(f'--isin "{n}=..."' for n in need[:3]))
    merged: dict[str, Parsed] = {}
    for p in parsed:
        if p.isin in merged:
            merged[p.isin].quantity += p.quantity
        else:
            merged[p.isin] = p
    old = {h.isin: h for h in existing.holdings} if existing else {}
    kind_over = {k.upper(): v.strip().lower() for k, v in kinds.items()}
    out, guessed = [], []
    for p in merged.values():
        prev = old.get(p.isin)
        kind = kind_over.get(p.isin) or kind_over.get(p.ticker.upper())
        if kind and kind not in KINDS:
            raise Refused(f"--kind {p.ticker or p.isin}={kind}: must be fund or stock")
        if not kind:
            kind = prev.kind if prev else guess_kind(p.name, p.ticker)
            if not prev:
                guessed.append(p.isin)
        out.append(Holding(p.isin, p.ticker or (prev.ticker if prev else ""),
                           p.name or (prev.name if prev else ""), kind, p.quantity,
                           prev.group if prev else DEFAULT_GROUP, prev.target if prev else None))
    dropped = [h.ticker or h.name or h.isin for i, h in old.items() if i not in merged]
    out.sort(key=lambda h: (h.group, 0 if h.kind == "fund" else 1, h.ticker or h.name))
    return out, guessed, dropped


def _last_date(values: list[str]) -> date | None:
    found = []
    for v in values:
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", v)
        if m:
            try:
                found.append(date(int(m.group(1)), int(m.group(2)), int(m.group(3))))
            except ValueError:
                pass
            continue
        m = re.search(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b", v)
        if m:  # day first: the European order these exports use
            try:
                found.append(date(int(m.group(3)), int(m.group(2)), int(m.group(1))))
            except ValueError:
                pass
    return max(found) if found else None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("files", nargs="+", type=Path, help="one or more exports (CSV/TSV/TXT/XLSX)")
    ap.add_argument("-o", "--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--map", action="append", default=[], metavar="FIELD=HEADER",
                    help="which column holds a field: quantity, isin, ticker, name, type, date")
    ap.add_argument("--isin", action="append", default=[], metavar="TICKER=ISIN")
    ap.add_argument("--kind", action="append", default=[], metavar="ISIN_OR_TICKER=fund|stock")
    ap.add_argument("--as-of", type=date.fromisoformat, default=None,
                    help="date the positions are from (default: last trade, else today)")
    ap.add_argument("--decimal", choices=("comma", "dot"), default=None,
                    help="which separator is the decimal one in quantities, when the "
                         "export leaves it open (1,250 or 1.250)")
    ap.add_argument("--dry-run", action="store_true", help="print, do not write")
    args = ap.parse_args(argv)

    overrides = _pairs(args.map, "--map")
    bad = set(overrides) - set(SYNONYMS)
    if bad:
        print("--map: unknown field(s) " + ", ".join(sorted(bad)))
        return 2
    try:
        parsed: list[Parsed] = []
        infos = []
        for f in args.files:
            rows, info = parse_export(f, overrides, args.decimal)
            parsed.extend(rows)
            infos.append(info)
        existing = load_holdings(args.out) if args.out.exists() else None
        holdings, guessed, dropped = build(parsed, existing, _pairs(args.isin, "--isin"),
                                           _pairs(args.kind, "--kind"))
    except NeedsInput as exc:
        print(f"Needs input: {exc}")
        return 2
    except Refused as exc:
        print(f"Import: Not available - {exc}")
        return 1

    dates = [d for i in infos for d in i["dates"]]
    as_of = args.as_of or (_last_date(dates) if dates else None) or date.today()
    source = "; ".join(f"{i['label']} ({i['mode']})" for i in infos)
    for i in infos:
        cols = ", ".join(f'{f} from "{h}"' for f, h in i["came_from"].items()
                         if f in ("isin", "ticker", "name", "quantity", "type"))
        print(f"Read: {i['label']} - {i['mode']}, header on line {i['header_line']}; {cols}")
        if i["skipped"]:
            print(f"Skipped: {i['skipped']} rows that are not a holding (cash, totals, blanks)")
        if i["ignored_types"]:
            print("Not buys or sells, left out: " + ", ".join(
                f"{k} x{n}" for k, n in sorted(i["ignored_types"].items())))
        for w in i["warnings"]:
            print(f"Check: {w}")
    print()
    print("| ISIN | Ticker | Name | Kind | Quantity | Group | Target % |")
    print("|---|---|---|---|---|---|---|")
    for h in holdings:
        kind = h.kind + (" (guessed)" if h.isin in guessed else "")
        print(f"| {h.isin} | {h.ticker or '-'} | {h.name or '-'} | {kind} | {_fmt(h.quantity)} "
              f"| {h.group} | {'-' if h.target is None else _fmt(h.target)} |")
    print()
    if dropped:
        print("No longer in the export, removed: " + ", ".join(dropped))
    if guessed:
        print(f"Kind guessed from the name for {len(guessed)} holding(s): confirm, "
              "or pass --kind TICKER=fund|stock")
    if args.dry_run:
        print(f"Dry run: {args.out} not written")
    else:
        write_holdings(args.out, holdings, as_of, source)
        print(f"Wrote {args.out.as_posix()} ({len(holdings)} holdings, as of {as_of})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
