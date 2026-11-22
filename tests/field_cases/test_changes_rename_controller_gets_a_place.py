"""Field case: a controller, alone or with a connector wired to it, is given a `place=` between two releases and keeps its identity.
The bug: the change list matched items by printed designation, so a rename printed as a removal, and so did the wire between two renamed items.
Fixed by model-0300 (CHANGES-RENAME), both listings carry item keys, so the diff gives one `renamed` row per item and none for the wire."""

from typing import TYPE_CHECKING

import fransys as fr
from _changes_rows import changes_rows, rows_of
from fransys.colours import BK

if TYPE_CHECKING:
    from pathlib import Path


def _build(revision: int, *, place: str | None, both: bool = False) -> fr.BuildResult:
    """Controller `K1` wired to connector `X1`; `place` is the only thing that moves, on `X1` too when `both`."""
    d = fr.design("demo_parts")
    d.project(title="Rename", number="CR-1", customer="Example Co", revision=revision, author="XX")
    for n in range(1, revision + 1):
        d.revision(n, date="2026-10-16", text="Issue", created="XX")
    d.location("CSN", "Cabinet")
    k1 = d.device("K1", "DEMO-CTRL-8", place=place)
    x1 = d.device("X1", "DEMO-CONN-2P", place=place if both else None)
    d.series(k1.X1["1"], x1["1"], wire=(BK, 0.5))
    return fr.build(d)


def test_a_placed_controller_gives_one_renamed_row(tmp_path: Path) -> None:
    """One `renamed` row names the controller; no item, wire, mate or net is added or removed."""
    fr.release(_build(1, place=None), tmp_path)
    rows = changes_rows(fr.release(_build(2, place="CSN"), tmp_path))
    (renamed,) = rows_of(rows, "items", "renamed")
    assert (renamed["subject"], renamed["before"], renamed["after"]) == (
        "+CSN-K1",
        "-K1",
        "+CSN-K1",
    )
    assert [r for r in rows if r["change"] in {"added", "removed"}] == []


def test_a_wire_between_two_renamed_items_gives_no_conductor_row(tmp_path: Path) -> None:
    """Two `renamed` item rows, and no row of any kind in the conductors section."""
    fr.release(_build(1, place=None, both=True), tmp_path)
    rows = changes_rows(fr.release(_build(2, place="CSN", both=True), tmp_path))
    assert len(rows_of(rows, "items", "renamed")) == 2
    assert [r for r in rows if r["section"] == "conductors"] == []
