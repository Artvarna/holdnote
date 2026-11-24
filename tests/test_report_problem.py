"""scripts/report_problem.py: a pre-filled issue link that never carries private details."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import report_problem as rp  # noqa: E402


def test_scrub_removes_amounts_long_numbers_and_emails():
    s = rp.scrub("€12,345.67 and 3,600.00 EUR, $1,000, 300 лв, card 1234 5678 9012 3456, a.b@x.com")
    assert s == "[amount] and [amount], [amount], [amount], card [number], [email]"


def test_scrub_keeps_what_a_report_needs():
    s = "IE00B4L5Y983 is 9.41% of VWCE on 2026-11-24; KO +0.32%"
    assert rp.scrub(s) == s


def test_link_fields_match_the_issue_forms():
    """Every field the script fills is an id in the form it opens, so GitHub prefills it."""
    for kind, template in rp.TEMPLATES.items():
        form = yaml.safe_load((ROOT / ".github" / "ISSUE_TEMPLATE" / template).read_text())
        ids = {b["id"] for b in form["body"] if "id" in b} | {"title", "template"}
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "report_problem.py"),
                              "--kind", kind, "--title", "t", "--what", "w", "--broker", "Degiro",
                              "--headers", "A,B,C\nsecret,row", "--expected", "e", "--asked", "a",
                              "--error", "x", "--why", "y", "--install", "plugin", "--filetype", "csv"],
                             capture_output=True, text=True, check=True).stdout
        link = out.splitlines()[0]
        query = parse_qs(urlparse(link).query)
        assert set(query) <= ids, (kind, set(query) - ids)
        assert query["template"] == [template]
        assert "secret" not in link  # only the header row of an export


def test_dropdown_values_are_options_of_their_forms():
    bug = yaml.safe_load((ROOT / ".github/ISSUE_TEMPLATE/bug.yml").read_text())
    broker = yaml.safe_load((ROOT / ".github/ISSUE_TEMPLATE/broker.yml").read_text())
    options = {b["id"]: b["attributes"]["options"] for f in (bug, broker) for b in f["body"]
               if b.get("type") == "dropdown"}
    assert set(rp.INSTALL.values()) <= set(options["install"])
    assert set(rp.FILETYPE.values()) <= set(options["filetype"])
