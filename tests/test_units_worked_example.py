"""The worked example, completed with the demo parts (known: CONNECTION_NOT_DRAWN KI-413).

Adapted from the spec's literal text, as its own note invites ("use the
real ones"): the field terminals' cable-side ports are marked `.outer` (their role), not
"""

import dataclasses
from typing import Any

import fransys as fr
import fransys_parts
import pytest
from _core_boxes import connector_names, named_boxes
from _drawn_pages import drawn_pages
from _expected_codes import expect_codes
from _model_build_cover import printed
from _worked_wiring import wire_field_to_motor, wire_field_to_switch
from fransys_author.design import Design
from fransys_kicad import netlist as kicad_netlist
from root_library import freeze

from fransys_model.checks.units import (
    BOUNDARY_NOT_IN_UNIT,
    BOUNDARY_UNCONNECTED,
    MATE_PORT_MISMATCH,
    UNIT_BOUNDARY_BYPASSED,
    UNUSED_CONTRADICTED,
)
from fransys_model.derive import boundary as unit_boundary
from fransys_model.derive import (
    reference_designation,
    standalone,
    unit_release,
    units,
)
from fransys_model.derive.designation_label import own_designation_or_none
from fransys_model.derive.passes.numbering import PRODUCT_DESIGNATION_DUPLICATE, REFERENCE_DESIGNATION_DUPLICATE
from fransys_model.derive.passes.numbering import number as number_pass
from fransys_model.kernel import Origin, evolve, merge
from fransys_model.layout import (
    DrawingSet,
    Page,
)
from fransys_model.layout import layout_of as layout_of_model
from fransys_model.vocab.tables import boundaries
from fransys_model.vocab.tables import conductors as conductors_of
from fransys_model.vocab.tables import functions as functions_of
from fransys_model.vocab.tables import items as items_of
from fransys_model.vocab.tables import nets as nets_of
from fransys_model.vocab.tables import ports as ports_of
from fransys_model.vocab.tables import units as units_table

_PROJECT: dict[str, Any] = {
    "title": "Pump station",
    "number": "P-1001",
    "customer": "Example Co",
    "revision": 1,
    "author": "OJB",
}


def io_board(s, *, mark_boundary=True, tag=None):
    """Worked example: a board unit with one boundary connector, `X1`.

    `DEMO-PCB-IO` is a real board (`category = "board"`, a `[pcb]` facet, decision
    model-0040, closing author-0002's `KNOWN DEVIATION`), and the *sole* root item of its own
    """
    u = s.unit("demo-io-board", revision=3, interface="2", tag=tag)
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
    return x1, u


def pump_cabinet(s, *, name, tag=None, spares=False):
    """Worked example: a cabinet unit with two field-terminal boundaries; `spares` appends one terminal bridged to the first."""
    u = s.unit("demo-pump-cabinet", revision=2, interface="1", tag=tag)
    u.revision(2, date="2026-01-01", text="First release", created="XX")
    c = u.location(name, "Pump cabinet")
    grp = u.group("FLD", "Field wiring")
    x2 = u.strip("X2", at=c)
    field = [x2.terminal("DEMO-TB-2.5-TWIN", group=grp) for _ in range(2)]
    board_x1, _ = io_board(u.scope("io", at=c), tag=None if tag is None else "U1")
    cable = u.cable("DEMO-CBL-4G1.5", name="w1c", at=c)
    cable.core(1, field[0].outer, board_x1["1"])
    cable.core(2, field[1].outer, board_x1["2"])
    for t in field:
        u.boundary(t)
    if spares:
        field.append(x2.terminal("DEMO-TB-2.5-TWIN", group=grp))
        u.bridge(field[0], field[2])
        u.boundary(field[2])
    return field, u


def _system_design(parts, *, name1="C1", name2="C2", tags=(None, None), spares=False):
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    field1, _ = pump_cabinet(d.scope("pump1", at=er), name=name1, tag=tags[0], spares=spares)
    field2, _ = pump_cabinet(d.scope("pump2", at=er), name=name2, tag=tags[1], spares=False)
    fld = d.location("FLD", "Field")
    fld_grp = d.group("FLD", "Field wiring")
    wire_field_to_motor(d, field1, fld=fld, grp=fld_grp, motor_tag="M1")
    wire_field_to_motor(d, field2, fld=fld, grp=fld_grp, motor_tag="M2")
    switch = d.item("DEMO-SWITCH-2P", tag="K1", at=fld, group=fld_grp)
    wire_field_to_switch(d, field1[1], switch.fn("x1")["1"], cable_tag="WM1S")
    wire_field_to_switch(d, field2[1], switch.fn("x1")["2"], cable_tag="WM2S")
    return d, field1, field2


def _build_system(*, name1="C1", name2="C2"):
    parts = fransys_parts.load("demo_parts")
    d, field1, field2 = _system_design(parts, name1=name1, name2=name2)
    return fr.build(parts, *printed(d.draft())), field1, field2


def _build_cabinet_own(*, prefix, name):
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    field, _ = pump_cabinet(d.scope(prefix), name=name)
    return fr.build(parts, *printed(d.draft())), field


def _codes(result):
    return [f.code for f in result.findings]


def _designations_by_stripped_key(model, *, prefix):
    """`{key[1:]: designation}` for every numbered item whose key starts with `prefix`."""
    return {
        item.key[1:]: own_designation_or_none(model, item)
        for item in items_of(model).values()
        if item.key[0] == prefix and own_designation_or_none(model, item) is not None
    }


# -- U1: four `Unit` records, two per cabinet instance -----------------------------------


def test_the_system_build_has_four_units_two_per_cabinet_instance():
    result, _, _ = _build_system()
    assert len(units_table(result.model)) == 4


def test_no_unit_in_the_system_build_is_standalone():
    """Every unit's subtree misses the other cabinet's items."""
    result, _, _ = _build_system()
    found = sorted(units(result.model))
    assert len(found) == 4
    assert all(not standalone(result.model, unit) for unit in found)


# -- U7: per-unit numbering, item designation equal across builds ------------------------


@pytest.mark.parametrize("prefix", ["pump1", "pump2"])
def test_each_pumps_item_designations_match_between_the_system_and_its_own_build(prefix):
    """Each instance's items keep their designation once integrated, key for key."""
    system, _, _ = _build_system()
    own, _ = _build_cabinet_own(prefix="p", name="C1")
    system_by_key = _designations_by_stripped_key(system.model, prefix=prefix)
    own_by_key = _designations_by_stripped_key(own.model, prefix="p")
    shared = sorted(set(system_by_key) & set(own_by_key))
    assert len(shared) > 0
    assert all(system_by_key[key] == own_by_key[key] for key in shared)
    # every item the worked example numbers by hand is among them, not just a subset
    assert {("X2",), ("w1c",), ("io", "X1"), ("io", "k1"), ("io", "board")} <= set(shared)


def test_reference_designations_carry_each_cabinets_own_location():
    """Exact designations, matching the spec's own worked-example text: `+ER+C1-X2`,
    `+ER+C2-X2` (`x2`, the field strip, `at=c` in both instances)."""
    result, _, _ = _build_system()
    by_key = {
        item.key: reference_designation(result.model, item_id)
        for item_id, item in items_of(result.model).items()
        if own_designation_or_none(result.model, item) is not None
    }
    assert by_key[("pump1", "X2")] == "+ER+C1-X2"
    assert by_key[("pump2", "X2")] == "+ER+C2-X2"


# -- Can-fail (U7): omitting `unit` from the sibling group ------------------------------


def test_numbering_without_unit_in_the_sibling_group_diverges_on_the_second_boards_letter():
    """Can-fail: the comparison test would not have caught a regression that
    dropped `unit` from the numbering pass's sibling-group key, proven
    directly against the model layer, not by editing `derive/passes/numbering.py`.
    """
    parts = fransys_parts.load("demo_parts")
    d, _, _ = _system_design(parts)
    model = freeze(merge(parts, d.draft()))

    correct, _ = number_pass(model)
    correct_by_key = _designations_by_stripped_key(correct, prefix="pump1")
    correct_by_key_2 = _designations_by_stripped_key(correct, prefix="pump2")
    assert correct_by_key[("io", "board")] == "U1"
    assert correct_by_key_2[("io", "board")] == "U1"

    stripped_items = [dataclasses.replace(item, unit=None) for item in items_of(model).values() if item.unit is not None]
    assert len(stripped_items) > 0
    stripped_model = evolve(
        model,
        put=stripped_items,
        remove=[item.id for item in stripped_items],
        origin=Origin(file="<can-fail probe>", line=1, note="can-fail probe"),
    )
    broken, _ = number_pass(stripped_model)
    broken_by_key_1 = _designations_by_stripped_key(broken, prefix="pump1")
    broken_by_key_2 = _designations_by_stripped_key(broken, prefix="pump2")
    assert broken_by_key_1[("io", "board")] == "U1"
    assert broken_by_key_2[("io", "board")] == "U2"  # the regression: should be U1


# -- U5: BOUNDARY_UNCONNECTED --------------------------------------------------------------

_OTHER_U5_CODES = (
    UNIT_BOUNDARY_BYPASSED,
    MATE_PORT_MISMATCH,
    UNUSED_CONTRADICTED,
    BOUNDARY_NOT_IN_UNIT,
)


def _bare_two_cabinet_design(parts):
    """Two `pump_cabinet` instances with no external field wiring at all -- unlike
    `_system_design`, which (since the fixture fix below) wires every field terminal to a
    top-level motor. Kept as its own local builder so the "an unwired boundary is
    BOUNDARY_UNCONNECTED" and "declaring it unused clears it" scenarios stay exercisable
    """
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    field1, _ = pump_cabinet(d.scope("pump1", at=er), name="C1")
    field2, _ = pump_cabinet(d.scope("pump2", at=er), name="C2")
    return d, field1, field2


def _build_bare_two_cabinets():
    parts = fransys_parts.load("demo_parts")
    d, field1, field2 = _bare_two_cabinet_design(parts)
    return fr.build(parts, *printed(d.draft())), field1, field2


def test_an_unwired_field_terminal_is_boundary_unconnected_four_times():
    """This was `_build_system()`'s own state (the fixture's known,
    pre-existing gap). Since the fixture fix below (ruling 2026-09-23),
    `_system_design` now wires every field terminal to a real top-level motor cable, so this
    scenario -- an explicitly unwired two-cabinet build -- is exercised on its own local
    """
    result, _field1, _field2 = _build_bare_two_cabinets()
    codes = _codes(result)
    expect_codes(result, BOUNDARY_UNCONNECTED)
    assert codes.count(BOUNDARY_UNCONNECTED) == 4
    for code in _OTHER_U5_CODES:
        assert codes.count(code) == 0
    # the zero counts above are not vacuous: the model does have boundaries to check them
    # against (three per cabinet instance, two field terminals plus the board's own X1).
    assert len(boundaries(result.model)) == 6


def test_the_system_builds_field_terminals_are_wired_and_boundary_unconnected_clears():
    """Fixture fix (ruling 2026-09-23): `_system_design` now wires every field terminal to a real
    top-level motor cable, crossing each cabinet's own unit boundary, so `BOUNDARY_UNCONNECTED` no
    longer fires at all on `_build_system()`; every other U5 code still stays at zero.
    """
    result, _, _ = _build_system()
    codes = _codes(result)
    assert codes.count(BOUNDARY_UNCONNECTED) == 0
    for code in _OTHER_U5_CODES:
        assert codes.count(code) == 0
    # not vacuous: same non-zero boundary count as the bare (unwired) build above.
    assert len(boundaries(result.model)) == 6


_ANNEX_UNPLACED_STOCK = 0  # R420: only falls; the text stage (TS) places all six


def test_the_two_connector_markers_above_the_terminal_row_each_find_a_place():
    """On each cabinet the two sibling pins of the connector row carry a tall
    marker box over a 112-high gap above the terminal row. Each box stands beside the pins'
    lanes, one nearer its port than the other, and the leads cross no box: no marker is left
    unplaced and no wire runs over a label."""
    # UNDO: marker_row.py `_closer`: `range(0, max(...) + 1, WIRING_GRID)` -> `range(0, 1)`
    result, _, _ = _build_system()
    codes = _codes(result)
    # R420: a falling stock; on the text-stage tip every annex finds a free spot.
    assert codes.count("ANNEX_UNPLACED") == _ANNEX_UNPLACED_STOCK
    assert codes.count("WIRE_OVER_LABEL") == 0


def test_boundary_unconnected_clears_once_every_field_terminal_is_declared_unused():
    """Built through `_system_design`, whose field terminals were unwired, so
    declaring all four `unused` cleared `BOUNDARY_UNCONNECTED`.
    Since the fixture fix (ruling 2026-09-23), `_system_design`'s field terminals
    are now really wired (see `test_the_system_builds_field_terminals_are_wired_...` above),
    """
    parts = fransys_parts.load("demo_parts")
    d, field1, field2 = _bare_two_cabinet_design(parts)
    fields = (*field1, *field2)
    assert len(fields) == 4
    for terminal in fields:
        d.unused(terminal)
    result = fr.build(parts, *printed(d.draft()))
    assert result.model.tables["unused_boundary"]
    assert len(result.model.tables["unused_boundary"]) == 4
    assert _codes(result).count(BOUNDARY_UNCONNECTED) == 0


# -- U7: REFERENCE_DESIGNATION_DUPLICATE when both cabinets share one name ---------------


def test_reference_designation_duplicate_when_both_cabinets_are_named_c1():
    result, _, _ = _build_system(name1="C1", name2="C1")
    expect_codes(result, REFERENCE_DESIGNATION_DUPLICATE, PRODUCT_DESIGNATION_DUPLICATE)


def test_c1_and_c2_is_the_clean_twin():
    """Both cabinets are examined (each renders `+ER+C1-X2`/`+ER+C2-X2`), not just absent."""
    result, _, _ = _build_system(name1="C1", name2="C2")
    by_key = {
        item.key: reference_designation(result.model, item_id)
        for item_id, item in items_of(result.model).items()
        if own_designation_or_none(result.model, item) is not None
    }
    assert by_key[("pump1", "X2")] == "+ER+C1-X2"
    assert by_key[("pump2", "X2")] == "+ER+C2-X2"
    assert _codes(result).count(REFERENCE_DESIGNATION_DUPLICATE) == 0


# -- U2: the cabinet's own build has no BOUNDARY_UNCONNECTED -----------------------------


def test_the_cabinets_own_build_has_no_boundary_unconnected():
    result, field = _build_cabinet_own(prefix="p", name="C1")
    assert _codes(result).count(BOUNDARY_UNCONNECTED) == 0
    cabinet_unit = next(unit_id for unit_id in sorted(units(result.model)) if unit_release(result.model, unit_id).name == "demo-pump-cabinet")
    assert standalone(result.model, cabinet_unit)
    boundary_functions = unit_boundary(result.model, cabinet_unit)
    assert len(boundary_functions) == 2
    assert {t.function.id for t in field} == set(boundary_functions)


# -- Can-fail (U3/U5): removing the board's own boundary --------------------------------


def test_removing_the_boards_boundary_gives_unit_boundary_bypassed():
    """Can-fail: `io_board(..., mark_boundary=False)` (a scratch copy of the worked
    example's function, not an edit to it) drops `u.boundary(x1)`. The cabinet's mate onto
    the board's `X1` then crosses a unit boundary that is nobody's declared interface:
    "function pump1/io/X1/fn/x1 crosses out of pump1/io/unit without being its
    """

    def broken_pump_cabinet(s, *, name):
        u = s.unit("demo-pump-cabinet", revision=2, interface="1")
        u.revision(2, date="2026-01-01", text="First release", created="XX")
        c = u.location(name, "Pump cabinet")
        grp = u.group("FLD", "Field wiring")
        x2 = u.strip("X2", at=c)
        field = [x2.terminal("DEMO-TB-2.5-TWIN", group=grp) for _ in range(2)]
        board_x1, _ = io_board(u.scope("io", at=c), mark_boundary=False)
        cable = u.cable("DEMO-CBL-4G1.5", name="w1c", at=c)
        cable.core(1, field[0].outer, board_x1["1"])
        for t in field:
            u.boundary(t)
        return field

    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    broken_pump_cabinet(d.scope("pump1", at=er), name="C1")
    result = fr.build(parts, *printed(d.draft()))
    bypassed = [f for f in result.findings if f.code == UNIT_BOUNDARY_BYPASSED]
    expect_codes(result, UNIT_BOUNDARY_BYPASSED)
    assert "crosses out of " in bypassed[0].message


# -- model-0040/layout-0044: DEMO-PCB-IO is a real board -----------------------


def _function_of(model, item_id, name):
    return next(f for f in functions_of(model).values() if f.item == item_id and f.key[-1] == name)


def _ports_of(model, function_id):
    return {p.id for p in ports_of(model).values() if p.function == function_id}


def _port_named(model, function_id, name):
    return next(p.id for p in ports_of(model).values() if p.function == function_id and p.name == name)


def _unit_pages(model, unit):
    """Every page of the drawing sets of `unit`, as `{page id: (drawing_set, number)}`."""
    pages, sets = layout_of_model(model, Page), layout_of_model(model, DrawingSet)
    return {p.id: (p.drawing_set, p.number) for p in pages.values() if sets[p.drawing_set].unit == unit}


def _coil_pages(model, unit):
    """Every page of `unit`'s sets that draws a relay coil (operating device with A1 and A2)."""
    drawn = drawn_pages(model)
    return {
        where
        for page, where in _unit_pages(model, unit).items()
        if any(s.key == "operating-device" and {"A1", "A2"} <= {v for _, v in s.slots} for s in drawn[page].symbols)
    }


def _box_pages_of(model, function_id):
    """Every page `function_id` stands on as a connector box, as `(drawing_set, number)`."""
    pages = layout_of_model(model, Page)
    name = connector_names(model)[function_id]
    found = set()
    for page, drawing in drawn_pages(model).items():
        for box in named_boxes(drawing, {name}).values():
            assert box.texts  # a plug box and a unit interface box print their lines
            found.add((pages[page].drawing_set, pages[page].number))
    return found


def _wires_on(model, unit):
    """How many wires the pages of `unit`'s drawing sets draw."""
    drawn = drawn_pages(model)
    return sum(len(drawn[page].wires) for page in _unit_pages(model, unit))


def test_step_4b_board_internal_wiring_and_net_now_route_in_the_boards_own_unit() -> None:
    """Before the board-unit ruling:
    `io_board`'s internal wiring (`X1`-`K1`, two wires) and its one internal net (`K1`'s
    `co_1`/`co_2` pins) were board-internal and produced no route, no marker and no finding;
    """
    result = _build_system()[0]
    model = result.model
    assert [f for f in result.findings if f.code == "CONNECTION_TO_UNDRAWN"] == []
    touched_by_findings = {s for f in result.findings for s in f.subjects}

    by_key = {item.key: item.id for item in items_of(model).values()}
    for prefix in ("pump1", "pump2"):
        x1_item = by_key[(prefix, "io", "X1")]
        k1_item = by_key[(prefix, "io", "k1")]
        p1_item = by_key[(prefix, "P1")]

        coil_fn = _function_of(model, k1_item, "coil").id
        co_1_fn = _function_of(model, k1_item, "co_1").id
        co_2_fn = _function_of(model, k1_item, "co_2").id
        internal_ports = _ports_of(model, _function_of(model, x1_item, "x1").id) | {
            _port_named(model, coil_fn, "A1"),
            _port_named(model, coil_fn, "A2"),
            _port_named(model, co_1_fn, "11"),
            _port_named(model, co_2_fn, "21"),
        }
        assert len(internal_ports) == 6, "the fixture has six internal ports per cabinet"
        assert not (internal_ports & touched_by_findings)

        internal_conductors = {c.id for c in conductors_of(model).values() if {c.a, c.b} <= internal_ports}
        assert len(internal_conductors) == 2, "the two X1-K1 wires, per cabinet"
        assert not (internal_conductors & touched_by_findings)

        internal_nets = {n.id for n in nets_of(model).values() if set(n.ports) <= internal_ports}
        assert len(internal_nets) == 1, "the one internal net, per cabinet"
        assert not (internal_nets & touched_by_findings)

        board = items_of(model)[x1_item].unit
        assert _wires_on(model, board) >= len(internal_conductors) + len(internal_nets), (
            "both X1-K1 wires and the internal net now route in the board's own home set"
        )

        assert reference_designation(model, x1_item).endswith("-U1-X1")

        x1_fn = _function_of(model, x1_item, "x1")
        p1_fn = _function_of(model, p1_item, "x1")
        coil_pages = _coil_pages(model, board)
        x1_pages = _box_pages_of(model, x1_fn.id)
        (p1_page,) = _box_pages_of(model, p1_fn.id)
        assert len(coil_pages) == 1, "K1's coil is drawn once, in the board's own home set"
        assert x1_pages == coil_pages | {p1_page}, "X1 is boxed at home (with K1) and again on P1's page, face to face with it"

        # Per layout-0153, the cable WH1 is a harness line, so its cores are no route; the
        # line draws them, and P1's page draws the board as one middle outline
        pages = layout_of_model(model, Page)
        board_outlines = [
            page for page, drawing in drawn_pages(model).items() for _ in drawing.outlines if (pages[page].drawing_set, pages[page].number) == p1_page
        ]
        assert len(board_outlines) == 1, "the board draws one outline, on P1's page"


def _cabinet_terminal_straight_to_board_relay(s, *, name):
    """Scratch variant of `pump_cabinet`/`io_board`: a cabinet terminal wired straight to
    the board's relay coil, bypassing `X1`/`P1` entirely (the second model,
    can-fail against the base commit)."""
    u = s.unit("demo-pump-cabinet", revision=2, interface="1")
    u.revision(2, date="2026-01-01", text="First release", created="XX")
    c = u.location(name, "Pump cabinet")
    grp = u.group("FLD", "Field wiring")
    x2 = u.strip("X2", at=c)
    field = [x2.terminal("DEMO-TB-2.5-TWIN", group=grp) for _ in range(2)]
    io = u.scope("io", at=c)
    io_u = io.unit("demo-io-board", revision=3, interface="2")
    io_u.revision(3, date="2026-01-01", text="First release", created="XX")
    board_grp = io_u.group("BRD", "I/O board")
    board = io_u.item("DEMO-PCB-IO", name="board", group=board_grp)
    x1 = io_u.item("DEMO-CONN-2P", tag="X1", parent=board, group=board_grp)
    k1 = io_u.item("DEMO-RLY-2CO-24", name="k1", parent=board, group=board_grp)
    io_u.boundary(x1)
    wire = u.wiring(colour="BU", gauge="0.5")
    wire(field[0].outer, k1.fn("coil")["A1"])
    h1 = io_u.item("DEMO-LAMP-24", name="h1", parent=board, group=board_grp)  # a lamp across the coil closes its second leg inside the board
    io_wire = io_u.wiring(colour="BU", gauge="0.5")
    io_wire(k1.fn("coil")["A2"], h1.fn("lamp")["1"])
    io_wire(h1.fn("lamp")["2"], k1.fn("coil")["A1"])
    for t in field:
        u.boundary(t)
    return field


def test_a_cabinet_terminal_wired_straight_to_the_board_relay_bypasses_its_own_unit_boundary() -> None:
    """Before the board-unit ruling: exactly one `CONNECTION_TO_UNDRAWN`, subjects
    the relay coil's one wired port --
    the field terminal was drawn, the board relay was not (the blanket exclusion),
    """
    parts = fransys_parts.load("demo_parts")
    d = Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    _cabinet_terminal_straight_to_board_relay(d.scope("pump1", at=er), name="C1")
    result = fr.build(parts, *printed(d.draft()))

    to_undrawn = [f for f in result.findings if f.code == "CONNECTION_TO_UNDRAWN"]
    assert to_undrawn == []

    by_key = {item.key: item.id for item in items_of(result.model).values()}
    k1_item = by_key[("pump1", "io", "k1")]
    x1_item = by_key[("pump1", "io", "X1")]
    coil_fn = _function_of(result.model, k1_item, "coil")
    x1_fn = _function_of(result.model, x1_item, "x1")

    bypassed = [f for f in result.findings if f.code == UNIT_BOUNDARY_BYPASSED]
    expect_codes(result, UNIT_BOUNDARY_BYPASSED, BOUNDARY_UNCONNECTED)
    assert len(bypassed) == 1
    assert coil_fn.id in bypassed[0].subjects

    unconnected = [f for f in result.findings if f.code == BOUNDARY_UNCONNECTED]
    assert len(unconnected) == 1
    assert x1_fn.id in unconnected[0].subjects


# -- The board-relative fix threaded into pin_of's fallback --------------------


def test_step_4b_the_kicad_netlist_of_the_board_is_board_relative() -> None:
    """`fransys_kicad.netlist(model, pump1/io/board)` reads `K1`, not `U1-K1`: `pin_of`'s
    fallback threads `relative_to=board` into `item_designation`, the same board-relative rule
    `board_netlist` uses; both parts carry a footprint (parts-0024), so both are components.
    """
    result, _field1, _field2 = _build_system()
    model = result.model
    by_key = {item.key: item.id for item in items_of(model).values()}
    board = by_key[("pump1", "io", "board")]

    text = kicad_netlist(model, board)

    assert "U1-" not in text
    assert text.count('(comp (ref "K1")') == 1
    assert text.count('(comp (ref "X1")') == 1
    assert text.endswith(
        "  (nets\n"
        '    (net (code "1") (name "Net-(K1-A1)")\n'
        '      (node (ref "K1") (pin "A1"))\n'
        '      (node (ref "X1") (pin "1")))\n'
        '    (net (code "2") (name "Net-(K1-A2)")\n'
        '      (node (ref "K1") (pin "A2"))\n'
        '      (node (ref "X1") (pin "2")))\n'
        '    (net (code "3") (name "internal")\n'
        '      (node (ref "K1") (pin "11"))\n'
        '      (node (ref "K1") (pin "21"))))'
        ")\n"
    )
