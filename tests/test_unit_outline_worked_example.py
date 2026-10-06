"""The unit boundary outline (units spec U1), probed against the units worked example's
own real, laid-out geometry -- not `packages/fransys-render/tests/test_outlines.py`'s
hand-built placements, which prove the grouping and box math correct but cannot show
whether the "kept together" guarantee actually holds once the real layout engine has
assigned real coordinates to everything else on the page too.

`io_board`/`pump_cabinet`/`_PROJECT`/`_system_design`/`_build_system` below are copied
verbatim from `tests/test_units_worked_example.py` (not imported: that file's own job is
STEP 4's model/layout acceptance, not render, and it is mid-flight from separate,
already-accepted work in this worktree -- not to be touched here). Root tests are where
`fransys` (the facade) and `fransys_render` may both be imported (spec section 5:
`fransys` imports everything; a root test is bound by no package's own import table).
"""

from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _model_build_cover import system_document
from fransys_render._symbol_geometry import oriented_symbol, to_grid
from graphical_symbols.boxes import body_box

from fransys_model.layout import (
    Label,
    Outline,
    Page,
    SymbolPlacement,
    default_profile,
    layout_of,
)
from fransys_model.vocab.tables import functions as functions_of
from fransys_model.vocab.tables import items as items_of

_PROJECT: dict[str, Any] = {
    "title": "Pump station",
    "number": "P-1001",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def io_board(s, *, mark_boundary=True):
    """Units spec worked example: a board unit with one boundary connector, `X1`."""
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
    """Units spec worked example: a cabinet unit with two field-terminal boundaries."""
    u = s.unit("demo-pump-cabinet", revision=2, interface="1")
    u.revision(2, date="2026-01-01", text="First release", created="XX")
    c = u.location(name, "Pump cabinet")
    grp = u.group("FLD", "Field wiring")
    x2 = u.strip("X2", at=c)
    field = [x2.terminal("DEMO-TB-2.5", group=grp) for _ in range(2)]
    board_x1 = io_board(u.scope("io", at=c))
    w1 = u.harness(name="w1", tag="WH1", at=c, group=grp)
    p1 = u.item("DEMO-CONN-2P", tag="P1", parent=w1, at=c, group=grp)
    cable = u.cable("DEMO-CBL-4G1.5", name="w1c", parent=w1, at=c)
    cable.core(1, field[0].outer, p1["1"])
    cable.core(2, field[1].outer, p1["2"])
    u.mate(p1, board_x1)
    for t in field:
        u.boundary(t)
    return field


def _wire_field_to_motor(d, field, *, fld, grp, motor_tag):
    """Copied verbatim from `tests/test_units_worked_example.py` (module docstring)."""
    motor = d.item("DEMO-MOTOR-4KW", tag=motor_tag, at=fld, group=grp)
    cable = d.cable("DEMO-CBL-4G1.5", tag=f"W{motor_tag}", length_mm=15000)
    cable.core(1, field[0].outer, motor["U"])
    return motor


def _wire_field_to_switch(d, terminal, switch_port, *, cable_tag):
    """Copied verbatim from `tests/test_units_worked_example.py` (module docstring)."""
    cable = d.cable("DEMO-CBL-4G1.5", tag=cable_tag, length_mm=15000)
    cable.core(1, terminal.outer, switch_port)


def _system_design(parts, *, name1="C1", name2="C2"):
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    field1 = pump_cabinet(d.scope("pump1", at=er), name=name1)
    field2 = pump_cabinet(d.scope("pump2", at=er), name=name2)
    fld = d.location("FLD", "Field")
    fld_grp = d.group("FLD", "Field wiring")
    _wire_field_to_motor(d, field1, fld=fld, grp=fld_grp, motor_tag="M1")
    _wire_field_to_motor(d, field2, fld=fld, grp=fld_grp, motor_tag="M2")
    switch = d.item("DEMO-SWITCH-2P", tag="K1", at=fld, group=fld_grp)
    _wire_field_to_switch(d, field1[1], switch.fn("x1")["1"], cable_tag="WM1S")
    _wire_field_to_switch(d, field2[1], switch.fn("x1")["2"], cable_tag="WM2S")
    return d, field1, field2


def _build_system():
    parts = fransys_parts.load("demo_parts")
    d, _field1, _field2 = _system_design(parts)
    return fr.build(parts, d.draft(), system_document())


def _body_g(model, placement):
    """`placement`'s own absolute body extent, grid units (the symbol's ink, no slots)."""
    symbol = oriented_symbol(model, placement)
    assert symbol is not None
    box = body_box(symbol)
    return (
        placement.x + to_grid(box.min.x),
        placement.y + to_grid(box.min.y),
        placement.x + to_grid(box.max.x),
        placement.y + to_grid(box.max.y),
    )


def _intersects(box_a, box_b):
    ax0, ay0, ax1, ay1 = box_a
    bx0, by0, bx1, by1 = box_b
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


# 7, not 4 (measured directly against this build, a probe script, not guessed): units spec
# U1's board-unit ruling (model-0041) makes `DEMO-PCB-IO` -- the sole root item of its own
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
# 6 (the old count) + 1 (this new page) = 7.
_EXPECTED_SYSTEM_PAGE_COUNT = 7

# Group shapes, measured directly against this build (a probe script, not guessed): the
# io-board's own 1-member `X1` boundary appears on each cabinet's own page, alongside 3
# other placements of that cabinet's own content (`X2`'s two terminals, `P1`) -- a real,
# non-vacuous exclusion check. The cabinet's own 2-member (`X2`'s pair) boundary appears on
# the top-level page alone, and *only* that group's own two placements are on it -- the
# exclusion check there has nothing else to check against, measured and asserted as such
# (0), not silently skipped.
_EXPECTED_SINGLE_MEMBER_GROUP_COUNT = 2
_EXPECTED_TWO_MEMBER_GROUP_COUNT = 2
_EXPECTED_TOTAL_GROUP_COUNT = _EXPECTED_SINGLE_MEMBER_GROUP_COUNT + _EXPECTED_TWO_MEMBER_GROUP_COUNT
_EXPECTED_NON_MEMBERS_PER_SINGLE_MEMBER_GROUP = 3
_EXPECTED_NON_MEMBERS_PER_TWO_MEMBER_GROUP = 0


def test_every_outline_group_encloses_its_own_members_and_nothing_else():
    """The acceptance line, against real geometry: "encloses every black-box function on the
    page and nothing else". Layout owns the outline (I2a, designer's ruling): for every
    `layout.outline` record, every member's body lies inside its rectangle, no other
    placement's body on that page intersects it, and its title label sits inside the
    content area and outside the rectangle. A member is a placement whose item belongs to
    the outline's unit.

    R7 A (deep dive, G1): a connector is drawn as one placement per pin, so a group and its
    non-members are counted in functions, not placements.
    """
    result = _build_system()
    model = result.model

    pages_by_id = layout_of(model, Page)
    assert len(pages_by_id) == _EXPECTED_SYSTEM_PAGE_COUNT

    all_placements = layout_of(model, SymbolPlacement)
    titles = [label for label in layout_of(model, Label).values() if label.slot == "outline_title"]
    outlines = layout_of(model, Outline).values()
    single_member_group_count = 0
    two_member_group_count = 0
    for outline in outlines:
        box = (outline.x, outline.y, outline.x + outline.width, outline.y + outline.height)
        page_placements = [p for p in all_placements.values() if p.page == outline.page]
        members = [
            p
            for p in page_placements
            if items_of(model)[functions_of(model)[p.function].item].unit == outline.unit
        ]
        assert members, "an outline encloses at least one black-box placement"
        for member in members:
            m_min_x, m_min_y, m_max_x, m_max_y = _body_g(model, member)
            assert box[0] <= m_min_x
            assert box[1] <= m_min_y
            assert m_max_x <= box[2]
            assert m_max_y <= box[3]

        member_ids = {p.id for p in members}
        non_members = [p for p in page_placements if p.id not in member_ids]
        for other in non_members:
            assert not _intersects(box, _body_g(model, other)), (
                f"non-member placement {other.key!r} intersects a unit boundary outline"
            )

        (title,) = [
            t
            for t in titles
            if t.page == outline.page and t.function in {m.function for m in members}
        ]
        assert title.y >= 0
        text_height = default_profile().text_height
        assert title.y + text_height <= box[1] or title.y >= box[3]

        member_functions = {p.function for p in members}
        other_functions = {p.function for p in non_members}
        if len(member_functions) == 1:
            single_member_group_count += 1
            assert len(other_functions) == _EXPECTED_NON_MEMBERS_PER_SINGLE_MEMBER_GROUP
        elif len(member_functions) == 2:
            two_member_group_count += 1
            assert len(other_functions) == _EXPECTED_NON_MEMBERS_PER_TWO_MEMBER_GROUP
        else:
            msg = f"unexpected group size {len(member_functions)}"
            raise AssertionError(msg)

    assert single_member_group_count == _EXPECTED_SINGLE_MEMBER_GROUP_COUNT
    assert two_member_group_count == _EXPECTED_TWO_MEMBER_GROUP_COUNT
    assert len(outlines) == _EXPECTED_TOTAL_GROUP_COUNT
    assert len(titles) == _EXPECTED_TOTAL_GROUP_COUNT


def test_every_unit_outline_and_its_title_stay_inside_the_content_box() -> None:
    """R3 (designer): a black box at the content box's left edge keeps its frame and title
    inside it, so no `OUT_OF_CONTENT_BOX`. Can-fail, checked by hand: without the clamp in
    `_outlines` a title starts left of the content box and both assertions fail."""
    result = _build_system()
    titles = [lb for lb in layout_of(result.model, Label).values() if lb.slot == "outline_title"]
    assert all(one.x >= 0 for one in (*layout_of(result.model, Outline).values(), *titles))
    assert "OUT_OF_CONTENT_BOX" not in {f.code for f in result.findings}
