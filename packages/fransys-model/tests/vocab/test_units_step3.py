"""Units spec STEP 3: `vocab/validators/units.py`, the U5 checks.

`docs/archive/specs/2026-09-22-units.md` U3, U4, U5; `docs/decisions/model-0038-units.md`.
"""

from plant import Plant

from fransys_model.derive import boundary as unit_boundary
from fransys_model.derive import standalone
from fransys_model.kernel import Severity
from fransys_model.vocab.enums import FunctionKind
from fransys_model.vocab.tables import conductors, mates, nets
from fransys_model.vocab.validators.units import (
    BOUNDARY_KIND,
    BOUNDARY_NOT_IN_UNIT,
    BOUNDARY_UNCONNECTED,
    MATE_NOT_CONNECTOR,
    MATE_PORT_MISMATCH,
    UNIT_BOUNDARY_BYPASSED,
    UNIT_CONNECTOR_DANGLING,
    UNUSED_CONTRADICTED,
    check_units,
)

# ---- BOUNDARY_UNCONNECTED ---------------------------------------------------------------------


def _integrated_unit_with_unconnected_boundary(plant: Plant) -> tuple:
    unit = plant.unit("board")
    item = plant.item("board-item", unit=unit)
    function = plant.function(item, "x1", kind=FunctionKind.CONNECTOR)
    plant.port(function, "1")
    return unit, function


def test_boundary_unconnected_for_an_integrated_units_boundary() -> None:
    """A boundary function of an integrated unit, not connected, not declared unused."""
    plant = Plant()
    unit, function = _integrated_unit_with_unconnected_boundary(plant)
    plant.boundary(unit, function)
    plant.item("outside")  # unit=None: keeps the model from being standalone for `unit`
    model = plant.model()
    # examined: the unit is integrated and the function really is its boundary
    assert standalone(model, unit) is False
    assert unit_boundary(model, unit) == (function,)
    findings = [f for f in check_units(model) if f.code == BOUNDARY_UNCONNECTED]
    assert len(findings) == 1
    (finding,) = findings
    assert finding.severity == Severity.ERROR
    assert set(finding.subjects) == {unit, function}


def test_can_fail_boundary_unconnected_standalone_twin_reports_nothing() -> None:
    """Twin: the same model made standalone (no outside item) reports nothing (U5)."""
    plant = Plant()
    unit, function = _integrated_unit_with_unconnected_boundary(plant)
    plant.boundary(unit, function)
    model = plant.model()
    # examined: the unit is standalone this time, and still really has the boundary function
    assert standalone(model, unit) is True
    assert unit_boundary(model, unit) == (function,)
    assert [f for f in check_units(model) if f.code == BOUNDARY_UNCONNECTED] == []


def test_boundary_unconnected_twin_with_an_unused_boundary_reports_nothing() -> None:
    """Twin: the same integrated model, but the boundary is declared `UnusedBoundary`."""
    plant = Plant()
    unit, function = _integrated_unit_with_unconnected_boundary(plant)
    plant.boundary(unit, function)
    plant.unused(function)
    plant.item("outside")
    model = plant.model()
    # examined: still integrated, still a real boundary function
    assert standalone(model, unit) is False
    assert unit_boundary(model, unit) == (function,)
    assert [f for f in check_units(model) if f.code == BOUNDARY_UNCONNECTED] == []


# ---- UNIT_BOUNDARY_BYPASSED ---------------------------------------------------------------------


def test_unit_boundary_bypassed_for_a_conductor_from_outside_to_a_boards_relay() -> None:
    """A conductor from outside a unit lands directly on a relay, not the boundary connector."""
    plant = Plant()
    board = plant.unit("board")
    board_item = plant.item("board-item", unit=board)
    relay = plant.function(board_item, "coil", kind=FunctionKind.COIL)
    relay_port = plant.port(relay, "A1")
    outside_item = plant.item("outside")
    outside_fn = plant.function(outside_item, "wire")
    outside_port = plant.port(outside_fn, "1")
    conductor = plant.wire(outside_port, relay_port, key="bypass")
    model = plant.model()
    # examined: the conductor exists and the relay is not the board's boundary
    assert conductor in conductors(model)
    assert unit_boundary(model, board) == ()
    findings = [f for f in check_units(model) if f.code == UNIT_BOUNDARY_BYPASSED]
    assert len(findings) == 1
    (finding,) = findings
    assert finding.severity == Severity.ERROR
    assert set(finding.subjects) == {board, relay, conductor}


def test_can_fail_unit_boundary_bypassed_twin_landing_on_the_boundary_reports_nothing() -> None:
    """Twin: the same conductor landing on the board's boundary connector instead (U5)."""
    plant = Plant()
    board = plant.unit("board")
    board_item = plant.item("board-item", unit=board)
    connector = plant.function(board_item, "x1", kind=FunctionKind.CONNECTOR)
    connector_port = plant.port(connector, "1")
    plant.boundary(board, connector)
    outside_item = plant.item("outside")
    outside_fn = plant.function(outside_item, "wire")
    outside_port = plant.port(outside_fn, "1")
    conductor = plant.wire(outside_port, connector_port, key="through-boundary")
    model = plant.model()
    # examined: the conductor exists and the connector really is the board's boundary
    assert conductor in conductors(model)
    assert unit_boundary(model, board) == (connector,)
    assert [f for f in check_units(model) if f.code == UNIT_BOUNDARY_BYPASSED] == []


def test_a_boards_own_boundary_wired_from_outside_the_cabinet_bypasses_the_cabinet_only() -> None:
    """A connector that is the board's boundary but not the cabinet's: reported for the cabinet."""
    plant = Plant()
    cabinet = plant.unit("cabinet")
    board = plant.unit("board", parent=cabinet)
    board_item = plant.item("board-item", unit=board)
    connector = plant.function(board_item, "x1", kind=FunctionKind.CONNECTOR)
    connector_port = plant.port(connector, "1")
    plant.boundary(board, connector)  # boundary of the board, not of the cabinet
    outside_item = plant.item("outside")  # outside the cabinet entirely
    outside_fn = plant.function(outside_item, "wire")
    outside_port = plant.port(outside_fn, "1")
    conductor = plant.wire(outside_port, connector_port, key="external")
    model = plant.model()
    # examined: the connector really is the board's boundary and not the cabinet's
    assert unit_boundary(model, board) == (connector,)
    assert connector not in unit_boundary(model, cabinet)
    findings = [f for f in check_units(model) if f.code == UNIT_BOUNDARY_BYPASSED]
    assert len(findings) == 1
    (finding,) = findings
    assert set(finding.subjects) == {cabinet, connector, conductor}


# ---- UNIT_CONNECTOR_DANGLING ---------------------------------------------------------------------


def _unmarked_terminal(plant: Plant) -> tuple:
    unit = plant.unit("cabinet")
    item = plant.item("item", unit=unit)
    function = plant.function(item, "t1", kind=FunctionKind.TERMINAL)
    plant.port(function, "1")
    return unit, function


def test_unit_connector_dangling_for_an_unmarked_unconnected_terminal() -> None:
    """A terminal whose item belongs directly to a unit, not a boundary, connected to nothing."""
    plant = Plant()
    unit, function = _unmarked_terminal(plant)
    model = plant.model()
    # examined: the function really belongs directly to the unit, and is not its boundary
    assert function not in unit_boundary(model, unit)
    findings = [f for f in check_units(model) if f.code == UNIT_CONNECTOR_DANGLING]
    assert len(findings) == 1
    (finding,) = findings
    assert finding.severity == Severity.WARNING
    assert set(finding.subjects) == {unit, function}


def test_can_fail_unit_connector_dangling_twin_marked_boundary_reports_nothing() -> None:
    """Twin: the same terminal, marked as the unit's boundary (U5)."""
    plant = Plant()
    unit, function = _unmarked_terminal(plant)
    plant.boundary(unit, function)
    model = plant.model()
    # examined: the function is now really the unit's boundary
    assert unit_boundary(model, unit) == (function,)
    assert [f for f in check_units(model) if f.code == UNIT_CONNECTOR_DANGLING] == []


def test_can_fail_unit_connector_dangling_twin_wired_reports_nothing() -> None:
    """Twin: the same terminal, wired to something (U5)."""
    plant = Plant()
    _unit, function = _unmarked_terminal(plant)
    terminal_port = plant.port(function, "2")
    elsewhere_fn = plant.function(plant.item("elsewhere"), "f")
    elsewhere_port = plant.port(elsewhere_fn, "1")
    conductor = plant.wire(terminal_port, elsewhere_port, key="wired")
    model = plant.model()
    # examined: the conductor really exists and lands on the terminal's function
    assert conductor in conductors(model)
    assert [f for f in check_units(model) if f.code == UNIT_CONNECTOR_DANGLING] == []


# ---- MATE_PORT_MISMATCH ---------------------------------------------------------------------


def _mate_of(plant: Plant, *, a_pins: tuple, b_pins: tuple) -> tuple:
    item_a = plant.item("conn-a")
    fn_a = plant.function(item_a, "j1", kind=FunctionKind.CONNECTOR)
    for name in a_pins:
        plant.port(fn_a, name)
    item_b = plant.item("conn-b")
    fn_b = plant.function(item_b, "p1", kind=FunctionKind.CONNECTOR)
    for name in b_pins:
        plant.port(fn_b, name)
    mate = plant.mate(fn_a, fn_b)
    return mate, fn_a, fn_b


def test_mate_port_mismatch_for_a_4_pin_to_3_pin_mate_names_pin_4() -> None:
    """A 4-pin connector mated to a 3-pin one: the message names the unmatched pin `4`."""
    plant = Plant()
    mate, fn_a, fn_b = _mate_of(plant, a_pins=("1", "2", "3", "4"), b_pins=("1", "2", "3"))
    model = plant.model()
    # examined: the mate really exists
    assert mate in mates(model)
    findings = [f for f in check_units(model) if f.code == MATE_PORT_MISMATCH]
    assert len(findings) == 1
    (finding,) = findings
    assert finding.severity == Severity.WARNING
    assert "4" in finding.message
    assert set(finding.subjects) == {mate, fn_a, fn_b}


def test_can_fail_mate_port_mismatch_4_to_4_twin_reports_nothing() -> None:
    """Twin: a 4-pin connector mated to another 4-pin one (U5)."""
    plant = Plant()
    mate, _fn_a, _fn_b = _mate_of(plant, a_pins=("1", "2", "3", "4"), b_pins=("1", "2", "3", "4"))
    model = plant.model()
    assert mate in mates(model)
    assert [f for f in check_units(model) if f.code == MATE_PORT_MISMATCH] == []


# ---- MATE_NOT_CONNECTOR -----------------------------------------------------------------------


def _mate_of_kinds(plant: Plant, kind_a: FunctionKind, kind_b: FunctionKind) -> tuple:
    fn_a = plant.function(plant.item("end-a"), "a", kind=kind_a)
    fn_b = plant.function(plant.item("end-b"), "b", kind=kind_b)
    for fn in (fn_a, fn_b):
        plant.port(fn, "1")
    return plant.mate(fn_a, fn_b), fn_a, fn_b


def test_mate_not_connector_names_the_coil_end_of_a_plug_to_coil_mate() -> None:
    """A connector mated to a coil: one ERROR, subjects the mate and the coil function."""
    plant = Plant()
    mate, _plug, coil = _mate_of_kinds(plant, FunctionKind.CONNECTOR, FunctionKind.COIL)
    model = plant.model()
    findings = [f for f in check_units(model) if f.code == MATE_NOT_CONNECTOR]
    assert [f.severity for f in findings] == [Severity.ERROR]
    assert set(findings[0].subjects) == {mate, coil}


def test_can_fail_mate_not_connector_connector_and_terminal_twin_reports_nothing() -> None:
    """Twin: a connector mated to a terminal is a valid mate."""
    plant = Plant()
    mate, _a, _b = _mate_of_kinds(plant, FunctionKind.CONNECTOR, FunctionKind.TERMINAL)
    model = plant.model()
    assert mate in mates(model)
    assert [f for f in check_units(model) if f.code == MATE_NOT_CONNECTOR] == []


def test_mate_not_connector_reports_each_offending_end() -> None:
    """Two non-connector ends give two findings."""
    plant = Plant()
    _mate, _a, _b = _mate_of_kinds(plant, FunctionKind.COIL, FunctionKind.COIL)
    findings = [f for f in check_units(plant.model()) if f.code == MATE_NOT_CONNECTOR]
    assert len(findings) == 2


# ---- UNUSED_CONTRADICTED ---------------------------------------------------------------------


def test_unused_contradicted_when_the_function_is_the_boundary_of_no_unit() -> None:
    """`UnusedBoundary` names a function that no `Boundary` record ever names."""
    plant = Plant()
    item = plant.item("item")
    function = plant.function(item, "x1", kind=FunctionKind.CONNECTOR)
    plant.port(function, "1")
    plant.unused(function)
    model = plant.model()
    findings = [f for f in check_units(model) if f.code == UNUSED_CONTRADICTED]
    assert len(findings) == 1
    (finding,) = findings
    assert finding.severity == Severity.WARNING
    assert set(finding.subjects) == {function}


def test_unused_contradicted_when_the_function_is_connected_across_its_unit() -> None:
    """`UnusedBoundary` names a function that is a boundary of `unit` but crosses out of it."""
    plant = Plant()
    unit = plant.unit("cabinet")
    item = plant.item("item", unit=unit)
    function = plant.function(item, "x1", kind=FunctionKind.CONNECTOR)
    port = plant.port(function, "1")
    plant.boundary(unit, function)
    plant.unused(function)
    outside_item = plant.item("outside")
    outside_fn = plant.function(outside_item, "far")
    outside_port = plant.port(outside_fn, "1")
    conductor = plant.wire(port, outside_port, key="crosses")
    model = plant.model()
    # examined: the function really is the unit's boundary, and the conductor really crosses it
    assert unit_boundary(model, unit) == (function,)
    assert conductor in conductors(model)
    findings = [f for f in check_units(model) if f.code == UNUSED_CONTRADICTED]
    assert len(findings) == 1
    (finding,) = findings
    assert set(finding.subjects) == {unit, function}


def test_a_declared_net_across_the_unit_is_not_a_crossing() -> None:
    """U4: declared `Net`s are intent and do not count; only a conductor or mate end crosses."""
    plant = Plant()
    unit = plant.unit("cabinet")
    item = plant.item("item", unit=unit)
    function = plant.function(item, "x1", kind=FunctionKind.CONNECTOR)
    port = plant.port(function, "1")
    plant.boundary(unit, function)
    plant.unused(function)
    outside_item = plant.item("outside")
    outside_port = plant.port(plant.function(outside_item, "far"), "1")
    plant.net("intent", (port, outside_port))
    model = plant.model()
    # examined: the net really joins the boundary port to an outside port, with no conductor
    assert unit_boundary(model, unit) == (function,)
    assert len(nets(model)) == 1
    assert conductors(model) == {}
    assert [f for f in check_units(model) if f.code == UNUSED_CONTRADICTED] == []
    assert [f for f in check_units(model) if f.code == UNIT_BOUNDARY_BYPASSED] == []


def test_can_fail_unused_contradicted_twin_a_real_unconnected_boundary_reports_nothing() -> None:
    """Twin: `UnusedBoundary` names a real boundary that is in fact left unconnected (U5)."""
    plant = Plant()
    unit = plant.unit("cabinet")
    item = plant.item("item", unit=unit)
    function = plant.function(item, "x1", kind=FunctionKind.CONNECTOR)
    plant.port(function, "1")
    plant.boundary(unit, function)
    plant.unused(function)
    model = plant.model()
    assert unit_boundary(model, unit) == (function,)
    assert [f for f in check_units(model) if f.code == UNUSED_CONTRADICTED] == []


# ---- BOUNDARY_KIND ---------------------------------------------------------------------


def test_boundary_kind_for_a_relay_coil_marked_boundary() -> None:
    """A `COIL` function marked as a unit's boundary: neither `TERMINAL` nor `CONNECTOR`."""
    plant = Plant()
    unit = plant.unit("cabinet")
    item = plant.item("item", unit=unit)
    function = plant.function(item, "coil", kind=FunctionKind.COIL)
    plant.port(function, "A1")
    plant.boundary(unit, function)
    model = plant.model()
    # examined: the coil really is declared this unit's boundary
    assert unit_boundary(model, unit) == (function,)
    findings = [f for f in check_units(model) if f.code == BOUNDARY_KIND]
    assert len(findings) == 1
    (finding,) = findings
    assert finding.severity == Severity.ERROR
    assert set(finding.subjects) == {unit, function}
    assert "coil" in finding.message


def test_can_fail_boundary_kind_twin_a_connector_reports_nothing() -> None:
    """Twin: the same unit's boundary is a `CONNECTOR` function instead (U5)."""
    plant = Plant()
    unit = plant.unit("cabinet")
    item = plant.item("item", unit=unit)
    function = plant.function(item, "x1", kind=FunctionKind.CONNECTOR)
    plant.port(function, "1")
    plant.boundary(unit, function)
    model = plant.model()
    assert unit_boundary(model, unit) == (function,)
    assert [f for f in check_units(model) if f.code == BOUNDARY_KIND] == []


# ---- BOUNDARY_NOT_IN_UNIT ---------------------------------------------------------------------


def test_boundary_not_in_unit_for_a_function_of_another_unit() -> None:
    """A `Boundary` of unit `a` names a function whose item belongs to unrelated unit `b`."""
    plant = Plant()
    unit_a = plant.unit("a")
    unit_b = plant.unit("b")
    item_b = plant.item("item-b", unit=unit_b)
    function = plant.function(item_b, "x1", kind=FunctionKind.CONNECTOR)
    plant.port(function, "1")
    plant.boundary(unit_a, function)
    model = plant.model()
    # examined: the function's item really belongs to the other unit, not `a`'s subtree
    assert function not in unit_boundary(model, unit_b)
    findings = [f for f in check_units(model) if f.code == BOUNDARY_NOT_IN_UNIT]
    assert len(findings) == 1
    (finding,) = findings
    assert finding.severity == Severity.ERROR
    assert set(finding.subjects) == {unit_a, function}


def test_can_fail_boundary_not_in_unit_twin_declared_on_its_own_unit_reports_nothing() -> None:
    """Twin: the same function declared as its own unit's boundary instead (U5)."""
    plant = Plant()
    unit_b = plant.unit("b")
    item_b = plant.item("item-b", unit=unit_b)
    function = plant.function(item_b, "x1", kind=FunctionKind.CONNECTOR)
    plant.port(function, "1")
    plant.boundary(unit_b, function)
    model = plant.model()
    assert unit_boundary(model, unit_b) == (function,)
    assert [f for f in check_units(model) if f.code == BOUNDARY_NOT_IN_UNIT] == []
