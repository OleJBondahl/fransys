"""`just regen-goldens [PKG]`: rewrite the tracked goldens on a work branch, show their diff stat.

Decision 0101: the one named shape for a golden regeneration, so an order names a recipe and not an
ad-hoc command chain. It refuses on `main`: agents cannot discard tracked changes there. PKG is
`model`, `layout`, `listing` or empty for all three. Layout runs only the test files that read
the option.
Run via `uv run python scripts/regen_goldens.py [PKG]`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LAYOUT_DIR = "packages/fransys-layout/tests"
# Alphabetical: drawing_text_equality must run before test_usecases (narrow digest).
LAYOUT_GOLDEN_TESTS = (
    f"{LAYOUT_DIR}/engines/test_cable_golden.py",
    f"{LAYOUT_DIR}/usecases/test_drawing_text_equality.py",
    f"{LAYOUT_DIR}/usecases/test_power_golden.py",
    f"{LAYOUT_DIR}/usecases/test_usecases.py",
)
RUNS = {
    "model": (
        ["uv", "run", "python", "packages/fransys-model/tests/usecases/regenerate_goldens.py"],
        "packages/fransys-model/tests/golden",
    ),
    "layout": (
        ["uv", "run", "pytest", *LAYOUT_GOLDEN_TESTS, "--regenerate-golden", "-q"],
        "packages/fransys-layout/tests/golden",
    ),
    "listing": (["uv", "run", "python", "tests/listing_golden_cases.py"], "tests/golden/listing"),
}


def _run(args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess:
    """`args` is a fixed `git`/`uv` list built here, never user input."""
    return subprocess.run(  # noqa: S603 - fixed argument lists from RUNS and main, no user input
        args, cwd=ROOT, check=False, capture_output=capture, text=True
    )


def main(argv: list[str]) -> int:
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], capture=True).stdout.strip()
    if branch == "main":
        sys.stderr.write("regen-goldens: refused on main; run it in a work branch's worktree\n")
        return 2
    picked = argv or list(RUNS)
    unknown = [p for p in picked if p not in RUNS]
    if unknown:
        sys.stderr.write(f"regen-goldens: unknown package {unknown}; choose from {list(RUNS)}\n")
        return 2
    code = max(_run(RUNS[name][0]).returncode for name in picked)
    _run(["git", "diff", "--stat", "--", *(RUNS[name][1] for name in picked)])
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
