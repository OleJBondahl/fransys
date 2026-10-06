"""`just cov`'s coverage-floor gate (decision 0048: fixed floors, no ratchet).

Driven by a `coverage.py` JSON report and the tracked `coverage-floors.toml`. `check REPORT
FLOORS` fails when a package's measured statement coverage is below its floor, is missing from
the floors file, or has no measured statements at all (a grouping defect that must be loud,
never a silent pass). Floors are fixed at 95.0 per package and never raised; there is no
`raise` or `land` command here any more.

Not a package module (loaded by file path, never imported): lives under root `scripts/`, run via
`uv run python scripts/cov_floors.py check REPORT FLOORS`.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence


def workspace_packages(root: Path) -> dict[str, str]:
    """Import name -> root-relative posix path, for every `packages/*` workspace member.

    Reads the root `pyproject.toml`'s `[tool.uv.workspace] members`, keeps only members under
    `packages/` (the set `just cov` measures), and reads each kept member's own `pyproject.toml`
    for its `[project] name`, normalized (hyphens to underscores) to an import name.
    """
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    members: list[str] = data["tool"]["uv"]["workspace"]["members"]
    expected: dict[str, str] = {}
    for member in members:
        posix_member = member.replace("\\", "/")
        if not posix_member.startswith("packages/"):
            continue
        project = tomllib.loads((root / member / "pyproject.toml").read_text(encoding="utf-8"))
        import_name = project["project"]["name"].replace("-", "_")
        expected[import_name] = posix_member
    return expected


def _statement_totals(report: dict, expected: Mapping[str, str]) -> dict[str, tuple[int, int]]:
    """Sum `(num_statements, missing_lines)` per package, grouping by path segment.

    A file belongs to a package iff its normalized (backslashes to forward slashes) path starts
    with `f"{member}/src/"`. This is a path-segment prefix, never a dotted-name prefix: a
    `startswith` on the import name would put `fransys_model`'s files under `fransys` too.
    """
    totals: dict[str, tuple[int, int]] = dict.fromkeys(expected, (0, 0))
    prefixes = {pkg: f"{member}/src/" for pkg, member in expected.items()}
    for raw_path, file_data in report["files"].items():
        normalized = raw_path.replace("\\", "/")
        summary = file_data["summary"]
        for pkg, prefix in prefixes.items():
            if normalized.startswith(prefix):
                statements, missing = totals[pkg]
                totals[pkg] = (
                    statements + summary["num_statements"],
                    missing + summary["missing_lines"],
                )
                break
    return totals


def _percent(statements: int, missing: int) -> Decimal | None:
    """The covered percent, or `None` when `statements` is zero (nothing measured)."""
    if statements == 0:
        return None
    return Decimal(statements - missing) / Decimal(statements) * 100


def measure_packages(report: dict, expected: Mapping[str, str]) -> dict[str, Decimal | None]:
    """Each expected package's measured percent, or `None` when it has no measured statements."""
    totals = _statement_totals(report, expected)
    return {pkg: _percent(*totals[pkg]) for pkg in expected}


def check(
    expected: Mapping[str, str],
    floors: Mapping[str, Decimal],
    measured: Mapping[str, Decimal | None],
) -> tuple[str, ...]:
    """Failure lines: no measured coverage, missing from the floors file, or below floor."""
    failures: list[str] = []
    for pkg in sorted(expected):
        percent = measured[pkg]
        if percent is None:
            failures.append(f"FAIL {pkg}: no measured coverage found (coverage.json)")
            continue
        if pkg not in floors:
            failures.append(f"FAIL {pkg}: missing from coverage-floors.toml")
            continue
        floor = floors[pkg]
        if percent < floor:
            failures.append(
                f"FAIL {pkg}: {percent:.1f} measured, floor {floor:.1f} (coverage-floors.toml)"
            )
    return tuple(failures)


def load_floors(path: Path) -> dict[str, Decimal]:
    """Read `coverage-floors.toml` (`name = 99.2` lines) into `name -> Decimal("99.2")`."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return {name: Decimal(str(value)) for name, value in data.items()}


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point: `check REPORT FLOORS`, the only command.

    Exits 1 on any failure and never writes.
    """
    parser = argparse.ArgumentParser(prog="cov_floors.py", description=__doc__.splitlines()[0])
    subparsers = parser.add_subparsers(dest="command", required=True)
    sub = subparsers.add_parser("check")
    sub.add_argument("report", type=Path)
    sub.add_argument("floors", type=Path)
    args = parser.parse_args(argv)

    root = Path(__file__).resolve().parent.parent
    expected = workspace_packages(root)
    report = json.loads(args.report.read_text(encoding="utf-8"))
    floors = load_floors(args.floors)
    measured = measure_packages(report, expected)
    failures = check(expected, floors, measured)

    sys.stdout.write(f"coverage floors: {len(expected)} packages\n")
    for line in failures:
        sys.stdout.write(f"{line}\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
