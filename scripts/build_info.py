"""Which build of Holdnote is running: the text for METHOD's `Build:` line.

    python3 <skill>/scripts/build_info.py

Holdnote reaches people three ways, and each one leaves a different trace:

- the release zip carries a `BUILD` file, e.g. `6138ce0 2026-10-03`;
- a clone of the repo has git history, so the stamp is read from it;
- a Claude Code plugin install has neither. Claude Code names the install
  folder after the commit it installed (`.../cache/holdnote/holdnote/
  a5e925efa5b2/`), so that 12-character hash is the stamp.

Prints one line. `unknown` only when none of the three is there.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
COMMIT = re.compile(r"[0-9a-f]{12}")


def build_stamp(root: Path = SKILL) -> str:
    for f in (root / "BUILD", root / "scripts" / "BUILD"):
        if f.is_file():
            text = f.read_text(encoding="utf-8").strip()
            if text:
                return text
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%h %cs"], cwd=root,
                             capture_output=True, text=True, check=True).stdout.strip()
        if out:
            return out + " (repo)"
    except (OSError, subprocess.CalledProcessError):
        pass
    if COMMIT.fullmatch(root.name):
        return root.name[:7] + " (plugin)"
    return "unknown"


if __name__ == "__main__":
    print(build_stamp())
