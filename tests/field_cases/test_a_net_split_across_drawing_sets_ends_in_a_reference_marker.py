"""Field case: a net split across two drawing sets keeps a reference marker at its far end.

The engineering shape: a sensor wired at the top level to the input channel of a PLC card that sits
inside a unit, so the two ends of the net fall into different drawing sets.

The bug: `placement_sets._net` drops a net with fewer than two pins in a set, so the net has no wire
and no reference marker in either set, and the build says only `NET_CUT_BY_SET`. The rule is
CROSS-SET-NET (GAP-FLIP-207): each set draws its end of the net with a reference marker. Known
gap (designer 2026-10-19 R301); strict xfail until the core draws it.
"""

import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages
from fransys.colours import BU

_MARKER = "reference-marker"  # the library symbol an end draws as (ELECTRICAL-MARKERS)


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
    d.detail.wire(sensor["1"], cab.card.di_1["1"], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Room\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, room, cover=cover))


def test_the_far_end_of_a_net_split_across_sets_shows_a_reference_marker() -> None:
    pages = drawn_pages(_build().model).values()
    markers = [s for d in pages for s in d.symbols if s.key == _MARKER]
    assert len(markers) + sum(len(d.markers) for d in pages) >= 1
