"""`just ci`: the gates run side by side, each gate's output prints as one block, in order (AW14).

The cheap groups (`check`, `dead-code`, the lean checks) run at once; `cov` with the floors and the internal gate start only when they are green.
Output is captured per gate and printed in the serial order (check, dead-code, cov, cov_floors,
lean hard, enforce, report), so a log reads as before. The exit code is the first failing
gate's; a failure never hides a later block of the same phase.
"""

import subprocess
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

_GROUPS: tuple[tuple[tuple[str, ...], ...], ...] = (
    (("just", "check"),),
    (("just", "dead-code"),),
    (
        ("just", "cov"),
        (
            "uv",
            "run",
            "python",
            "scripts/cov_floors.py",
            "check",
            ".fransys/coverage.json",
            "coverage-floors.toml",
        ),
    ),
    (
        ("uv", "run", "python", "scripts/lean_check.py", "hard"),
        ("uv", "run", "python", "scripts/lean_check.py", "enforce"),
        ("uv", "run", "python", "scripts/lean_check.py", "report"),
    ),
)

Block = tuple[int, bytes]
Groups = tuple[tuple[tuple[str, ...], ...], ...]
Runner = Callable[[list[str], dict[str, str]], tuple[int, str]]

ROOT = Path(__file__).resolve().parents[1]
PYTEST_MARKS = ("cov", "internal-gate")

# Tracked files a test reads as data or at import only; the sweep key (sweep_cache) hashes them.
DATA_GLOBS: tuple[str, ...] = (
    "packages/electrical-symbols/symbols/**",
    "packages/electrical-symbols/build/**",
    "examples/**",
    "**/pyproject.toml",
    "uv.lock",
    "packages/*/src/*/conventions/**",  # module-level tables are read at import only
    "packages/fransys-el/src/*/texts.py",  # the text-placement table, read at import only
    "packages/fransys-model/src/fransys_model/derive/rows.py",  # the same, for the row shapes
)
# Every non-.py file under these is data too (bundle.json, guide pages, fonts, fixtures).
NON_PY_UNDER: tuple[str, ...] = ("packages/*/src/**", "packages/*/tests/**", "tests/**")


def run_group(group: tuple[tuple[str, ...], ...]) -> list[Block]:
    """Run one group's commands in order; stop the group at its first failure."""
    blocks: list[Block] = []
    for argv in group:
        done = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)  # noqa: S603 -- fixed argv
        blocks.append((done.returncode, done.stdout))
        if done.returncode:
            break
    return blocks


def all_groups(root: Path = ROOT) -> Groups:
    """`_GROUPS`, plus the maintainers' own gate (`internal-gate`, internal/internal.just) where the full repo has its recipes (R1348)."""
    internal = (("just", "internal-gate"),)
    return (*_GROUPS, internal) if (root / "internal" / "internal.just").is_file() else _GROUPS


def runs_pytest(group: tuple[tuple[str, ...], ...]) -> bool:
    """True for the groups that start pytest: `just cov` and the internal gate."""
    return any(mark in argv for argv in group for mark in PYTEST_MARKS)


def run_phase(groups: Groups) -> list[list[Block]]:
    with ThreadPoolExecutor(max(1, len(groups))) as pool:
        return list(pool.map(run_group, groups))


def run_all(groups: Groups | None = None) -> int:
    """Phase 1 runs the cheap gates at once; phase 2, the pytest groups, starts only when phase 1 is green (AWS-COST-1, lint first)."""
    groups = all_groups() if groups is None else groups
    cheap = run_phase(tuple(g for g in groups if not runs_pytest(g)))
    skipped = any(code for blocks in cheap for code, _ in blocks)
    heavy = [] if skipped else run_phase(tuple(g for g in groups if runs_pytest(g)))
    results = iter(cheap), iter(heavy)
    none: list[Block] = []
    code = 0
    for group in groups:
        for returncode, output in next(results[runs_pytest(group)], none):
            sys.stdout.flush()
            sys.stdout.buffer.write(output)
            sys.stdout.buffer.flush()
            code = code or returncode
    if skipped:
        sys.stdout.write("pytest not started: a lint or lean gate failed; fix it and run again\n")
    return code


def source_files(root: Path) -> list[Path]:
    """Every `.py` under `root/packages/*/src`, sorted: the one walk of the source tree."""
    return sorted(root.glob("packages/*/src/**/*.py"))


def test_files(root: Path) -> list[Path]:
    """Every `.py` under `packages/*/tests`, `tests` and the root-level `*/tests` (the internal tools'), sorted: the one walk of the test trees."""
    return sorted(f for pattern in ("packages/*/tests/**/*.py", "tests/**/*.py", "*/tests/**/*.py") for f in root.glob(pattern))


if __name__ == "__main__":
    sys.exit(run_all())
