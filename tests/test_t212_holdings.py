"""Tests for scripts/t212_holdings.py.

Fixtures are built from the column set and value formats of a real export
(see docs/t212-csv-schema.md), including the awkward ones: dividend rows with
an empty ID, GBX pricing, a Total currency that changes mid-history, and a
zero-byte export.
"""

from __future__ import annotations

import csv
import re
import shutil
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import contract  # noqa: E402
import t212_holdings as t  # noqa: E402

# --------------------------------------------------------------------------
# Fixture builders
# --------------------------------------------------------------------------

HEADER = [
    "Action",
    "Time (UTC)",
    "ISIN",
    "Ticker",
    "Name",
    "Notes",
    "ID",
    "No. of shares",
    "Price / share",
    "Currency (Price / share)",
    "Exchange rate",
    "Result",
    "Currency (Result)",
    "Total",
    "Currency (Total)",
    "Withholding tax",
    "Currency (Withholding tax)",
    "Currency conversion from amount",
    "Currency (Currency conversion from amount)",
    "Currency conversion to amount",
    "Currency (Currency conversion to amount)",
    "Currency conversion fee",
    "Currency (Currency conversion fee)",
]

COLUMN_ALIASES = {
    "action": "Action",
    "time": "Time (UTC)",
    "isin": "ISIN",
    "ticker": "Ticker",
    "name": "Name",
    "notes": "Notes",
    "tx_id": "ID",
    "qty": "No. of shares",
    "price": "Price / share",
    "price_ccy": "Currency (Price / share)",
    "fx": "Exchange rate",
    "result": "Result",
    "result_ccy": "Currency (Result)",
    "total": "Total",
    "total_ccy": "Currency (Total)",
    "fee": "Currency conversion fee",
    "fee_ccy": "Currency (Currency conversion fee)",
}


def row(**kwargs) -> dict[str, str]:
    """Build one CSV row. Keyword names are the short aliases above."""
    out = {column: "" for column in HEADER}
    for key, value in kwargs.items():
        out[COLUMN_ALIASES[key]] = str(value)
    return out


def buy(isin="IE00BFY0GT14", ticker="SPPW", qty="1.0", price="46.0230000000",
        price_ccy="EUR", fx="1.00000000", total="46.02", total_ccy="EUR",
        time="2026-09-09 12:16:01+00:00", tx_id="EOF1", **kwargs) -> dict[str, str]:
    return row(
        action="Market buy", isin=isin, ticker=ticker, qty=qty, price=price,
        price_ccy=price_ccy, fx=fx, total=total, total_ccy=total_ccy, time=time,
        tx_id=tx_id, **kwargs
    )


def sell(**kwargs) -> dict[str, str]:
    record = buy(**kwargs)
    record["Action"] = "Market sell"
    return record


def dividend(isin="IE00B3XXRP09", ticker="VUSA", qty="0.5000000000",
             price="0.250000", price_ccy="GBP", fx="1.20000000", total="0.15",
             total_ccy="EUR", time="2026-04-01 15:10:44+00:00") -> dict[str, str]:
    """A dividend row: parenthesised action, no ID, shares held not moved."""
    return row(
        action="Dividend (Dividend)", isin=isin, ticker=ticker, qty=qty,
        price=price, price_ccy=price_ccy, fx=fx, total=total,
        total_ccy=total_ccy, time=time, tx_id="",
    )


def csv_text(rows, header=None, newline="\n", bom="") -> str:
    columns = header if header is not None else HEADER
    lines = [",".join(columns)]
    for record in rows:
        lines.append(",".join(f'"{record.get(c, "")}"' for c in columns))
    return bom + newline.join(lines) + newline


def write_export(directory: Path, name: str, rows, **kwargs) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(csv_text(rows, **kwargs), encoding="utf-8")
    return path


PIES_TEMPLATE = """---
Last updated: {updated}
---

# Pies

## Pie shares

| Pie | Target share of portfolio |
|---|---|
{shares}

{pie_tables}

## Not in a pie

| ISIN | Ticker | Name | Status |
|---|---|---|---|
{excluded}
"""


def write_pies(
    path: Path,
    updated="2026-09-17",
    shares=(("ETF", "75%"), ("Stock", "25%")),
    pies=(
        ("ETF", (("IE00BFY0GT14", "SPPW", "SPDR MSCI World (Acc)", "100%"),)),
        ("Stock", (("US0378331005", "AAPL", "Apple", "100%"),)),
    ),
    excluded=(),
) -> Path:
    tables = []
    for name, holdings in pies:
        rows = "\n".join(f"| {' | '.join(h)} |" for h in holdings)
        tables.append(
            f"## Pie: {name}\n\n| ISIN | Ticker | Name | Target in pie |\n"
            f"|---|---|---|---|\n{rows}"
        )
    path.write_text(
        PIES_TEMPLATE.format(
            updated=updated,
            shares="\n".join(f"| {name} | {share} |" for name, share in shares),
            pie_tables="\n\n".join(tables),
            excluded="\n".join(f"| {' | '.join(e)} |" for e in excluded),
        ),
        encoding="utf-8",
    )
    return path


OWNERSHIP_TEMPLATE = """---
Last updated: {updated}
Cutoff: {cutoff}{extra}
---

# Ownership

## Pre-cutoff ISINs

| ISIN | Ticker | Name | Evidence |
|---|---|---|---|
{declared}
"""


BGN_RATE = (
    "1 EUR = 1.95583 BGN (Council Regulation (EU) 2025/1409 of 8 July 2025, "
    "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32025R1409)"
)


def write_ownership(
    path: Path,
    cutoff="2025-10-13",
    declared=(),
    updated="2026-09-17",
    fixed_rate: str | None = None,
) -> Path:
    path.write_text(
        OWNERSHIP_TEMPLATE.format(
            cutoff=cutoff,
            extra=f"\nFixed rate: {fixed_rate}" if fixed_rate else "",
            updated=updated,
            declared="\n".join(f"| {' | '.join(d)} |" for d in declared),
        ),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    (tmp_path / "data" / "t212").mkdir(parents=True)
    write_ownership(tmp_path / "ownership.md")
    return tmp_path


CUTOFF = date(2025, 10, 13)


def load(directory: Path, cutoff: date = CUTOFF):
    ledger = t.load_transactions(directory)
    return ledger, t.aggregate(ledger.txs, cutoff)


def states_for(positions, workspace: Path):
    return t.classify_ownership(
        positions, t.load_ownership(workspace / "ownership.md")
    )


def run_in(
    workspace: Path, attribute=t.ATTRIBUTE_FIFO, proof=False, **pies_kwargs
) -> str:
    """Run the importer against a workspace built by these fixtures."""
    return t.run(
        workspace / "data" / "t212",
        write_pies(workspace / "pies.md", **pies_kwargs),
        workspace / "ownership.md",
        attribute=attribute,
        proof=proof,
    )


# --------------------------------------------------------------------------
# Quantity aggregation
# --------------------------------------------------------------------------


def test_net_quantity_is_exact_decimal(workspace):
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(qty="0.2566032200", tx_id="EOF1"),
            buy(qty="0.2897547600", tx_id="EOF2"),
            sell(qty="0.0970076600", tx_id="EOF3"),
        ],
    )
    _, positions = load(data)
    assert positions["IE00BFY0GT14"].net_qty == Decimal("0.4493503200")


def test_closed_position_nets_to_exact_zero(workspace):
    """Float arithmetic leaves -1e-18 here, which would trip the halt."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(qty="0.0050290300", tx_id="EOF1"),
            buy(qty="0.0056505300", tx_id="EOF2"),
            sell(qty="0.0106795600", tx_id="EOF3"),
        ],
    )
    _, positions = load(data)
    position = positions["IE00BFY0GT14"]
    assert position.net_qty == Decimal(0)
    assert not position.is_open
    t.check_no_negative_quantity(
        positions, states_for(positions, workspace)
    )  # zero is not negative


def test_negative_quantity_after_the_cutoff_still_halts(workspace):
    """Opened with a buy after the cutoff and still oversold: missing data."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(isin="US0378331005", ticker="AAPL", qty="1.0",
                time="2026-06-18 14:08:08+00:00", tx_id="EOF1"),
            sell(isin="US0378331005", ticker="AAPL", qty="3.0",
                 time="2026-09-09 14:06:52+00:00", tx_id="EOF2"),
            buy(isin="IE00BFY0GT14", qty="1.0", tx_id="EOF3"),
        ],
    )
    _, positions = load(data)
    states = states_for(positions, workspace)
    assert states["US0378331005"] == t.MINE
    with pytest.raises(t.Halt) as excinfo:
        t.check_no_negative_quantity(positions, states)
    message = str(excinfo.value)
    assert "US0378331005" in message
    assert "AAPL" in message
    assert "IE00BFY0GT14" not in message  # the healthy position is not named


# --------------------------------------------------------------------------
# Ownership cutoff (shared account)
# --------------------------------------------------------------------------


def test_pre_cutoff_position_is_not_mine(workspace):
    """All activity before the cutoff: the account holder's, excluded."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(isin="US01609W1027", ticker="BABA", qty="0.5",
                time="2025-09-20 13:31:55+00:00", tx_id="EOF1"),
            sell(isin="US01609W1027", ticker="BABA", qty="0.2",
                 time="2025-10-11 13:31:55+00:00", tx_id="EOF2"),
            buy(qty="1.0", time="2025-10-20 09:48:15+00:00", tx_id="EOF3"),
        ],
    )
    _, positions = load(data)
    baba = positions["US01609W1027"]
    assert baba.net_qty == Decimal(0)  # nothing on or after the cutoff
    assert baba.pre_net_qty == Decimal("0.3")
    assert baba.pre_rows == 2

    states = states_for(positions, workspace)
    assert states["US01609W1027"] == t.PRE_CUTOFF_ONLY
    assert states["IE00BFY0GT14"] == t.MINE

    # Excluded from weights, and reported in its own section.
    currency, weights = t.cost_weights(positions, states)
    assert list(weights) == ["IE00BFY0GT14"]
    # Named in METHOD on every run; its table is a diagnostic, in PROOF.
    report = run_in(workspace)
    assert "1 instrument(s) have no rows on or after the cutoff" in report
    assert "US01609W1027" not in report.split("\nMETHOD\n")[0]
    shown = run_in(workspace, proof=True)
    proof = shown.split("\nPROOF\n", 1)[1].split("\nSOURCES\n")[0]
    assert "Pre-cutoff only (the account holder's, not mine)" in proof
    assert "US01609W1027" in proof
    # No post-cutoff activity: no row of zeros in the cash-flow table either.
    flows = report.split("## Cash flows per instrument", 1)[1].split("\n## ")[0]
    assert "US01609W1027" not in flows


def test_a_spanning_position_fifo_settles_at_zero_is_not_a_gap(workspace):
    """Inherited, then sold out with nothing bought after: known zero.

    Three positions on a real account. Reporting them as positions
    whose owner split is missing, and every weight as inflated by their
    absence, was wrong: they hold nothing of the user's.
    """
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(isin="US01609W1027", ticker="BABA", qty="0.5",
                time="2025-09-20 13:31:55+00:00", tx_id="EOF1"),
            sell(isin="US01609W1027", ticker="BABA", qty="0.5",
                 time="2025-10-15 13:31:55+00:00", tx_id="EOF2"),
            buy(qty="1.0", time="2025-10-20 09:48:15+00:00", tx_id="EOF3"),
        ],
    )
    report = run_in(workspace)
    assert "owner split of those shares is not in the export" not in report
    assert "larger than its share of the whole account" not in report
    assert "resolve to zero shares of mine (BABA)" in report
    assert "(floor) marker" not in report


def test_position_spanning_the_cutoff_is_not_attributable(workspace):
    """Bought before the cutoff, still traded after: no quantity claimed.

    A real export showed this shape -- the first row on or after the cutoff
    is a sell, so shares were already there.
    """
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            sell(isin="US67066G1040", ticker="NVDA", qty="0.5000000000",
                 time="2025-10-15 13:30:09+00:00", tx_id="EOF1"),
            buy(isin="US67066G1040", ticker="NVDA", qty="0.6000000000",
                time="2025-10-15 13:31:56+00:00", tx_id="EOF2"),
            buy(qty="1.0", time="2026-09-09 12:16:01+00:00", tx_id="EOF3"),
        ],
    )
    _, positions = load(data)
    states = states_for(positions, workspace)
    assert states["US67066G1040"] == t.SPANS_CUTOFF

    # Net is positive, so the old check would have passed it silently as a
    # real holding; it must not halt, and must not carry a weight.
    assert positions["US67066G1040"].net_qty > 0
    t.check_no_negative_quantity(positions, states)
    _, weights = t.cost_weights(positions, states)
    assert "US67066G1040" not in weights

    report = run_in(
        workspace,
        attribute=t.ATTRIBUTE_NONE,
        pies=(
            ("ETF", (("IE00BFY0GT14", "SPPW", "SPDR MSCI World (Acc)", "100%"),)),
            ("Stock", (("US67066G1040", "NVDA", "Nvidia", "100%"),)),
        ),
    )
    assert "Positions that existed at the cutoff" in report
    assert t.NOT_ATTRIBUTABLE in report
    assert "first row on or after cutoff is a sell on 2025-10-15" in report


def test_inherited_position_sold_out_does_not_halt(workspace):
    """Sells with no matching buy after the cutoff: inherited, not a bug."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            sell(isin="IE000XZSV718", ticker="SPXL", qty="2.0000000000",
                 time="2025-10-15 09:52:41+00:00", tx_id="EOF1"),
            buy(qty="1.0", time="2026-09-09 12:16:01+00:00", tx_id="EOF2"),
        ],
    )
    _, positions = load(data)
    states = states_for(positions, workspace)
    assert states["IE000XZSV718"] == t.SPANS_CUTOFF
    assert positions["IE000XZSV718"].net_qty < 0
    t.check_no_negative_quantity(positions, states)  # must not raise

    report = run_in(workspace, attribute=t.ATTRIBUTE_NONE)
    assert t.NOT_ATTRIBUTABLE in report
    assert "IE000XZSV718" in report


def test_post_cutoff_only_position_is_fully_mine(workspace):
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(qty="2.0", time="2025-10-20 09:48:15+00:00", tx_id="EOF1"),
            sell(qty="0.5", time="2026-09-09 12:16:01+00:00", tx_id="EOF2"),
        ],
    )
    _, positions = load(data)
    position = positions["IE00BFY0GT14"]
    assert position.pre_rows == 0
    assert position.net_qty == Decimal("1.5")

    states = states_for(positions, workspace)
    assert states["IE00BFY0GT14"] == t.MINE
    report = run_in(workspace, proof=True)
    assert "No position existed at the ownership cutoff" in report
    assert t.NOT_ATTRIBUTABLE not in report


def test_cutoff_boundary_is_inclusive(workspace):
    """A transaction dated exactly on the cutoff is mine."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [buy(qty="1.0", time="2025-10-13 00:00:01+00:00", tx_id="EOF1")],
    )
    _, positions = load(data)
    position = positions["IE00BFY0GT14"]
    assert position.net_qty == Decimal("1.0")
    assert position.pre_rows == 0
    assert states_for(positions, workspace)["IE00BFY0GT14"] == t.MINE

    # One second earlier is the account holder's.
    write_export(
        data,
        "b.csv",
        [buy(qty="1.0", time="2025-10-11 23:59:59+00:00", tx_id="EOF2")],
    )
    _, positions = load(data)
    assert positions["IE00BFY0GT14"].pre_rows == 1
    assert positions["IE00BFY0GT14"].net_qty == Decimal("1.0")


def test_cutoff_is_read_from_ownership_file_not_hardcoded(workspace):
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [buy(qty="1.0", time="2025-10-20 09:48:15+00:00", tx_id="EOF1")],
    )
    write_ownership(workspace / "ownership.md", cutoff="2026-01-01")
    ownership = t.load_ownership(workspace / "ownership.md")
    assert ownership.cutoff == date(2026, 1, 1)

    _, positions = load(data, ownership.cutoff)
    assert positions["IE00BFY0GT14"].pre_rows == 1
    assert positions["IE00BFY0GT14"].net_qty == Decimal(0)
    assert (
        t.classify_ownership(positions, ownership)["IE00BFY0GT14"]
        == t.PRE_CUTOFF_ONLY
    )


def test_cutoff_override_beats_the_file(workspace):
    ownership = t.load_ownership(
        workspace / "ownership.md", cutoff_override=date(2024, 5, 1)
    )
    assert ownership.cutoff == date(2024, 5, 1)
    assert "overriding 2025-10-13" in ownership.cutoff_source


def test_missing_ownership_file_halts_unless_cutoff_given(workspace):
    (workspace / "ownership.md").unlink()
    with pytest.raises(t.Halt, match="ownership file not found"):
        t.load_ownership(workspace / "ownership.md")
    ownership = t.load_ownership(
        workspace / "ownership.md", cutoff_override=date(2025, 10, 13)
    )
    assert ownership.cutoff == date(2025, 10, 13)
    assert ownership.declared == {}


UNHANDLED_KEYS = [
    ("HOLDER_CASH_AT_OWN_FROM", "unknown"),
    ("INDETERMINATE_HALT_ABOVE", "5%"),
    ("CASH_CONSUMPTION", "pro-rata"),
]


def write_lines(path: Path, lines) -> Path:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_policy(path: Path, block, body=()) -> Path:
    """An ownership file whose policy block holds exactly ``block``.

    The block occupies lines 1..len(block)+2, so a key at ``block[i]`` is on
    line ``i + 2``.
    """
    return write_lines(path, ["---", *block, "---", "", *body])


@pytest.mark.parametrize("key, value", UNHANDLED_KEYS)
def test_declared_but_unimplemented_key_halts(workspace, key, value):
    """A policy key this build ignores must stop the run, not be skipped.

    ownership.md reads as though the importer honours what it declares, so a
    key with nothing behind it is a silent claim about how the numbers were
    produced.
    """
    path = write_policy(
        workspace / "ownership.md",
        ["Last updated: 2026-09-17", "Cutoff: 2025-10-13", f"{key}: {value}"],
    )
    with pytest.raises(t.Halt) as excinfo:
        t.load_ownership(path)
    message = str(excinfo.value)
    assert f"declares {key}: {value}" in message
    assert "this build does not implement it" in message
    assert "Remove the line or implement the policy." in message
    assert "(line 4)" in message  # the key's own line, not the block's first


def test_unhandled_key_halts_wherever_it_sits(workspace):
    """Order must not matter: a parsed Cutoff does not excuse what follows."""
    for key, value in UNHANDLED_KEYS:
        path = write_policy(
            workspace / "ownership.md",
            [f"{key}: {value}", "Cutoff: 2025-10-13"],
        )
        with pytest.raises(t.Halt, match=f"declares {key}"):
            t.load_ownership(path)


def test_unhandled_key_halts_before_the_report_is_built(workspace):
    """The halt reaches a real run, not only the loader in isolation."""
    write_export(workspace / "data" / "t212", "a.csv", [buy(qty="1.0")])
    write_policy(
        workspace / "ownership.md",
        ["Cutoff: 2025-10-13", "CASH_CONSUMPTION: pro-rata"],
    )
    with pytest.raises(t.Halt, match="declares CASH_CONSUMPTION"):
        run_in(workspace)


def test_a_multi_word_key_in_the_block_still_halts(workspace):
    """Inside the block the shape is greedy, so no key escapes by spelling.

    A pattern that spared prose by matching only one or two bare words let
    `HOLDER CASH AT OWN FROM: 2025-06-01` through in silence: four tokens
    matched nothing, the line was skipped, and the guard reported success.
    Scoping by location removes the pattern, and with it that hole.
    """
    path = write_policy(
        workspace / "ownership.md",
        ["Cutoff: 2025-10-13", "HOLDER CASH AT OWN FROM: 2025-06-01"],
    )
    with pytest.raises(t.Halt) as excinfo:
        t.load_ownership(path)
    message = str(excinfo.value)
    assert "declares HOLDER CASH AT OWN FROM: 2025-06-01" in message
    assert "(line 3)" in message


def test_a_key_outside_the_block_is_not_a_declaration(workspace):
    """Below the fence nothing is policy, including what would halt above it."""
    path = write_policy(
        workspace / "ownership.md",
        ["Last updated: 2026-09-17", "Cutoff: 2025-10-13"],
        body=[
            "# Ownership",
            "",
            "CASH_CONSUMPTION: pro-rata",
            "HOLDER CASH AT OWN FROM: 2025-06-01",
            "",
            "The default is FIFO: sells are allocated against the lot.",
            "",
            "```",
            "INDETERMINATE_HALT_ABOVE: 5%",
            "```",
        ],
    )
    ownership = t.load_ownership(path)
    assert ownership.cutoff == date(2025, 10, 13)
    assert ownership.updated == "2026-09-17"


def test_a_missing_policy_block_halts_naming_the_file(workspace):
    """A file with no block is an error, never a silent empty parse."""
    path = write_lines(
        workspace / "ownership.md",
        ["# Ownership", "", "Cutoff: 2025-10-13"],
    )
    with pytest.raises(t.Halt, match="ownership.md: no policy block"):
        t.load_ownership(path)


def test_an_unclosed_policy_block_halts_naming_the_file(workspace):
    path = write_lines(
        workspace / "ownership.md",
        ["---", "Cutoff: 2025-10-13", "", "# Ownership"],
    )
    with pytest.raises(t.Halt, match="ownership.md: policy block opens"):
        t.load_ownership(path)


def test_a_non_declaration_inside_the_block_halts(workspace):
    path = write_lines(
        workspace / "ownership.md",
        ["---", "Cutoff: 2025-10-13", "just prose, no colon", "---"],
    )
    with pytest.raises(t.Halt, match="ownership.md:3: .* is not a 'Key: value'"):
        t.load_ownership(path)


def test_pies_is_scoped_the_same_way(workspace):
    """pies.md carries declarations too, so it carries the same guard."""
    path = workspace / "pies.md"
    write_pies(path)
    assert t.load_pies(path).updated == "2026-09-17"

    fence = "---" + chr(10)
    body = path.read_text(encoding="utf-8").split(fence, 2)[2].lstrip(chr(10))
    write_lines(path, ["---", "TARGET_TOLERANCE_PP: 0.5", "---", "", body])
    with pytest.raises(t.Halt, match="declares TARGET_TOLERANCE_PP"):
        t.load_pies(path)

    write_lines(path, [body])
    with pytest.raises(t.Halt, match="pies.md: no policy block"):
        t.load_pies(path)


@pytest.mark.skipif(
    not (Path(__file__).resolve().parents[1] / "me" / "ownership.md").is_file(),
    reason="no me/ folder: this copy has not run setup",
)
def test_the_users_policy_files_load():
    """The user's own files must satisfy the rule they are the subject of.

    Every key they declare is one the importer honours; the cash-provenance
    policies ownership.md used to carry are prose in DECISIONS.md, read by
    nothing.
    """
    root = Path(__file__).resolve().parents[1]
    ownership = t.load_ownership(root / "me" / "ownership.md")
    assert ownership.cutoff_source == "ownership.md"
    t.load_pies(root / "me" / "pies.md")


def test_handled_keys_are_read_not_merely_tolerated(workspace):
    """Membership of a key set is a claim that the value is used."""
    path = write_policy(
        workspace / "ownership.md",
        [
            "Last updated: 2026-09-17",
            "Cutoff: 2025-10-13",
            f"Fixed rate: {BGN_RATE}",
        ],
    )
    ownership = t.load_ownership(path)
    assert ownership.cutoff == date(2025, 10, 13)
    assert ownership.updated == "2026-09-17"
    assert ownership.fixed_rate.rate == Decimal("1.95583")
    assert t.OWNERSHIP_KEYS == {"CUTOFF", "FIXED RATE", "LAST UPDATED"}
    assert t.PIES_KEYS == {"LAST UPDATED"}


def test_prose_with_a_colon_is_not_read_as_a_declaration(workspace):
    """ownership.md is prose as well as policy; a sentence is not a key.

    Every line below the fence keeps its shape -- a sentence with a colon, a
    key inside a fenced sample -- and none of them is read, because of where
    they sit rather than what they look like.
    """
    path = write_lines(
        workspace / "ownership.md",
        [
            "---",
            "Cutoff: 2025-10-13",
            "---",
            "",
            "# Ownership",
            "",
            "The default is FIFO: sells are allocated against the inherited lot.",
            "`--attribute none` opts out: those positions carry no quantity.",
            "opened *after* the cutoff still does: that one is missing data.",
            "",
            "```",
            "CASH_CONSUMPTION: pro-rata",
            "```",
        ],
    )
    assert t.load_ownership(path).cutoff == date(2025, 10, 13)


def test_declared_isin_is_excluded_even_when_it_looks_clean(workspace):
    """The file carries what the CSV cannot express, so it wins."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(isin="US0378331005", ticker="AAPL", qty="1.0",
                time="2026-06-18 14:08:08+00:00", tx_id="EOF1"),
            buy(qty="1.0", time="2026-09-09 12:16:01+00:00", tx_id="EOF2"),
        ],
    )
    write_ownership(
        workspace / "ownership.md",
        declared=(("US0378331005", "AAPL", "Apple", "transferred in"),),
    )
    _, positions = load(data)
    ownership = t.load_ownership(workspace / "ownership.md")
    states = t.classify_ownership(positions, ownership)
    assert states["US0378331005"] == t.SPANS_CUTOFF

    notes = t.reconcile_ownership(positions, states, ownership)
    assert any("opening with a buy on 2026-06-18" in note for note in notes)
    report = run_in(workspace)
    assert "transferred in" in report


def test_undeclared_pre_cutoff_position_is_reported(workspace):
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            sell(isin="IE000XZSV718", ticker="SPXL", qty="2.0",
                 time="2025-10-15 09:52:41+00:00", tx_id="EOF1"),
            buy(qty="1.0", time="2026-09-09 12:16:01+00:00", tx_id="EOF2"),
        ],
    )
    _, positions = load(data)
    ownership = t.load_ownership(workspace / "ownership.md")  # declares nothing
    states = t.classify_ownership(positions, ownership)
    notes = t.reconcile_ownership(positions, states, ownership)
    assert any("IE000XZSV718 SPXL looks pre-cutoff" in note for note in notes)


def test_dividend_rows_do_not_move_quantity(workspace):
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(isin="IE00B3XXRP09", ticker="VUSA", qty="0.5000000000",
                tx_id="EOF1"),
            dividend(),  # 'No. of shares' repeats the whole holding
        ],
    )
    _, positions = load(data)
    position = positions["IE00B3XXRP09"]
    assert position.net_qty == Decimal("0.5000000000")
    assert position.dividends["EUR"] == Decimal("0.15")
    assert position.trades == 1


def test_parenthesised_and_order_type_actions_classify(workspace):
    assert t.classify_action("Dividend (Dividend)") == "dividend"
    assert (
        t.classify_action("Dividend (Dividends paid by us corporations)")
        == "dividend"
    )
    assert t.classify_action("Market buy") == "buy"
    assert t.classify_action("Limit sell") == "sell"
    assert t.classify_action("Stop limit buy") == "buy"
    assert t.classify_action("Interest on cash") == "cash"
    assert t.classify_action("Stock split") == "unknown"


def test_unknown_action_with_shares_halts(workspace):
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [row(action="Stock split", isin="US67066G1040", ticker="NVDA",
             qty="10.0", time="2026-06-01 10:00:00+00:00", tx_id="X1")],
    )
    with pytest.raises(t.Halt, match="Stock split"):
        load(data)


def test_unknown_cash_action_without_shares_only_warns(workspace):
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            row(action="Mystery adjustment", time="2026-06-01 10:00:00+00:00",
                total="1.00", total_ccy="EUR", tx_id="X1"),
            buy(qty="1.0", tx_id="EOF1"),
        ],
    )
    ledger, positions = load(data)
    assert len(ledger.warnings) == 1
    assert "Mystery adjustment" in ledger.warnings[0]
    assert positions["IE00BFY0GT14"].net_qty == Decimal("1.0")


# --------------------------------------------------------------------------
# Deduplication
# --------------------------------------------------------------------------


def test_overlapping_exports_dedup_by_id(workspace):
    data = workspace / "data" / "t212"
    shared = buy(qty="1.0", tx_id="EOF40302306564")
    write_export(data, "full_history.csv", [shared, buy(qty="2.0", tx_id="EOF2")])
    write_export(data, "recent.csv", [shared])
    ledger, positions = load(data)
    assert ledger.rows_read == 3
    assert len(ledger.txs) == 2
    assert len(ledger.duplicates) == 1
    assert positions["IE00BFY0GT14"].net_qty == Decimal("3.0")


def test_dividend_dedup_falls_back_to_date_isin_qty_price(workspace):
    """Dividend rows have no ID, so the fallback key is what dedups them."""
    data = workspace / "data" / "t212"
    shared = dividend()
    write_export(data, "full_history.csv", [shared])
    write_export(data, "recent.csv", [shared])
    ledger, positions = load(data)
    assert len(ledger.txs) == 1
    assert len(ledger.duplicates) == 1
    assert positions["IE00B3XXRP09"].dividends["EUR"] == Decimal("0.15")


def test_two_distinct_dividends_same_day_are_not_merged(workspace):
    """Same ISIN, same day, different timestamps: two separate payments."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            dividend(time="2026-04-01 15:10:44+00:00"),
            dividend(time="2026-04-01 18:22:03+00:00"),
        ],
    )
    ledger, positions = load(data)
    assert len(ledger.txs) == 2
    assert positions["IE00B3XXRP09"].dividends["EUR"] == Decimal("0.30")


def test_same_id_with_different_values_halts(workspace):
    data = workspace / "data" / "t212"
    write_export(data, "a.csv", [buy(qty="1.0", tx_id="EOF9")])
    write_export(data, "b.csv", [buy(qty="2.0", tx_id="EOF9")])
    with pytest.raises(t.Halt) as excinfo:
        load(data)
    assert "EOF9" in str(excinfo.value)
    assert "one of these rows is not what it claims" in str(excinfo.value)


def test_fallback_key_collision_with_different_total_halts(workspace):
    """Identical date+ISIN+qty+price but a different Total is not a duplicate."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [dividend(total="0.16"), dividend(total="0.19")],
    )
    with pytest.raises(t.Halt) as excinfo:
        load(data)
    assert "timestamp+ISIN+quantity+price" in str(excinfo.value)
    assert "IE00B3XXRP09" in str(excinfo.value)


# --------------------------------------------------------------------------
# Currency handling
# --------------------------------------------------------------------------


def test_gbx_priced_position_needs_no_rescale(workspace):
    """MEUD trades in pence; the row's own rate is quoted per GBX."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(isin="LU0908500753", ticker="MEUD", qty="0.1000000000",
                price="27000.0000000000", price_ccy="GBX", fx="86.00000000",
                total="31.45", total_ccy="EUR", tx_id="EOF1", fee="0.05",
                fee_ccy="EUR"),
        ],
    )
    _, positions = load(data)
    # Cost comes from the row's own Total in EUR, so a pence-quoted price
    # never has to be rescaled to reach it.
    assert positions["LU0908500753"].cost_basis() == {"EUR": Decimal("31.45")}


def test_cash_is_grouped_by_currency_never_summed(workspace):
    """This account's Total currency changes from BGN to EUR mid-history."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(qty="0.2566032200", total="20.00", total_ccy="BGN",
                time="2025-10-15 09:48:15+00:00", tx_id="EOF1"),
            buy(qty="0.1445765600", total="5.97", total_ccy="EUR",
                time="2026-02-09 08:04:49+00:00", tx_id="EOF2"),
        ],
    )
    _, positions = load(data)
    assert dict(positions["IE00BFY0GT14"].buy_cost) == {
        "BGN": Decimal("20.00"),
        "EUR": Decimal("5.97"),
    }


def test_mixed_cost_currencies_report_weights_unavailable(workspace):
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(qty="1.0", total="20.00", total_ccy="BGN",
                time="2025-10-15 09:48:15+00:00", tx_id="EOF1"),
            buy(isin="US0378331005", ticker="AAPL", qty="1.0",
                price="299.09", price_ccy="USD", fx="1.14738997",
                total="15.06", total_ccy="EUR",
                time="2026-06-18 14:08:08+00:00", tx_id="EOF2"),
        ],
    )
    _, positions = load(data)
    assert t.cost_weights(positions) is None

    report = run_in(workspace)
    # Listed under Not available with the currencies that blocked the sum.
    assert "cost-basis weights - cost bases denominated in BGN, EUR" in report
    assert "no rate declared in ownership.md" in report


def _mixed_book(workspace):
    """20.00 BGN of SPPW and 15.06 EUR of AAPL, as in the real account."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(qty="1.0", total="20.00", total_ccy="BGN",
                time="2025-10-15 09:48:15+00:00", tx_id="EOF1"),
            buy(isin="US0378331005", ticker="AAPL", qty="1.0",
                price="299.09", price_ccy="USD", fx="1.14738997",
                total="15.06", total_ccy="EUR",
                time="2026-06-18 14:08:08+00:00", tx_id="EOF2"),
        ],
    )
    return load(data)[1]


def test_declared_fixed_rate_weights_a_mixed_book_in_its_base(workspace):
    """BGN restated at the declared rate; the arithmetic is redone here."""
    positions = _mixed_book(workspace)
    rate = t.parse_fixed_rate(BGN_RATE, "test")
    currency, weights = t.cost_weights(positions, fixed_rate=rate)
    assert currency == "EUR"
    sppw = Decimal("20.00") / Decimal("1.95583")
    total = sppw + Decimal("15.06")
    assert weights["IE00BFY0GT14"] == sppw * 100 / total
    assert weights["US0378331005"] == Decimal("15.06") * 100 / total
    assert abs(sum(weights.values()) - Decimal(100)) < Decimal("0.0001")


def test_fixed_rate_that_misses_a_currency_is_still_refused(workspace):
    """A USD/EUR rate cannot stand in for BGN: the book stays Not available."""
    positions = _mixed_book(workspace)
    rate = t.parse_fixed_rate("1 EUR = 1.1 USD (made up for the test)", "test")
    assert t.cost_weights(positions, fixed_rate=rate) is None
    write_ownership(
        workspace / "ownership.md", fixed_rate="1 EUR = 1.1 USD (test only)"
    )
    report = run_in(workspace)
    assert "the declared 1 EUR = 1.1 USD does not cover BGN" in report


def test_report_prints_the_restated_column_and_its_proof(workspace):
    _mixed_book(workspace)
    write_ownership(workspace / "ownership.md", fixed_rate=BGN_RATE)
    report = run_in(workspace, proof=True)
    # 20.00 / 1.95583 = 10.2258...; with 15.06 EUR the column adds to 25.29.
    assert "| Cost basis | Cost basis (EUR) | Weight (cost) |" in report
    assert "| 20.00 BGN | 10.23 EUR |" in report
    assert "20.00 BGN / 1.95583 = 10.23 EUR -> 10.23 EUR" in report
    assert "10.23 + 15.06 = 25.29 EUR" in report
    assert "BGN restated at the fixed 1 EUR = 1.95583 BGN" in report
    assert "cost-basis weights -" not in report
    # The rate's source is a SOURCES row, with its URL.
    sources = report.split("\nSOURCES\n", 1)[1]
    assert "Council Regulation (EU) 2025/1409" in sources
    assert "CELEX:32025R1409" in sources


def test_single_currency_book_ignores_the_rate(workspace):
    """A rate is only reached for when the book needs it."""
    data = workspace / "data" / "t212"
    write_export(data, "a.csv", [buy(qty="1.0", total="20.00", total_ccy="EUR",
                                     time="2026-02-09 08:04:49+00:00", tx_id="E1")])
    write_ownership(workspace / "ownership.md", fixed_rate=BGN_RATE)
    report = run_in(workspace)
    assert "Cost basis (EUR)" not in report
    assert "restated" not in report


@pytest.mark.parametrize(
    "value, message",
    [
        ("1 EUR = 1.95583 BGN", "The source is required"),
        ("1.95583", "is not '1 EUR = 1.95583 BGN"),
        ("1 EUR = 0 BGN (x)", "positive rate"),
        ("1 EUR = 1 EUR (x)", "two different currencies"),
    ],
)
def test_malformed_fixed_rate_halts(workspace, value, message):
    path = write_policy(
        workspace / "ownership.md",
        ["Last updated: 2026-09-17", "Cutoff: 2025-10-13", f"Fixed rate: {value}"],
    )
    with pytest.raises(t.Halt, match=message) as info:
        t.load_ownership(path)
    assert info.value.figure == "ownership.md:4"


def test_fx_direction_audit_separates_trades_from_dividends(workspace):
    """Trade Totals divide by 'Exchange rate'; dividend Totals multiply."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(isin="IE00B3XXRP09", ticker="VUSA", qty="0.2000000000",
                price="100.0000000000", price_ccy="GBP", fx="0.86000000",
                total="23.29", total_ccy="EUR", tx_id="EOF1", fee="0.03",
                fee_ccy="EUR"),
            dividend(),  # 0.15 multiplying vs 0.10 dividing, on 0.15
        ],
    )
    ledger, _ = load(data)
    audit = t.fx_direction_audit(ledger.txs)
    assert audit["buy"]["divide"] == 1
    assert audit["buy"]["neither"] == 0
    assert audit["dividend"]["multiply"] == 1
    assert audit["dividend"]["neither"] == 0


def test_sub_cent_dividend_is_ambiguous_not_wrong(workspace):
    """At 0.01 the cent rounding is larger than the gap between directions.

    The audit reports buckets rather than asserting one direction so these
    rows stay honest instead of being forced into the wrong one.
    """
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            dividend(isin="US02079K3059", ticker="GOOGL", qty="0.0669917300",
                     price="0.198000", price_ccy="USD", fx="0.86428200",
                     total="0.01", time="2026-09-14 11:14:28+00:00"),
        ],
    )
    ledger, _ = load(data)
    audit = t.fx_direction_audit(ledger.txs)
    assert audit["dividend"]["ambiguous"] == 1
    assert audit["dividend"]["neither"] == 0


# --------------------------------------------------------------------------
# File and schema handling
# --------------------------------------------------------------------------


def test_zero_byte_export_is_empty_not_malformed(workspace):
    data = workspace / "data" / "t212"
    (data / "from_2026-09-17_to_2026-09-17.csv").write_text("", encoding="utf-8")
    ledger, positions = load(data)
    assert ledger.empty_files and not ledger.txs
    assert positions == {}

    report = run_in(workspace)
    assert "no rows" in report
    assert "zero-byte file" in report


def test_bom_and_crlf_are_tolerated(workspace):
    data = workspace / "data" / "t212"
    write_export(data, "a.csv", [buy(qty="1.5")], newline="\r\n", bom="\ufeff")
    _, positions = load(data)
    assert positions["IE00BFY0GT14"].net_qty == Decimal("1.5")


def test_missing_required_column_halts(workspace):
    data = workspace / "data" / "t212"
    header = [c for c in HEADER if c != "ISIN"]
    (data / "a.csv").write_text(
        csv_text([buy(qty="1.0")], header=header), encoding="utf-8"
    )
    with pytest.raises(t.Halt, match="missing required column"):
        load(data)


def test_unrecognised_column_is_noted_not_fatal(workspace):
    data = workspace / "data" / "t212"
    header = HEADER + ["Sustainability score"]
    (data / "a.csv").write_text(
        csv_text([buy(qty="1.0")], header=header), encoding="utf-8"
    )
    ledger, positions = load(data)
    assert positions["IE00BFY0GT14"].net_qty == Decimal("1.0")
    assert any("Sustainability score" in note for note in ledger.schema_notes)


def test_empty_data_dir_points_at_the_space_named_sibling(workspace, monkeypatch):
    monkeypatch.chdir(workspace)
    (workspace / "data t212").mkdir()
    write_export(workspace / "data t212", "a.csv", [buy()])
    with pytest.raises(t.Halt) as excinfo:
        t.load_transactions(Path("data/t212"))
    assert "data t212" in str(excinfo.value)


# --------------------------------------------------------------------------
# pies.md and weights
# --------------------------------------------------------------------------


def test_pies_mapping_parses(workspace):
    pies = t.load_pies(
        write_pies(
            workspace / "pies.md",
            pies=(
                (
                    "ETF",
                    (
                        ("IE00BFY0GT14", "SPPW", "SPDR MSCI World (Acc)", "55%"),
                        ("LU0908500753", "MEUD", "Amundi Stoxx 600 (Acc)", "20%"),
                        ("IE00BKM4GZ66", "EIMI", "iShares EM IMI (Acc)", "15%"),
                        ("IE00B3XXRP09", "VUSA", "Vanguard S&P 500 (Dist)", "10%"),
                    ),
                ),
                ("Stock", (("US0378331005", "AAPL", "Apple", "100%"),)),
            ),
            excluded=(
                ("IE00B53SZB19", "CNDX", "iShares NASDAQ 100 (Acc)",
                 "closed 2026-09-09"),
            ),
        )
    )
    assert pies.shares == {"ETF": Decimal(75), "Stock": Decimal(25)}
    assert pies.pie_of("IE00BFY0GT14") == "ETF"
    assert pies.target_of_portfolio("IE00BFY0GT14") == Decimal("41.25")
    assert pies.excluded["IE00B53SZB19"] == "closed 2026-09-09"
    assert pies.updated == "2026-09-17"


def test_weights_summing_to_100_pass(workspace):
    pies = t.load_pies(write_pies(workspace / "pies.md"))
    notes = t.check_weights_sum(pies, {})
    assert any("100" in note for note in notes)


def test_in_pie_weights_off_by_more_than_tolerance_halt(workspace):
    pies = t.load_pies(
        write_pies(
            workspace / "pies.md",
            pies=(
                (
                    "ETF",
                    (
                        ("IE00BFY0GT14", "SPPW", "SPDR MSCI World (Acc)", "55%"),
                        ("IE00B3XXRP09", "VUSA", "Vanguard S&P 500 (Dist)", "45.2%"),
                    ),
                ),
                ("Stock", (("US0378331005", "AAPL", "Apple", "100%"),)),
            ),
        )
    )
    with pytest.raises(t.Halt) as excinfo:
        t.check_weights_sum(pies, {})
    assert "'ETF'" in str(excinfo.value)
    assert "100.2" in str(excinfo.value)


def test_in_pie_weights_within_tolerance_pass(workspace):
    pies = t.load_pies(
        write_pies(
            workspace / "pies.md",
            pies=(
                (
                    "ETF",
                    (
                        ("IE00BFY0GT14", "SPPW", "SPDR MSCI World (Acc)", "55%"),
                        ("IE00B3XXRP09", "VUSA", "Vanguard S&P 500 (Dist)", "45.05%"),
                    ),
                ),
                ("Stock", (("US0378331005", "AAPL", "Apple", "100%"),)),
            ),
        )
    )
    t.check_weights_sum(pies, {})  # 100.05% is inside 0.1pp


def test_pie_shares_not_summing_to_100_halt(workspace):
    pies = t.load_pies(
        write_pies(
            workspace / "pies.md", shares=(("ETF", "75%"), ("Stock", "20%"))
        )
    )
    with pytest.raises(t.Halt) as excinfo:
        t.check_weights_sum(pies, {})
    assert "pie shares sum to 95%" in str(excinfo.value)


def test_duplicate_isin_across_pies_halts(workspace):
    path = write_pies(
        workspace / "pies.md",
        pies=(
            ("ETF", (("IE00BFY0GT14", "SPPW", "SPDR MSCI World (Acc)", "100%"),)),
            ("Stock", (("IE00BFY0GT14", "SPPW", "SPDR MSCI World (Acc)", "100%"),)),
        ),
    )
    with pytest.raises(t.Halt, match="appears in both"):
        t.load_pies(path)


def test_pie_with_holdings_but_no_share_halts(workspace):
    path = write_pies(workspace / "pies.md", shares=(("ETF", "100%"),))
    with pytest.raises(t.Halt) as excinfo:
        t.load_pies(path)
    assert "Stock" in str(excinfo.value)


def test_held_isin_absent_from_pies_halts(workspace):
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [buy(isin="IE00B53SZB19", ticker="CNDX", qty="0.01", tx_id="EOF1")],
    )
    _, positions = load(data)
    pies = t.load_pies(write_pies(workspace / "pies.md"))
    with pytest.raises(t.Halt) as excinfo:
        t.check_mapping_covers_holdings(pies, positions)
    assert "IE00B53SZB19" in str(excinfo.value)
    assert "CNDX" in str(excinfo.value)


def test_closed_isin_absent_from_pies_does_not_halt(workspace):
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(isin="IE00B53SZB19", ticker="CNDX", qty="0.01", tx_id="EOF1"),
            sell(isin="IE00B53SZB19", ticker="CNDX", qty="0.01", tx_id="EOF2"),
        ],
    )
    _, positions = load(data)
    pies = t.load_pies(write_pies(workspace / "pies.md"))
    t.check_mapping_covers_holdings(pies, positions)


def test_cost_weights_sum_to_100(workspace):
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(qty="2.3000000000", price="46.0230000000", price_ccy="EUR",
                fx="1.00000000", total="105.85", total_ccy="EUR", tx_id="EOF1"),
            buy(isin="US0378331005", ticker="AAPL", qty="0.1200000000",
                price="316.0900000000", price_ccy="USD", fx="1.16480969",
                total="32.56", total_ccy="EUR", tx_id="EOF2"),
        ],
    )
    _, positions = load(data)
    currency, weights = t.cost_weights(positions)
    assert currency == "EUR"
    assert abs(sum(weights.values()) - Decimal(100)) < Decimal("0.0001")


# --------------------------------------------------------------------------
# End to end
# --------------------------------------------------------------------------


def test_run_produces_report_with_header_block(workspace):
    data = workspace / "data" / "t212"
    write_export(
        data,
        "full_history.csv",
        [
            row(action="Deposit", time="2025-10-15 07:20:26+00:00",
                notes="Bank Transfer", tx_id="8c64c369", total="100.00",
                total_ccy="BGN"),
            buy(qty="2.3000000000", price="46.0230000000", price_ccy="EUR",
                fx="1.00000000", total="105.85", total_ccy="EUR",
                time="2026-09-09 12:16:01+00:00", tx_id="EOF1"),
            buy(isin="US0378331005", ticker="AAPL", qty="0.1200000000",
                price="316.0900000000", price_ccy="USD", fx="1.16480969",
                total="32.56", total_ccy="EUR",
                time="2026-09-09 13:30:12+00:00", tx_id="EOF2"),
            dividend(isin="US0378331005", ticker="AAPL", qty="0.0759001700",
                     price="0.243000", price_ccy="USD", fx="0.86759600",
                     total="0.02", time="2026-08-13 14:10:47+00:00"),
        ],
    )
    report = run_in(workspace, proof=True)
    assert "Data as of:      2026-09-09" in report
    assert "Coverage:        2 open position(s) attributable" in report
    assert "IE00BFY0GT14" in report and "US0378331005" in report
    assert "No attributable position has negative net quantity" in report
    assert "0.02 EUR" in report  # dividend, in its own currency column


def test_main_exit_codes(workspace, monkeypatch, capsys):
    monkeypatch.chdir(workspace)
    data = workspace / "data" / "t212"
    write_export(data, "a.csv", [buy(qty="1.0")])
    # main() reads the user's files from me/ by default
    (workspace / "me").mkdir()
    (workspace / "me" / "ownership.md").write_bytes((workspace / "ownership.md").read_bytes())
    write_pies(workspace / "me" / "pies.md")
    assert t.main([]) == 0
    assert t.main(["--attribute", "none"]) == 0

    write_export(
        data,
        "b.csv",
        [sell(isin="IE000XZSV718", ticker="SPXL", qty="5.0", tx_id="EOF99")],
    )
    assert t.main([]) == 0  # inherited position: reported, not fatal

    write_export(
        data,
        "c.csv",
        [sell(qty="99.0", time="2026-09-10 12:16:01+00:00", tx_id="EOF98")],
    )
    capsys.readouterr()  # drop the complete runs above
    assert t.main([]) == 1
    halted = capsys.readouterr()
    assert halted.err == ""  # a halt prints on stdout, like any other run
    assert "HALTED - check_no_negative_quantity" in halted.out
    assert "IE00BFY0GT14" in halted.out


# --------------------------------------------------------------------------
# FIFO attribution
# --------------------------------------------------------------------------


def attribute(data: Path, cutoff: date = CUTOFF):
    ledger = t.load_transactions(data)
    return t.fifo_attribution(ledger.txs, cutoff)


def test_fifo_sells_consume_the_inherited_lot_first(workspace):
    """Whole inherited lot sold off: everything left is mine.

    Inherited 1.0 before the cutoff, then I buy 4.0 and sell 3.0. FIFO takes
    the 1.0 inherited first, then 2.0 of mine, leaving me 2.0 and the holder 0.
    """
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(qty="1.0", time="2025-10-08 13:30:08+00:00", tx_id="EOF1"),
            buy(qty="4.0", time="2025-10-20 13:30:08+00:00", tx_id="EOF2"),
            sell(qty="3.0", time="2026-01-15 13:30:08+00:00", tx_id="EOF3"),
        ],
    )
    a = attribute(data)["IE00BFY0GT14"]
    assert a.inherited_at_cutoff == Decimal("1.0")
    assert a.mine_qty == Decimal("2.0")
    assert a.holder_qty == Decimal("0")
    assert a.unbacked_sold == Decimal("0")
    assert not a.is_floor


def test_fifo_leaves_the_inherited_lot_intact_when_sells_are_small(workspace):
    """Inherited 5.0, I buy 3.0 and sell 1.0: the sell is all the holder's."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(qty="5.0", time="2025-10-08 13:30:08+00:00", tx_id="EOF1"),
            buy(qty="3.0", time="2025-10-20 13:30:08+00:00", tx_id="EOF2"),
            sell(qty="1.0", total="46.02", time="2026-01-15 13:30:08+00:00",
                 tx_id="EOF3"),
        ],
    )
    a = attribute(data)["IE00BFY0GT14"]
    assert a.mine_qty == Decimal("3.0")
    assert a.holder_qty == Decimal("4.0")
    assert dict(a.holder_proceeds) == {"EUR": Decimal("46.02")}
    assert dict(a.mine_proceeds) == {}


def test_fifo_splits_one_sell_row_between_owners(workspace):
    """A sell that straddles two lots splits that row's Total pro rata."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(qty="1.0", time="2025-10-08 13:30:08+00:00", tx_id="EOF1"),
            buy(qty="3.0", time="2025-10-20 13:30:08+00:00", tx_id="EOF2"),
            sell(qty="2.0", total="100.00", time="2026-01-15 13:30:08+00:00",
                 tx_id="EOF3"),
        ],
    )
    a = attribute(data)["IE00BFY0GT14"]
    assert a.holder_qty == Decimal("0")
    assert a.mine_qty == Decimal("2.0")
    # 1.0 of the 2.0 sold was the holder's, so half the proceeds are theirs.
    assert a.holder_proceeds["EUR"] == Decimal("50.00")
    assert a.mine_proceeds["EUR"] == Decimal("50.00")


def test_fifo_marks_a_floor_when_sells_have_no_backing_lot(workspace):
    """SPXL: sold with no buy anywhere in the export.

    The inherited lot is understated, which makes FIFO attribute too little to
    me -- so the quantity is a lower bound and must say so.
    """
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            sell(isin="IE000XZSV718", ticker="SPXL", qty="2.0000000000",
                 total="57.95", time="2025-10-15 09:52:41+00:00", tx_id="EOF1"),
        ],
    )
    a = attribute(data)["IE000XZSV718"]
    assert a.mine_qty == Decimal("0")
    assert a.unbacked_sold == Decimal("2.0000000000")
    assert a.is_floor
    assert a.describe_qty().startswith(">= 0.0000000000 (FIFO, floor)")
    assert a.holder_proceeds["EUR"] == Decimal("57.95")


def test_fifo_attributed_position_enters_the_weights(workspace):
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(isin="US67066G1040", ticker="NVDA", qty="1.0", price="200.00",
                price_ccy="EUR", total="200.00",
                time="2025-10-08 13:30:08+00:00", tx_id="EOF1"),
            buy(isin="US67066G1040", ticker="NVDA", qty="4.0", price="200.00",
                price_ccy="EUR", total="800.00",
                time="2025-10-20 13:30:08+00:00", tx_id="EOF2"),
            sell(isin="US67066G1040", ticker="NVDA", qty="3.0", price="200.00",
                 price_ccy="EUR", total="600.00",
                 time="2026-01-15 13:30:08+00:00", tx_id="EOF3"),
            buy(qty="2.0", price="200.00", price_ccy="EUR", total="400.00",
                time="2026-09-09 12:16:01+00:00", tx_id="EOF4"),
        ],
    )
    ledger, positions = load(data)
    states = states_for(positions, workspace)
    assert states["US67066G1040"] == t.SPANS_CUTOFF

    # Without attribution NVDA is excluded; with it, it is half the account.
    _, bare = t.cost_weights(positions, states)
    assert "US67066G1040" not in bare

    attributions = t.fifo_attribution(ledger.txs, CUTOFF)
    _, weighted = t.cost_weights(positions, states, attributions)
    assert weighted["US67066G1040"] == Decimal(50)
    assert weighted["IE00BFY0GT14"] == Decimal(50)
    assert abs(sum(weighted.values()) - Decimal(100)) < Decimal("0.0001")


def test_cost_basis_keeps_surviving_lots_at_their_own_unit_cost(workspace):
    """FIFO: a sell eats the oldest lot, the rest keep what they cost."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(qty="2.0", total="100.00", time="2026-01-05 09:00:00+00:00",
                tx_id="EOF1"),
            buy(qty="1.0", total="80.00", time="2026-02-05 09:00:00+00:00",
                tx_id="EOF2"),
            sell(qty="1.0", total="60.00", time="2026-03-05 09:00:00+00:00",
                 tx_id="EOF3"),
        ],
    )
    _, positions = load(data)
    # 1 share left of the 50.00 lot, 1 share of the 80.00 lot.
    assert positions["IE00BFY0GT14"].cost_basis() == {"EUR": Decimal("130.00")}


def test_weights_follow_cost_not_the_last_traded_price(workspace):
    """Equal money in, equal weight - whatever each last traded at.

    The old table valued each position at its last transacted price, which
    dates every row differently (portfolio-sync.md Step 4). A later trade at
    a very different price must not move a cost weight.
    """
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(qty="2.0", price="50.00", total="100.00",
                time="2026-01-05 09:00:00+00:00", tx_id="EOF1"),
            buy(isin="US0378331005", ticker="AAPL", qty="1.0", price="100.00",
                total="100.00", time="2026-01-05 09:00:00+00:00", tx_id="EOF2"),
            buy(isin="US0378331005", ticker="AAPL", qty="0.0000000001",
                price="900.00", total="0.00",
                time="2026-09-01 09:00:00+00:00", tx_id="EOF3"),
        ],
    )
    _, positions = load(data)
    _, weights = t.cost_weights(positions)
    assert weights["IE00BFY0GT14"] == Decimal(50)
    assert weights["US0378331005"] == Decimal(50)


def test_open_positions_table_has_no_last_price_value_or_drift(workspace):
    """The removed columns stay removed: no last-px value, no drift reading."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [buy(qty="1.0", total="100.00", tx_id="EOF1")],
    )
    report = run_in(
        workspace,
        pies=(
            ("ETF", (("IE00BFY0GT14", "SPPW", "SPDR MSCI World (Acc)", "100%"),)),
        ),
        shares=(("ETF", "100%"),),
    )
    result = report.split("RESULT", 1)[1].split("METHOD", 1)[0]
    header = next(line for line in result.splitlines() if line.startswith("| Pie"))
    assert "Weight (cost)" in header and "Cost basis" in header
    for gone in ("Value (last px)", "Last traded", "Drift", "Actual"):
        assert gone not in header, gone
    assert "drift" not in result.lower()
    assert "100 EUR" in result or "100.00 EUR" in result
    assert "weights on cost basis (EUR)" in report


def test_floored_position_prints_weight_bounds(workspace):
    """A floor's cost is a lower bound, so its weight is too; others are caps."""
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            sell(isin="US67066G1040", ticker="NVDA", qty="0.5", total="100.00",
                 time="2025-10-15 13:30:09+00:00", tx_id="EOF1"),
            buy(isin="US67066G1040", ticker="NVDA", qty="1.0", total="200.00",
                time="2025-10-20 13:30:09+00:00", tx_id="EOF2"),
            buy(qty="1.0", total="200.00", time="2026-09-09 12:16:01+00:00",
                tx_id="EOF3"),
        ],
    )
    ledger, positions = load(data)
    states = states_for(positions, workspace)
    attributions = t.fifo_attribution(ledger.txs, CUTOFF)
    assert attributions["US67066G1040"].is_floor
    assert attributions["US67066G1040"].cost_basis() == {"EUR": Decimal("200.00")}
    _, weights = t.cost_weights(positions, states, attributions)
    assert weights == {"US67066G1040": Decimal(50), "IE00BFY0GT14": Decimal(50)}

    report = run_in(
        workspace,
        pies=(
            ("ETF", (("IE00BFY0GT14", "SPPW", "SPDR MSCI World (Acc)", "100%"),)),
            ("Stock", (("US67066G1040", "NVDA", "Nvidia", "100%"),)),
        ),
    )
    result = report.split("RESULT", 1)[1].split("METHOD", 1)[0]
    nvda = next(line for line in result.splitlines() if "US67066G1040" in line)
    sppw = next(line for line in result.splitlines() if "IE00BFY0GT14" in line)
    assert ">= 50%" in nvda and "(floor)" in nvda
    assert "<= 50%" in sppw


def test_fifo_mode_is_on_by_default(workspace):
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            sell(isin="US67066G1040", ticker="NVDA", qty="0.5",
                 time="2025-10-15 13:30:09+00:00", tx_id="EOF1"),
            buy(isin="US67066G1040", ticker="NVDA", qty="1.0",
                time="2025-10-20 13:31:56+00:00", tx_id="EOF2"),
            buy(qty="1.0", time="2026-09-09 12:16:01+00:00", tx_id="EOF3"),
        ],
    )
    pies_kwargs = dict(
        pies=(
            ("ETF", (("IE00BFY0GT14", "SPPW", "SPDR MSCI World (Acc)", "100%"),)),
            ("Stock", (("US67066G1040", "NVDA", "Nvidia", "100%"),)),
        )
    )
    default = run_in(workspace, **pies_kwargs)
    assert "- Attribution: FIFO" in default  # METHOD, not the header block
    assert t.NOT_ATTRIBUTABLE not in default
    assert "(FIFO, floor)" in default  # the 0.5 sell has no backing lot

    opted_out = run_in(
        workspace, attribute=t.ATTRIBUTE_NONE, **pies_kwargs
    )
    assert "- Attribution: none" in opted_out
    assert t.NOT_ATTRIBUTABLE in opted_out


def test_unknown_attribution_mode_halts(workspace):
    write_export(workspace / "data" / "t212", "a.csv", [buy(qty="1.0")])
    with pytest.raises(t.Halt, match="unknown attribution mode"):
        t.run(
            workspace / "data" / "t212",
            write_pies(workspace / "pies.md"),
            workspace / "ownership.md",
            attribute="lifo",
        )


def test_fifo_when_every_buy_precedes_every_sell(workspace):
    """Constructed ordering, checkable in one line of arithmetic.

    Inherited 0.0113473600, then buys 0.2904648500, then sells
    0.2842038200. With no sell before the buys, the inherited lot is still
    there to absorb the first 0.0113473600 of selling, so
    mine = 0.2904648500 - (0.2842038200 - 0.0113473600) = 0.0176083900.

    The real NVDA history does not look like this: a sell lands before the
    buys, which no closed form captures. See the real-export test.
    """
    data = workspace / "data" / "t212"
    write_export(
        data,
        "a.csv",
        [
            buy(isin="US67066G1040", ticker="NVDA", qty="0.0113473600",
                time="2025-10-08 13:30:08+00:00", tx_id="EOF1"),
            buy(isin="US67066G1040", ticker="NVDA", qty="0.2904648500",
                time="2025-10-20 13:30:08+00:00", tx_id="EOF2"),
            sell(isin="US67066G1040", ticker="NVDA", qty="0.2842038200",
                 time="2026-09-09 13:30:02+00:00", tx_id="EOF3"),
        ],
    )
    a = attribute(data)["US67066G1040"]
    assert a.mine_qty == Decimal("0.0176083900")
    assert a.holder_qty == Decimal("0")
    assert not a.is_floor


# --------------------------------------------------------------------------
# The real export, when it is present
# --------------------------------------------------------------------------

def _newest_real_export() -> Path | None:
    """The newest non-empty export on disk, wherever it currently lives.

    Exports get replaced as the window is widened, so this must not pin a
    filename.
    """
    root = Path(__file__).resolve().parents[1]
    candidates = [
        p
        for directory in (root / "data" / "t212", root / "data t212")
        if directory.is_dir()
        for p in directory.glob("*.csv")
        if p.stat().st_size > 0
    ]
    # Latest window by the end date Trading 212 writes into the name, not by
    # mtime: copying a set of exports stamps them all with one mtime, and
    # the oldest window must never be mistaken for the newest.
    def window_end(p: Path) -> tuple[str, float]:
        m = re.search(r"_to_(\d{4}-\d{2}-\d{2})_", p.name)
        return (m.group(1) if m else "", p.stat().st_mtime)

    return max(candidates, key=window_end, default=None)


REAL_EXPORT = _newest_real_export()


def _assert_weights_follow_currencies(positions, states, attributions):
    """One cost currency: weights sum to 100. Several: Not available without
    a declared rate, and in EUR with the BGN one ownership.md declares."""
    bases = t.cost_bases(positions, states, attributions)
    weights = t.cost_weights(positions, states, attributions)
    rate = t.parse_fixed_rate(BGN_RATE, "test")
    if not bases:
        # A window with no buy of the user's (a dividends-only export, as
        # 2026-09-28 to 2026-10-10 was) has nothing to weight.
        assert weights is None
        return
    if len(t.cost_currencies(bases)) == 1:
        assert abs(sum(weights[1].values()) - Decimal(100)) < Decimal("0.0001")
        assert set(weights[1]) == set(bases)
    else:
        assert weights is None
        assert set(t.cost_currencies(bases)) <= {"BGN", "EUR"}
        weights = t.cost_weights(positions, states, attributions, rate)
        assert weights[0] == "EUR"
        assert abs(sum(weights[1].values()) - Decimal(100)) < Decimal("0.0001")
        assert set(weights[1]) == set(bases)


@pytest.mark.skipif(REAL_EXPORT is None, reason="no real export present")
def test_real_export_splits_at_the_cutoff_without_halting(tmp_path):
    """Real data, real cutoff: nothing here is a data error.

    Row counts either side of the cutoff are recomputed from the CSV with a
    separate code path, so this checks the module rather than restating it.
    """
    data = tmp_path / "data" / "t212"
    data.mkdir(parents=True)
    (data / REAL_EXPORT.name).write_bytes(REAL_EXPORT.read_bytes())
    ownership_path = write_ownership(tmp_path / "ownership.md")

    raw = list(
        csv.DictReader(REAL_EXPORT.read_text(encoding="utf-8-sig").splitlines())
    )
    cutoff_iso = CUTOFF.isoformat()
    expected_pre = [
        r for r in raw if r["Time (UTC)"][:10] < cutoff_iso and r["ISIN"]
    ]

    ledger, positions = load(data)
    assert ledger.rows_read == len(raw)
    assert not ledger.duplicates
    assert sum(p.pre_rows for p in positions.values()) == len(expected_pre)

    # Dividend rows carry no ID, so every one of them used the fallback key.
    assert all(not tx.tx_id for tx in ledger.txs if tx.kind == "dividend")

    audit = t.fx_direction_audit(ledger.txs)
    assert audit["dividend"]["divide"] == 0
    assert all(buckets["neither"] == 0 for buckets in audit.values())

    ownership = t.load_ownership(ownership_path)
    states = t.classify_ownership(positions, ownership)

    # Anything holding pre-cutoff shares at the cutoff is not attributable.
    for isin, pos in positions.items():
        if pos.pre_net_qty > 0:
            assert states[isin] == t.SPANS_CUTOFF, isin
        if pos.trades == 0 and not pos.dividends:
            assert states[isin] == t.PRE_CUTOFF_ONLY, isin

    # No halt: negative quantities here are inherited shares being sold.
    t.check_no_negative_quantity(positions, states)

    # Cost weights need every surviving lot in one currency, or the fixed
    # BGN/EUR rate ownership.md declares: this account's 2025 lots are in BGN.
    bases = t.cost_bases(positions, states)
    assert all(states[isin] == t.MINE for isin in bases)
    _assert_weights_follow_currencies(positions, states, None)

    # FIFO on the real rows: whatever this export holds, every split keeps
    # its invariants. No position or quantity is pinned here, because this
    # file is public and the export is not.
    attributions = t.fifo_attribution(ledger.txs, CUTOFF)
    for isin, attr in attributions.items():
        assert attr.mine_qty >= 0, isin
        assert attr.is_floor == (attr.unbacked_sold > 0), isin
        if attr.is_floor:
            # A floor is bounded above by everything bought after the cutoff.
            assert attr.mine_qty <= positions[isin].bought_qty, isin

    # Attributed positions join the weights and the total still holds.
    _assert_weights_follow_currencies(positions, states, attributions)


def _full_history_exports() -> list[Path]:
    """Every non-empty real export on disk, in data/t212/."""
    root = Path(__file__).resolve().parents[1]
    return sorted(
        p
        for directory in (root / "data" / "t212",)
        if directory.is_dir()
        for p in directory.glob("*.csv")
        if p.stat().st_size > 0
    )


FULL_HISTORY = _full_history_exports()


@pytest.mark.skipif(
    not any(p.name.startswith("from_2023") for p in FULL_HISTORY),
    reason="no export reaching the account's opening",
)
def test_full_history_settles_every_fifo_split(tmp_path):
    """With exports back to the account's first trade, nothing is a floor.

    A one-year window can end a position's history mid-stream, so its
    quantity is a floor; with the earlier exports every split is exact.
    """
    data = tmp_path / "t212"
    data.mkdir()
    for p in FULL_HISTORY:
        (data / p.name).write_bytes(p.read_bytes())
    ledger = t.load_transactions(data)
    attributions = t.fifo_attribution(ledger.txs, CUTOFF)
    assert all(a.unbacked_sold == 0 for a in attributions.values())
    assert not any(a.is_floor for a in attributions.values())


# --------------------------------------------------------------------------
# Output contract (RULES.md Part IV)
#
# These run the real CLI and read only its rendered output, because the
# contract is about what a reader sees. contract.py is the only file that
# knows how the script is invoked.
# --------------------------------------------------------------------------

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _cli(workspace: Path, label: str = "", **pies_kwargs) -> contract.Run:
    """Run the CLI over a workspace built by the fixture builders above."""
    write_pies(workspace / "pies.md", **pies_kwargs)
    return contract.run(
        workspace / "data" / "t212",
        workspace / "pies.md",
        workspace / "ownership.md",
        label=label or workspace.name,
    )


def _workspace(root: Path) -> Path:
    (root / "data" / "t212").mkdir(parents=True, exist_ok=True)
    write_ownership(root / "ownership.md")
    return root


@pytest.fixture(scope="session")
def complete_run(tmp_path_factory) -> contract.Run:
    """A run that reaches a report: two open positions and a dividend."""
    ws = _workspace(tmp_path_factory.mktemp("complete"))
    write_export(
        ws / "data" / "t212",
        "a.csv",
        [
            buy(qty="2.3000000000", total="105.85",
                time="2026-09-09 12:16:01+00:00", tx_id="EOF1"),
            buy(isin="US0378331005", ticker="AAPL", qty="0.1200000000",
                price="316.0900000000", price_ccy="USD", fx="1.16480969",
                total="32.56", time="2026-09-09 13:30:12+00:00", tx_id="EOF2"),
            dividend(isin="US0378331005", ticker="AAPL", qty="0.0759001700",
                     price="0.243000", price_ccy="USD", fx="0.86759600",
                     total="0.02", time="2026-08-13 14:10:47+00:00"),
        ],
    )
    return _cli(ws)


@pytest.fixture(scope="session")
def halt_run(tmp_path_factory) -> contract.Run:
    """quantity_discontinuity.csv: 10 shares sold out of a 1-share position.

    An unrecorded corporate action. The export says the position went to -9,
    which no cutoff explains.
    """
    ws = _workspace(tmp_path_factory.mktemp("discontinuity"))
    shutil.copy(
        FIXTURES / "quantity_discontinuity.csv",
        ws / "data" / "t212" / "quantity_discontinuity.csv",
    )
    return _cli(
        ws,
        shares=(("Stock", "100%"),),
        pies=(
            ("Stock", (("US02079K3059", "GOOGL", "Alphabet Inc Class A", "100%"),)),
        ),
    )


@pytest.fixture(scope="session")
def early_halt_run(tmp_path_factory) -> contract.Run:
    """A halt in load_ownership, before CONTEXT can be populated at all."""
    ws = tmp_path_factory.mktemp("early")
    (ws / "data" / "t212").mkdir(parents=True)
    write_export(ws / "data" / "t212", "a.csv", [buy(qty="1.0")])
    return _cli(ws)  # no ownership.md written


@pytest.fixture(scope="session")
def contract_runs(complete_run, halt_run, early_halt_run) -> list[contract.Run]:
    return [complete_run, halt_run, early_halt_run]


def test_status_is_first_line(contract_runs):
    for r in contract_runs:
        first = r.stdout.lstrip().splitlines()[0].strip()
        assert first == "STATUS", f"{r.fixture}: output opens with {first!r}"


def test_section_order_is_fixed(contract_runs):
    for r in contract_runs:
        order = contract.section_order(r.stdout)
        assert order == sorted(order, key=contract.SECTIONS.index), (
            f"{r.fixture}: sections out of order -> {order}"
        )
        assert len(set(order)) == len(order), f"{r.fixture}: duplicate section"


def test_context_fields_present(contract_runs):
    """Every mandated field prints on every run. A halt that could not
    populate one prints it as 'not reached' rather than dropping it."""
    for r in contract_runs:
        ctx = r.context()
        missing = [
            f for f in contract.CONTEXT_FIELDS if not any(k.startswith(f) for k in ctx)
        ]
        assert not missing, f"{r.fixture}: CONTEXT missing {missing}"


def test_halt_omits_result(halt_run, early_halt_run):
    """A halt prints STATUS, CONTEXT, METHOD, PROOF, SOURCES -- never RESULT."""
    for r in (halt_run, early_halt_run):
        assert r.halted, f"{r.fixture}: expected a halt -> {r.status_line!r}"
        assert r.exit_code == contract.EXIT_HALT
        assert "RESULT" not in r.sections, (
            f"{r.fixture}: halted but printed RESULT tables"
        )
        for section in ("CONTEXT", "METHOD", "PROOF", "SOURCES"):
            assert section in r.sections, f"{r.fixture}: halted without {section}"
        assert "Withheld:" in r.sections["STATUS"], (
            f"{r.fixture}: halt does not name what did not print"
        )


def test_completed_run_hides_proof_unless_asked(workspace):
    """RULES.md Part IV v9: five sections by default, PROOF on --proof."""
    write_export(
        workspace / "data" / "t212",
        "a.csv",
        [buy(qty="1.0", total="20.00", total_ccy="EUR",
             time="2026-02-09 08:04:49+00:00", tx_id="E1")],
    )
    default = _cli(workspace)
    assert default.exit_code == 0
    assert contract.section_order(default.stdout) == [
        "STATUS", "CONTEXT", "RESULT", "METHOD", "SOURCES"
    ]
    assert contract.text_outside_sections(default.stdout) == []
    # The checks still ran: the report is the one a passing run produces.
    assert "Weight (cost)" in default.sections["RESULT"]

    shown = contract.run(
        workspace / "data" / "t212",
        workspace / "pies.md",
        workspace / "ownership.md",
        proof=True,
    )
    assert contract.section_order(shown.stdout) == contract.SECTIONS
    assert "cost weights sum to 100.0000%" in shown.sections["PROOF"]
    # Everything but PROOF is identical: the flag adds a section, nothing else.
    for name in ("STATUS", "CONTEXT", "RESULT", "METHOD", "SOURCES"):
        assert shown.sections[name] == default.sections[name], name


def test_halt_prints_proof_without_being_asked(halt_run):
    """A halt is the one time the working is the answer."""
    assert "PROOF" in halt_run.sections


def test_halt_status_names_the_check(halt_run, early_halt_run):
    """'Halted' alone is not a status: the line names the check and its
    figure, and the figure is reproduced in PROOF."""
    assert halt_run.halt_check == "check_no_negative_quantity"
    assert "-9" in halt_run.status_line, halt_run.status_line
    assert "check_no_negative_quantity" in halt_run.sections["PROOF"]
    assert early_halt_run.halt_check == "load_ownership"


def test_status_line_matches_the_form_the_rules_fix(contract_runs):
    """Either "complete" or the halt form, separator and all.

    RULES.md Part IV fixes the separator as an ASCII hyphen-minus between
    single spaces. Asserting the whole line is what stops the code and the
    rules drifting on it again: a parser that searches for "HALTED" and
    reads the rest as free text cannot tell one dash from another.
    """
    for r in contract_runs:
        line = r.status_line
        if line == contract.STATUS_COMPLETE:
            continue
        assert contract.HALT_STATUS.match(line), (
            f"{r.fixture}: STATUS is neither "
            f"{contract.STATUS_COMPLETE!r} nor the halt form -> {line!r}"
        )
        assert not any(dash in line for dash in (chr(0x2014), chr(0x2013)))


def test_no_recommendation_language(contract_runs):
    for r in contract_runs:
        hits = contract.banned_hits(r.stdout)
        assert not hits, f"{r.fixture}: rule 6 violation\n" + "\n".join(hits)


def test_no_placeholder_time(contract_runs):
    """RULES.md Part IV: a time is an exact HH:MM or it is left off."""
    for r in contract_runs:
        assert contract.placeholder_times(r.stdout) == [], r.fixture


def test_nothing_prints_outside_the_six_sections(contract_runs):
    for r in contract_runs:
        assert contract.text_outside_sections(r.stdout) == [], r.fixture


def test_complete_run_prints_result(complete_run):
    assert complete_run.exit_code == contract.EXIT_COMPLETE
    assert not complete_run.halted
    assert complete_run.status_line == "Complete."
    assert "| ISIN |" in complete_run.sections["RESULT"]


def test_quantity_discontinuity_halts(halt_run):
    """Selling 10 shares of a 1-share position is a corporate action the
    export did not record.

    The run halts, but through check_no_negative_quantity -- the position
    nets to -9 and nothing about the cutoff explains it. There is no
    discontinuity detector: an action that left net quantity positive would
    still pass. The check that fires is named so the distinction is visible
    in the output rather than assumed here.
    """
    assert halt_run.halted
    assert halt_run.exit_code == contract.EXIT_HALT
    assert "check_no_negative_quantity" in halt_run.status_line
    assert "US02079K3059" in halt_run.status_line


def test_halt_marks_unreached_context_fields(early_halt_run):
    """An empty field is a statement; a missing section is a gap."""
    ctx = early_halt_run.context()
    assert ctx["Data as of"] == "not reached"
    assert ctx["Coverage"] == "not reached"
    # The fields that do not depend on a loaded file still print.
    assert "unitless" in ctx["Currency/units"]
    assert "load_ownership" in ctx["Not available"]


def test_sources_lists_every_file_read(complete_run):
    """Every file the run read is a SOURCES row, with the date it carries."""
    sources = complete_run.sections["SOURCES"]
    assert "a.csv" in sources
    assert "pies.md (updated 2026-09-17)" in sources
    assert "ownership.md (cutoff 2025-10-13, updated 2026-09-17)" in sources
    assert sources.count("published n/a - local file") == 3


def test_context_carries_values_not_a_file_list(complete_run):
    """CONTEXT states the cutoff and the policy date; SOURCES names the files.

    The cutoff bounds the measured period, so it rides on Latest period
    rather than adding a field.
    """
    period = complete_run.context()["Latest period"]
    assert "ownership cutoff 2025-10-13" in period
    assert "policy as of 2026-09-17" in period
    assert ".md" not in complete_run.sections["CONTEXT"]


# The policy block has its own halt paths, added after the halt contract was
# written. Each is a CLI run, because what is under test is the printed
# STATUS line rather than the exception.
POLICY_HALTS = {
    "missing block": ["# Ownership", "", "Cutoff: 2025-10-13"],
    "unclosed block": ["---", "Cutoff: 2025-10-13", "", "# Ownership"],
    "unhandled key": [
        "---", "Cutoff: 2025-10-13", "CASH_CONSUMPTION: pro-rata", "---",
    ],
    "multi-word key": [
        "---", "Cutoff: 2025-10-13", "HOLDER CASH AT OWN FROM: 2025-06-01",
        "---",
    ],
    "non-declaration line": [
        "---", "Cutoff: 2025-10-13", "just prose, no colon", "---",
    ],
}


@pytest.fixture(scope="session")
def policy_halt_runs(tmp_path_factory) -> dict[str, contract.Run]:
    runs = {}
    for name, lines in POLICY_HALTS.items():
        ws = tmp_path_factory.mktemp("policy")
        (ws / "data" / "t212").mkdir(parents=True)
        write_export(ws / "data" / "t212", "a.csv", [buy(qty="1.0")])
        write_lines(ws / "ownership.md", lines)
        runs[name] = _cli(ws, label=name)
    return runs


@pytest.fixture(scope="session")
def every_halt_run(
    halt_run, early_halt_run, policy_halt_runs, loader_halt_runs,
    dedup_collision_run,
):
    """Every halt any fixture reaches. The STATUS cap binds all of them."""
    return [
        halt_run,
        early_halt_run,
        dedup_collision_run,
        *policy_halt_runs.values(),
        *loader_halt_runs.values(),
    ]


def test_policy_halts_print_the_halt_contract(policy_halt_runs):
    """The paths added with the policy block obey the shape too."""
    for name, r in policy_halt_runs.items():
        assert r.exit_code == contract.EXIT_HALT, name
        assert r.halt_check == "read_policy_block", f"{name}: {r.status_line!r}"
        assert "RESULT" not in r.sections, name
        for section in ("CONTEXT", "METHOD", "PROOF", "SOURCES"):
            assert section in r.sections, f"{name}: no {section}"


def test_halt_figure_is_the_identifying_fact_not_the_reason(policy_halt_runs):
    """A key, a file, a locator -- the reason stays in PROOF."""
    figures = {name: r.halt_figure for name, r in policy_halt_runs.items()}
    assert figures == {
        "missing block": "ownership.md",
        "unclosed block": "ownership.md:1",
        "unhandled key": "CASH_CONSUMPTION",
        "multi-word key": "HOLDER CASH AT OWN FROM",
        "non-declaration line": "ownership.md:3",
    }


def test_proof_still_carries_the_whole_explanation(policy_halt_runs):
    """Shortening STATUS must not shorten the evidence."""
    proof = policy_halt_runs["missing block"].sections["PROOF"]
    assert "The file must open with" in proof
    assert "Declarations anywhere else in the file are not read." in proof
    assert "this build does not implement it" in (
        policy_halt_runs["unhandled key"].sections["PROOF"]
    )


def test_halt_status_stays_scannable(every_halt_run):
    """A STATUS line is read at a glance or it is not read.

    The figure defaults to the first line of the message when a raise site
    passes none, which is how five halts came to print ~200 characters that
    PROOF already carried verbatim.
    """
    for r in every_halt_run:
        assert len(r.status_line) < 120, (
            f"{r.fixture}: STATUS is {len(r.status_line)} chars -> "
            f"{r.status_line!r}"
        )


# --------------------------------------------------------------------------
# Rule 6 -- what the exclusions exempt, and what they must not
#
# The list exempts the verbs where this module prints them as nouns. The
# exemption is per occurrence, not per line, and it is anchored to the
# position the noun actually appears in -- a prefix that can also occur in a
# sentence exempts the sentence too, which is a hole rather than a rule.
# --------------------------------------------------------------------------


def test_a_legitimate_token_does_not_exempt_its_line():
    """One line, one Action value and one recommendation: the second fires.

    The exclusions are lookarounds on each occurrence, and banned_hits scans
    every occurrence independently, so a legitimate token cannot buy its
    neighbours an exemption.
    """
    line = "a.csv:3 - Market sell 1E+1 on 2026-02-05, so sell the rest now"
    hits = contract.banned_hits(line)
    assert len(hits) == 1, hits
    assert "so sell the rest now" in hits[0]

    line = "| Buy cost | Sell proceeds |  buy more AAPL"
    assert len(contract.banned_hits(line)) == 1


def test_an_order_type_in_prose_does_not_shield_the_verb():
    """'market sell' is an Action value in a cell, not two words in a clause.

    Exempting the verb wherever "market " precedes it exempted the sentence
    "in a falling market sell into strength", which is the recommendation
    rule 6 exists to stop.
    """
    assert contract.banned_hits("in a falling market sell into strength")
    assert contract.banned_hits("a thin market buy the dip")
    # The real Action value, in the two positions this module prints it.
    assert contract.banned_hits("| Market sell | 10 sh |") == []
    assert contract.banned_hits("at a.csv:3 - Market sell 1E+1 on 2026-02-05") == []


def test_a_colon_exempts_a_row_kind_not_a_verdict():
    """"buy: 1 divide" is a tally row. "buy: take it" is advice."""
    assert contract.banned_hits("- Exchange-rate direction: buy: 1 divide") == []
    assert contract.banned_hits("sell: 2 multiply, 1 ambiguous") == []
    assert contract.banned_hits("Verdict: buy: take the position")
    assert contract.banned_hits("Call: sell: exit before the print")


@pytest.fixture(scope="session")
def dedup_collision_run(tmp_path_factory) -> contract.Run:
    """Two exports, one ID, different rows. Halts inside dedup."""
    ws = _workspace(tmp_path_factory.mktemp("dedup"))
    write_export(ws / "data" / "t212", "a.csv", [buy(qty="1.0", tx_id="DUP")])
    write_export(ws / "data" / "t212", "b.csv", [sell(qty="2.0", tx_id="DUP")])
    return _cli(ws, label="dedup collision")


def test_dedup_halt_is_clean_of_rule_6(dedup_collision_run):
    """dedup prints two Action values; neither is advice.

    It printed them after ": " until the separator was unified, which the
    anchored exclusion does not cover and should not: a ": " anchor would
    exempt "in this market: sell everything" to preserve an inconsistency.
    """
    assert contract.banned_hits(dedup_collision_run.stdout) == []
    assert dedup_collision_run.halt_check == "dedup"
    assert " - Market buy " in dedup_collision_run.sections["PROOF"]
    assert " - Market sell " in dedup_collision_run.sections["PROOF"]


def test_a_clean_report_and_halt_trip_nothing(complete_run, halt_run):
    """The tightened list, over output known to carry both verbs as nouns."""
    for r in (complete_run, halt_run):
        assert contract.banned_hits(r.stdout) == [], r.fixture


# --------------------------------------------------------------------------
# Disagreeing policy dates
# --------------------------------------------------------------------------


def _dated_workspace(root: Path, rows) -> Path:
    (root / "data" / "t212").mkdir(parents=True)
    write_ownership(root / "ownership.md", updated="2026-09-17")
    write_export(root / "data" / "t212", "a.csv", rows)
    return root


@pytest.fixture(scope="session")
def disagreeing_dates_complete(tmp_path_factory) -> contract.Run:
    ws = _dated_workspace(
        tmp_path_factory.mktemp("dates"), [buy(qty="1.0", tx_id="EOF1")]
    )
    return _cli(ws, label="disagreeing dates", updated="2026-08-01")


@pytest.fixture(scope="session")
def disagreeing_dates_halt(tmp_path_factory) -> contract.Run:
    """Same disagreement, on a run that halts after both files are read."""
    ws = _dated_workspace(
        tmp_path_factory.mktemp("dates_halt"),
        [
            buy(qty="1.0", time="2026-01-05 10:00:00+00:00", tx_id="B1"),
            sell(qty="10.0", time="2026-02-05 10:00:00+00:00", tx_id="S1"),
        ],
    )
    return _cli(ws, label="disagreeing dates, halted", updated="2026-08-01")


def test_disagreeing_policy_dates_are_named_never_merged(
    disagreeing_dates_complete, disagreeing_dates_halt
):
    """One date across two files would claim an agreement that is not there.

    ownership.md and pies.md each carry their own Last updated. When they
    differ, CONTEXT names which file states which, on both paths -- a halt
    that reached both files knows as much about them as a complete run.
    """
    expected = "policy as of ownership.md 2026-09-17, pies.md 2026-08-01"
    for r in (disagreeing_dates_complete, disagreeing_dates_halt):
        assert expected in r.context()["Latest period"], (
            f"{r.fixture}: {r.context()['Latest period']!r}"
        )
    assert disagreeing_dates_halt.halt_check == "check_no_negative_quantity"
    # The agreeing case prints one date, not two: covered by
    # test_context_carries_values_not_a_file_list.


# --------------------------------------------------------------------------
# The loader halts
#
# One fixture per raise site, because the STATUS cap only binds a halt some
# test actually reaches. A site with no fixture is a site where the cap is
# decorative.
# --------------------------------------------------------------------------


def _loadable(root: Path) -> Path:
    """A workspace where every file is valid, ready to be spoilt one way."""
    (root / "data" / "t212").mkdir(parents=True)
    write_ownership(root / "ownership.md")
    write_pies(root / "pies.md")
    write_export(root / "data" / "t212", "a.csv", [buy(qty="1.0")])
    return root


@pytest.fixture(scope="session")
def loader_halt_runs(tmp_path_factory) -> dict[str, contract.Run]:
    runs = {}

    ws = _loadable(tmp_path_factory.mktemp("no_column"))
    write_export(
        ws / "data" / "t212", "a.csv", [buy(qty="1.0")],
        header=[c for c in HEADER if c != "Time (UTC)"],
    )
    runs["missing column"] = contract.run(
        ws / "data" / "t212", ws / "pies.md", ws / "ownership.md",
        label="missing column",
    )

    ws = _loadable(tmp_path_factory.mktemp("no_dir"))
    runs["data dir absent"] = contract.run(
        ws / "data" / "nowhere", ws / "pies.md", ws / "ownership.md",
        label="data dir absent",
    )

    ws = _loadable(tmp_path_factory.mktemp("empty_dir"))
    (ws / "data" / "t212" / "a.csv").unlink()
    runs["data dir empty"] = contract.run(
        ws / "data" / "t212", ws / "pies.md", ws / "ownership.md",
        label="data dir empty",
    )

    ws = _loadable(tmp_path_factory.mktemp("no_pies"))
    (ws / "pies.md").unlink()
    runs["pies absent"] = contract.run(
        ws / "data" / "t212", ws / "pies.md", ws / "ownership.md",
        label="pies absent",
    )

    ws = _loadable(tmp_path_factory.mktemp("no_cutoff"))
    write_policy(ws / "ownership.md", ["Last updated: 2026-09-17"])
    runs["no cutoff"] = contract.run(
        ws / "data" / "t212", ws / "pies.md", ws / "ownership.md",
        label="no cutoff",
    )

    # The dedup key falls back to timestamp+ISIN+quantity+price when a row
    # carries no ID, as dividend rows do. That label is the longest figure
    # this module can print, so it is the one the cap has to bind on.
    ws = _loadable(tmp_path_factory.mktemp("no_id"))
    (ws / "data" / "t212" / "a.csv").unlink()
    for name, total in (("a.csv", "0.16"), ("b.csv", "0.99")):
        write_export(
            ws / "data" / "t212", name,
            [dividend(total=total, time="2026-04-01 15:10:44+00:00")],
        )
    runs["dedup on the fallback key"] = contract.run(
        ws / "data" / "t212", ws / "pies.md", ws / "ownership.md",
        label="dedup on the fallback key",
    )
    return runs


def test_loader_halts_name_their_check_and_their_figure(loader_halt_runs):
    """Every figure is the short identifying fact, and no two collide.

    The two load_ownership halts matter most: the file being absent and the
    file lacking CUTOFF are different failures raised from one function, so
    the figure is the only thing that tells them apart.
    """
    seen = {
        name: (r.halt_check, r.halt_figure) for name, r in loader_halt_runs.items()
    }
    assert seen == {
        "missing column": ("read_csv_file", "a.csv, no 'Time (UTC)'"),
        "data dir absent": ("load_transactions", "data/nowhere not a directory"),
        "data dir empty": ("load_transactions", "data/t212 holds no CSV"),
        "pies absent": ("load_pies", "pies.md"),
        "no cutoff": ("load_ownership", "ownership.md, no CUTOFF"),
        "dedup on the fallback key": (
            "dedup",
            "timestamp+ISIN+quantity+price "
            "(2026-04-01T15:10:44+00:00, IE00B3XXRP09)",
        ),
    }
    assert len(set(seen.values())) == len(seen), "two halts share one STATUS line"


def test_loader_halts_keep_the_explanation_in_proof(loader_halt_runs):
    """The figure is short because PROOF is not."""
    proof = loader_halt_runs["missing column"].sections["PROOF"]
    assert "Columns found:" in proof and "Action" in proof
    assert "It records the ownership cutoff" not in proof  # that is the other halt
    assert "not defaulted" in loader_halt_runs["no cutoff"].sections["PROOF"]
    assert "mapping file not found" in loader_halt_runs["pies absent"].sections["PROOF"]


# Trading 212 leaves out a column no row in the export uses. A window holding
# only dividends comes without ID (live export 2026-09-28 to 2026-10-10).
def test_dividends_only_export_without_id_column_is_read(workspace):
    data = workspace / "data" / "t212"
    write_export(data, "a.csv", [buy(qty="1.0")])
    header = [c for c in HEADER if c != "ID"]
    (data / "b.csv").write_text(csv_text([dividend()], header=header), encoding="utf-8")
    ledger, positions = load(data)
    assert positions["IE00BFY0GT14"].net_qty == Decimal("1.0")
    assert any(tx.kind == "dividend" for tx in ledger.txs)


def test_trade_rows_without_id_column_still_halt(workspace):
    data = workspace / "data" / "t212"
    header = [c for c in HEADER if c != "ID"]
    (data / "a.csv").write_text(csv_text([buy(qty="1.0")], header=header), encoding="utf-8")
    with pytest.raises(t.Halt, match="missing required column.*ID"):
        load(data)


# A new user runs a script before setup: the halt says how to go on.
def test_blank_template_ownership_halts_with_the_way_forward(tmp_path):
    path = tmp_path / "ownership.md"
    template = Path(__file__).resolve().parents[1] / "templates" / "me" / "ownership.md"
    path.write_text(template.read_text(), encoding="utf-8")
    with pytest.raises(t.Halt) as info:
        t.load_ownership(path)
    assert info.value.status() == "HALTED - load_ownership, ownership.md, not set up"
    assert "set up Holdnote" in info.value.message
    assert t.load_ownership(path, cutoff_override=date(2026, 1, 5)).cutoff == date(2026, 1, 5)


def test_missing_files_point_to_setup_not_to_anyones_cutoff(tmp_path):
    with pytest.raises(t.Halt) as info:
        t.load_ownership(tmp_path / "ownership.md")
    assert "set up Holdnote" in info.value.message and "2025-10-13" not in info.value.message
    with pytest.raises(t.Halt, match="set up Holdnote"):
        t.load_pies(tmp_path / "pies.md")
    with pytest.raises(t.Halt, match="History -> Export"):
        t.load_transactions(tmp_path / "data" / "t212")
