"""`just regen-goldens [PKG]`: rewrite the tracked goldens on a work branch, show their diff stat.

Decision 0101: the one named shape for a golden regeneration, so an order names a recipe and not an
ad-hoc command chain. It refuses on `main`: agents cannot discard tracked changes there. PKG is
`model`, `layout`, `render`, `listing` or empty for all four. Layout runs only the test files
that read the option.
Run via `uv run python scripts/regen_goldens.py [PKG]`.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from fransys_model.vocab import SCHEMA_VERSION

ROOT = Path(__file__).resolve().parent.parent
LAYOUT_DIR = "packages/fransys-layout/tests"
# `cable_blocks.txt` regenerates through pytest. The two `*_laid_out.json` that `test_marker_box_size.py` reads were
# written by an engine that is gone, so `_migrate_laid_out` carries them to the current record shape. `overview_html_sha256.txt`
# has no entry: it is edited by hand.
LAYOUT_GOLDEN_TESTS = (f"{LAYOUT_DIR}/engines/test_cable_golden.py",)
REMOVED_TABLES = ("layout.chain", "layout.break_before", "layout.keep_together", "layout.page_title", "layout.pins_below", "layout.side_hint")
REMOVED_MARKER_KEYS = ("box_x", "lead", "stub_extra", "via_x", "via_y", "vertical", "wrap_at")  # schema 30 (R2228)
REMOVED_PROFILE_KEYS = ("actuator_each_contact", "marker_padding", "route_crossing_penalty", "route_turn_penalty")
RUNS = {
    "model": (
        [
            "env",
            "PYTHONPATH=packages/fransys-model/tests/derive:tests",  # derive_helpers.with_house, library_records
            "uv",
            "run",
            "python",
            "packages/fransys-model/tests/usecases/regenerate_goldens.py",
        ],
        "packages/fransys-model/tests/golden",
    ),
    "layout": (
        ["uv", "run", "pytest", *LAYOUT_GOLDEN_TESTS, "--regenerate-golden", "-q"],
        "packages/fransys-layout/tests/golden",
    ),
    "render": (
        ["uv", "run", "python", "packages/fransys-render/tests/test_drawing_golden.py"],
        "packages/fransys-render/tests/golden",
    ),
    "listing": (["uv", "run", "python", "tests/listing_golden_cases.py"], "tests/golden/listing"),
}


def _run(args: list[str], *, capture: bool = False) -> subprocess.CompletedProcess[str]:
    """`args` is a fixed `git`/`uv` list built here, never user input."""
    return subprocess.run(  # noqa: S603 - fixed argument lists from RUNS and main, no user input
        args, cwd=ROOT, check=False, capture_output=capture, text=True
    )


ADDED_NULL_KEYS = (  # (table, key) each schema added as a nullable field
    ("conductor", "block"),  # schema 25 (model-0442)
    ("port_template", "connector"),  # schema 28 (model-0448)
    ("port_template", "connector_pin"),  # schema 28
    ("function_template", "box_side"),  # schema 29 (model-0449)
)


def _aspects_by_name(data: dict[str, Any]) -> None:
    """Schema 31 (model-0457): a refdef enum is stored by member name, so `"function"` becomes `"FUNCTION"`; idempotent."""
    for row in data["tables"].get("aspect_node", ()):
        row["aspect"] = row["aspect"].upper()


def _migrate_marker(row: dict[str, Any]) -> None:
    """One marker row: the seven unwritten fields go (schema 30), `far` became `pairs` (R1334) and its `carrier` a pair's (R1590)."""
    for key in REMOVED_MARKER_KEYS:
        row.pop(key, None)
    if "far" in row:
        far = row.pop("far")
        row["pairs"] = [] if far is None else [{"far": far, "port": row["port"]}]
    carrier = row.pop("carrier", None)
    for pair in row["pairs"]:
        pair.setdefault("carrier", carrier)
        carrier = None


def _migrate_laid_out() -> None:
    """Carry the two laid-out goldens to the current schema: a marker's `far` became `pairs` (R1334), its `carrier` a pair's (R1590); idempotent."""
    for path in (ROOT / LAYOUT_DIR / "golden").glob("cabinet_*_laid_out.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["schema_version"] = SCHEMA_VERSION
        for table in REMOVED_TABLES:  # API-022 P2: the hints and their records are gone
            data["tables"].pop(table, None)
        for row in data["tables"].get("layout.profile", ()):
            for key in REMOVED_PROFILE_KEYS:
                row.pop(key, None)
        _aspects_by_name(data)
        for table, key in ADDED_NULL_KEYS:
            for row in data["tables"].get(table, ()):
                row.setdefault(key, None)
        for row in data["tables"].get("layout.link_marker", ()):
            _migrate_marker(row)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    if "layout" in picked:
        _migrate_laid_out()
    _run(["git", "diff", "--stat", "--", *(RUNS[name][1] for name in picked)])
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
