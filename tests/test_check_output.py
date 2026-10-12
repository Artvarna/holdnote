"""The draft check BuffettBot runs before printing, and the two overlap rules.

SYNTHETIC. Tickers are invented (AAA..DDD) and index names use real
providers only so the provider rule has something to read; no figure is a
record of a run (RULES.md rule 15).
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import contract  # noqa: E402
from test_stocks_table import stocks_output  # noqa: E402

REPO = Path(__file__).resolve().parent.parent

COMPARISON = [
    "Comparison",
    "| Ticker | Index | Universe | TER | Replication | Acc/Dist | Currency | Domicile | AUM | Top-10 |",
    "|---|---|---|---|---|---|---|---|---|---|",
    "| AAA | STOXX Europe 600 | Europe | 0.07% | Physical | Acc | EUR | LU | EUR 100m, fund | 20% |",
    "| BBB | MSCI EM IMI | EM | 0.18% | Physical | Acc | USD | IE | USD 100m, fund | 30% |",
    "| CCC | MSCI World | DM | 0.12% | Optimised | Acc | USD | IE | USD 100m, fund | 25% |",
    "",
]
STRUCTURAL_OK = [
    "Structural",
    "| Pair | Overlap | Index fact |",
    "|---|---|---|",
    "| CCC · BBB | disjoint | developed vs emerging, one provider's classification |",
    "| AAA · BBB | overlapping | a country is in both country lists |",
    "",
]
HOLDINGS_OK = [
    "Holdings (top 10 only)",
    "| Pair | Shared names | Shared weight |",
    "|---|---|---|",
    "| AAA · CCC | 2 | 3.10 |",
    "| AAA · BBB | 0 | 0 |",
    "",
]


def mode_c(structural=STRUCTURAL_OK, holdings=HOLDINGS_OK) -> str:
    text = stocks_output().replace("\nMETHOD\n\n", "\nMETHOD\n\nBuild:             0000000 2026-01-01\n", 1)
    head, _, tail = text.partition("\nStocks\n")
    block = "\n".join(COMPARISON + structural + holdings)
    return f"{head}\n{block}\nStocks\n{tail}"


def problems(text: str) -> list[str]:
    return contract.output_problems(text)


# --------------------------------------------------------------------------
# The whole check
# --------------------------------------------------------------------------


def test_a_conforming_mode_c_output_is_ok():
    assert problems(mode_c()) == []


def test_the_cli_prints_ok_and_exits_zero(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(mode_c(), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(REPO / "scripts" / "check_output.py"), str(draft)],
                          capture_output=True, text=True)
    assert (proc.returncode, proc.stdout.strip()) == (0, "ok")


def test_the_cli_lists_problems_and_exits_one(tmp_path):
    draft = tmp_path / "draft.md"
    draft.write_text(mode_c().replace("STATUS\n\nComplete.", "STATUS: Complete - 1 of 3 single source"),
                     encoding="utf-8")
    proc = subprocess.run([sys.executable, str(REPO / "scripts" / "check_output.py"), str(draft)],
                          capture_output=True, text=True)
    assert proc.returncode == 1 and "nothing more" in proc.stdout


def test_status_must_come_first():
    text = mode_c()
    status, _, rest = text.partition("\nCONTEXT\n")
    moved = "CONTEXT\n" + rest.replace("\nRESULT\n", "\n" + status + "\n\nRESULT\n", 1)
    assert "STATUS is not the first section" in problems(moved)


def test_the_stocks_method_labels_are_checked_too():
    text = mode_c().replace("Earnings dates:    company-announced only, never estimated\n", "")
    assert problems(text) == ["METHOD does not say Earnings dates: company-announced only"]


# --------------------------------------------------------------------------
# Structural: across providers, country lists decide
# --------------------------------------------------------------------------


@pytest.mark.parametrize("fact", ["Europe DM vs emerging markets", "developed vs emerging"])
def test_cross_provider_disjoint_by_label_is_caught(fact):
    rows = STRUCTURAL_OK[:3] + [f"| AAA · BBB | disjoint | {fact} |", ""]
    found = contract.structural_problems(contract.split_sections(mode_c(structural=rows)))
    assert len(found) == 1 and found[0].startswith("AAA · BBB")


def test_cross_provider_disjoint_on_country_lists_passes():
    rows = STRUCTURAL_OK[:3] + ["| AAA · BBB | disjoint | no country in both lists |", ""]
    assert contract.structural_problems(contract.split_sections(mode_c(structural=rows))) == []


def test_same_provider_disjoint_by_classification_passes():
    assert contract.structural_problems(contract.split_sections(mode_c())) == []


@pytest.mark.parametrize("verdict, fact", [
    ("Not available", "(browser route down)"),
    ("Not available (browser route down)", "MSCI Emerging Markets IMI country list"),
    ("Not available", "MSCI EM IMI factsheet returned 404"),
])
def test_not_available_with_a_reason_passes(verdict, fact):
    rows = STRUCTURAL_OK[:3] + [f"| AAA · BBB | {verdict} | {fact} |", ""]
    assert contract.structural_problems(contract.split_sections(mode_c(structural=rows))) == []


@pytest.mark.parametrize("fact", [
    "MSCI Emerging Markets IMI country list not fetched",
    "MSCI Emerging Markets IMI country list not fetched (STOXX Europe 600 list includes Poland)",
    "country list unavailable",
])
def test_not_available_without_a_reason_is_caught(fact):
    """The 2026-10-03 run left two rows empty this way with the browser up."""
    rows = STRUCTURAL_OK[:3] + [f"| AAA · BBB | Not available | {fact} |", ""]
    found = contract.structural_problems(contract.split_sections(mode_c(structural=rows)))
    assert len(found) == 1 and found[0].startswith("AAA · BBB: Not available without a reason")


def test_not_available_is_never_read_as_a_disjoint_claim():
    rows = STRUCTURAL_OK[:3] + ["| AAA · BBB | Not available | (browser route down) |", ""]
    found = contract.structural_problems(contract.split_sections(mode_c(structural=rows)))
    assert not any("called disjoint" in f for f in found)


def test_the_live_2026_10_03_structural_rows_are_caught():
    rows = STRUCTURAL_OK[:3] + [
        "| VUSA - EIMI | Not available | MSCI Emerging Markets IMI country list not fetched |",
        "| MEUD - EIMI | Not available | MSCI Emerging Markets IMI country list not fetched "
        "(STOXX Europe 600 list includes Poland) |",
        "",
    ]
    found = contract.structural_problems(contract.split_sections(mode_c(structural=rows)))
    assert [f.split(":")[0] for f in found] == ["VUSA - EIMI", "MEUD - EIMI"]


# --------------------------------------------------------------------------
# Holdings: one shared-weight figure per pair
# --------------------------------------------------------------------------


@pytest.mark.parametrize("cell", ["AAA 3.10% · CCC 4.20%", "3.10 / 4.20", "about 3%"])
def test_two_figures_or_prose_in_shared_weight_is_caught(cell):
    rows = HOLDINGS_OK[:3] + [f"| AAA · CCC | 2 | {cell} |", ""]
    found = contract.holdings_problems(contract.split_sections(mode_c(holdings=rows)))
    assert found == [f"AAA · CCC: shared weight is one figure, not {cell!r}"]


@pytest.mark.parametrize("cell", ["3.10", "3.10%", "0", "26"])
def test_one_figure_passes(cell):
    rows = HOLDINGS_OK[:3] + [f"| AAA · CCC | 2 | {cell} |", ""]
    assert contract.holdings_problems(contract.split_sections(mode_c(holdings=rows))) == []


# --------------------------------------------------------------------------
# Spec, SKILL.md and the zip carry it
# --------------------------------------------------------------------------


def _read(path: str) -> str:
    return (REPO / path).read_text(encoding="utf-8")


def test_the_spec_states_the_three_rules():
    spec = _read("references/etf-brief.md")
    assert "**Across providers, compare country lists, never labels.**" in spec
    assert "**Shared weight is one figure:**" in spec
    assert "never from a WebFetch\nsummary.**" in spec


def test_skill_md_runs_the_check_before_printing():
    skill = _read("SKILL.md")
    assert "python3 scripts/check_output.py <file>" in skill
    assert "Self-check: not run" in skill


def test_the_zip_ships_the_checker_with_its_contract(tmp_path):
    sys.path.insert(0, str(REPO / "scripts"))
    import build_zip
    files = build_zip.FILES
    assert files["tests/contract.py"] == "scripts/contract.py"
    assert "scripts/check_output.py" in files
    for src in files:
        assert (REPO / src).exists(), src


def test_the_checker_finds_contract_next_to_it_as_in_the_zip(tmp_path):
    scripts = tmp_path / "buffettbot" / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "check_output.py").write_bytes((REPO / "scripts" / "check_output.py").read_bytes())
    (scripts / "contract.py").write_bytes((REPO / "tests" / "contract.py").read_bytes())
    draft = tmp_path / "draft.md"
    draft.write_text(mode_c(), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(scripts / "check_output.py"), str(draft)],
                          capture_output=True, text=True, cwd=tmp_path)
    assert (proc.returncode, proc.stdout.strip()) == (0, "ok"), proc.stdout + proc.stderr


def test_a_draft_without_a_build_line_is_caught():
    text = mode_c().replace("Build:             0000000 2026-01-01\n", "")
    assert problems(text) == ["METHOD has no Build: line (the text of BUILD in the skill folder)"]


@pytest.mark.parametrize("sep", ["·", "×", "x", "–", "-", "/"])
def test_every_pair_separator_is_read(sep):
    rows = STRUCTURAL_OK[:3] + [f"| AAA {sep} BBB | disjoint | Europe DM vs emerging markets |", ""]
    found = contract.structural_problems(contract.split_sections(mode_c(structural=rows)))
    assert len(found) == 1, (sep, found)


def test_the_zip_carries_a_build_stamp(tmp_path):
    sys.path.insert(0, str(REPO / "scripts"))
    import build_zip
    target = build_zip.build(tmp_path / "b.zip")
    stamp = zipfile.ZipFile(target).read("buffettbot/BUILD").decode().strip()
    assert stamp == build_zip.build_stamp() and len(stamp.split()) == 2


def _skill_references() -> set[str]:
    import re
    return set(re.findall(r"`(references/[\w-]+\.md)`", _read("SKILL.md")))


def test_every_reference_file_ships_in_the_zip():
    sys.path.insert(0, str(REPO / "scripts"))
    import build_zip
    on_disk = {f"references/{p.name}" for p in (REPO / "references").glob("*.md")}
    assert on_disk <= set(build_zip.FILES), sorted(on_disk - set(build_zip.FILES))


def test_every_reference_skill_md_names_exists():
    missing = sorted(r for r in _skill_references() if not (REPO / r).exists())
    assert missing == []
