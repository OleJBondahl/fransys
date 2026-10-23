"""Field case: the text of a supply bar never leaves the sheet's content box, nor rests on its edge.

The engineering shape: a cabinet on a 24 V DC supply (rails 24 V and 0 V) with a PSU, five PLC
input channels and five lamps, all pins wired to their rail's hub, so each cut end is a power
symbol. The PSU's `+` output stands at the left edge of the first page's first column. Its bar
prints the net's name "24V" beside the bar (since layout-0114 below it, past the bar).

The bug: the bar's text was placed with no content box, so the first free candidate was left of
the bar, at x = -8, across the drawing frame's left border. The page shift then moved the whole
page 8 units right, which left the text flush on the border instead of clear of it.

The rule (the owner's predefined text positions, best wins, 2026-09-25): a text
candidate that crosses the content box is never chosen. The fix passes the page's content box
to the power texts' space.

The second bug: with that rule the PSU's "24V" had no place on its page. Its right side is the
PSU's own 0 V stem, its left side was outside the content box, and the unplaced text lay on the
stem. The PSU's box also stood on the frame's left line, because only the old page shift had
ever given the left text room. The fix counts a supply text in its column's room, as a tag is
counted.

Layout-0114 (owner 2026-10-05): a supply text stands past its bar, centred on the lead, never
beside it, so it needs no room to the left of the box, and the box may stand at the frame's
left edge as any first box of a page does.
"""

import fransys as fr
from _drawn_extent import body_g
from _drawn_pages import drawn_pages
from fransys.colours import BU

from fransys_model.layout import PowerSymbol, layout_of


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
        d.detail.wire(psu.output["+"], di.di_1["1"], wire=(BU, 0.5))
        d.detail.wire(psu.output["+"], lamp["1"], wire=(BU, 0.5))
        d.detail.wire(psu.output["-"], lamp["2"], wire=(BU, 0.5))
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def overlaps(a, b) -> bool:
    """Whether the boxes (x0, y0, x1, y1) share area."""
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _power_texts(model):
    """Every drawn power text, with its page's drawing."""
    return [(d, t) for d in drawn_pages(model).values() for t in d.texts if t.kind == "POWER"]


def test_no_power_text_touches_the_content_box_edge(tmp_path) -> None:
    model = _build(tmp_path).model
    texts = _power_texts(model)
    assert texts
    for drawing, one in texts:
        assert one.box.x > 0
        assert one.box.x + one.box.w < drawing.area.w
        assert one.box.y > 0
        assert one.box.y + one.box.h < drawing.area.h


def _t1(model):
    """The PSU's page: its box, its supply text and the stem of its 0 V symbol, in G."""
    ground = next(
        o
        for o in layout_of(model, PowerSymbol).values()
        if fr.derive.port_designation(model, o.port).startswith("-T1:") and o.symbol == "ground"
    )
    drawing = drawn_pages(model)[ground.page]
    # a drawn symbol names no subject: the PSU is the box under its printed tag
    tag = next(t for t in drawing.texts if t.text == "-T1")
    psu = min(
        (s for s in drawing.symbols if s.key == "generic-box"),
        key=lambda s: abs(s.x - tag.box.x) + abs(s.y - tag.box.y),
    )
    box = body_g(psu)
    text = next(t for d, t in _power_texts(model) if d is drawing and t.text == "24V")
    stem = (ground.pin_x - 1, ground.pin_y, ground.pin_x + 1, ground.y)
    return (
        box,
        (text.box.x, text.box.y, text.box.x + text.box.w, text.box.y + text.box.h),
        stem,
        drawing,
    )


def test_a_supply_text_has_room_past_its_bar_and_stays_clear_of_the_frame(tmp_path) -> None:
    built = _build(tmp_path)
    box, text, stem, drawing = _t1(built.model)
    assert [f for f in built.findings if f.code in {"LABEL_UNPLACED", "ANNEX_UNPLACED"}] == []
    assert text[0] > 0
    assert text[2] < drawing.area.w
    assert not overlaps(text, stem)
    assert not overlaps(text, box)
    assert box[0] >= 0  # inside the content box; flush at the frame edge, as any first box (0114)
