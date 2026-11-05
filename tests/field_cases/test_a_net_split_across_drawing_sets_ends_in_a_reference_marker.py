"""Field case: a sensor at the top level is wired to a PLC card input inside a unit, so the net's ends fall in different sets.
The claim: each set draws its end of the net as a reference marker symbol, on both pages (CROSS-SET-NET, GAP-FLIP-207; designer R301)."""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages, markers_in
from fransys.colours import BU


class _Io(NamedTuple):
    card: Any


@fr.unit("demo-di-cab", revision=1, interface_version=1, date="2026-10-19", text="1", by="XX")
def _cab(u: Any) -> _Io:
    return _Io(u.device("DI", "DEMO-PLC-DI-2", interface=("di_1",)))


def _build() -> fr.BuildResult:
    d = fr.design("demo_parts")
    room = d.location("R", "Room")
    cab = d.add(_cab, "U1", place="R")
    sensor = d.device("B1", "DEMO-SENSOR-2W", place="R")
    d.series(sensor["1"], cab.card.di_1["1"], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Room\n", encoding="utf-8")
    cabinet = fr.DocumentPreset.CABINET_SCHEMATIC
    return fr.build(d, fr.document(cabinet, room, cover=cover), fr.document(cabinet, "demo-di-cab", cover=cover))


def test_the_far_end_of_a_net_split_across_sets_shows_a_reference_marker() -> None:
    pages = drawn_pages(_build().model).values()
    assert sum(len(markers_in(d)) for d in pages) >= 2
