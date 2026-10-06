"""Reference-designation check (spec `2026-09-25-release-read-fixes.md`, acceptance 1).

R1: a reference ends with the designation the row prints (`derive.designation.
reference_designation`, folded with its `unit=` form). At Schematika v0.3.1 a terminal's
reference dropped its strip (`-X01:L1:1` read `=SUP+<place>-L1:1`, no `X01:` in it), so this checks
every row of every `designations.csv` -- cabinet, board and all -- against the row it names,
not against a hardcoded expectation: the fix must hold for every row, not just the ones this
test's author thought to enumerate.
"""

import csv
from pathlib import Path


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _assert_references_end_with_their_designation(path: Path) -> None:
    rows = _read_rows(path)
    assert rows, f"{path} has no rows"
    for row in rows:
        designation = row["designation"]
        reference = row["reference"]
        assert reference.endswith(designation), (
            f"{path}: designation {designation!r} has reference {reference!r}, "
            f"which does not end with it"
        )


def test_cabinet_designations_reference_ends_with_designation(built: tuple) -> None:
    _result, out_dir, _intermediates = built
    _assert_references_end_with_their_designation(
        out_dir / "cabinet" / "pump-cabinet-v1.6-designations.csv"
    )


def test_board_designations_reference_ends_with_designation(built: tuple) -> None:
    _result, out_dir, _intermediates = built
    _assert_references_end_with_their_designation(
        out_dir / "board" / "relay-interface-board-v1.3-designations.csv"
    )


def test_all_designations_reference_ends_with_designation(built: tuple) -> None:
    _result, out_dir, _intermediates = built
    _assert_references_end_with_their_designation(out_dir / "all" / "EX-1-v1.3-designations.csv")
