#!/usr/bin/env python3
"""Refresh the demo portfolio's frozen data (demo/data/).

    python3 scripts/demo_snapshot.py

Runs in the `Demo data` GitHub Action (.github/workflows/demo-data.yml),
never in Claude's workspace or on a user's computer: those shells reach
only package registries and GitHub, while GitHub's runners reach the issuer,
exchange, ECB and SEC sites this needs. The skill zip ships what it writes,
so "show me a demo" runs with no fetch at all (scripts/demo.py).

What it writes, all for one session date (`as_of`):

    demo/data/holdings/<TICKER>-<date>.xlsx  each fund's full SSGA holdings file
    demo/data/prices.json   closes and ECB rates, in market_weights' format
    demo/data/stocks.json   each stock's EDGAR filings and next earnings date
    demo/data/sources.json  every document read, with URL and both dates
    demo/data/snapshot.log  what each source returned

and moves demo/holdings.csv's `as_of` to the same date.

Every close is read from two sources -- the exchange (London Stock Exchange
or Nasdaq) and Yahoo Finance -- and the exchange's figure is the one used.
Nothing is estimated: a source that fails stops the run with exit 1 and the
committed snapshot stays as it was.
"""

from __future__ import annotations

import csv
import json
import re
import shutil
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fund_holdings as fh  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
DEMO = REPO / "demo"
OUT = DEMO / "data"
UA = fh.UA
# A close two sources state differently by more than this is not used.
TOLERANCE_PCT = Decimal("0.10")
MONTHS = ("January February March April May June July August September "
          "October November December").split()


class Failed(Exception):
    pass


class NotYet(Exception):
    """Every market's close for one date is not available yet: no failure,
    the committed snapshot simply stays."""


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def get(url: str, headers: dict | None = None) -> bytes:
    h = {"User-Agent": UA, "Accept": "*/*", **(headers or {})}
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise Failed(f"{url} returned {exc.code}")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise Failed(f"{url} not reached ({getattr(exc, 'reason', exc)})")


def listings() -> list[dict]:
    lines = [ln for ln in (DEMO / "listings.csv").read_text().splitlines()
             if ln.strip() and not ln.startswith("#")]
    return list(csv.DictReader(lines))


# --- closes -----------------------------------------------------------------

def yahoo_closes(symbol: str) -> tuple[dict[str, Decimal], str, str]:
    """Yahoo's daily closes. Its chart data leaves some completed sessions
    null (an LSE ETF on 2026-10-14), so two ranges and both hosts are read and
    merged; a session null in all of them stays missing."""
    closes: dict[str, Decimal] = {}
    ccy, first_url = "", ""
    for host in ("query1", "query2"):
        for rng in ("1mo", "5d"):
            url = f"https://{host}.finance.yahoo.com/v8/finance/chart/{symbol}?range={rng}&interval=1d"
            first_url = first_url or url
            try:
                res = json.loads(get(url))["chart"]["result"][0]
            except (Failed, KeyError, IndexError, TypeError, ValueError):
                continue
            ccy = ccy or res["meta"].get("currency", "")
            tz = timezone(timedelta(seconds=res["meta"].get("gmtoffset", 0)))
            for ts, close in zip(res.get("timestamp") or [], res["indicators"]["quote"][0]["close"]):
                if close is not None:
                    day = datetime.fromtimestamp(ts, tz).date().isoformat()
                    closes.setdefault(day, Decimal(str(close)).quantize(Decimal("0.0001")))
    return closes, ccy, first_url


def lse_close(tidm: str) -> tuple[str, Decimal, str, str, str]:
    url = f"https://api.londonstockexchange.com/api/gw/lse/instruments/alldata/{tidm}"
    data = json.loads(get(url, {"Origin": "https://www.londonstockexchange.com",
                                "Referer": "https://www.londonstockexchange.com/"}))
    if data.get("lastclose") is None or not data.get("lastclosedate"):
        raise Failed(f"LSE {tidm}: no last close in {url}")
    day = data["lastclosedate"][:10]
    return day, Decimal(str(data["lastclose"])), data.get("currency", ""), data.get("isin", ""), url


def nasdaq_closes(symbol: str, start: date, end: date) -> tuple[dict[str, Decimal], str]:
    url = (f"https://api.nasdaq.com/api/quote/{symbol}/historical?assetclass=stocks"
           f"&fromdate={start.isoformat()}&limit=30&todate={end.isoformat()}")
    data = json.loads(get(url, {"Accept": "application/json", "Origin": "https://www.nasdaq.com",
                                "Referer": "https://www.nasdaq.com/"}))
    rows = ((data.get("data") or {}).get("tradesTable") or {}).get("rows") or []
    closes = {}
    for r in rows:
        m, d, y = r["date"].split("/")
        closes[f"{y}-{m}-{d}"] = Decimal(r["close"].replace("$", "").replace(",", ""))
    if not closes:
        raise Failed(f"Nasdaq {symbol}: no rows in {url}")
    return closes, url


def ecb_rates() -> tuple[dict[str, dict[str, Decimal]], str]:
    url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
    root = ET.fromstring(get(url))
    out: dict[str, dict[str, Decimal]] = {}
    for cube in root.iter():
        if cube.tag.endswith("Cube") and cube.get("time"):
            out[cube.get("time")] = {c.get("currency"): Decimal(c.get("rate")) for c in cube}
    if not out:
        raise Failed(f"ECB: no rates in {url}")
    return out, url


# --- stocks -----------------------------------------------------------------

PERIODIC = {"10-K", "10-Q", "10-K/A", "10-Q/A", "8-K", "8-K/A"}


def edgar(cik: str, as_of: date) -> tuple[str, list[dict], str]:
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    data = json.loads(get(url))
    recent = data["filings"]["recent"]
    keep = []
    for form, filed, period in zip(recent["form"], recent["filingDate"], recent["reportDate"]):
        if form in PERIODIC and filed <= as_of.isoformat():
            keep.append({"form": form, "filed": filed, "period": period})
    return data["name"], keep[:40], url


def earnings_date(url: str, as_of: date) -> tuple[str | None, str]:
    """The next earnings event the company's own page lists, or None.

    Reads the page's event links (`.../20261027-3rd-quarter-2026-earnings-call`)
    and its dated event headings. Returns the date and the text it came from.
    """
    text = get(url).decode("utf-8", "replace")
    found: list[tuple[str, str]] = []
    for m in re.finditer(r"(20\d{6})-[a-z0-9-]*?(earnings|results)[a-z0-9-]*", text, re.I):
        d = m.group(1)
        found.append((f"{d[:4]}-{d[4:6]}-{d[6:]}", m.group(0)))
    pattern = (r"(" + "|".join(MONTHS) + r") (\d{1,2}), (20\d\d)[^<]{0,120}?"
               r"(earnings|results)")
    for m in re.finditer(pattern, text, re.I):
        day = date(int(m.group(3)), MONTHS.index(m.group(1)) + 1, int(m.group(2)))
        found.append((day.isoformat(), " ".join(m.group(0).split())))
    future = sorted(f for f in found if f[0] >= as_of.isoformat())
    return (future[0][0], future[0][1]) if future else (None, f"{len(found)} dated earnings events, none on or after {as_of}")


# --- run ----------------------------------------------------------------------

def main() -> int:
    log: list[str] = []
    sources: list[dict] = []

    def source(doc: str, url: str, published: str) -> None:
        sources.append({"document": doc, "url": url, "published": published, "retrieved": now()})

    rows = listings()
    work = OUT.with_name("data.new")
    shutil.rmtree(work, ignore_errors=True)
    (work / "holdings").mkdir(parents=True)

    try:
        # 1. Closes: the exchange's latest session for the funds fixes as_of.
        lse = {}
        for r in rows:
            kind, _, code = r["exchange"].partition(":")
            if kind == "lse":
                day, close, ccy, isin, url = lse_close(code)
                if isin and isin != r["isin"]:
                    raise Failed(f"LSE {code} is {isin}, not {r['isin']}")
                lse[r["isin"]] = (day, close, ccy, url, code)
                log.append(f"LSE {code}: {ccy} {close} on {day}")
        days = {v[0] for v in lse.values()}
        if len(days) != 1:
            raise Failed(f"LSE closes are for different sessions: {sorted(days)}")
        as_of = date.fromisoformat(days.pop())

        rates, ecb_url = ecb_rates()
        if as_of.isoformat() not in rates:
            raise Failed(f"ECB published no rates for {as_of}")
        source("ECB euro foreign exchange reference rates (90 days)", ecb_url, as_of.isoformat())

        prices: dict[str, dict] = {}
        currencies: set[str] = set()
        for r in rows:
            kind, _, code = r["exchange"].partition(":")
            yclose, yccy, yurl = yahoo_closes(r["yahoo"])
            if kind == "lse":
                day, close, ccy, url, tidm = lse[r["isin"]]
                exch = f"London Stock Exchange, {tidm} last close"
                source(f"London Stock Exchange instrument data, {tidm}", url, day)
            else:
                closes, url = nasdaq_closes(code, as_of - timedelta(days=10), as_of)
                if as_of.isoformat() not in closes:
                    # London closes at 15:30 UTC, New York at 20:00 UTC: a run in
                    # between has London's close for a day New York has not
                    # finished. The scheduled 06:17 UTC run never lands there.
                    latest = max(closes)
                    if latest < as_of.isoformat():
                        raise NotYet(f"Nasdaq {code}: newest close is {latest}; the US session "
                                     f"of {as_of} has not closed yet")
                    raise NotYet(f"Nasdaq {code}: no session on {as_of} (a US market holiday)")
                close, ccy = closes[as_of.isoformat()], "USD"
                exch = f"Nasdaq historical quotes, {code} close"
                source(f"Nasdaq historical quotes, {code}", url, as_of.isoformat())
            if yccy and ccy and yccy != ccy:
                raise Failed(f"{r['ticker']}: exchange currency {ccy}, Yahoo {yccy}")
            entry = {"price": str(close), "currency": ccy, "date": as_of.isoformat(),
                     "source": exch}
            other = yclose.get(as_of.isoformat())
            if other is None:
                # One source, said so: the demo prints it on its Confirmation line.
                entry["confirmed_by"] = None
                entry["unconfirmed"] = f"Yahoo Finance chart, {r['yahoo']}, has no close for {as_of}"
                log.append(f"{r['ticker']}: {ccy} {close} ({exch}); Yahoo has no close for {as_of}")
            else:
                diff = (other - close) / close * 100
                source(f"Yahoo Finance chart, {r['yahoo']}", yurl, as_of.isoformat())
                if abs(diff) > TOLERANCE_PCT:
                    raise Failed(f"{r['ticker']}: {exch} {close} vs Yahoo {other} ({diff:.3f}%)")
                entry["confirmed_by"] = {"source": f"Yahoo Finance chart, {r['yahoo']}",
                                         "price": str(other), "diff_pct": f"{diff:.3f}"}
                log.append(f"{r['ticker']}: {ccy} {close} ({exch}); Yahoo {other}, {diff:+.3f}%")
            prices[r["isin"]] = entry
            currencies.add(ccy)
        fx = {c: {"per_eur": str(rates[as_of.isoformat()][c]), "date": as_of.isoformat(),
                  "source": "ECB euro foreign exchange reference rates"}
              for c in sorted(currencies) if c != "EUR"}
        (work / "prices.json").write_text(json.dumps(
            {"as_of": as_of.isoformat(), "prices": prices, "fx": fx}, indent=2) + "\n")

        # 2. Full fund holdings files, through the skill's own fetcher.
        fh.use_funds(DEMO / "funds.md")
        for src in fh.SOURCES.values():
            data = fh.fetch(src)
            tmp = work / "holdings" / f"{src.ticker}.tmp"
            tmp.write_bytes(data)
            fund = fh.load_fund(src, tmp)
            path = tmp.with_name(f"{src.ticker}-{fund.as_of.isoformat()}.{src.ext}")
            tmp.rename(path)
            equity = sum(1 for x in fund.rows if x.equity)
            source(f"SSGA daily holdings file, {src.ticker}", src.url, fund.as_of.isoformat())
            log.append(f"{src.ticker}: {len(fund.rows)} rows, {equity} equity, as of {fund.as_of}")

        # 3. Stocks: EDGAR filings and the company's own earnings date.
        stocks = {}
        for r in rows:
            if not r["cik"]:
                continue
            name, filings, url = edgar(r["cik"], as_of)
            source(f"SEC EDGAR submissions, {name}", url, filings[0]["filed"] if filings else "n/a")
            when, why = earnings_date(r["ir"], as_of)
            source(f"{name} investor relations events page", r["ir"], "n/a — web page")
            stocks[r["isin"]] = {"ticker": r["ticker"], "company": name, "cik": r["cik"],
                                 "filings": filings, "earnings": when, "earnings_basis": why,
                                 "ir": r["ir"]}
            log.append(f"{r['ticker']}: EDGAR {name}, {len(filings)} filings; earnings {when} ({why})")
        (work / "stocks.json").write_text(json.dumps(stocks, indent=2) + "\n")
    except NotYet as exc:
        print("\n".join(log))
        print(f"SKIPPED: {exc}. The committed snapshot is unchanged; the next run takes it.")
        shutil.rmtree(work, ignore_errors=True)
        return 0
    except (Failed, fh.Refused, KeyError, ValueError) as exc:
        print("\n".join(log))
        print(f"FAILED: {exc}")
        shutil.rmtree(work, ignore_errors=True)
        return 1

    (work / "sources.json").write_text(json.dumps(sources, indent=2, ensure_ascii=False) + "\n")
    log.insert(0, f"as_of {as_of} · run {now()}")
    (work / "snapshot.log").write_text("\n".join(log) + "\n")
    shutil.rmtree(OUT, ignore_errors=True)
    work.rename(OUT)
    # The demo's quantities are synthetic and stated as of the snapshot, so
    # Allocation never reads them as months older than the prices.
    holdings = DEMO / "holdings.csv"
    holdings.write_text(re.sub(r"^# as_of: .*$", f"# as_of: {as_of.isoformat()}",
                               holdings.read_text(), count=1, flags=re.MULTILINE))
    print("\n".join(log))
    return 0


if __name__ == "__main__":
    sys.exit(main())
