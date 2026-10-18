"""Build dist/buffettbot.zip from the committed files (HEAD).

    python3 scripts/build_zip.py

The Claude app runs the zip, not the repo, so every change ships through
here. Built from HEAD, not the working tree, so an uncommitted edit never
ships. The previous zip is kept as dist/buffettbot-<old short hash>.zip only
when you pass --keep.
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ZIP = REPO / "dist" / "buffettbot.zip"

# repo path -> path inside the zip's buffettbot/ folder
FILES = {
    "DECISIONS.md": "DECISIONS.md",
    "DISCLAIMER.md": "DISCLAIMER.md",
    "LICENSE": "LICENSE",
    "RULES.md": "RULES.md",
    "SKILL.md": "SKILL.md",
    "scripts/t212_holdings.py": "scripts/t212_holdings.py",
    "scripts/import_holdings.py": "scripts/import_holdings.py",
    "scripts/market_weights.py": "scripts/market_weights.py",
    "scripts/fund_holdings.py": "scripts/fund_holdings.py",
    "templates/me/profile.md": "templates/me/profile.md",
    "templates/me/portfolio.md": "templates/me/portfolio.md",
    "templates/me/pies.md": "templates/me/pies.md",
    "templates/me/ownership.md": "templates/me/ownership.md",
    "templates/me/funds.md": "templates/me/funds.md",
    "templates/me/theses/README.md": "templates/me/theses/README.md",
    "scripts/check_output.py": "scripts/check_output.py",
    "scripts/demo.py": "scripts/demo.py",
    "demo/holdings.csv": "demo/holdings.csv",
    "demo/funds.md": "demo/funds.md",
    "scripts/render.py": "scripts/render.py",
    "scripts/card.py": "scripts/card.py",
    "tests/contract.py": "scripts/contract.py",
    "references/buffett.md": "references/buffett.md",
    "references/buffett-scorecard.md": "references/buffett-scorecard.md",
    "references/checklist.md": "references/checklist.md",
    "references/demo.md": "references/demo.md",
    "references/any-broker.md": "references/any-broker.md",
    "references/etf-brief.md": "references/etf-brief.md",
    "references/lenses.md": "references/lenses.md",
    "references/market-context.md": "references/market-context.md",
    "references/portfolio-sync.md": "references/portfolio-sync.md",
    "references/run-journal.md": "references/run-journal.md",
    "references/setup.md": "references/setup.md",
    "references/stock-brief.md": "references/stock-brief.md",
    "references/thesis-journal.md": "references/thesis-journal.md",
}


# The demo's frozen snapshot (scripts/demo_snapshot.py): every committed file
# under it ships, whatever date its holdings files carry.
DEMO_DATA = "demo/data"


def demo_files() -> dict[str, str]:
    names = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD", DEMO_DATA + "/"], cwd=REPO,
        capture_output=True, text=True, check=True,
    ).stdout.split()
    return {n: n for n in names}


def committed(path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"HEAD:{path}"], cwd=REPO, capture_output=True, check=True
    ).stdout


def build_stamp() -> str:
    """Short commit hash and commit date of HEAD, e.g. `6138ce0 2026-10-03`."""
    return subprocess.run(
        ["git", "log", "-1", "--format=%h %cs"], cwd=REPO,
        capture_output=True, text=True, check=True,
    ).stdout.strip()


def build(target: Path = ZIP) -> Path:
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for src, dst in {**FILES, **demo_files()}.items():
            z.writestr("buffettbot/" + dst, committed(src))
        z.writestr("buffettbot/BUILD", build_stamp() + "\n")
    with zipfile.ZipFile(target) as z:
        bad = z.testzip()
        if bad:
            raise SystemExit(f"corrupt entry in zip: {bad}")
    return target


if __name__ == "__main__":
    if "--keep" in sys.argv and ZIP.exists():
        head = subprocess.run(["git", "rev-parse", "--short", "HEAD~1"], cwd=REPO,
                              capture_output=True, text=True).stdout.strip()
        ZIP.replace(ZIP.with_name(f"buffettbot-{head}.zip"))
    print(f"built {build()} with {len(FILES) + len(demo_files())} files")
