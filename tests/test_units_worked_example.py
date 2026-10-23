"""The worked example, completed with the demo parts.

Adapted from the spec's literal text, as its own note invites ("use the
real ones"): the field terminals' cable-side ports are marked `.outer` (their role), not
`"1"`/`"2"` (`DEMO-TB-2.5` has no such markings); every item that a wire or mate touches
needs a `group=` placement for `fransys_layout` to find it a column (the spec's own
pseudocode elides this with `...`); `p1` additionally needs `at=c` (not in the literal
text) so its reference designation carries the cabinet's own location, the same as every
other per-instance item -- without it, `P1` renders bare `=FLD+ER-P1` in both cabinets
and collides on `REFERENCE_DESIGNATION_DUPLICATE` for a reason unrelated to units (see
`docs/decisions/author-0002-units-authoring.md`).

Root tests build through `fr.build` (not `packages/fransys-author/tests`, which cannot
import the facade `fransys` without a layering exception; the choice is logged in the
hand-back).
"""

import dataclasses
from typing import Any

import fransys as fr
import fransys_author
import fransys_parts
from _core_boxes import connector_names, named_boxes
from _drawn_pages import drawn_pages
from _model_build_cover import layout_trigger_document
from fransys_kicad import netlist as kicad_netlist
from root_library import freeze

from fransys_layout.lint.codes import CONNECTION_TO_UNDRAWN
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
from fransys_model.derive.passes.numbering import REFERENCE_DESIGNATION_DUPLICATE
from fransys_model.derive.passes.numbering import number as number_pass
from fransys_model.kernel import Origin, evolve, merge
from fransys_model.layout import (
    DrawingSet,
    Page,
)
from fransys_model.layout import layout_of as layout_of_model
from fransys_model.vocab.tables import boundaries, mates
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


def io_board(s, *, mark_boundary=True):
    """Worked example: a board unit with one boundary connector, `X1`.

    `DEMO-PCB-IO` is a real board (`category = "board"`, a `[pcb]` facet, decision
    model-0040, closing author-0002's `KNOWN DEVIATION`), and the *sole* root item of its own
    nested unit `demo-io-board` (board-unit ruling, model-0041):
    the board is itself a whole unit, not board-inside-a-unit furniture, so in its own home
    set the schematic engine draws its functions and its board-internal wiring like any
    unit's set, not as a black box. `X1`'s two wires to `K1`'s coil and the net below
    therefore draw normally -- a real route each, no `CONNECTION_TO_UNDRAWN` -- in
    `demo-io-board`'s own home set; the board-internal silent-drop rule (decision
    layout-0044) still applies exactly as before to a board that is merely *inside* a larger
    unit (B1's ordinary case, `enclosing_boards` non-empty but not `is_sole_unit_root`),
    which this ruling leaves unchanged.
    """
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
    return x1, u


def pump_cabinet(s, *, name):
    """Worked example: a cabinet unit with two field-terminal boundaries."""
    u = s.unit("demo-pump-cabinet", revision=2, interface="1")
    u.revision(2, date="2026-01-01", text="First release", created="XX")
    c = u.location(name, "Pump cabinet")
    grp = u.group("FLD", "Field wiring")
    x2 = u.strip("X2", at=c)
    field = [x2.terminal("DEMO-TB-2.5", group=grp) for _ in range(2)]
    board_x1, _ = io_board(u.scope("io", at=c))
    w1 = u.harness(name="w1", tag="WH1", at=c, group=grp)
    p1 = u.item("DEMO-CONN-2P", tag="P1", parent=w1, at=c, group=grp)
    cable = u.cable("DEMO-CBL-4G1.5", name="w1c", parent=w1, at=c)
    cable.core(1, field[0].outer, p1["1"])
    cable.core(2, field[1].outer, p1["2"])
    u.mate(p1, board_x1)
    for t in field:
        u.boundary(t)
    return field, u


def _wire_field_to_motor(d, field, *, fld, grp, motor_tag):
    """Wire `field[0]` to a top-level motor, across the cabinet's own unit boundary (spec
    worked example, amended 2026-09-23: "Every boundary terminal of each cabinet is wired at
    the use site, here by a top-level cable to a field item"). `d.cable` (unlike `u.cable`
    inside `pump_cabinet`) is authored directly on `Design`, so the motor and cable items
    carry `unit=None`: a real top-level cable, not one scoped inside either
    unit. The field terminal's `outer` (external/field-cable side) port already carries one
    conductor from `pump_cabinet`'s own internal `w1c` cable (to `P1`, inside the same unit)
    -- this adds a second, external one, so the boundary function's interface genuinely
    crosses its unit (validator `_boundary_unconnected`: "any conductor or mate
    end" on the function, not the port alone), clearing `BOUNDARY_UNCONNECTED` for real
    instead of routing around it.

    NEW (the recommended reading of the worked example's "-M1, -M2, -A3", three
    top-level devices, four top-level cables): each cabinet's two field terminals no longer
    share one cable to the cabinet's own motor. `field[0]` gets its own one-core cable to the
    motor here; `field[1]` gets a separate one-core cable to the one shared switch
    (`_wire_field_to_switch`, called by `_system_design` below). The motor's `V`/`W`/`PE`
    ports stay unwired, the same partial-core pattern `pump_cabinet`'s own `w1c` cable already
    uses on this part (two of its four cores).
    """
    motor = d.item("DEMO-MOTOR-4KW", tag=motor_tag, at=fld, group=grp)
    cable = d.cable("DEMO-CBL-4G1.5", tag=f"W{motor_tag}", length_mm=15000)
    cable.core(1, field[0].outer, motor["U"])
    return motor


def _wire_field_to_switch(d, terminal, switch_port, *, cable_tag):
    """Wire one field terminal to one port of the one shared top-level switch, its own
    one-core top-level cable (mirrors `_wire_field_to_motor`'s cable shape). Called once per
    cabinet instance, each time on that cabinet's `field[1]` (its second field terminal, the
    one `_wire_field_to_motor` above does not use) against the switch's two connector ports in
    turn -- `switch.fn("x1")["1"]` for pump1, `switch.fn("x1")["2"]` for pump2 -- so the one
    switch item is a real shared top-level device, not a per-cabinet one like the motors.
    """
    cable = d.cable("DEMO-CBL-4G1.5", tag=cable_tag, length_mm=15000)
    cable.core(1, terminal.outer, switch_port)


def _system_design(parts, *, name1="C1", name2="C2"):
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    field1, _ = pump_cabinet(d.scope("pump1", at=er), name=name1)
    field2, _ = pump_cabinet(d.scope("pump2", at=er), name=name2)
    fld = d.location("FLD", "Field")
    fld_grp = d.group("FLD", "Field wiring")
    _wire_field_to_motor(d, field1, fld=fld, grp=fld_grp, motor_tag="M1")
    _wire_field_to_motor(d, field2, fld=fld, grp=fld_grp, motor_tag="M2")
    switch = d.item("DEMO-SWITCH-2P", tag="K1", at=fld, group=fld_grp)
    _wire_field_to_switch(d, field1[1], switch.fn("x1")["1"], cable_tag="WM1S")
    _wire_field_to_switch(d, field2[1], switch.fn("x1")["2"], cable_tag="WM2S")
    return d, field1, field2


def _build_system(*, name1="C1", name2="C2"):
    parts = fransys_parts.load("demo_parts")
    d, field1, field2 = _system_design(parts, name1=name1, name2=name2)
    return fr.build(parts, d.draft(), layout_trigger_document()), field1, field2


def _build_cabinet_own(*, prefix, name):
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    field, _ = pump_cabinet(d.scope(prefix), name=name)
    return fr.build(parts, d.draft(), layout_trigger_document()), field


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


def test_pump1s_item_designations_match_between_the_system_and_its_own_build():
    """pump1's items keep their designation once integrated."""
    system, _, _ = _build_system()
    own, _ = _build_cabinet_own(prefix="p", name="C1")
    system_by_key = _designations_by_stripped_key(system.model, prefix="pump1")
    own_by_key = _designations_by_stripped_key(own.model, prefix="p")
    shared = sorted(set(system_by_key) & set(own_by_key))
    assert len(shared) > 0
    assert all(system_by_key[key] == own_by_key[key] for key in shared)
    # every item the worked example numbers by hand is among them, not just a subset
    assert {("X2",), ("P1",), ("w1c",), ("io", "X1"), ("io", "k1"), ("io", "board")} <= set(shared)


def test_pump2s_item_designations_also_match_its_own_build():
    """The same equality holds for the second instance, key for key."""
    system, _, _ = _build_system()
    own, _ = _build_cabinet_own(prefix="p", name="C1")
    system_by_key = _designations_by_stripped_key(system.model, prefix="pump2")
    own_by_key = _designations_by_stripped_key(own.model, prefix="p")
    shared = sorted(set(system_by_key) & set(own_by_key))
    assert len(shared) > 0
    assert all(system_by_key[key] == own_by_key[key] for key in shared)


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

    The board (`DEMO-PCB-IO`, class code `U`), not the relay, is the item that moves:
    the relay's `parent` is its own per-instance board item, already unique, so `parent`
    alone disambiguates it with or without `unit`. The board itself has `parent=None`
    (`u.item("DEMO-PCB-IO", name="board")`, no `parent=`), the
    one item in this worked example that collides once `unit` stops telling the two
    cabinets' boards apart: pump1's board sorts first by `(key, id)` and keeps `U1`;
    pump2's, sharing the same `(None, None)` group once stripped, becomes `U2`.
    """
    parts = fransys_parts.load("demo_parts")
    d, _, _ = _system_design(parts)
    model = freeze(merge(parts, d.draft()))

    correct, _ = number_pass(model)
    correct_by_key = _designations_by_stripped_key(correct, prefix="pump1")
    correct_by_key_2 = _designations_by_stripped_key(correct, prefix="pump2")
    assert correct_by_key[("io", "board")] == "U1"
    assert correct_by_key_2[("io", "board")] == "U1"

    stripped_items = [
        dataclasses.replace(item, unit=None)
        for item in items_of(model).values()
        if item.unit is not None
    ]
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
    without relying on `_system_design`'s own (now real) wiring.
    """
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    field1, _ = pump_cabinet(d.scope("pump1", at=er), name="C1")
    field2, _ = pump_cabinet(d.scope("pump2", at=er), name="C2")
    return d, field1, field2


def _build_bare_two_cabinets():
    parts = fransys_parts.load("demo_parts")
    d, field1, field2 = _bare_two_cabinet_design(parts)
    return fr.build(parts, d.draft(), layout_trigger_document()), field1, field2


def test_an_unwired_field_terminal_is_boundary_unconnected_four_times():
    """This was `_build_system()`'s own state (the fixture's known,
    pre-existing gap). Since the fixture fix below (ruling 2026-09-23),
    `_system_design` now wires every field terminal to a real top-level motor cable, so this
    scenario -- an explicitly unwired two-cabinet build -- is exercised on its own local
    `_bare_two_cabinet_design`, kept alive rather than lost.
    """
    result, _field1, _field2 = _build_bare_two_cabinets()
    codes = _codes(result)
    assert codes.count(BOUNDARY_UNCONNECTED) == 4
    for code in _OTHER_U5_CODES:
        assert codes.count(code) == 0
    # the zero counts above are not vacuous: the model does have mates and boundaries to
    # check them against (one mate per cabinet, p1 onto the board's X1; three boundaries
    # per cabinet instance, two field terminals plus the board's own X1).
    assert len(mates(result.model)) == 2
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
    # not vacuous: same non-zero mate/boundary counts as the bare (unwired) build above.
    assert len(mates(result.model)) == 2
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
    assert codes.count("LABEL_UNPLACED") == 0
    # R420: a falling stock; on the text-stage tip every annex finds a free spot.
    assert codes.count("ANNEX_UNPLACED") == _ANNEX_UNPLACED_STOCK
    assert codes.count("WIRE_OVER_LABEL") == 0


def test_boundary_unconnected_clears_once_every_field_terminal_is_declared_unused():
    """Built through `_system_design`, whose field terminals were unwired, so
    declaring all four `unused` cleared `BOUNDARY_UNCONNECTED`.
    Since the fixture fix (ruling 2026-09-23), `_system_design`'s field terminals
    are now really wired (see `test_the_system_builds_field_terminals_are_wired_...` above),
    so this scenario moved to `_bare_two_cabinet_design`, which keeps them unwired -- the
    same rule under test (an explicitly `unused` boundary with no real connection still
    clears the ERROR), just no longer aliased to `_system_design`.
    """
    parts = fransys_parts.load("demo_parts")
    d, field1, field2 = _bare_two_cabinet_design(parts)
    fields = (*field1, *field2)
    assert len(fields) == 4
    for terminal in fields:
        d.unused(terminal)
    result = fr.build(parts, d.draft(), layout_trigger_document())
    assert result.model.tables["unused_boundary"]
    assert len(result.model.tables["unused_boundary"]) == 4
    assert _codes(result).count(BOUNDARY_UNCONNECTED) == 0


# -- U7: REFERENCE_DESIGNATION_DUPLICATE when both cabinets share one name ---------------


def test_reference_designation_duplicate_when_both_cabinets_are_named_c1():
    result, _, _ = _build_system(name1="C1", name2="C1")
    assert _codes(result).count(REFERENCE_DESIGNATION_DUPLICATE) > 0


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
    cabinet_unit = next(
        unit_id
        for unit_id in sorted(units(result.model))
        if unit_release(result.model, unit_id).name == "demo-pump-cabinet"
    )
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
    boundary" (captured verbatim from this scenario for the hand-back).
    """

    def broken_pump_cabinet(s, *, name):
        u = s.unit("demo-pump-cabinet", revision=2, interface="1")
        u.revision(2, date="2026-01-01", text="First release", created="XX")
        c = u.location(name, "Pump cabinet")
        grp = u.group("FLD", "Field wiring")
        x2 = u.strip("X2", at=c)
        field = [x2.terminal("DEMO-TB-2.5", group=grp) for _ in range(2)]
        board_x1, _ = io_board(u.scope("io", at=c), mark_boundary=False)
        w1 = u.harness(name="w1", tag="WH1", at=c, group=grp)
        p1 = u.item("DEMO-CONN-2P", tag="P1", parent=w1, at=c, group=grp)
        cable = u.cable("DEMO-CBL-4G1.5", name="w1c", parent=w1, at=c)
        cable.core(1, field[0].outer, p1["1"])
        cable.core(2, field[1].outer, p1["2"])
        u.mate(p1, board_x1)
        for t in field:
            u.boundary(t)
        return field

    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    broken_pump_cabinet(d.scope("pump1", at=er), name="C1")
    result = fr.build(parts, d.draft(), layout_trigger_document())
    bypassed = [f for f in result.findings if f.code == UNIT_BOUNDARY_BYPASSED]
    assert len(bypassed) > 0
    assert "crosses out of " in bypassed[0].message


# -- model-0040/layout-0044: DEMO-PCB-IO is a real board -----------------------


def _function_of(model, item_id, name):
    return next(f for f in functions_of(model).values() if f.item == item_id and f.key[-1] == name)


def _ports_of(model, function_id):
    return {p.id for p in ports_of(model).values() if p.function == function_id}


def _port_named(model, function_id, name):
    return next(
        p.id for p in ports_of(model).values() if p.function == function_id and p.name == name
    )


def _unit_pages(model, unit):
    """Every page of the drawing sets of `unit`, as `{page id: (drawing_set, number)}`."""
    pages, sets = layout_of_model(model, Page), layout_of_model(model, DrawingSet)
    return {
        p.id: (p.drawing_set, p.number) for p in pages.values() if sets[p.drawing_set].unit == unit
    }


def _coil_pages(model, unit):
    """Every page of `unit`'s sets that draws a relay coil (operating device with A1 and A2)."""
    drawn = drawn_pages(model)
    return {
        where
        for page, where in _unit_pages(model, unit).items()
        if any(
            s.key == "operating-device" and {"A1", "A2"} <= {v for _, v in s.slots}
            for s in drawn[page].symbols
        )
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
    `X1` had no route of its own (only a `Mate` to `P1`, closure not a drawn connection), so
    every route onto its designation's page came from `P1`'s cable cores alone.

    NEW premise (board-unit ruling, model-0041): `DEMO-PCB-IO` is
    the sole root item of its own nested unit `demo-io-board`, so `is_sole_unit_root` makes
    both `schematic_functions` (both wire ends now drawn) and `_is_board_internal` (the board
    no longer counts as opaque) stop suppressing this wiring -- the two wires and the internal
    net now get a real route each, still with no finding (`fr.build` still raises nothing);
    true for both cabinet instances, not just one. `X1` is now placed on *two* pages: its own
    home page (`demo-io-board`'s own set, alongside `K1`) and the boundary replica on `P1`'s
    page (unconditional replication, unchanged by this ruling) -- so
    `X1`'s own ports are now touched by a route too (the two wires to `K1`), not only `P1`'s.

    NEW assertions: both internal conductors and the internal net are routed; `X1` is placed
    on both its own home page (shared with `K1`'s coil) and `P1`'s page; both `X1`'s and
    `P1`'s own ports are touched by a route (the wires to `K1`, and the cable cores, in turn).
    Per layout-0155, `X1` and `P1` stand at the harness line's end, so each is a box.
    Per layout-0153, the cable cores are the line's, no route; the board is a middle
    outline.

    The page Drawings name no conductor, net or port of a wire, so the routes are counted: the
    board's own sets draw a wire for each internal conductor and net, and `P1`'s page draws the
    board as one middle outline.
    """
    result = _build_system()[0]
    model = result.model
    assert [f for f in result.findings if f.code == CONNECTION_TO_UNDRAWN] == []
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

        internal_conductors = {
            c.id for c in conductors_of(model).values() if {c.a, c.b} <= internal_ports
        }
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
        assert x1_pages == coil_pages | {p1_page}, (
            "X1 is boxed at home (with K1) and again on P1's page, face to face with it"
        )

        # Per layout-0153, the cable WH1 is a harness line, so its cores are no route; the
        # line draws them, and P1's page draws the board as one middle outline
        pages = layout_of_model(model, Page)
        board_outlines = [
            page
            for page, drawing in drawn_pages(model).items()
            for _ in drawing.outlines
            if (pages[page].drawing_set, pages[page].number) == p1_page
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
    field = [x2.terminal("DEMO-TB-2.5", group=grp) for _ in range(2)]
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
    for t in field:
        u.boundary(t)
    return field


def test_a_cabinet_terminal_wired_straight_to_the_board_relay_bypasses_its_own_unit_boundary() -> (
    None
):
    """Before the board-unit ruling: exactly one `CONNECTION_TO_UNDRAWN`, subjects
    the relay coil's one wired port --
    the field terminal was drawn, the board relay was not (the blanket exclusion),
    and they shared no common board (the terminal is off any board), so this was not
    board-internal either; the finding was purely "an end is not drawn".

    NEW premise (board-unit ruling, model-0041): `DEMO-PCB-IO` is
    now the sole root item of its own nested unit `demo-io-board`, so `K1`'s coil is drawn in
    that unit's own home set -- nothing about this wire is undrawn any more. But the wire
    still reaches `k1`'s coil directly from outside `demo-io-board`, bypassing its one
    declared boundary function (`X1`) entirely: this is now a genuine authoring mistake the
    model layer already has a code for, `UNIT_BOUNDARY_BYPASSED` (the coil's own crossing
    conductor) -- and, since `X1` itself is declared the boundary but never actually wired to
    anything in this fixture, `BOUNDARY_UNCONNECTED` too. Both `ERROR`, `fr.build` still
    raises nothing (only `fr.write` refuses an `ERROR` export, per the facade findings
    policy); `result.findings` carries both.

    Historical can-fail, quoted from the base commit (044e0c1, `DEMO-PCB-IO` still `category =
    "generic"`, no `[pcb]` facet -- author-0002's `KNOWN DEVIATION`, unaffected by this
    step): building the identical model there raises
        LayoutError: a connection names a function that is in no column or has no spec
    (measured directly: `git worktree add` at 044e0c1, the amended `pcb-io.toml` applied,
    `uv sync`, this model built and the exception's text captured, the worktree then
    removed -- no git discard used).

    NEW assertions: zero `CONNECTION_TO_UNDRAWN`; exactly one `UNIT_BOUNDARY_BYPASSED`,
    subjects including the coil's own crossing conductor and the coil function; exactly one
    `BOUNDARY_UNCONNECTED`, subjects `X1`'s function and the unit.
    """
    parts = fransys_parts.load("demo_parts")
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    er = d.location("ER", "Engine room")
    _cabinet_terminal_straight_to_board_relay(d.scope("pump1", at=er), name="C1")
    result = fr.build(parts, d.draft(), layout_trigger_document())

    to_undrawn = [f for f in result.findings if f.code == CONNECTION_TO_UNDRAWN]
    assert to_undrawn == []

    by_key = {item.key: item.id for item in items_of(result.model).values()}
    k1_item = by_key[("pump1", "io", "k1")]
    x1_item = by_key[("pump1", "io", "X1")]
    coil_fn = _function_of(result.model, k1_item, "coil")
    x1_fn = _function_of(result.model, x1_item, "x1")

    bypassed = [f for f in result.findings if f.code == UNIT_BOUNDARY_BYPASSED]
    assert len(bypassed) == 1
    assert coil_fn.id in bypassed[0].subjects

    unconnected = [f for f in result.findings if f.code == BOUNDARY_UNCONNECTED]
    assert len(unconnected) == 1
    assert x1_fn.id in unconnected[0].subjects


# -- The board-relative fix threaded into pin_of's fallback --------------------


def test_step_4b_the_kicad_netlist_of_the_board_is_board_relative() -> None:
    """`fransys_kicad.netlist(model, pump1/io/board)` reads `K1`, not `U1-K1`: `pin_of`'s
    fallback (an item with no footprint row, `DEMO-RLY-2CO-24` has none) now threads
    `relative_to=board` into `item_designation`, the same board-relative rule `board_netlist`
    already applies to its own `parts` rows (decision model-0040, the board-relative KiCad
    refinement). Hand-built expectation: the board has no footprinted parts (empty
    `components`); its content is now the `X1`-`K1` board-internal wiring too, not only the
    one internal net -- `board_netlist`'s grouping (decision model-0042, the board-netlist-
    conductors change) gives each of the two `X1`-`K1` wires its own undeclared net,
    `Net-(K1-A1)` and `Net-(K1-A2)`, `K1` beating `X1` as the smaller board-relative
    reference, and its pins listing in that order; `internal`, the one declared net, sorts after
    both (`'N' < 'i'`).

    Can-fail (measured before this fix, `pin_of`'s fallback with no `relative_to`, then
    undone with Edit -- not kept as a toggle in this test):
        (net (code "1") (name "internal")
          (node (ref "U1-K1") (pin "11"))
          (node (ref "U1-K1") (pin "21")))
    """
    result, _field1, _field2 = _build_system()
    model = result.model
    by_key = {item.key: item.id for item in items_of(model).values()}
    board = by_key[("pump1", "io", "board")]

    text = kicad_netlist(model, board)

    assert text == (
        '(export (version "E")\n'
        "  (design\n"
        '    (source "U1")\n'
        '    (tool "fransys_kicad"))\n'
        "  (components)\n"
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
