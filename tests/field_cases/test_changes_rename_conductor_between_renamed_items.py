"""Field case: a wire between two items that are both renamed gives no row.

The engineering shape: a controller and a connector joined by one conductor. In the next revision
both get `place="CSN"`, so both ends of the conductor print differently (`-K1:1 -X1:1` becomes
`+CSN-K1:1 +CSN-X1:1`). The conductor itself is unchanged.

The bug: conductors were matched by their printed ends, so the wire printed as removed plus added.

The rule (decision model-0300, CHANGES-RENAME): ends are compared by item key and pin, so the two
items give two `renamed` rows and the conductor gives no row at all.
"""

import csv
import io
from typing import TYPE_CHECKING

import fransys as fr
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
    d.detail.wire(k1.X1["1"], x1["1"], wire=(BK, 0.5))
    return fr.build(d)


def _rows(release: Path) -> list[dict[str, str]]:
    """The stored change list of a release, one dict per CSV row."""
    text = (release / "data" / "changes.csv").read_text(encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def _of(rows: list[dict[str, str]], section: str, change: str) -> list[dict[str, str]]:
    return [r for r in rows if r["section"] == section and r["change"] == change]


def test_a_wire_between_two_renamed_items_gives_no_conductor_row(tmp_path: Path) -> None:
    """Two `renamed` item rows, and no row of any kind in the conductors section."""
    fr.release(_build(1, place=None), tmp_path)
    rows = _rows(fr.release(_build(2, place="CSN"), tmp_path))
    assert len(_of(rows, "items", "renamed")) == 2
    assert [r for r in rows if r["section"] == "conductors"] == []
