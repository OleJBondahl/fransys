"""Field case: a lamp and a unit's black box in one sub-place, shown together on the place's page.

The shape: a place R holds a sub-place S1, and S1 holds a unit U1 (a boundary strip X1) and a
lamp H1 wired to X1:SIG:1. R's document shows both on one page.

The bug: the engine draws no black box for U1 on R's page, so the wire to H1 is cut into a stub
`<- -U1-X1:SIG:1` on H1's pin. Owner 2026-10-16, "Draw the wire": when a device and a unit's
black box share a page, a real wire joins them, and an arrow stays only for an end on another
page. U1's own document still prints its stub `<- +R+S1-H1:1`. Strict xfail until P7.4.

The record to come: a layout decision, written when P7.4 lands it.
"""

from typing import TYPE_CHECKING, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages

from fransys_model.layout import DrawingSet, Page, layout_of

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    out: fr.Terminal


@fr.unit("demo-sub-box", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _box(u: fr.Design) -> _Io:
    lamp = u.device("P1", "DEMO-LAMP-24")
    sig = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True).run("SIG", 1)
    u.detail.wire(sig[1], lamp.lamp["1"], wire=("WH", 0.75))
    return _Io(sig[1])


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts")
    room = d.location("R", "Room")
    d.location("S1", "Sub", within="R")
    io = d.add(_box, "U1", place="S1")
    lamp = d.device("H1", "DEMO-LAMP-24", place="S1")
    d.detail.wire(io.out, lamp.lamp["1"], wire=("WH", 0.75))
    (tmp_path / "r.md").write_text("# Room\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    return fr.build(d, fr.document(preset, room, cover=tmp_path / "r.md"))


def test_a_same_page_black_box_is_joined_by_a_drawn_wire_and_no_stub(tmp_path: Path) -> None:
    """R's page draws a wire to the black box and no stub on H1; U1's document keeps its stub."""
    model = _build(tmp_path).model
    sets, pages = layout_of(model, DrawingSet), layout_of(model, Page)
    own_page = {p.id for p in pages.values() if sets[p.drawing_set].unit is None}
    drawn = drawn_pages(model)
    texts = [text for page in own_page for m in drawn[page].markers for _, text in m.texts]
    assert texts == [], texts
    # a drawn wire carries no subject, so "joins -H1:1 to -U1-X1:SIG:1" reads as: it has a wire
    assert any(drawn[page].wires for page in own_page)
    unit_texts = [
        text
        for page, d in drawn.items()
        if page not in own_page
        for m in d.markers
        for _, text in m.texts
    ]
    assert any("+R+S1-H1:1" in text for text in unit_texts), unit_texts
