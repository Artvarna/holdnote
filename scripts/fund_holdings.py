#!/usr/bin/env python3
"""Full fund holdings for Mode C: the Holdings and Look-through tables.

Follow RULES.md.

Each fund in the ETF pie publishes its whole portfolio, not only a top 10.
This module reads those files, so holdings overlap and look-through cover
every company a fund holds rather than its ten largest.

Two commands, both run in the repo folder on the user's computer:

    python3 scripts/fund_holdings.py fetch
    python3 scripts/fund_holdings.py report --prices "$HOME/prices.json"

``fetch`` downloads each issuer's file into ``data/holdings/`` as
``<TICKER>-<fetch date>.<ext>``, unchanged, so a reader can open the exact
bytes a table came from. ``report`` reads the newest file per fund and
prints the two tables, then the METHOD and PROOF lines behind them. Its
look-through weights are the Allocation table's ``Weight (market)``,
computed by ``market_weights`` from the same ``--prices`` file; without it the
look-through is ``Not available``.

What the files carry, as found on 2026-10-09:

    SPPW  SSGA       daily xlsx   ISIN per row
    EIMI  iShares    daily CSV    no ISIN: local ticker and exchange only;
                                  weights rounded to 0.01 by the issuer
    VUSA  Vanguard   monthly JSON ISIN per row (month-end portfolio)
    MEUD  Amundi     daily JSON   ISIN and Bloomberg ticker per row; sector and
                                  currency when the request asks for them

Companies are matched by issuer, not by share class: a US or Canadian ISIN
carries the CUSIP, whose first six characters name the issuer, so Alphabet A
and C are one company. Other ISINs match exactly. EIMI's rows have no ISIN,
so each is matched through its ticker and exchange to a fund row that has a
Bloomberg ticker (MEUD's); an EIMI row on an exchange not in ``EXCHANGES``
matches nothing and METHOD says how many such rows there are.

Nothing here is recalled. A file that cannot be fetched or does not pass its
checks makes that fund ``Not available`` with the reason, and every pair
and look-through cell that needs it says so.

Exit codes: 0 printed, 1 nothing could be printed (message on stdout).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

CENT = Decimal("0.01")
HUNDRED = Decimal(100)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0 Safari/537.36"
)


@dataclass(frozen=True)
class Source:
    ticker: str
    isin: str
    issuer: str
    url: str
    ext: str
    method: str = "GET"
    body: dict | None = None
    headers: tuple[tuple[str, str], ...] = ()


_VANGUARD_QUERY = (
    "query FundsHoldingsQuery($portIds: [String!]!, $lastItemKey: String) "
    "{ borHoldings(portIds: $portIds) { holdings(limit: 1500, lastItemKey: $lastItemKey) "
    "{ items { issuerName securityLongDescription marketValuePercentage isin ticker "
    "securityType effectiveDate bloombergIsoCountry } totalHoldings lastItemKey } } }"
)

AMUNDI_URL = "https://www.amundietf.de/mapi/ProductAPI/getProductsData"
VANGUARD_URL = "https://www.vanguard.co.uk/gpx/graphql"
ISSUERS = ("ssga", "ishares", "vanguard", "amundi")


def make_source(ticker: str, isin: str, issuer: str, holdings: str = "") -> Source:
    """A fund's holdings source from its issuer and the one thing that issuer needs.

    ssga and ishares: the holdings file's URL. vanguard: the fund's port ID.
    amundi: nothing beyond the ISIN.
    """
    issuer = issuer.strip().lower()
    holdings = holdings.strip()
    if issuer in ("ssga", "ishares"):
        if not holdings.startswith("https://"):
            raise Refused(f"{ticker}: {issuer} needs the holdings file's https:// link")
        return Source(ticker, isin, issuer, holdings, "xlsx" if issuer == "ssga" else "csv")
    if issuer == "vanguard":
        if not holdings.isdigit():
            raise Refused(f"{ticker}: vanguard needs the fund's port ID (a number)")
        return Source(ticker, isin, issuer, VANGUARD_URL, "json", "POST",
                      {"operationName": "FundsHoldingsQuery", "query": _VANGUARD_QUERY,
                       "variables": {"portIds": [holdings], "lastItemKey": None}},
                      (("x-consumer-id", "uk0"),))
    if issuer == "amundi":
        return Source(ticker, isin, issuer, AMUNDI_URL, "json", "POST",
                      {"context": {"countryCode": "DEU", "languageCode": "de",
                                   "userProfileName": "RETAIL"},
                       "productIds": [isin],
                       "composition": {"compositionFields": [
                           "date", "type", "bbg", "isin", "name", "weight", "countryOfRisk",
                           "sector", "currency"]}})
    raise Refused(f"{ticker}: issuer {issuer!r} is not one of {', '.join(ISSUERS)}")


# The funds this project was built on; also what runs when no funds file exists.
CATALOG = (
    make_source("SPPW", "IE00BFY0GT14", "ssga",
                "https://www.ssga.com/ie/en_gb/intermediary/library-content/products/"
                "fund-data/etfs/emea/holdings-daily-emea-en-sppw-gy.xlsx"),
    make_source("MEUD", "LU0908500753", "amundi"),
    make_source("EIMI", "IE00BKM4GZ66", "ishares",
                "https://www.ishares.com/uk/individual/en/products/264659/"
                "ishares-core-msci-em-imi-ucits-etf/latest-holdings.csv"),
    make_source("VUSA", "IE00B3XXRP09", "vanguard", "9503"),
)
SOURCES: dict[str, Source] = {s.isin: s for s in CATALOG}
ISIN_OF = {s.ticker: s.isin for s in SOURCES.values()}
DEFAULT_FUNDS = Path("me/funds.md")


def load_funds(path: Path) -> dict[str, Source]:
    """The `## Funds` table of a funds file: Ticker | ISIN | Issuer | Holdings file.

    Rows print in the file's order. A row whose ISIN is in CATALOG and whose
    holdings cell is blank takes the catalog's source under the row's ticker.
    """
    out: dict[str, Source] = {}
    known = {s.isin: s for s in CATALOG}
    in_table = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("#"):
            in_table = line.lstrip("#").strip().lower() == "funds"
            continue
        if not in_table or not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 3 or cells[0].lower() == "ticker" or set("".join(cells)) <= set("-: "):
            continue
        ticker, isin, issuer = cells[0].upper(), cells[1].upper(), cells[2]
        holdings = cells[3] if len(cells) > 3 else ""
        if not (ticker and ISIN.match(isin)):
            raise Refused(f"{path.name}: row {line!r} needs a ticker and a valid ISIN")
        if not holdings and isin in known and known[isin].issuer == issuer.strip().lower():
            base = known[isin]
            out[isin] = Source(ticker, isin, base.issuer, base.url, base.ext, base.method,
                               base.body, base.headers)
        else:
            out[isin] = make_source(ticker, isin, issuer, holdings)
    return out


SETUP_HINT = 'say "set up Holdnote" to add your funds (references/setup.md)'


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def use_funds(path: Path | None) -> str:
    """Point the module at a funds file; returns what METHOD should say.

    ``None`` is the built-in CATALOG, for tests. A path that is missing, or
    whose Funds table is empty, means no funds: a new or stocks-only user's
    run never borrows the funds this project was built on.
    """
    global SOURCES, ISIN_OF
    if path is None:
        funds = {s.isin: s for s in CATALOG}
        note = f"built-in catalog, {plural(len(funds), 'fund')}"
    elif not path.is_file():
        funds, note = {}, f"no funds file at {path.as_posix()} - {SETUP_HINT}"
    else:
        funds = load_funds(path)
        note = (f"{path.as_posix()}, {plural(len(funds), 'fund')}" if funds
                else f"{path.as_posix()} lists no fund")
    SOURCES = funds
    ISIN_OF = {s.ticker: s.isin for s in SOURCES.values()}
    return note


def no_funds_reason(note: str) -> str:
    """The cell text every table carries when no fund is listed."""
    return note


# A company's display name: issuer-level names first (Vanguard's), then the
# fuller legal names. Sector and currency are borrowed in the PEERS order.
_NAME_RANK = {"vanguard": 0, "ssga": 1, "amundi": 2, "ishares": 3}
_PEER_RANK = {"ssga": 0, "ishares": 1, "amundi": 2}


def name_order() -> list[str]:
    return [s.ticker for s in sorted(SOURCES.values(), key=lambda s: _NAME_RANK.get(s.issuer, 9))]


def peers() -> list[str]:
    return [s.ticker for s in sorted(SOURCES.values(), key=lambda s: _PEER_RANK.get(s.issuer, 9))
            if s.issuer in _PEER_RANK]

# iShares exchange names -> the Bloomberg exchange code a Bloomberg ticker
# carries. Only markets another fund in the portfolio can also hold.
EXCHANGES = {
    "Warsaw Stock Exchange/Equities/Main Market": "PW",
    "Athens Exchange S.A. Cash Market": "GA",
    "Prague Stock Exchange": "CK",
    "Budapest Stock Exchange": "HB",
    "Istanbul Stock Exchange": "TI",
    "London Stock Exchange": "LN",
    "Xetra": "GY",
}

ISIN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
# A fund file's weights, all rows together, must land in this band (% of fund).
# iShares rounds every row to 0.01, so ~3,000 rows lose up to ~1.7pp.
WEIGHT_BAND = (Decimal(97), Decimal(102))
MIN_EQUITY_ROWS = 20


class Refused(Exception):
    """A fund's file is unusable: the reason is printed in its place."""


@dataclass
class Holding:
    name: str
    weight: Decimal  # % of the fund
    equity: bool
    isin: str = ""
    bbg: str = ""  # "PKO PW": ticker and Bloomberg exchange code
    issuer_name: str = ""  # issuer-level name, where the file has one
    country: str = ""  # canonical name (canonical_country); "" when not stated
    sector: str = ""  # GICS sector as the file states it (canonical_sector)
    currency: str = ""  # trading currency of the line, ISO code
    currency_from: str = "file"  # "file" or "exchange" (from the Bloomberg exchange code)
    local: str = ""  # iShares: "<ticker> @ <exchange>", the row's own stable id


@dataclass
class Fund:
    source: Source
    as_of: date
    rows: list[Holding]
    path: Path
    unmatched_exchanges: int = 0  # EIMI rows on an exchange not in EXCHANGES

    @property
    def ticker(self) -> str:
        return self.source.ticker


# --- reading the issuers' formats -------------------------------------------

def _dec(raw: object) -> Decimal | None:
    text = str(raw if raw is not None else "").strip().replace(",", "")
    if text in ("", "-"):
        return None
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


_M = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _col(ref: str) -> int:
    n = 0
    for ch in re.match(r"[A-Z]+", ref).group(0):
        n = n * 26 + ord(ch) - 64
    return n - 1


def xlsx_rows(data: bytes) -> dict[int, list[str]]:
    """First sheet of an xlsx as {row number: cell texts}. Stdlib only.

    Numbers stay as the text the file stores, so a weight is read exactly.
    """
    try:
        z = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise Refused("file is not an xlsx")
    shared: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        for si in ET.fromstring(z.read("xl/sharedStrings.xml")).iter(f"{_M}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{_M}t")))
    sheets = sorted(
        (n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n)),
        key=lambda n: int(re.search(r"(\d+)\.xml$", n).group(1)),
    )
    if not sheets:
        raise Refused("xlsx has no worksheet")
    out: dict[int, list[str]] = {}
    for i, row in enumerate(ET.fromstring(z.read(sheets[0])).iter(f"{_M}row")):
        number = int(row.get("r") or i + 1)
        cells: dict[int, str] = {}
        for j, c in enumerate(row.iter(f"{_M}c")):
            ref = c.get("r")
            col = _col(ref) if ref else j
            kind, v = c.get("t"), c.find(f"{_M}v")
            if kind == "s" and v is not None:
                text = shared[int(v.text)]
            elif kind == "inlineStr":
                text = "".join(t.text or "" for t in c.iter(f"{_M}t"))
            else:
                text = v.text if v is not None and v.text is not None else ""
            cells[col] = text
        if cells:
            out[number] = [cells.get(k, "") for k in range(max(cells) + 1)]
    return out


def _excel_date(text: str) -> date | None:
    for fmt in ("%d-%b-%Y", "%d/%b/%Y", "%Y-%m-%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            pass
    serial = _dec(text)
    if serial is not None and 30000 < serial < 80000:
        return date(1899, 12, 30) + timedelta(days=int(serial))
    return None


def parse_ssga(data: bytes, source: Source) -> tuple[date, list[Holding]]:
    rows = xlsx_rows(data)
    numbers = sorted(rows)
    header_at = next((n for n in numbers if rows[n] and rows[n][0].strip() == "ISIN"), None)
    if header_at is None:
        raise Refused("no holdings header row (ISIN, ... Percent of Fund)")
    # The label rows above the table: "ISIN:", "Holdings As Of:" and so on.
    meta = {rows[n][0].strip().rstrip(":").lower(): (rows[n][1] if len(rows[n]) > 1 else "")
            for n in numbers if n < header_at and rows[n] and rows[n][0].strip().endswith(":")}
    isin = meta.get("isin", "").strip()
    if isin != source.isin:
        raise Refused(f"file is for ISIN {isin or 'none stated'}, not {source.isin}")
    as_of = _excel_date(meta.get("holdings as of", ""))
    if as_of is None:
        raise Refused("no 'Holdings As Of' date in the file")
    header = [h.strip() for h in rows[header_at]]
    try:
        ci, cn, cw = (header.index(h) for h in ("ISIN", "Security Name", "Percent of Fund"))
    except ValueError:
        raise Refused(f"holdings header changed: {header}")
    cc = header.index("Trade Country Name") if "Trade Country Name" in header else None
    cs = header.index("Sector Classification") if "Sector Classification" in header else None
    cu = header.index("Currency") if "Currency" in header else None
    out: list[Holding] = []
    expect = header_at + 1
    for n in numbers:
        if n <= header_at:
            continue
        r = rows[n]
        if n != expect or not r or not r[0].strip():
            break  # the blank row before the disclaimer ends the table
        expect += 1
        cells = r + [""] * (len(header) - len(r))
        code = cells[ci].strip()
        weight = _dec(cells[cw])
        out.append(Holding(
            name=cells[cn].strip(),
            weight=weight if weight is not None else Decimal(0),
            equity=bool(ISIN.match(code)) and weight is not None,
            isin=code if ISIN.match(code) else "",
            country=canonical_country(cells[cc]) if cc is not None else "",
            sector=canonical_sector(cells[cs]) if cs is not None else "",
            currency=canonical_currency(cells[cu]) if cu is not None else "",
        ))
    return as_of, out


def parse_ishares(data: bytes, source: Source) -> tuple[date, list[Holding], int]:
    text = data.decode("utf-8-sig", errors="replace")
    lines = text.splitlines()
    if not lines or not lines[0].startswith("Fund Holdings as of"):
        raise Refused("first line is not 'Fund Holdings as of' (not the English file?)")
    first = next(csv.reader([lines[0]]))
    as_of = _excel_date(first[1] if len(first) > 1 else "")
    if as_of is None:
        raise Refused(f"unreadable as-of date in {lines[0]!r}")
    body = [ln for ln in lines[1:] if ln.strip()]
    reader = csv.reader(body)
    header = next(reader, [])
    try:
        ct, cn, ca, cw, cx = (header.index(h) for h in
                              ("Ticker", "Name", "Asset Class", "Weight (%)", "Exchange"))
    except ValueError:
        raise Refused(f"holdings header changed: {header}")
    cl = header.index("Location") if "Location" in header else None
    cs = header.index("Sector") if "Sector" in header else None
    cu = header.index("Market Currency") if "Market Currency" in header else None
    out: list[Holding] = []
    unmatched = 0
    for r in reader:
        if len(r) <= max(ct, cn, ca, cw, cx):
            continue
        weight = _dec(r[cw])
        equity = r[ca].strip() == "Equity" and weight is not None
        code = EXCHANGES.get(r[cx].strip(), "")
        if equity and not code:
            unmatched += 1
        out.append(Holding(
            name=r[cn].strip(),
            weight=weight if weight is not None else Decimal(0),
            equity=equity,
            bbg=f"{r[ct].strip()} {code}" if code and r[ct].strip() else "",
            country=canonical_country(r[cl]) if cl is not None and len(r) > cl else "",
            sector=canonical_sector(r[cs]) if cs is not None and len(r) > cs else "",
            currency=canonical_currency(r[cu]) if cu is not None and len(r) > cu else "",
            local=f"{r[ct].strip()} @ {r[cx].strip()}" if r[ct].strip() else "",
        ))
    return as_of, out, unmatched


def parse_vanguard(data: bytes, source: Source) -> tuple[date, list[Holding]]:
    try:
        payload = json.loads(data)
        block = payload["data"]["borHoldings"][0]["holdings"]
        items = block["items"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise Refused("response is not the holdings JSON (data.borHoldings[0].holdings)")
    if block.get("lastItemKey"):
        raise Refused("response is one page of several (lastItemKey set); limit too low")
    if block.get("totalHoldings") is not None and block["totalHoldings"] != len(items):
        raise Refused(f"{len(items)} rows against totalHoldings {block['totalHoldings']}")
    dates = {i.get("effectiveDate") for i in items if i.get("effectiveDate")}
    if len(dates) != 1:
        raise Refused(f"rows carry {len(dates)} effective dates, not one: {sorted(dates)[:3]}")
    as_of = date.fromisoformat(dates.pop())
    out = []
    for i in items:
        weight = _dec(i.get("marketValuePercentage"))
        code = (i.get("isin") or "").strip()
        out.append(Holding(
            name=(i.get("securityLongDescription") or "").strip(),
            weight=weight if weight is not None else Decimal(0),
            equity=str(i.get("securityType", "")) in ("EQ.STOCK", "EQ.REIT")
            and bool(ISIN.match(code)) and weight is not None,
            isin=code if ISIN.match(code) else "",
            issuer_name=(i.get("issuerName") or "").strip(),
            country=canonical_country(i.get("bloombergIsoCountry")),
        ))
    return as_of, out


def parse_amundi(data: bytes, source: Source) -> tuple[date, list[Holding]]:
    try:
        product = json.loads(data)["products"][0]
        rows = product["composition"]["compositionData"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise Refused("response is not the product JSON (products[0].composition)")
    if product.get("productId") != source.isin:
        raise Refused(f"response is for {product.get('productId')}, not {source.isin}")
    total = product["composition"].get("totalNumberOfInstruments")
    if total is not None and total != len(rows):
        raise Refused(f"{len(rows)} rows against totalNumberOfInstruments {total}")
    chars = [r.get("compositionCharacteristics") or {} for r in rows]
    dates = {c.get("date") for c in chars if c.get("date")}
    if len(dates) != 1:
        raise Refused(f"rows carry {len(dates)} dates, not one")
    as_of = date.fromisoformat(dates.pop())
    out = []
    for c in chars:
        fraction = _dec(c.get("weight"))
        code = (c.get("isin") or "").strip()
        out.append(Holding(
            name=(c.get("name") or "").strip(),
            weight=fraction * HUNDRED if fraction is not None else Decimal(0),
            equity=c.get("type") in ("EQUITY_ORDINARY", "PREFERENCE_SHARES")
            and bool(ISIN.match(code)) and fraction is not None,
            isin=code if ISIN.match(code) else "",
            bbg=(c.get("bbg") or "").strip(),
            country=canonical_country(c.get("countryOfRisk")),
            sector=canonical_sector(c.get("sector")),
            currency=canonical_currency(c.get("currency")) or exchange_currency(c.get("bbg")),
            currency_from="file" if canonical_currency(c.get("currency")) else "exchange",
        ))
    return as_of, out


def load_fund(source: Source, path: Path) -> Fund:
    data = path.read_bytes()
    unmatched = 0
    if source.issuer == "ssga":
        as_of, rows = parse_ssga(data, source)
    elif source.issuer == "ishares":
        as_of, rows, unmatched = parse_ishares(data, source)
    elif source.issuer == "vanguard":
        as_of, rows = parse_vanguard(data, source)
    elif source.issuer == "amundi":
        as_of, rows = parse_amundi(data, source)
    else:
        raise Refused(f"no reader for issuer {source.issuer}")
    equity = [r for r in rows if r.equity]
    if len(equity) < MIN_EQUITY_ROWS:
        raise Refused(f"{len(equity)} equity rows; a full holdings file has hundreds")
    total = sum((r.weight for r in rows), Decimal(0))
    if not WEIGHT_BAND[0] <= total <= WEIGHT_BAND[1]:
        raise Refused(f"weights sum to {total:.2f}, outside {WEIGHT_BAND[0]}-{WEIGHT_BAND[1]}")
    return Fund(source, as_of, rows, path, unmatched)


def latest_file(holdings_dir: Path, ticker: str) -> Path | None:
    files = sorted(holdings_dir.glob(f"{ticker}-????-??-??.*"))
    return files[-1] if files else None


# --- fetching ---------------------------------------------------------------

def fetch(source: Source, timeout: float = 60) -> bytes:
    body = json.dumps(source.body).encode() if source.body is not None else None
    headers = {"User-Agent": UA, "Accept": "*/*", **dict(source.headers)}
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(source.url, data=body, method=source.method, headers=headers)
    host = urlparse(source.url).hostname
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise Refused(f"{host} returned {exc.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        raise Refused(f"{host} not reached from this shell ({reason}); "
                      "it may need adding to the allowed domains")


def cmd_fetch(holdings_dir: Path, today: date, only: set[str] | None = None) -> int:
    holdings_dir.mkdir(parents=True, exist_ok=True)
    failed = 0
    for source in SOURCES.values():
        if only and source.ticker not in only:
            continue
        path = holdings_dir / f"{source.ticker}-{today.isoformat()}.{source.ext}"
        try:
            data = fetch(source)
            path.write_bytes(data)
            fund = load_fund(source, path)
        except Refused as exc:
            failed += 1
            print(f"{source.ticker}: Not available - {exc}")
            continue
        equity = sum(1 for r in fund.rows if r.equity)
        print(f"{source.ticker}: {path.as_posix()} - {len(fund.rows)} rows, "
              f"{equity} equity, as of {fund.as_of}")
    return 1 if failed and only is None and failed == len(SOURCES) else 0


# --- countries --------------------------------------------------------------

# Each issuer's own country field, aligned on one spelling. The fields do not
# measure the same thing: SSGA gives the country a security trades in,
# Amundi and iShares a country of risk / location, Vanguard a Bloomberg ISO
# code. METHOD says so. A spelling not listed here is kept as written.
COUNTRY_ALIASES = {
    "korea (south)": "South Korea", "korea": "South Korea", "korea, republic of": "South Korea",
    "uae": "United Arab Emirates", "russian federation": "Russia",
    "usa": "United States", "united states of america": "United States",
    "uk": "United Kingdom", "great britain": "United Kingdom",
    "czechia": "Czech Republic", "turkiye": "Turkey", "türkiye": "Turkey",
}
# Bloomberg ISO country codes (Vanguard's field). XE is the euro area, not a
# country, and only marks currency rows.
ISO_COUNTRIES = {
    "US": "United States", "GB": "United Kingdom", "CA": "Canada", "IE": "Ireland",
    "NL": "Netherlands", "CH": "Switzerland", "DE": "Germany", "FR": "France",
    "JP": "Japan", "BM": "Bermuda", "JE": "Jersey", "PR": "Puerto Rico",
    "LR": "Liberia", "PA": "Panama", "IL": "Israel", "SG": "Singapore",
    "HK": "Hong Kong", "CN": "China", "TW": "Taiwan", "KR": "South Korea",
    "IN": "India", "BR": "Brazil", "MX": "Mexico", "AU": "Australia",
}
_NO_COUNTRY = {"", "-", "none", "n/a", "european union", "xe"}


def canonical_country(raw: object) -> str:
    text = str(raw if raw is not None else "").strip()
    if text.lower() in _NO_COUNTRY:
        return ""
    if len(text) == 2 and text.isupper():
        return ISO_COUNTRIES.get(text, text)
    return COUNTRY_ALIASES.get(text.lower(), text)


NOT_STATED = "Country not stated"
CASH = "Cash and other"


# --- sectors and currencies -------------------------------------------------

# GICS sector names as SSGA prints them. iShares shortens one.
SECTOR_ALIASES = {"communication": "Communication Services"}
_NO_SECTOR = {"", "-", "unassigned", "cash and/or derivatives", "n/a", "other"}
NO_SECTOR = "Sector not stated"


def canonical_sector(raw: object) -> str:
    text = str(raw if raw is not None else "").strip()
    if text.lower() in _NO_SECTOR:
        return ""
    return SECTOR_ALIASES.get(text.lower(), text)


# Pence and offshore quotes fold into their currency; CNH stays apart from CNY
# because they are two traded currencies, not two spellings.
CURRENCY_ALIASES = {"GBX": "GBP", "GBp": "GBP", "ZAC": "ZAR", "ILA": "ILS"}
NO_CURRENCY = "Currency not stated"


def canonical_currency(raw: object) -> str:
    text = str(raw if raw is not None else "").strip()
    if text in CURRENCY_ALIASES:
        return CURRENCY_ALIASES[text]
    text = text.upper()
    return text if re.fullmatch(r"[A-Z]{3}", text) else ""


# The currency each Bloomberg exchange code trades in, for Amundi's rows,
# whose file carries the exchange but no currency. Only the codes MEUD's
# file used on 2026-10-10; an unlisted code leaves the currency not stated.
EXCHANGE_CURRENCY = {
    "LN": "GBP", "SE": "CHF", "SW": "CHF", "SS": "SEK", "DC": "DKK", "NO": "NOK",
    "PW": "PLN", "FP": "EUR", "GY": "EUR", "GR": "EUR", "NA": "EUR", "SM": "EUR",
    "IM": "EUR", "FH": "EUR", "BB": "EUR", "ID": "EUR", "AV": "EUR", "GA": "EUR",
    "PL": "EUR",
}


def exchange_currency(bbg: object) -> str:
    parts = str(bbg or "").split()
    return EXCHANGE_CURRENCY.get(parts[-1], "") if len(parts) == 2 else ""


def fund_countries(fund: Fund) -> dict[str, Decimal]:
    """% of the fund per country (equity rows); non-equity rows are CASH."""
    out: dict[str, Decimal] = {}
    for r in fund.rows:
        key = (r.country or NOT_STATED) if r.equity else CASH
        out[key] = out.get(key, Decimal(0)) + r.weight
    return out


def country_of(key: str, funds: list[Fund]) -> tuple[str, str]:
    """The country the fund files give a directly held company, and which file."""
    for fund in funds:
        for r in fund.rows:
            if r.equity and r.isin and r.country and company_key(r.isin) == key:
                return r.country, fund.ticker
    return "", ""


def bucket_table(column: str, other: str, not_stated: str, order: list[str],
                 split: dict[str, dict[str, Decimal]], fund_weights: dict[str, Decimal],
                 direct: dict[str, Decimal], min_total: Decimal) -> tuple[list[str], dict]:
    """One row per bucket (country, sector, currency): Direct, via each fund, Total.

    A via cell is fund weight x the fund's % in that bucket / 100, to 0.01.
    Buckets whose Total is under ``min_total`` fold into one Other row, and
    each of its cells is the sum of the printed cells it replaced, so every
    column and every row re-adds; the Total row is the column sums.
    """
    names = set(direct)
    for t in order:
        names |= split[t].keys()
    cells: dict[str, list[Decimal | None]] = {}
    for c in names:
        row: list[Decimal | None] = [_q(direct[c]) if c in direct else None]
        for t in order:
            w = split[t].get(c)
            row.append(_q(fund_weights[t] * w / HUNDRED) if w is not None else None)
        cells[c] = row

    def total(row):
        return sum((x for x in row if x is not None), Decimal(0))

    tail = {CASH, not_stated}
    ranked = sorted((c for c in cells if c not in tail), key=lambda c: (-total(cells[c]), c))
    shown = [c for c in ranked if total(cells[c]) >= min_total]
    folded = [c for c in ranked if c not in shown]
    printed: list[tuple[str, list[Decimal | None]]] = [(c, cells[c]) for c in shown]
    if folded:
        width = len(order) + 1
        rest: list[Decimal | None] = [None] * width
        for c in folded:
            for i, x in enumerate(cells[c]):
                if x is not None:
                    rest[i] = (rest[i] or Decimal(0)) + x
        printed.append((f"{other} ({len(folded)})", rest))
    for c in (not_stated, CASH):
        if c in cells and total(cells[c]) != 0:
            printed.append((c, cells[c]))
    cols = len(order) + 1
    sums = [sum((row[i] or Decimal(0) for _, row in printed), Decimal(0)) for i in range(cols)]
    lines = [
        f"| {column} | Direct | " + " | ".join(f"via {t}" for t in order) + " | Total |",
        "|---|---|" + "---|" * len(order) + "---|",
    ]
    for name, row in printed:
        lines.append(f"| {name} | " + " | ".join("-" if x is None else f"{x:.2f}" for x in row)
                     + f" | {total(row):.2f} |")
    lines.append("| Total | " + " | ".join(f"{x:.2f}" for x in sums)
                 + f" | {sum(sums, Decimal(0)):.2f} |")
    stats = {"shown": len(shown), "folded": len(folded), "buckets": len(ranked),
             "countries": len(ranked), "sum": sum(sums, Decimal(0)), "split": split}
    return lines, stats


# Funds whose own file states sector and currency are peers(): SSGA, then
# iShares, then Amundi. Vanguard's file states neither, so its companies
# always borrow; an Amundi row borrows only where its own file is blank.


def peer_values(funds: dict[str, Fund], attr: str) -> dict[str, tuple[str, str]]:
    """Company key -> (value, ticker), from the first PEERS file stating it.

    Only values a file states itself: a currency Amundi's rows take from an
    exchange code is not lent to another fund.
    """
    pool = list(funds.values())
    by_bbg = bbg_keys(pool)
    out: dict[str, tuple[str, str]] = {}
    for t in peers():
        fund = funds.get(t)
        if fund is None:
            continue
        for r in fund.rows:
            value = getattr(r, attr)
            if r.equity and value and (attr != "currency" or r.currency_from == "file"):
                out.setdefault(row_key(fund, r, by_bbg), (value, t))
    return out


def fund_split(fund: Fund, attr: str, peers: dict[str, tuple[str, str]],
               by_bbg: dict[str, str], not_stated: str) -> tuple[dict[str, Decimal], dict[str, Decimal]]:
    """% of the fund per sector or currency, and the weight behind each basis.

    A row uses its own file's value; else the same company's value in a PEERS
    file; else ``not_stated``. Non-equity rows are CASH. The basis tally
    (file, exchange, borrowed, none) is equity weight, for METHOD.
    """
    split: dict[str, Decimal] = {}
    basis = {"file": Decimal(0), "exchange": Decimal(0), "borrowed": Decimal(0), "none": Decimal(0)}
    for r in fund.rows:
        if not r.equity:
            split[CASH] = split.get(CASH, Decimal(0)) + r.weight
            continue
        value = getattr(r, attr)
        how = (r.currency_from if attr == "currency" else "file") if value else ""
        if not value:
            found = peers.get(row_key(fund, r, by_bbg))
            if found and found[1] != fund.ticker:
                value, how = found[0], "borrowed"
        if not value:
            value, how = not_stated, "none"
        split[value] = split.get(value, Decimal(0)) + r.weight
        basis[how] += r.weight
    return split, basis


def countries_table(order: list[str], funds: dict[str, Fund],
                    fund_weights: dict[str, Decimal], direct: dict[str, Decimal],
                    min_total: Decimal) -> tuple[list[str], dict]:
    split = {t: fund_countries(funds[t]) for t in order}
    return bucket_table("Country", "Other countries", NOT_STATED, order, split,
                        fund_weights, direct, min_total)


# --- matching ---------------------------------------------------------------

def company_key(isin: str) -> str:
    """One key per issuer: US/CA ISINs carry the CUSIP, whose first six
    characters are the issuer; elsewhere the ISIN is the security."""
    if isin[:2] in ("US", "CA"):
        return f"cusip:{isin[2:8]}"
    return f"isin:{isin}"


_CLASS = re.compile(
    r"[\s,-]+(class|cl|series|ser)\.?\s+[a-z0-9]{1,2}$|\s+(non[\s-]?voting.*|pref.*|adr)$",
    re.IGNORECASE,
)


def display_name(name: str) -> str:
    return _CLASS.sub("", name).strip()


# Legal-form words only. "Holdings" and "Group" stay: PSK Inc and PSK Holdings
# are two companies, as are Youngone and Youngone Holdings (EIMI, 2026-10-10).
_SUFFIX = re.compile(r"\b(ltd|limited|inc|corp|corporation|co|company|sa|plc|ag|nv|"
                     r"bhd|tbk|pcl|jsc|ord|shs)\b\.?", re.IGNORECASE)


def name_key(name: str) -> str:
    """A file's own rows for one issuer under one key when it has no ISIN:
    'SAMSUNG ELECTRONICS LTD' and 'SAMSUNG ELECTRONICS NON VOTING PRE'."""
    text = _SUFFIX.sub(" ", display_name(name))
    return " ".join(re.sub(r"[^A-Za-z0-9 ]", " ", text).upper().split())


@dataclass
class Exposure:
    """A fund's weight in each company, share classes summed."""
    weights: dict[str, Decimal] = field(default_factory=dict)
    names: dict[str, str] = field(default_factory=dict)
    issuer_names: dict[str, str] = field(default_factory=dict)


def bbg_keys(funds: list[Fund]) -> dict[str, str]:
    """Bloomberg ticker -> company key, from every row that carries both."""
    by_bbg: dict[str, str] = {}
    for fund in funds:
        for r in fund.rows:
            if r.equity and r.isin and r.bbg:
                by_bbg.setdefault(r.bbg, company_key(r.isin))
    return by_bbg


def row_key(fund: Fund, r: Holding, by_bbg: dict[str, str]) -> str:
    """The company a row belongs to, across funds (exposures' matching)."""
    if r.isin:
        return company_key(r.isin)
    if r.bbg and r.bbg in by_bbg:
        return by_bbg[r.bbg]
    if r.bbg:
        return f"bbg:{r.bbg}"
    return f"name:{fund.ticker}:{name_key(r.name)}"


def exposures(funds: list[Fund]) -> dict[str, Exposure]:
    by_bbg = bbg_keys(funds)
    out: dict[str, Exposure] = {}
    for fund in funds:
        exp = Exposure()
        for r in fund.rows:
            if not r.equity or r.weight == 0:
                continue
            key = row_key(fund, r, by_bbg)
            exp.weights[key] = exp.weights.get(key, Decimal(0)) + r.weight
            exp.names.setdefault(key, display_name(r.name))
            if r.issuer_name:
                exp.issuer_names.setdefault(key, r.issuer_name)
        out[fund.ticker] = exp
    return out


def name_for(key: str, exps: dict[str, Exposure], order: list[str]) -> str:
    for t in order:
        if t in exps and key in exps[t].issuer_names:
            return exps[t].issuer_names[key]
    for t in order:
        if t in exps and key in exps[t].names:
            return exps[t].names[key]
    return key.split(":", 1)[-1]


# --- tables -----------------------------------------------------------------

def _q(value: Decimal) -> Decimal:
    # Half up, as market_weights rounds: the two tables share their weights.
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _cell(value: Decimal) -> str:
    return f"{_q(value):.2f}"


def holdings_table(order: list[str], funds: dict[str, Fund], refused: dict[str, str],
                   exps: dict[str, Exposure], name_order: list[str]) -> list[str]:
    lines = ["| Pair | Shared names | Shared weight |", "|---|---|---|"]
    if len(order) == 1:
        # One fund has no pair; an empty table would read as a failure.
        lines.append(f"| {order[0]} alone | none - overlap needs two funds | 0 |")
        return lines
    for i, a in enumerate(order):
        for b in order[i + 1:]:
            pair = f"{a} - {b}"
            missing = [t for t in (a, b) if t not in funds]
            if missing:
                why = "; ".join(f"{t}: {refused.get(t, 'no file')}" for t in missing)
                lines.append(f"| {pair} | Not available - {why} | Not available |")
                continue
            wa, wb = exps[a].weights, exps[b].weights
            shared = {k: min(wa[k], wb[k]) for k in wa.keys() & wb.keys()}
            if not shared:
                lines.append(f"| {pair} | 0 | 0 |")
                continue
            top = sorted(shared, key=lambda k: (-shared[k], k))[:5]
            names = ", ".join(name_for(k, exps, name_order) for k in top)
            more = ", ..." if len(shared) > 5 else ""
            lines.append(
                f"| {pair} | {len(shared)} (largest: {names}{more}) | "
                f"{_cell(sum(shared.values(), Decimal(0)))} |"
            )
    return lines


def lookthrough_table(order: list[str], exps: dict[str, Exposure],
                      fund_weights: dict[str, Decimal], direct: dict[str, Decimal],
                      direct_names: dict[str, str], top: int,
                      name_order: list[str]) -> tuple[list[str], dict]:
    """One row per company: Direct, via each fund, Total.

    Each via cell is fund weight x company weight in the fund / 100, to the
    cent; Total is the sum of the printed cells, so every row re-adds.
    """
    exps = {t: exps.get(t, Exposure()) for t in order}
    keys = set(direct)
    for t in order:
        keys |= exps[t].weights.keys()
    rows = {}
    for k in keys:
        cells = []
        d = direct.get(k)
        cells.append(_q(d) if d is not None else None)
        for t in order:
            w = exps[t].weights.get(k)
            cells.append(_q(fund_weights[t] * w / HUNDRED) if w is not None else None)
        total = sum((c for c in cells if c is not None), Decimal(0))
        rows[k] = (cells, total)
    held = sorted((k for k in direct), key=lambda k: (-rows[k][1], k))
    others = sorted((k for k in rows if k not in direct and rows[k][1] > 0),
                    key=lambda k: (-rows[k][1], k))[:top]
    lines = [
        "| Company | Direct | " + " | ".join(f"via {t}" for t in order) + " | Total |",
        "|---|---|" + "---|" * len(order) + "---|",
    ]
    def name(k: str) -> str:
        if k in direct and not any(k in exps[t].weights for t in order):
            return direct_names.get(k) or name_for(k, exps, name_order)
        return name_for(k, exps, name_order)

    for k in held + others:
        cells, total = rows[k]
        lines.append(
            f"| {name(k)} | " + " | ".join("-" if c is None else f"{c:.2f}" for c in cells)
            + f" | {total:.2f} |"
        )
    printed = sum((rows[k][1] for k in held + others), Decimal(0))
    everything = sum((r[1] for r in rows.values()), Decimal(0))
    labels = ["Direct"] + [f"via {t}" for t in order]
    # Every company the cells reach, printed or not, in Look-through's own
    # labels and cells: what Hidden bets reads, so it never depends on --top.
    reached = [(name(k), list(zip(labels, rows[k][0])), rows[k][1])
               for k in rows if len([c for c in rows[k][0] if c]) >= 2]
    stats = {"companies": len(rows), "printed": printed, "everything": everything,
             "shown": len(held) + len(others), "reached": reached}
    return lines, stats


# --- hidden bets -------------------------------------------------------------

# A company counts when the portfolio reaches it through two or more holdings
# and its Look-through Total is at least this, in % of the portfolio.
HIDDEN_MIN = Decimal("1.00")
HIDDEN_HEADER = ["Company", "Through", "Largest part", "Total", "Added by the others"]


def hidden_bets(reached: list[tuple[str, list[tuple[str, Decimal | None]], Decimal]],
                minimum: Decimal = HIDDEN_MIN) -> list[tuple[str, list[tuple[str, Decimal]], Decimal]]:
    """Companies reached through 2+ holdings with a Total of `minimum` or more.

    `reached` is Look-through's rows: (company, [(label, cell or None)], Total),
    Total being the sum of the cells. Largest Total first.
    """
    out = []
    for name, parts, total in reached:
        through = [(label, c) for label, c in parts if c is not None and c > 0]
        if len(through) >= 2 and total >= minimum:
            out.append((name, through, total))
    out.sort(key=lambda r: (-r[2], r[0]))
    return out


def hidden_bets_table(bets: list[tuple[str, list[tuple[str, Decimal]], Decimal]],
                      minimum: Decimal = HIDDEN_MIN) -> list[str]:
    """One row per company: each route with its cell, the largest one, the
    Total, and what the other routes add to the largest. Total = the sum of the
    routes, as in Look-through, so every row re-adds both ways."""
    lines = ["| " + " | ".join(HIDDEN_HEADER) + " |", "|" + "---|" * len(HIDDEN_HEADER)]
    if not bets:
        lines.append(f"| none | no company reaches {minimum:.2f} through two or more holdings "
                     "| - | 0 | 0 |")
        return lines
    for name, through, total in bets:
        label, largest = max(through, key=lambda p: (p[1], p[0] == "Direct"))
        lines.append(
            f"| {name} | " + " · ".join(f"{lab} {c:.2f}" for lab, c in through)
            + f" | {label} {largest:.2f} | {total:.2f} | {total - largest:.2f} |"
        )
    return lines


def hidden_bets_method(bets: list, minimum: Decimal = HIDDEN_MIN) -> str:
    together = sum((b[2] for b in bets), Decimal(0))
    return (f"Hidden bets: companies with a Look-through Total of {minimum:.2f} or more reached "
            "through two or more holdings (a direct stock or a fund); Largest part = the "
            "largest single cell, which is all a single holding shows; Added by the others = "
            f"Total - Largest part; {len(bets)} {'company' if len(bets) == 1 else 'companies'}, "
            f"{together:.2f} of the "
            "portfolio together")


def parse_lookthrough(lines: list[str]) -> tuple[list[tuple[str, list[tuple[str, Decimal | None]], Decimal]], Decimal | None]:
    """A printed Look-through table back into rows, and its completeness floor.

    The table prints every direct stock, then the largest others by Total, so
    any company it leaves out has a Total no larger than the smallest printed
    fund-only row: that Total is returned as the floor (None when nothing
    fund-only printed). Hidden bets read this way are complete only for a
    minimum above the floor.
    """
    table = [ln for ln in lines if ln.startswith("|")]
    if len(table) < 2:
        return [], None
    header = [c.strip() for c in table[0].strip("|").split("|")]
    if header[0] != "Company" or header[-1] != "Total":
        return [], None
    rows, floor = [], None
    for ln in table[2:]:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if len(cells) != len(header):
            continue
        try:
            total = Decimal(cells[-1])
            values = [None if c == "-" else Decimal(c) for c in cells[1:-1]]
        except InvalidOperation:
            continue
        parts = list(zip(header[1:-1], values))
        rows.append((cells[0], parts, total))
        if dict(parts).get("Direct") is None:
            floor = total if floor is None else min(floor, total)
    return rows, floor


# --- market weights ---------------------------------------------------------

def market_weights(prices_path: Path, data_dir: Path, pies_path: Path,
                   ownership_path: Path, holdings_path: Path | None = None,
                   ) -> tuple[dict[str, Decimal], dict[str, str], dict[str, str], date]:
    """Weight (market) per ISIN, exactly as the Allocation table prints it.

    Returns (weights, tickers by ISIN, kinds by ISIN -- "stock" or "fund" --,
    as-of). Quantities come from holdings.csv when it exists, else from the
    Trading 212 exports, as in market_weights.main. Raises Refused with the
    Allocation table's own reason when a weight cannot be printed.
    """
    import market_weights as mw
    import t212_holdings as t

    try:
        spec = json.loads(prices_path.read_text(encoding="utf-8"))
        as_of = date.fromisoformat(spec["as_of"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise Refused(f"{prices_path}: {exc}")
    try:
        if holdings_path is not None and holdings_path.exists():
            rows, _targets, _snapshot, _source = mw.csv_rows(holdings_path)
            last_trade = None
        else:
            rows, _pies, last_trade = mw.holdings_rows(data_dir, pies_path, ownership_path)
    except (mw.Refused, t.Halt) as exc:
        raise Refused(str(exc))
    if last_trade is not None and as_of < last_trade:
        raise Refused(f"as-of {as_of} precedes the last trade in the exports ({last_trade})")
    priced = mw.price_rows(rows, as_of, spec.get("prices", {}), spec.get("fx", {}))
    missing = [f"{p.row.ticker} ({p.reason})" for p in priced if p.value is None]
    if missing:
        raise Refused("Allocation weights Not available - " + "; ".join(missing))
    total = sum((p.value for p in priced), Decimal(0))
    if total == 0:
        raise Refused("portfolio value is zero")
    weights = {p.row.isin: mw._q(p.value / total * 100) for p in priced}
    return (weights, {p.row.isin: p.row.ticker for p in priced},
            {p.row.isin: "stock" if p.row.is_stock else "fund" for p in priced}, as_of)


# --- report -----------------------------------------------------------------

# What each issuer's file says, for METHOD. Only the issuers of the funds in
# this run are named, under the user's own tickers.
ISSUER_NAME = {"ssga": "SSGA", "amundi": "Amundi", "ishares": "iShares", "vanguard": "Vanguard"}
COUNTRY_FIELD = {"ssga": "the country a security trades in", "amundi": "country of risk",
                 "ishares": "location", "vanguard": "Bloomberg ISO country"}
CURRENCY_FIELD = {"ssga": "Currency", "amundi": "currency", "ishares": "Market Currency"}


def _who(issuer: str, order: list[str]) -> str:
    tickers = [t for t in order if SOURCES[ISIN_OF[t]].issuer == issuer]
    return f"{ISSUER_NAME[issuer]} ({', '.join(tickers)})"


def _issuers(order: list[str]) -> list[str]:
    seen: list[str] = []
    for t in order:
        i = SOURCES[ISIN_OF[t]].issuer
        if i not in seen:
            seen.append(i)
    return seen


def _and(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def countries_basis(order: list[str]) -> str:
    fields = [f"{_who(i, order)} {COUNTRY_FIELD[i]}" for i in _issuers(order)]
    return ("Countries basis: each issuer's own country field - " + ", ".join(fields)
            + "; spellings aligned (Korea (South) and Korea -> South Korea, UAE -> United "
            f"Arab Emirates, ISO codes -> names); non-equity rows (cash, FX, futures) are '{CASH}'")


def sectors_basis(order: list[str]) -> str:
    issuers = _issuers(order)
    stating = [_who(i, order) for i in issuers if i != "vanguard"]
    parts = []
    if stating:
        parts.append(f"the sector {_and(stating)} state{'s' if len(stating) == 1 else ''} per row")
    if "ishares" in issuers:
        parts.append("iShares' 'Communication' read as Communication Services")
    borrow = []
    if "vanguard" in issuers:
        borrow.append(f"{_who('vanguard', order)}'s file carries none, so its companies")
    if "amundi" in issuers:
        borrow.append("any Amundi row its file leaves blank")
    if borrow:
        parts.append(" - and ".join(borrow) + " - take the sector another fund's file gives "
                     "the same company, by ISIN issuer or Bloomberg ticker")
    return "Sectors basis: " + "; ".join(parts)


def currencies_basis(order: list[str]) -> str:
    issuers = _issuers(order)
    stated = [f"{ISSUER_NAME[i]}'s {CURRENCY_FIELD[i]}" for i in issuers if i in CURRENCY_FIELD]
    parts = []
    if stated:
        parts.append("the currency each line trades in - " + _and(stated) + " as stated")
    if "amundi" in issuers:
        parts.append(f"an {_who('amundi', order)} row with none takes its Bloomberg exchange "
                     "code's currency (LN GBP, SE CHF, SS SEK, DC DKK, NO NOK, PW PLN, "
                     "euro-area codes EUR)")
    if "vanguard" in issuers:
        parts.append(f"{_who('vanguard', order)}'s taken from the same company in another "
                     "fund's file")
    return ("Currencies basis: " + "; ".join(parts)
            + ". A trading currency, not where a company earns its revenue")

def report_no_funds(note: str) -> int:
    """A stocks-only or not-yet-set-up user: nothing to look through, not an error."""
    why = no_funds_reason(note)
    print("Holdings")
    print("| Pair | Shared names | Shared weight |\n|---|---|---|")
    print(f"| none | none - {why} | 0 |")
    print()
    for title, column in (("Look-through", "Company"), ("Hidden bets", "Company"),
                          ("Countries", "Country"),
                          ("Sectors", "Sector"), ("Currencies", "Currency")):
        print(title)
        print(f"| {column} | Total |\n|---|---|")
        print(f"| all | none - {why}; direct stocks are in Allocation |")
        print()
    print("METHOD")
    print(f"Funds list: {note}")
    print()
    print("PROOF")
    print("No fund file read.")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    if not SOURCES:
        return report_no_funds(getattr(args, "funds_note", "") or "none")
    order = [s.ticker for s in SOURCES.values()]
    funds: dict[str, Fund] = {}
    refused: dict[str, str] = {}
    for source in SOURCES.values():
        path = latest_file(args.holdings_dir, source.ticker)
        if path is None:
            refused[source.ticker] = f"no file in {args.holdings_dir.as_posix()} (the Fund holdings Action fetches it - run it once from your repo's Actions tab)"
            continue
        try:
            funds[source.ticker] = load_fund(source, path)
        except Refused as exc:
            refused[source.ticker] = f"{path.name}: {exc}"

    # Allocation's weights decide the fund order (largest first) when present.
    weights: dict[str, Decimal] = {}
    tickers: dict[str, str] = {}
    pies: dict[str, str] = {}
    lt_reason = ""
    as_of = None
    if args.prices is None:
        lt_reason = "no --prices file, so no market weights"
    else:
        try:
            weights, tickers, pies, as_of = market_weights(
                args.prices, args.data_dir, args.pies, args.ownership,
                getattr(args, "holdings", None))
        except Refused as exc:
            lt_reason = str(exc)
    if weights:
        by_ticker = {s.ticker: weights.get(isin, Decimal(0)) for isin, s in SOURCES.items()}
        order.sort(key=lambda t: (-by_ticker[t], t))
    name_order_ = name_order()
    exps = exposures(list(funds.values()))

    dated = ", ".join(f"{t} {funds[t].as_of}" for t in order if t in funds)
    depth = f"full issuer files, as of {dated}" if funds else "no issuer file read"
    if refused and funds:
        depth += "; not every fund read"
    print(f"Holdings ({depth})")
    print("\n".join(holdings_table(order, funds, refused, exps, name_order_)))
    print()

    stats = None
    if not lt_reason:
        unpriced = [isin for isin, kind in pies.items()
                    if isin not in SOURCES and kind.lower() != "stock" and weights.get(isin)]
        missing = [t for t in order if t not in funds and weights.get(ISIN_OF[t], Decimal(0)) > 0]
        if unpriced:
            lt_reason = "no holdings source for " + ", ".join(tickers[i] for i in unpriced)
        elif missing:
            lt_reason = "holdings Not available for " + "; ".join(
                f"{t} ({refused[t]})" for t in missing)
    if lt_reason:
        print("Look-through")
        print("| Company | Total |\n|---|---|")
        print(f"| all | Not available - {lt_reason} |")
    else:
        fund_weights = {s.ticker: weights[isin] for isin, s in SOURCES.items()}
        direct = {}
        direct_names = {}
        for isin, kind in pies.items():
            if kind.lower() == "stock" and isin not in SOURCES:
                k = company_key(isin)
                direct[k] = direct.get(k, Decimal(0)) + weights[isin]
                direct_names[k] = tickers[isin]
        lines, stats = lookthrough_table(order, exps, fund_weights, direct, direct_names,
                                         args.top, name_order_)
        print(f"Look-through (market weights, as of {as_of})")
        print("\n".join(lines))
    print()

    bets = None
    if lt_reason:
        print("Hidden bets")
        print("| Company | Total |\n|---|---|")
        print(f"| all | Not available - {lt_reason} |")
    else:
        bets = hidden_bets(stats["reached"])
        print(f"Hidden bets (market weights, as of {as_of})")
        print("\n".join(hidden_bets_table(bets)))
    print()

    cstats = None
    direct_country: dict[str, str] = {}
    if lt_reason:
        print("Countries")
        print("| Country | Total |\n|---|---|")
        print(f"| all | Not available - {lt_reason} |")
    else:
        by_country: dict[str, Decimal] = {}
        fund_list = [funds[t] for t in name_order_ if t in funds]
        for k, w in direct.items():
            c, src = country_of(k, fund_list)
            direct_country[direct_names[k]] = f"{c or NOT_STATED}" + (f" (from {src})" if src else "")
            c = c or NOT_STATED
            by_country[c] = by_country.get(c, Decimal(0)) + w
        clines, cstats = countries_table(order, funds, fund_weights, by_country, args.min_country)
        print(f"Countries (market weights, as of {as_of})")
        print("\n".join(clines))
    print()

    bstats: dict[str, tuple[dict, dict]] = {}
    for title, column, other, missing, attr, minimum in (
            ("Sectors", "Sector", "Other sectors", NO_SECTOR, "sector", Decimal(0)),
            ("Currencies", "Currency", "Other currencies", NO_CURRENCY, "currency",
             args.min_currency)):
        if lt_reason:
            print(title)
            print(f"| {column} | Total |\n|---|---|")
            print(f"| all | Not available - {lt_reason} |")
            print()
            continue
        peers = peer_values(funds, attr)
        by_bbg = bbg_keys(list(funds.values()))
        split, basis = {}, {}
        for t in order:
            split[t], basis[t] = fund_split(funds[t], attr, peers, by_bbg, missing)
        direct_b: dict[str, Decimal] = {}
        direct_src: dict[str, str] = {}
        for k, w in direct.items():
            value, src = peers.get(k, ("", ""))
            direct_src[direct_names[k]] = (value or missing) + (f" (from {src})" if src else "")
            direct_b[value or missing] = direct_b.get(value or missing, Decimal(0)) + w
        blines, bst = bucket_table(column, other, missing, order, split, fund_weights,
                                   direct_b, minimum)
        bstats[title] = (bst, {"basis": basis, "direct": direct_src})
        print(f"{title} (market weights, as of {as_of})")
        print("\n".join(blines))
        print()

    print("METHOD")
    if getattr(args, "funds_note", ""):
        print(f"Funds list: {args.funds_note}")
    for t in order:
        if t in funds:
            f = funds[t]
            eq = sum(1 for r in f.rows if r.equity)
            print(f"Holdings file {t}: {f.path.as_posix()}, {f.source.issuer}, as of {f.as_of}, "
                  f"{len(f.rows)} rows, {eq} equity")
        else:
            print(f"Holdings file {t}: Not available - {refused[t]}")
    print("Holdings matching: one company per issuer - US/CA ISINs by CUSIP issuer "
          "(first six characters, so share classes combine), other ISINs exactly; "
          "iShares files have no ISINs, their rows matched by ticker + exchange to "
          "Bloomberg tickers in Amundi's file")
    for f in (funds[t] for t in order if t in funds and funds[t].source.issuer == "ishares"):
        eq = [r for r in f.rows if r.equity]
        zero = sum(1 for r in eq if r.weight == 0)
        print(f"Holdings precision: {f.ticker} weights are rounded to 0.01 by iShares, so "
              f"{zero} of its {len(eq)} equity rows print 0.00 and carry no weight here; "
              f"its rows sum to {sum((r.weight for r in f.rows), Decimal(0)):.2f}. "
              f"{f.unmatched_exchanges} {f.ticker} equity rows trade on exchanges no other fund "
              f"file names with a ticker, and can match nothing")
    dates = sorted({f.as_of for f in funds.values()})
    if len(dates) > 1:
        print("Holdings dates: the files are dated " + ", ".join(
            f"{t} {funds[t].as_of}" for t in order if t in funds)
              + " - each is the issuer's latest; Vanguard publishes month-end only")
    print("Holdings arithmetic: Shared weight = sum over the shared companies of the "
          "smaller of the two funds' weights; via cell = fund Weight (market) x "
          "company weight in the fund / 100, to 0.01; Total = sum of the printed cells")
    if stats:
        print(f"Look-through rows: the {stats['shown']} printed are the "
              f"directly held companies and the {args.top} largest others by Total, of "
              f"{stats['companies']} companies; printed rows sum to {stats['printed']:.2f} "
              f"of the {stats['everything']:.2f} the cells reach")
    if bets is not None:
        print(hidden_bets_method(bets))
    print(countries_basis(order))
    if cstats:
        print("Countries direct stocks: the country the fund files give the same company - "
              + ", ".join(f"{t} {c}" for t, c in direct_country.items()))
        print(f"Countries rows: {cstats['shown']} countries with a Total of "
              f"{args.min_country:.2f} or more printed; Other countries sums the remaining "
              f"{cstats['folded']} cell by cell; Total row = column sums; printed rows sum "
              f"to {cstats['sum']:.2f} of 100.00 - the gap is the funds' own rows not summing "
              f"to 100" + (" (iShares' 0.01 rounding)" if "ishares" in _issuers(order) else "")
              + " and each cell rounded to 0.01 on its own")
    if bstats:
        print(sectors_basis(order))
        print(currencies_basis(order))
        for title, (bst, extra) in bstats.items():
            parts = []
            for t in order:
                b = extra["basis"][t]
                bits = [f"{k} {v:.2f}" for k, v in b.items() if v]
                parts.append(f"{t} " + (", ".join(bits) if bits else "none"))
            print(f"{title} sources (% of each fund's equity): " + "; ".join(parts))
            print(f"{title} direct stocks: " + ", ".join(
                f"{n} {v}" for n, v in extra["direct"].items()))
            if title == "Currencies":
                print(f"Currencies rows: {bst['shown']} currencies with a Total of "
                      f"{args.min_currency:.2f} or more printed; Other currencies sums the "
                      f"remaining {bst['folded']}; Total row = column sums")
    print()
    print("PROOF")
    for t in order:
        if t in funds:
            f = funds[t]
            allw = sum((r.weight for r in f.rows), Decimal(0))
            eqw = sum((r.weight for r in f.rows if r.equity), Decimal(0))
            print(f"{t}: all rows sum {allw:.4f}, equity rows {eqw:.4f}, "
                  f"{len(exps[t].weights)} companies after share classes combine")
    if stats:
        if cstats:
            for t in order:
                sp = cstats["split"][t]
                eq = sum((v for k, v in sp.items() if k != CASH), Decimal(0))
                top = sorted(((k, v) for k, v in sp.items() if k not in (CASH, NOT_STATED)),
                             key=lambda kv: -kv[1])[:3]
                n = len(sp) - (CASH in sp)
                print(f"Countries {t}: {n} {'country' if n == 1 else 'countries'}, equity "
                      f"{eq:.4f} + {CASH.lower()} {sp.get(CASH, Decimal(0)):.4f}; largest "
                      + ", ".join(f"{k} {v:.2f}" for k, v in top))
        for title, (bst, _extra) in bstats.items():
            for t in order:
                sp = bst["split"][t]
                total = sum(sp.values(), Decimal(0))
                top = sorted(((k, v) for k, v in sp.items() if k != CASH),
                             key=lambda kv: (-kv[1], kv[0]))[:3]
                print(f"{title} {t}: {len(sp) - (CASH in sp)} buckets sum {total:.4f}; largest "
                      + ", ".join(f"{k} {v:.2f}" for k, v in top))
        print("Fund weights consumed: " + ", ".join(
            f"{t} {weights[ISIN_OF[t]]:.2f}"
            for t in order))
    return 0 if funds else 1


# --- history: weekly snapshots and what changed ----------------------------

# A snapshot is written when the fund's newest one is at least this old, so
# the history keeps about one file per fund per week however often the job
# runs, and Vanguard's month-end file is written once per month-end.
SNAPSHOT_EVERY = timedelta(days=7)
SNAPSHOT_HEADER = ["key", "name", "weight", "country", "sector", "currency"]
CASH_KEY = "cash"


def snapshot_key(r: Holding) -> str:
    """A row's id within its own fund, stable from one file to the next.

    Not the cross-fund company key: EIMI's rows reach that only through
    MEUD's file, and a key that depends on another fund's file would read as
    names added and dropped whenever that file changed.
    """
    if r.isin:
        return company_key(r.isin)
    if r.local:
        return f"tkr:{r.local}"
    return f"name:{name_key(r.name)}"


@dataclass
class Snapshot:
    ticker: str
    as_of: date
    rows: dict[str, dict[str, str]]  # key -> name, weight (str), country, sector, currency
    path: Path | None = None

    def weight(self, key: str) -> Decimal:
        return Decimal(self.rows[key]["weight"])

    @property
    def names(self) -> set[str]:
        return {k for k in self.rows if k != CASH_KEY}


def take_snapshot(fund: Fund) -> Snapshot:
    """One row per company (share classes summed), one for everything else."""
    rows: dict[str, dict[str, str]] = {}
    weights: dict[str, Decimal] = {}
    for r in fund.rows:
        key = snapshot_key(r) if r.equity else CASH_KEY
        weights[key] = weights.get(key, Decimal(0)) + r.weight
        if key not in rows:
            rows[key] = {"name": CASH if key == CASH_KEY else (r.issuer_name or display_name(r.name)),
                         "country": r.country if r.equity else "",
                         "sector": r.sector if r.equity else "",
                         "currency": r.currency if r.equity else ""}
    for key, w in weights.items():
        rows[key]["weight"] = f"{w:.6f}"
    if rows.get(CASH_KEY, {}).get("weight") == f"{Decimal(0):.6f}":
        del rows[CASH_KEY]
    return Snapshot(fund.ticker, fund.as_of, rows)


def write_snapshot(snap: Snapshot, path: Path, source: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    buf.write(f"# fund={snap.ticker} isin={ISIN_OF[snap.ticker]} as_of={snap.as_of} "
              f"source={source.name}\n")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(SNAPSHOT_HEADER)
    for key in sorted(snap.rows):
        r = snap.rows[key]
        w.writerow([key, r["name"], r["weight"], r["country"], r["sector"], r["currency"]])
    path.write_text(buf.getvalue(), encoding="utf-8")


def read_snapshot(path: Path) -> Snapshot:
    lines = path.read_text(encoding="utf-8").splitlines()
    meta = dict(kv.split("=", 1) for kv in lines[0].lstrip("# ").split()) if lines[0].startswith("#") else {}
    reader = csv.DictReader(ln for ln in lines if not ln.startswith("#"))
    rows = {r["key"]: {k: r[k] for k in SNAPSHOT_HEADER[1:]} for r in reader}
    ticker = meta.get("fund") or path.parent.name
    return Snapshot(ticker, date.fromisoformat(meta.get("as_of") or path.stem), rows, path)


def snapshot_dates(history_dir: Path, ticker: str) -> list[date]:
    out = []
    for f in (history_dir / ticker).glob("????-??-??.csv"):
        try:
            out.append(date.fromisoformat(f.stem))
        except ValueError:
            continue
    return sorted(out)


def cmd_snapshot(holdings_dir: Path, history_dir: Path) -> int:
    """Write a fund's snapshot when its newest is 7+ days older than its file."""
    for source in SOURCES.values():
        t = source.ticker
        path = latest_file(holdings_dir, t)
        if path is None:
            print(f"{t}: Not available - no file in {holdings_dir.as_posix()}")
            continue
        try:
            fund = load_fund(source, path)
        except Refused as exc:
            print(f"{t}: Not available - {path.name}: {exc}")
            continue
        dates = snapshot_dates(history_dir, t)
        if dates and fund.as_of - dates[-1] < SNAPSHOT_EVERY:
            print(f"{t}: skipped - newest snapshot {dates[-1]}, file as of {fund.as_of}")
            continue
        out = history_dir / t / f"{fund.as_of}.csv"
        snap = take_snapshot(fund)
        write_snapshot(snap, out, path)
        print(f"{t}: wrote {out.as_posix()} - {len(snap.names)} companies, as of {fund.as_of}")
    return 0


def baseline(history_dir: Path, ticker: str, as_of: date) -> Snapshot | None:
    """The newest snapshot at least SNAPSHOT_EVERY older than ``as_of``."""
    ok = [d for d in snapshot_dates(history_dir, ticker) if as_of - d >= SNAPSHOT_EVERY]
    return read_snapshot(history_dir / ticker / f"{ok[-1]}.csv") if ok else None


def _signed(value: Decimal) -> str:
    q = _q(value)
    return f"+{q:.2f}" if q > 0 else f"{q:.2f}"


def changes_table(order: list[str], funds: dict[str, Fund], refused: dict[str, str],
                  history_dir: Path, top: int = 3) -> tuple[list[str], dict]:
    """One row per fund: names then and now, added, dropped, largest moves.

    Weights are % of the fund, as its own files state them, not portfolio
    weights. A move is the change in a company's weight in the fund between
    the two files; Added and Dropped are companies in one file and not the
    other. Nothing here says why a weight moved (rule 7).
    """
    lines = ["| Fund | Since | Companies | Added | Dropped | Largest moves (pp of fund) |",
             "|---|---|---|---|---|---|"]
    proof: dict[str, dict] = {}
    for t in order:
        if t not in funds:
            lines.append(f"| {t} | Not available - {refused.get(t, 'no file')} | - | - | - | - |")
            continue
        now = take_snapshot(funds[t])
        base = baseline(history_dir, t, now.as_of)
        if base is None:
            dates = snapshot_dates(history_dir, t)
            why = (f"no snapshot 7+ days before {now.as_of}; history starts {dates[0]}"
                   if dates else "no snapshot yet")
            lines.append(f"| {t} | Not available - {why} | - | - | - | - |")
            continue
        added = sorted(now.names - base.names, key=lambda k: (-now.weight(k), k))
        dropped = sorted(base.names - now.names, key=lambda k: (-base.weight(k), k))
        held = now.names & base.names
        moves = {k: now.weight(k) - base.weight(k) for k in held}
        big = sorted((k for k in moves if _q(moves[k]) != 0), key=lambda k: (-abs(moves[k]), k))[:top]

        def listed(keys, snap):
            if not keys:
                return "0"
            shown = ", ".join(f"{snap.rows[k]['name']} {_cell(snap.weight(k))}" for k in keys[:top])
            return f"{len(keys)} ({shown}{', ...' if len(keys) > top else ''})"

        moved = ", ".join(f"{now.rows[k]['name']} {_signed(moves[k])}" for k in big) or "none"
        lines.append(
            f"| {t} | {base.as_of} to {now.as_of} | {len(base.names)} to {len(now.names)} | "
            f"{listed(added, now)} | {listed(dropped, base)} | {moved} |"
        )
        proof[t] = {
            "base": base, "now": now,
            "base_eq": sum((base.weight(k) for k in base.names), Decimal(0)),
            "now_eq": sum((now.weight(k) for k in now.names), Decimal(0)),
            "moves": sum(moves.values(), Decimal(0)),
            "added": sum((now.weight(k) for k in added), Decimal(0)),
            "dropped": sum((base.weight(k) for k in dropped), Decimal(0)),
            "n_added": len(added), "n_dropped": len(dropped), "n_held": len(held),
        }
    return lines, proof


def cmd_changes(holdings_dir: Path, history_dir: Path) -> int:
    order = [s.ticker for s in SOURCES.values()]
    funds: dict[str, Fund] = {}
    refused: dict[str, str] = {}
    for source in SOURCES.values():
        path = latest_file(holdings_dir, source.ticker)
        if path is None:
            refused[source.ticker] = f"no file in {holdings_dir.as_posix()}"
            continue
        try:
            funds[source.ticker] = load_fund(source, path)
        except Refused as exc:
            refused[source.ticker] = f"{path.name}: {exc}"
    lines, proof = changes_table(order, funds, refused, history_dir)
    print("Holdings changes (each fund's latest file against its snapshot 7+ days older)")
    print("\n".join(lines))
    print()
    print("METHOD")
    print(f"Holdings history: {history_dir.as_posix()} - one snapshot per fund about weekly, "
          "written by the GitHub Actions job to the holdings-history branch from the same "
          "issuer files the tables read; each compared against the newest snapshot at least "
          "7 days older than the fund's current file")
    for t in order:
        if t in proof:
            pr = proof[t]
            print(f"Holdings changes {t}: {pr['base'].path.name if pr['base'].path else 'snapshot'} "
                  f"against {funds[t].path.name}")
    print("Holdings changes basis: a company is one issuer within one fund (share classes "
          "summed); Added and Dropped are companies in one file and not the other; a move is "
          "the change in the company's % of the fund, which reflects price changes and index "
          "changes together and is not attributed to either; moves under 0.005pp print as "
          "none; weights as each issuer's file states them, % of the fund")
    print()
    print("PROOF")
    for t, pr in proof.items():
        lhs = pr["now_eq"] - pr["base_eq"]
        rhs = pr["moves"] + pr["added"] - pr["dropped"]
        print(f"{t}: equity {pr['now_eq']:.6f} - {pr['base_eq']:.6f} = {lhs:.6f}; "
              f"moves {pr['moves']:.6f} ({pr['n_held']} held) + added {pr['added']:.6f} "
              f"({pr['n_added']}) - dropped {pr['dropped']:.6f} ({pr['n_dropped']}) = {rhs:.6f} "
              + ("PASS" if lhs == rhs else "MISMATCH"))
    return 0 if funds else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="download each issuer's holdings file")
    f.add_argument("--funds", type=Path, default=DEFAULT_FUNDS,
                   help="the funds table (default me/funds.md; no funds when absent)")
    f.add_argument("--holdings-dir", type=Path, default=Path("data/holdings"))
    f.add_argument("--only", default="", help="comma-separated tickers, e.g. SPPW,EIMI")
    r = sub.add_parser("report", help="print the Holdings and Look-through tables")
    r.add_argument("--funds", type=Path, default=DEFAULT_FUNDS,
                   help="the funds table (default me/funds.md; no funds when absent)")
    r.add_argument("--holdings-dir", type=Path, default=Path("data/holdings"))
    r.add_argument("--prices", type=Path, default=None,
                   help="the JSON market_weights.py reads; gives the look-through its weights")
    r.add_argument("--data-dir", type=Path, default=Path("data/t212"))
    r.add_argument("--pies", type=Path, default=Path("me/pies.md"))
    r.add_argument("--ownership", type=Path, default=Path("me/ownership.md"))
    r.add_argument("--holdings", type=Path, default=Path("me/holdings.csv"),
                   help="broker-neutral holdings; used instead of the Trading 212 exports "
                        "whenever it exists")
    r.add_argument("--top", type=int, default=15,
                   help="how many companies beyond the directly held to print")
    r.add_argument("--min-country", type=Decimal, default=Decimal("0.50"),
                   help="a country with a smaller Total folds into Other countries")
    r.add_argument("--min-currency", type=Decimal, default=Decimal("0.50"),
                   help="a currency with a smaller Total folds into Other currencies")
    s = sub.add_parser("snapshot", help="write each fund's weekly snapshot to the history folder")
    s.add_argument("--funds", type=Path, default=DEFAULT_FUNDS,
                   help="the funds table (default me/funds.md; no funds when absent)")
    s.add_argument("--holdings-dir", type=Path, default=Path("data/holdings"))
    s.add_argument("--history-dir", type=Path, default=Path("data/history"))
    c = sub.add_parser("changes", help="print what each fund's holdings changed week on week")
    c.add_argument("--funds", type=Path, default=DEFAULT_FUNDS,
                   help="the funds table (default me/funds.md; no funds when absent)")
    c.add_argument("--holdings-dir", type=Path, default=Path("data/holdings"))
    c.add_argument("--history-dir", type=Path, default=Path("data/history"))
    args = parser.parse_args(argv)
    try:
        args.funds_note = use_funds(args.funds)
    except Refused as exc:
        print(f"Not available - {exc}")
        return 1
    if not SOURCES and args.cmd != "report":
        if args.cmd == "changes":
            print("Holdings changes")
            print("| Fund | Since | Companies | Added | Dropped | Largest moves (pp of fund) |")
            print("|---|---|---|---|---|---|")
            print(f"| none | none - {no_funds_reason(args.funds_note)} | - | - | - | - |")
        else:
            print(f"Nothing to {args.cmd}: {no_funds_reason(args.funds_note)}")
        return 0
    if args.cmd == "snapshot":
        return cmd_snapshot(args.holdings_dir, args.history_dir)
    if args.cmd == "changes":
        return cmd_changes(args.holdings_dir, args.history_dir)
    if args.cmd == "fetch":
        only = {t.strip().upper() for t in args.only.split(",") if t.strip()} or None
        return cmd_fetch(args.holdings_dir, date.today(), only)
    return cmd_report(args)


if __name__ == "__main__":
    sys.exit(main())
