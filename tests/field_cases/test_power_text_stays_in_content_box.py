"""Field case: the text of a supply bar never leaves the sheet's content box, nor rests on its edge.

The engineering shape: a cabinet on a 24 V DC supply (rails 24 V and 0 V) with a PSU, five PLC
input channels and five lamps, all pins wired to their rail's hub, so each cut end is a power
symbol. The PSU's `+` output stands at the left edge of the first page's first column. Its bar
prints the net's name "24V" beside the bar (since layout-0114 below it, past the bar).

The bug: the bar's text was placed with no content box, so the first free candidate was left of
the bar, at x = -8, across the drawing frame's left border. The page shift then moved the whole
page 8 units right, which left the text flush on the border instead of clear of it.

The rule (spec P3, S18; the owner's predefined text positions, best wins, 2026-09-25): a text
candidate that crosses the content box is never chosen. The fix passes the page's content box
to the power texts' space (work order TEXT-IN-FRAME).

The second bug: with that rule the PSU's "24V" had no place on its page. Its right side is the
PSU's own 0 V stem, its left side was outside the content box, and the unplaced text lay on the
stem. The PSU's box also stood on the frame's left line, because only the old page shift had
ever given the left text room. The fix counts a supply text in its column's room, as a tag is
counted (work order TEXT-ROOM).

Layout-0114 (owner 2026-10-05): a supply text stands past its bar, centred on the lead, never
beside it, so it needs no room to the left of the box, and the box may stand at the frame's
left edge as any first box of a page does.
"""

import fransys as fr
from fransys.colours import BU

from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.geometry import Box, generic_box_geometry, overlaps, translate
from fransys_model.layout import Label, PowerSymbol, SymbolPlacement, layout_of


def _build(tmp_path):
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        loads = [
            (d.device(f"K{i}", "DEMO-PLC-DI-2"), d.device(f"P{i}", "DEMO-LAMP-24"))
            for i in range(5)
        ]
    d.ac_supply("MAINS", 230, psu.input["L"], n=psu.input["N"])
    d.dc_supply("S", psu)
    for di, lamp in loads:
        d.wire(psu.output["+"], di.di_1["1"], wire=(BU, 0.5))
        d.wire(psu.output["+"], lamp["1"], wire=(BU, 0.5))
        d.wire(psu.output["-"], lamp["2"], wire=(BU, 0.5))
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def test_no_power_text_touches_the_content_box_edge(tmp_path) -> None:
    model = _build(tmp_path).model
    sheet = read_inputs(model).sheet
    texts = [one for one in layout_of(model, Label).values() if one.slot == "power"]
    assert texts
    for one in texts:
        assert one.x > 0
        assert one.x + one.width < sheet.content_width
        assert one.y > 0
        assert one.y + one.height < sheet.content_height


def _t1(model):
    """The PSU's page: its box, its supply text and the stem of its 0 V symbol, in page units."""
    place = next(
        o for o in layout_of(model, SymbolPlacement).values() if o.key[3].rpartition("/")[2] == "T1"
    )
    geometry = generic_box_geometry(place.ports, tuple(s.value for s in place.sides))
    box = translate(geometry.body, dx=place.x, dy=place.y)
    text = next(o for o in layout_of(model, Label).values() if o.key[3].rpartition("/")[2] == "T1")
    ground = next(
        o
        for o in layout_of(model, PowerSymbol).values()
        if o.key[3].rpartition("/")[2] == "T1" and o.symbol == "ground"
    )
    stem = Box(x=ground.pin_x - 1, y=ground.pin_y, width=2, height=ground.y - ground.pin_y)
    return box, Box(x=text.x, y=text.y, width=text.width, height=text.height), stem


def test_a_supply_text_has_room_past_its_bar_and_stays_clear_of_the_frame(tmp_path) -> None:
    built = _build(tmp_path)
    sheet = read_inputs(built.model).sheet
    box, text, stem = _t1(built.model)
    assert [f for f in built.findings if f.code == "LABEL_UNPLACED"] == []
    assert text.x > 0
    assert text.x + text.width < sheet.content_width
    assert not overlaps(text, stem)
    assert not overlaps(text, box)
    assert box.x >= 0  # inside the content box; flush at the frame edge, as any first box (0114)
