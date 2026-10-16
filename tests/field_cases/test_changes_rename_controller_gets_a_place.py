"""Field case: a controller is given a `place=` between two releases and keeps its identity.

The engineering shape: a system holds a controller wired to a plain connector. In the next
revision the engineer adds `place="CSN"` to the controller, so it prints `+CSN-K1` instead of
`-K1`. Nothing else changes: the authoring key (scope prefix, tag) is the same.

The bug: the change list matched items, conductors, mates and nets by printed designation, so a
rename printed as a removal plus an addition of the item and of every wire on it.

The rule (decision model-0300, CHANGES-RENAME): both listings carry item keys, so the diff
matches by key and gives one `renamed` row (subject the new designation, `before` the old one,
`after` the new one), with no added or removed row for the item or its wires.
"""

import csv
import io
from typing import TYPE_CHECKING

import fransys as fr
from fransys.colours import BK

if TYPE_CHECKING:
    from pathlib import Path


def _build(revision: int, *, place: str | None) -> fr.BuildResult:
    """Controller `K1` wired to connector `X1`; `place` is the only thing that moves."""
    d = fr.design("demo_parts")
    d.project(title="Rename", number="CR-1", customer="Example Co", revision=revision, author="XX")
    for n in range(1, revision + 1):
        d.revision(n, date="2026-10-16", text="Issue", created="XX")
    d.location("CSN", "Cabinet")
    k1 = d.device("K1", "DEMO-CTRL-8", place=place)
    x1 = d.device("X1", "DEMO-CONN-2P")
    d.detail.wire(k1.X1["1"], x1["1"], wire=(BK, 0.5))
    return fr.build(d)


def _rows(release: Path) -> list[dict[str, str]]:
    """The stored change list of a release, one dict per CSV row."""
    text = (release / "data" / "changes.csv").read_text(encoding="utf-8")
    return list(csv.DictReader(io.StringIO(text)))


def _of(rows: list[dict[str, str]], section: str, change: str) -> list[dict[str, str]]:
    return [r for r in rows if r["section"] == section and r["change"] == change]


def test_a_placed_controller_gives_one_renamed_row(tmp_path: Path) -> None:
    """One `renamed` row names the controller; no item, wire, mate or net is added or removed."""
    fr.release(_build(1, place=None), tmp_path)
    rows = _rows(fr.release(_build(2, place="CSN"), tmp_path))
    (renamed,) = _of(rows, "items", "renamed")
    assert (renamed["subject"], renamed["before"], renamed["after"]) == (
        "+CSN-K1",
        "-K1",
        "+CSN-K1",
    )
    assert [r for r in rows if r["change"] in {"added", "removed"}] == []
