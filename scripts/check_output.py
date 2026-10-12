"""Check a composed BuffettBot output against the output contract.

    python3 scripts/check_output.py draft.md

Prints `ok` and exits 0, or prints one problem per line and exits 1. SKILL.md
-> Output contract runs it on every draft before the output is printed.

The checks live in contract.py: tests/contract.py in the repo, copied to
scripts/contract.py in the skill zip by scripts/build_zip.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for folder in (HERE, HERE.parent / "tests"):
    if (folder / "contract.py").exists():
        sys.path.insert(0, str(folder))
        break

import contract  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: python3 scripts/check_output.py <output file>")
        return 2
    text = Path(argv[1]).read_text(encoding="utf-8")
    problems = contract.output_problems(text)
    print("\n".join(problems) if problems else "ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
