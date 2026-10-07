"""The block-diagram spec's two worked examples, as tests on invented models (BD-1 M3).

`docs/specs/2026-10-07-block-diagrams.md`, "Worked example 1" and "Worked example 2", acceptance 1
to 4. Example 1 is a station-shaped system built from the demo parts: one tagged cabinet with no
place, four top-level cables, three of them to field items, one of those by others. Example 2 is
the units fixture's own cabinet reading.
"""

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import layout_trigger_document
from test_units_worked_example import _PROJECT, _build_cabinet_own, _build_system

from fransys_model.derive.block_diagram import (
    box_dashed,
    box_lines,
    diagram_facts,
    diagram_lines,
)
from fransys_model.derive.drawing_text import outline_title
from fransys_model.vocab.tables import units as units_table


def _station(*, second_strip=False):
    """Cabinet `-U1` (strips X1, X3, connector C1); four cables to a strip, two motors, a switch."""
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    u = d.scope("cab").unit("demo-pump-cabinet", revision=2, interface="1", tag="U1")
    u.revision(2, date="2026-01-01", text="First release", created="XX")
    grp = u.group("FLD", "Field wiring")
    x1, x3 = u.strip("X1"), u.strip("X3")
    t1 = x1.terminal("DEMO-TB-2.5", group=grp)
    t11, t21 = (x3.terminal("DEMO-TB-2.5", group=grp) for _ in range(2))
    c1 = u.item("DEMO-CONN-2P", tag="C1", group=grp)
    for handle in (t1, t11, t21, c1):
        u.boundary(handle)
    field = d.group("EXT", "Field")
    x0 = d.strip("X0", external=True)
    t0 = x0.terminal("DEMO-TB-2.5", group=field)
    m1 = d.item("DEMO-MOTOR-4KW", tag="M1", group=field)
    m2 = d.item("DEMO-MOTOR-4KW", tag="M2", group=field)
    k1 = d.item("DEMO-SWITCH-2P", tag="K1", group=field, external=True)
    d.cable("DEMO-CBL-4G1.5", tag="W1").core(1, t1.outer, t0.outer)
    w11 = d.cable("DEMO-CBL-4G1.5", tag="W11")
    w11.core(1, t11.outer, m1["U"])
    if second_strip:
        w11.core(2, x1.terminal("DEMO-TB-2.5", group=grp).outer, m1["V"])
    d.cable("DEMO-CBL-4G1.5", tag="W21").core(1, t21.outer, m2["U"])
    w3 = d.cable("DEMO-CBL-4G1.5", tag="W3")
    p3 = d.item("DEMO-CONN-2P", tag="P3", parent=w3, group=field)  # ty: ignore[invalid-argument-type] -- a cable handle is a plug parent
    w3.core(1, k1.fn("x1")["1"], p3["1"])
    d.mate(p3, c1)
    return fr.build(parts, d.draft(), layout_trigger_document()).model


def test_the_system_reading_draws_five_boxes_and_four_lines_with_their_tabs():
    """Worked example 1: cabinet `-U1` over its title, and the tabs `-X1`, `-X3` twice, `-C1`."""
    model = _station()
    lines = diagram_lines(model, None)
    assert [line.designation for line in lines] == ["-W1", "-W3", "-W11", "-W21"]
    boxes = {box for line in lines for box in (line.a, line.b)}
    assert len(boxes) == 5
    tabs = sorted(tab for line in lines for tab in (line.tab_a, line.tab_b) if tab)
    assert tabs == ["-C1", "-X1", "-X3", "-X3"]
    (cabinet,) = (box for box in boxes if box.kind == "unit")
    assert box_lines(model, cabinet, None) == ("-U1", outline_title(model, cabinet))
    dashed = sorted(box_lines(model, box, None)[0] for box in boxes if box_dashed(model, box, None))
    assert len(dashed) == 2
    assert all(text.endswith(" (by others)") for text in dashed)
    assert diagram_facts(model, None) == ()


def test_a_cabinets_own_reading_draws_its_cable_to_the_board_box_with_a_full_tab():
    """Worked example 2: strip `-X2` to the board instance; the board's tab reads `-U1-X1`."""
    model = _build_cabinet_own(prefix="p", name="C1")[0].model
    (cabinet,) = (u for u in units_table(model) if diagram_lines(model, u))
    (line,) = diagram_lines(model, cabinet)
    assert line.designation == "-WH1"
    assert {line.tab_a, line.tab_b} == {None, "-U1-X1"}
    texts = sorted(box_lines(model, box, cabinet) for box in (line.a, line.b))
    assert texts == [("-X2",), (outline_title(model, line.b if line.b.kind == "unit" else line.a),)]
    assert diagram_lines(model, None) == ()
    assert [u for u in units_table(model) if u != cabinet and diagram_lines(model, u)] == []


def test_a_core_landing_on_a_second_strip_drops_the_cabinet_tab_of_that_line():
    """Acceptance 2: `-W11` lands on two strips, so its cabinet end has no tab."""
    model = _station(second_strip=True)
    tabs = sorted(
        (line.designation, tab)
        for line in diagram_lines(model, None)
        for tab in (line.tab_a, line.tab_b)
        if tab
    )
    assert tabs == [("-W1", "-X1"), ("-W21", "-X3"), ("-W3", "-C1")]


def test_a_located_unit_instance_prints_its_place_on_line_one():
    """The units fixture's system reading: cabinets with a place and no tag print `+ER+C1`."""
    model = _build_system()[0].model
    lines = diagram_lines(model, None)
    firsts = {
        box_lines(model, box, None)[0]
        for line in lines
        for box in (line.a, line.b)
        if box.kind == "unit"
    }
    assert firsts == {"+ER+C1", "+ER+C2"}
