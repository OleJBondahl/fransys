"""The unit boundary outline, probed against the units worked example's
own real, laid-out geometry -- not `packages/fransys-render/tests/test_outlines.py`'s
hand-built placements, which prove the grouping and box math correct but cannot show
"""

from typing import Any, NamedTuple

import fransys as fr
import fransys_parts
from _core_boxes import box_rect, outline_rect
from _drawn_pages import drawn_pages
from _model_build_cover import printed
from _worked_wiring import wire_field_to_motor, wire_field_to_switch
from fransys_author.design import Design

from electrical_symbols import LIBRARY
from fransys_layout.symbols import text_room_on
from fransys_model.layout import sheet_format_of

_PROJECT: dict[str, Any] = {
    "title": "Pump station",
    "number": "P-1001",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def io_board(s, *, mark_boundary=True):
    """Worked example: a board unit with one boundary connector, `X1`."""
    u = s.unit("demo-io-board", revision=3, interface="2")
    u.revision(3, date="2026-01-01", text="First release", created="XX")
    grp = u.group("BRD", "I/O board")
    board = u.item("DEMO-PCB-IO", name="board", group=grp)
    x1 = u.item("DEMO-CONN-2P", tag="X1", parent=board, group=grp)
    k1 = u.item("DEMO-RLY-2CO-24", name="k1", parent=board, group=grp)
    wire = u.wiring(colour="BU", gauge="0.5")
    wire(x1["1"], k1.fn("coil")["A1"])
    wire(x1["2"], k1.fn("coil")["A2"])
    u.net("internal", k1.fn("co_1")["11"], k1.fn("co_2")["21"])
    if mark_boundary:
        u.boundary(x1)
    return x1


def pump_cabinet(s, *, name):
    """Worked example: a cabinet unit with two field-terminal boundaries."""
    u = s.unit("demo-pump-cabinet", revision=2, interface="1")
    u.revision(2, date="2026-01-01", text="First release", created="XX")
    c = u.location(name, "Pump cabinet")
    grp = u.group("FLD", "Field wiring")
    x2 = u.strip("X2", at=c)
    field = [x2.terminal("DEMO-TB-2.5-TWIN", group=grp) for _ in range(2)]
    board_x1 = io_board(u.scope("io", at=c))
    cable = u.cable("DEMO-CBL-4G1.5", name="w1c", at=c)
    cable.core(1, field[0].outer, board_x1["1"])
    cable.core(2, field[1].outer, board_x1["2"])
    for t in field:
        u.boundary(t)
    return field


def _system_design(parts, *, name1="C1", name2="C2"):
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    field1 = pump_cabinet(d.scope("pump1", at=er), name=name1)
    field2 = pump_cabinet(d.scope("pump2", at=er), name=name2)
    fld = d.location("FLD", "Field")
    fld_grp = d.group("FLD", "Field wiring")
    wire_field_to_motor(d, field1, fld=fld, grp=fld_grp, motor_tag="M1")
    wire_field_to_motor(d, field2, fld=fld, grp=fld_grp, motor_tag="M2")
    switch = d.item("DEMO-SWITCH-2P", tag="K1", at=fld, group=fld_grp)
    wire_field_to_switch(d, field1[1], switch.fn("x1")["1"], cable_tag="WM1S")
    wire_field_to_switch(d, field2[1], switch.fn("x1")["2"], cable_tag="WM2S")
    return d, field1, field2


def _build_system():
    parts = fransys_parts.load("demo_parts")
    d, _field1, _field2 = _system_design(parts)
    return fr.build(parts, *printed(d.draft()))


def _intersects(box_a, box_b):
    ax0, ay0, ax1, ay1 = box_a
    bx0, by0, bx1, by1 = box_b
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


# 7, not 4 (measured directly against this build, a probe script, not guessed): the board-unit
# ruling (model-0041) makes `DEMO-PCB-IO` -- the sole root item of its own
# nested unit `demo-io-board` -- draw its own home set now, one page per cabinet instance
# (`X1`, `K1`'s coil, `co_1`, `co_2`, four placements, zero outline groups: everything on it
# is that unit's own content, none of it another unit's black-box replica). Those two pages
# add no outline group of their own. The unit-documents worked example (this file's own copy
# of `_system_design`, kept in sync with `tests/test_units_worked_example.py`) then adds one
# more top-level page, at the top-level `FLD` location: the two motors and the one shared
# switch (four placements: `M1`'s function, `M2`'s function, and the switch's two functions
# `sw`/`x1`), none of them a unit, so it carries zero outline groups either -- it is a wholly
# new, separate page, not a merge into any existing group page (the two 2-member-group pages
# below, at locations `C1`/`C2`, are unaffected: still 2 placements, 0 non-members, each).
# 6 (the old count) + 1 (this new page) = 7. Since layout-0214 round 2 the two `C1`/`C2` pages
# go: their boxes draw no wire (each cable's stub stands at the cabinet's own page). 7 - 2 = 5.
_EXPECTED_SYSTEM_PAGE_COUNT = 5

# Group shapes, measured directly against this build (a probe script, not guessed): the
# io-board's own 1-member `X1` boundary appears on each cabinet's own page, alongside 3
# other placements of that cabinet's own content (`X2`'s two terminals, `P1`) -- a real,
# non-vacuous exclusion check. The cabinet's own 2-member (`X2`'s pair) boundary appears on
# the top-level page alone, and *only* that group's own two placements are on it -- the
# exclusion check there has nothing else to check against, measured and asserted as such
# (0), not silently skipped.
_EXPECTED_SINGLE_MEMBER_GROUP_COUNT = 2
_EXPECTED_TWO_MEMBER_GROUP_COUNT = 0  # layout-0214 round 2: the top-level box pages are gone
_EXPECTED_TOTAL_GROUP_COUNT = _EXPECTED_SINGLE_MEMBER_GROUP_COUNT + _EXPECTED_TWO_MEMBER_GROUP_COUNT
_EXPECTED_NON_MEMBERS_PER_SINGLE_MEMBER_GROUP = 3
_EXPECTED_NON_MEMBERS_PER_TWO_MEMBER_GROUP = 0


def test_every_outline_group_encloses_its_own_members_and_nothing_else():
    """The acceptance line, against real geometry: "encloses every black-box function on the
    page and nothing else". Layout owns the outline (layout-0153): for every drawn outline,
    every member's body lies inside its rectangle, no other symbol's body on that page
    """
    result = _build_system()
    model = result.model

    drawings = drawn_pages(model)
    assert len(drawings) == _EXPECTED_SYSTEM_PAGE_COUNT

    outlines = [(d, o) for d in drawings.values() for o in d.outlines]
    titles = [o.label for _, o in outlines if o.label is not None]
    single_member_group_count = 0
    two_member_group_count = 0
    text_height = text_room_on(model, sheet_format_of(model, None), LIBRARY)
    for drawing, outline in outlines:
        box = outline_rect(outline)
        bodies = [box_rect(symbol) for symbol in drawing.symbols]
        members = [b for b in bodies if _intersects(box, b)]
        assert members, "an outline encloses at least one black-box placement or box"
        for m_min_x, m_min_y, m_max_x, m_max_y in members:
            assert box[0] <= m_min_x
            assert box[1] <= m_min_y
            assert m_max_x <= box[2]
            assert m_max_y <= box[3]
        non_members = [b for b in bodies if b not in members]
        assert len(non_members) == _EXPECTED_NON_MEMBERS_PER_SINGLE_MEMBER_GROUP

        assert outline.label is not None
        title = outline.label.box
        assert title.y >= 0
        outside = title.y + text_height <= box[1] or title.y >= box[3]
        if len(members) == 1:
            # Per layout-0153, the board's X1 ends the harness WH1, so the board is a middle
            # outline and its title stands inside, left, between its edges
            assert not outside
            assert box[0] < title.x
            assert box[1] < title.y
            assert title.y + text_height < box[3]
            single_member_group_count += 1
        else:
            assert outside  # A frame's title stands outside it
            two_member_group_count += 1

    assert single_member_group_count == _EXPECTED_SINGLE_MEMBER_GROUP_COUNT
    assert two_member_group_count == _EXPECTED_TWO_MEMBER_GROUP_COUNT
    assert len(outlines) == _EXPECTED_TOTAL_GROUP_COUNT
    assert len(titles) == _EXPECTED_TOTAL_GROUP_COUNT


def test_every_unit_outline_and_its_title_stay_inside_the_content_box() -> None:
    """R3: a black box at the content box's left edge keeps its frame and title
    inside it, so no `OUT_OF_CONTENT_BOX`. Can-fail, checked by hand: without the clamp in
    `_outlines` a title starts left of the content box and both assertions fail."""
    result = _build_system()
    outlines = [o for d in drawn_pages(result.model).values() for o in d.outlines]
    titles = [o.label.box for o in outlines if o.label is not None]
    assert all(outline_rect(o)[0] >= 0 for o in outlines)
    assert all(t.x >= 0 for t in titles)


class _CabIo(NamedTuple):
    X1: fr.TerminalStrip


class _NoIo(NamedTuple):
    pass


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _CabIo:
    return _CabIo(u.terminal_strip("X1", "DEMO-TB-2.5-TWIN", 2, interface=(1, 2)))


@fr.unit("demo-skid", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _skid(u: Any) -> _NoIo:
    cab = u.add(_cab, "N")
    for i in (1, 2):
        with u.function(f"V{i}", f"Valve {i}"):
            valve = u.device(f"V{i}", "DEMO-ACT-4P-2SW")
            cable = u.cable(f"W{i}", "DEMO-CBL-8G0.75", length_m=5)
            cable.core(1, cab.X1[1].outer, valve.power["1"])
            cable.core(2, cab.X1[2].outer, valve.power["2"])
    return _NoIo()


def test_a_unit_nested_in_a_skid_draws_its_frame_where_its_terminals_are_replicated(tmp_path) -> None:
    """R833, R1093: the replicas of `demo-cab` in the skid's function sets draw one frame, titled by the unit, with room (no OUTLINE_NO_ROOM)."""
    (tmp_path / "c.md").write_text("# s\n")
    design = fr.design("demo_parts")
    design.add(_skid, "S1", place=None)
    docs = [fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, n, cover=tmp_path / "c.md") for n in ("demo-skid", "demo-cab")]
    result = fr.build(design, *docs)
    frames = [o for d in drawn_pages(result.model).values() for o in d.outlines]
    assert [o.label.text for o in frames if o.label] == ["demo-cab rev 1.1"]
    assert "OUTLINE_NO_ROOM" not in {f.code for f in result.findings}
