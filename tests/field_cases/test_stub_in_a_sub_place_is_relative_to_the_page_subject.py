"""Field case: a place R's page, a unit's boundary strip and a lamp, both in R's sub-place S1.

The rule (STUB-PAGE-CONTEXT, on the roadmap before 1.0): an off stub on a page prints no place
the page's subject states, so on R's page a far end in `+R+S1` prints `+S1-U1-X1:SIG:1`.

The gap: layout-0121 reads the near end's place, which here is S1, so the stub prints
`-U1-X1:SIG:1` and drops a sub-place the page does not state. The final rule is relative to the
page subject (R). Strict xfail until STUB-PAGE-CONTEXT lands.

The decision that pins the interim: layout-0121.
"""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
import pytest

from fransys_model.derive.drawing_text import marker_text
from fransys_model.layout import DrawingSet, LinkMarker, Page, layout_of

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    out: fr.Terminal


@fr.unit("demo-sub-box", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _box(u: fr.Design) -> _Io:
    lamp = u.device("P1", "DEMO-LAMP-24")
    sig = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True).run("SIG", 1)
    u.wire(sig[1], lamp.lamp["1"], wire=("WH", 0.75))
    return _Io(sig[1])


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts")
    room = d.location("R", "Room")
    d.location("S1", "Sub", within="R")
    io = d.add(_box, "U1", place="S1")
    lamp = d.device("H1", "DEMO-LAMP-24", place="S1")
    d.wire(io.out, lamp.lamp["1"], wire=("WH", 0.75))
    (tmp_path / "r.md").write_text("# Room\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    return fr.build(d, fr.document(preset, room, cover=tmp_path / "r.md"))


@pytest.mark.xfail(strict=True, reason="STUB-PAGE-CONTEXT: the stub is relative to the near end")
def test_a_stub_on_the_place_page_prints_the_sub_place_below_the_page_subject(
    tmp_path: Path,
) -> None:
    """On R's page, a far end in `+R+S1` prints `+S1-U1-X1:SIG:1`, as the page states only R."""
    model = _build(tmp_path).model
    sets, pages = layout_of(model, DrawingSet), layout_of(model, Page)
    texts = [
        marker_text(model, m)
        for m in layout_of(model, LinkMarker).values()
        if sets[pages[m.page].drawing_set].unit is None
    ]
    assert texts == ["← +S1-U1-X1:SIG:1"], texts
