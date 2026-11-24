"""A ready-to-submit GitHub issue for a Holdnote problem, as one link.

    python3 <skill>/scripts/report_problem.py --kind bug --title "..." \
        --what "..." [--expected "..."] [--asked "..."] [--error "..."] \
        [--install plugin|zip|agensi|other]
    python3 <skill>/scripts/report_problem.py --kind broker --broker Degiro \
        --filetype csv --headers "Product,ISIN,Amount,..." [--what "..."]
    python3 <skill>/scripts/report_problem.py --kind idea --title "..." --what "..." [--why "..."]

Prints the link to the matching issue form on github.com/Artvarna/holdnote,
with its fields filled in, then the text that went into it. Nothing is
sent: the user opens the link, reads it, and presses Submit themselves.

Before anything goes into the link, money amounts (a currency next to a
number), runs of 8 or more digits (account and card numbers) and email
addresses are replaced with [amount], [number] and [email]. Percentages,
tickers and ISINs stay. The build is filled in by scripts/build_info.py.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_info import build_stamp  # noqa: E402

REPO = "https://github.com/Artvarna/holdnote"
TEMPLATES = {"bug": "bug.yml", "broker": "broker.yml", "idea": "idea.yml"}
INSTALL = {"zip": "Claude app (zip from GitHub releases)", "plugin": "Claude Code plugin",
           "agensi": "Agensi", "other": "Other"}
FILETYPE = {"csv": "CSV export", "xlsx": "Excel export (.xlsx)", "screenshot": "Screenshot",
            "pdf": "PDF statement", "other": "Other"}
FIELD_LIMIT = 1500  # characters per field, so the link stays well under browsers' limits

CUR = r"(?:€|\$|£|¥|EUR|USD|GBP|BGN|CHF|JPY|PLN|SEK|NOK|DKK|CZK|HUF|RON|лв\.?)"
NUM = r"[-−]?\d{1,3}(?:[.,'’\u00a0\u202f ]\d{3})+(?:[.,]\d+)?|[-−]?\d+(?:[.,]\d+)?"
AMOUNT = re.compile(rf"{CUR}\s?(?:{NUM})|(?:{NUM})\s?{CUR}", re.IGNORECASE)
LONG_DIGITS = re.compile(r"(?<![A-Za-z0-9])\d[\d\s-]{6,}\d(?![A-Za-z0-9])")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def scrub(text: str) -> str:
    """Private details out, everything else as written."""
    text = EMAIL.sub("[email]", text)
    text = AMOUNT.sub("[amount]", text)

    def digits(m: re.Match) -> str:
        s = m.group()
        if DATE.fullmatch(s.strip()):
            return s  # a date (2026-11-24), not an account number
        return "[number]" if sum(c.isdigit() for c in s) >= 8 else s

    text = LONG_DIGITS.sub(digits, text)
    if len(text) > FIELD_LIMIT:
        text = text[:FIELD_LIMIT].rstrip() + " [cut]"
    return text


def issue_link(kind: str, fields: dict[str, str]) -> tuple[str, dict[str, str]]:
    clean = {k: v if k == "build" else scrub(v) for k, v in fields.items() if v}
    query = {"template": TEMPLATES[kind], **clean}
    return f"{REPO}/issues/new?{urlencode(query)}", clean


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--kind", choices=sorted(TEMPLATES), required=True)
    ap.add_argument("--title", default="")
    ap.add_argument("--what", default="")
    ap.add_argument("--expected", default="")
    ap.add_argument("--asked", default="")
    ap.add_argument("--error", default="")
    ap.add_argument("--why", default="")
    ap.add_argument("--install", choices=sorted(INSTALL), default=None)
    ap.add_argument("--broker", default="")
    ap.add_argument("--filetype", choices=sorted(FILETYPE), default=None)
    ap.add_argument("--headers", default="", help="the export's header row only")
    args = ap.parse_args(argv)

    prefix = {"bug": "Bug: ", "broker": "Broker export: ", "idea": "Idea: "}[args.kind]
    title = args.title or (args.broker if args.kind == "broker" else "")
    fields = {"title": prefix + title if title else ""}
    if args.kind == "bug":
        fields.update(what=args.what, expected=args.expected, asked=args.asked,
                      error=args.error, build=build_stamp(),
                      install=INSTALL.get(args.install or "", ""))
    elif args.kind == "broker":
        fields.update(broker=args.broker, headers=args.headers.splitlines()[0] if args.headers else "",
                      filetype=FILETYPE.get(args.filetype or "", ""), what=args.what,
                      build=build_stamp())
    else:
        fields.update(what=args.what, why=args.why)
    link, clean = issue_link(args.kind, fields)
    print(link)
    print()
    for key, value in clean.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
