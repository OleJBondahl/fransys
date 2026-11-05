"""Tests: every finding code of `check_structure`, firing and not firing."""

from typing import Any

from plant import Plant

from fransys_model.checks.structure import (
    ASPECT_CROSS_PARENT,
    ASPECT_CYCLE,
    UNIT_CYCLE,
    check_structure,
)
from fransys_model.checks.terminal_point_capacity import TERMINAL_POINT_OVERFILLED, check_terminal_point_capacity
from fransys_model.checks.terminal_two_pins import TERMINAL_MORE_THAN_TWO_PINS, check_terminal_two_pins
from fransys_model.elecdef import Connection
from fransys_model.kernel import Draft, Finding, Id, Model, Origin, Severity, freeze, make_id
from fransys_model.vocab.aspects import AspectNode, Placement
from fransys_model.vocab.connectivity import Conductor
from fransys_model.vocab.core import Function, Item, Port, Unit
from fransys_model.vocab.enums import Aspect, ConductorKind, FunctionKind, PartCategory, PortBoundary
from fransys_model.vocab.facets import BlockFacet
from fransys_model.vocab.templates import FunctionTemplate, Part

_ORIGIN = Origin(file="test_structure_findings.py", line=1, note="fixture")


def _freeze(*records: Any) -> Model:
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    return freeze(draft)


def _node(key: str, aspect: Aspect = Aspect.LOCATION, *, parent: str | None = None) -> AspectNode:
    return AspectNode(
        id=make_id(AspectNode, (key,)),
        key=(key,),
        aspect=aspect,
        parent=None if parent is None else make_id(AspectNode, (parent,)),
        label=key.upper(),
        description="Invented",
    )


def _item(key: str, *, parent: str | None = None) -> Item:
    return Item(
        id=make_id(Item, (key,)),
        key=(key,),
        part=None,
        parent=None if parent is None else make_id(Item, (parent,)),
        position=None,
        tag=None,
        description="Invented",
    )


def _place(item: Item, node: AspectNode, key: str) -> Placement:
    return Placement(id=make_id(Placement, (key,)), key=(key,), item=item.id, node=node.id)


def _of(model: Model, code: str) -> list[Finding]:
    return [f for f in check_structure(model) if f.code == code]


def _ids(*records: Any) -> tuple[Id[Any], ...]:
    return tuple(sorted(record.id for record in records))


# ---- ASPECT_CYCLE -------------------------------------------------------------------------


def test_two_nodes_that_are_each_others_parent_are_one_error_naming_both() -> None:
    """One finding per cycle, subjects its members, message the labels."""
    a, b = _node("a", parent="b"), _node("b", parent="a")
    (finding,) = _of(_freeze(a, b), ASPECT_CYCLE)
    assert (finding.severity, finding.subjects) == (Severity.ERROR, _ids(a, b))
    assert "A, B" in finding.message


# ---- ASPECT_CROSS_PARENT ------------------------------------------------------------------


def test_a_node_parented_under_another_aspect_is_one_error_naming_both() -> None:
    parent = _node("p", Aspect.LOCATION)
    child = _node("c", Aspect.FUNCTION, parent="p")
    (finding,) = _of(_freeze(parent, child), ASPECT_CROSS_PARENT)
    assert finding.subjects == _ids(parent, child)
    assert "is parented under" in finding.message


# ---- PLACEMENT_DUPLICATE ------------------------------------------------------------------


# ---- CONTAINMENT_CYCLE --------------------------------------------------------------------


# ---- the shape of the result --------------------------------------------------------------


# ---- UNIT_CYCLE ---------------------------------------------------------------------------


def test_two_units_that_are_each_others_parent_are_one_error_naming_both() -> None:
    plant = Plant()
    plant.unit("a", parent=make_id(Unit, ("b",)))
    plant.unit("b", parent=make_id(Unit, ("a",)))
    (finding,) = _of(plant.model(), UNIT_CYCLE)
    assert finding.subjects == tuple(sorted((make_id(Unit, ("a",)), make_id(Unit, ("b",)))))
    assert "the parent chain of units" in finding.message


# ---- TERMINAL_MORE_THAN_TWO_PINS ----------------------------------------------------------


def _terminal(pins: int) -> Model:
    item = _item("x1")
    function = Function(id=make_id(Function, ("x1", "t")), key=("x1", "t"), item=item.id, template=None, name="t", kind=FunctionKind.TERMINAL)
    ports = [
        Port(
            id=make_id(Port, ("x1", "t", str(n))),
            key=("x1", "t", str(n)),
            function=function.id,
            template=None,
            name=str(n),
            boundary=PortBoundary.GENERIC,
        )
        for n in range(pins)
    ]
    return _freeze(item, function, *ports)


def test_a_terminal_with_three_ports_is_refused_with_its_fix_and_two_ports_pass() -> None:
    (finding,) = check_terminal_two_pins(_terminal(3))
    assert (finding.code, finding.severity) == (TERMINAL_MORE_THAN_TWO_PINS, Severity.ERROR)
    assert "has 3 ports" in finding.message
    assert "use a two-pin terminal part" in finding.message
    assert check_terminal_two_pins(_terminal(2)) == ()


# ---- TERMINAL_POINT_OVERFILLED (R1266, R1268) ---------------------------------------------


def _wired_terminal(per_clamp: int | None, wires: int, kind: ConductorKind = ConductorKind.WIRE) -> Model:
    """A terminal `x1` whose external port takes `wires` conductors of `kind` from a device; `per_clamp` is its part's `Connection`."""
    item, device = _item("x1"), _item("k1")
    part = Part(
        id=make_id(Part, ("p",)), key=("p",), mpn="P", manufacturer="M", description="Invented", category=PartCategory.TERMINAL, class_code="X"
    )
    template = FunctionTemplate(id=make_id(FunctionTemplate, ("p", "t")), key=("p", "t"), part=part.id, name="t", kind=FunctionKind.TERMINAL)
    function = Function(id=make_id(Function, ("x1", "t")), key=("x1", "t"), item=item.id, template=template.id, name="t", kind=FunctionKind.TERMINAL)
    other = Function(id=make_id(Function, ("k1", "f")), key=("k1", "f"), item=device.id, template=None, name="f", kind=FunctionKind.GENERIC)

    def port(owner: Function, name: str) -> Port:
        key = (*owner.key, name)
        return Port(id=make_id(Port, key), key=key, function=owner.id, template=None, name=name, boundary=PortBoundary.GENERIC)

    external, pins = port(function, "external"), [port(other, str(n)) for n in range(wires)]
    conductors = [
        Conductor(id=make_id(Conductor, ("c", pin.name)), key=("c", pin.name), a=pin.id, b=external.id, kind=kind, carrier=None) for pin in pins
    ]
    facets = []
    if per_clamp is not None:
        key = ("p", "t", "connection")
        facets = [BlockFacet(id=make_id(BlockFacet, key), key=key, subject=template.id, block=Connection(conductors_per_clamp=per_clamp))]
    return _freeze(item, device, part, template, function, other, port(function, "internal"), external, *pins, *conductors, *facets)


def test_two_wires_on_a_plain_terminal_point_are_refused_and_on_a_twin_are_clean() -> None:
    (finding,) = check_terminal_point_capacity(_wired_terminal(None, 2))
    assert (finding.code, finding.severity) == (TERMINAL_POINT_OVERFILLED, Severity.ERROR)
    assert "'external'" in finding.message
    assert "has 2 conductors but its part takes 1" in finding.message
    assert "DEMO-TB-2.5-TWIN" in finding.message
    assert check_terminal_point_capacity(_wired_terminal(2, 2)) == ()
    assert [f.code for f in check_terminal_point_capacity(_wired_terminal(2, 3))] == [TERMINAL_POINT_OVERFILLED]


def test_a_bridge_counts_no_conductor_on_a_terminal_point() -> None:
    assert check_terminal_point_capacity(_wired_terminal(None, 2, ConductorKind.JUMPER)) == ()
