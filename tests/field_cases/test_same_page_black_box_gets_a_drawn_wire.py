"""Field case: a lamp and a unit's black box in one sub-place, a boundary strip X1 wired to the lamp, shown together on one page.
The bug: no black box is drawn for U1 on the place's page, so the wire to H1 is cut into a stub `<- -U1-X1:SIG:1` instead of a real wire.
Open: strict xfail until P7.4 lands its layout decision, which is not yet written."""

from typing import NamedTuple
lazy from pathlib import Path

import fransys as fr
from _drawn_pages import drawn_pages, markers_in, ref_texts

from fransys_model.layout import DrawingSet, Page, layout_of


class _Io(NamedTuple):
    out: fr.Terminal
    back: fr.Terminal


@fr.unit("demo-sub-box", revision=1, interface_version=1, date="2026-01-01", text="x", by="AB")
def _box(u: fr.Design) -> _Io:
    lamp = u.device("P1", "DEMO-LAMP-24")
    strip = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True)
    sig, back = strip.run("SIG", 1), strip.run("BACK", 1)
    u.series(sig[1].inner, lamp.lamp["1"], wire=("WH", 0.75))
    u.series(back[1].inner, lamp.lamp["2"], wire=("BK", 0.75))
    return _Io(sig[1], back[1])


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts")
    room = d.location("R", "Room")
    d.location("S1", "Sub", within="R")
    io = d.add(_box, "U1", place="S1")
    lamp = d.device("H1", "DEMO-LAMP-24", place="S1")
    d.series(io.out.outer, lamp.lamp["1"], wire=("WH", 0.75))
    d.series(io.back.outer, lamp.lamp["2"], wire=("BK", 0.75))
    (tmp_path / "r.md").write_text("# Room\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    return fr.build(d, fr.document(preset, room, cover=tmp_path / "r.md"), fr.document(preset, "demo-sub-box", cover=tmp_path / "r.md"))


def test_a_same_page_black_box_is_joined_by_a_drawn_wire_and_no_stub(tmp_path: Path) -> None:
    """R's page draws a wire to the black box and no stub on H1; U1's document keeps its stub."""
    model = _build(tmp_path).model
    sets, pages = layout_of(model, DrawingSet), layout_of(model, Page)
    own_page = {p.id for p in pages.values() if sets[p.drawing_set].unit is None}
    drawn = drawn_pages(model)
    texts = [text for page in own_page for m in markers_in(drawn[page]) for text in ref_texts(m)]
    assert texts == [], texts
    # a drawn wire carries no subject, so "joins -H1:1 to -U1-X1:SIG:1" reads as: it has a wire
    assert any(drawn[page].wires for page in own_page)
    unit_texts = [text for page, d in drawn.items() if page not in own_page for m in markers_in(d) for text in ref_texts(m)]
    assert any("+R+S1-H1:1" in text for text in unit_texts), unit_texts
