"""Field case: a controller and a connector joined by one conductor are both renamed to a new place in the next revision.
The bug: conductors were matched by their printed ends, so the unchanged wire printed as removed plus added.
Fixed by model-0300 (CHANGES-RENAME), ends are compared by item key and pin, so the wire gives no row at all."""

from typing import TYPE_CHECKING

import fransys as fr
from _changes_rows import changes_rows, rows_of
from fransys.colours import BK

if TYPE_CHECKING:
    from pathlib import Path


def _build(revision: int, *, place: str | None) -> fr.BuildResult:
    """Controller `K1` wired to connector `X1`; both take `place`."""
    d = fr.design("demo_parts")
    d.project(title="Rename", number="CR-5", customer="Example Co", revision=revision, author="XX")
    for n in range(1, revision + 1):
        d.revision(n, date="2026-10-16", text="Issue", created="XX")
    d.location("CSN", "Cabinet")
    k1 = d.device("K1", "DEMO-CTRL-8", place=place)
    x1 = d.device("X1", "DEMO-CONN-2P", place=place)
    d.series(k1.X1["1"], x1["1"], wire=(BK, 0.5))
    return fr.build(d)


def test_a_wire_between_two_renamed_items_gives_no_conductor_row(tmp_path: Path) -> None:
    """Two `renamed` item rows, and no row of any kind in the conductors section."""
    fr.release(_build(1, place=None), tmp_path)
    rows = changes_rows(fr.release(_build(2, place="CSN"), tmp_path))
    assert len(rows_of(rows, "items", "renamed")) == 2
    assert [r for r in rows if r["section"] == "conductors"] == []
