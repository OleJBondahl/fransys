"""HA4 (parts-0017): `UNIT_CONNECTOR_DANGLING` and the current graph read a header join as a wire.

One item in a unit has a header connector function `head` whose port 1 joins the port `f` of a
second function. With the join, `head` is connected and the graph holds a wire between the two
ports; the same item without the join (the twin) is dangling and holds no such wire.
"""

from plant import Plant

from fransys_model.kernel import Finding, Id, Model, Severity, make_id
from fransys_model.vocab import (
    FunctionKind,
    FunctionTemplate,
    PortRole,
    PortTemplate,
)
from fransys_model.vocab.current_graph import Wire, raw_of
from fransys_model.vocab.validators.units import (
    UNIT_CONNECTOR_DANGLING,
    check_units,
)
lazy from fransys_model.vocab.core import Port


def _build(*, joined: bool) -> tuple[Model, Id[Port], Id[Port]]:
    plant = Plant()
    part = plant.part("M")
    templates = {}
    for name, kind in (("head", FunctionKind.CONNECTOR), ("fn", FunctionKind.GENERIC)):
        templates[name] = FunctionTemplate(
            id=make_id(FunctionTemplate, ("p", name)),
            key=("p", name),
            part=part,
            name=name,
            kind=kind,
        )
    fn_port = PortTemplate(
        id=make_id(PortTemplate, ("p", "fn", "f")),
        key=("p", "fn", "f"),
        function=templates["fn"].id,
        name="f",
        role=PortRole.GENERIC,
    )
    head_port = PortTemplate(
        id=make_id(PortTemplate, ("p", "head", "1")),
        key=("p", "head", "1"),
        function=templates["head"].id,
        name="1",
        role=PortRole.GENERIC,
        joins=fn_port.id if joined else None,
    )
    plant.add(*templates.values(), fn_port, head_port)
    unit = plant.unit("board")
    item = plant.item("board-item", unit=unit)
    head = plant.function(item, "head", template=templates["head"].id, kind=FunctionKind.CONNECTOR)
    fn = plant.function(item, "fn", template=templates["fn"].id)
    first = plant.port(head, "1", template=head_port.id)
    second = plant.port(fn, "f", template=fn_port.id)
    return plant.model(), first, second


def _codes(model: Model, code: str) -> list[Finding]:
    return [f for f in check_units(model) if f.code == code]


def test_a_joined_header_connector_is_not_dangling() -> None:
    """`UNIT_CONNECTOR_DANGLING` reads the join as a connection; the twin without it warns."""
    twin, *_ = _build(joined=False)
    (finding,) = _codes(twin, UNIT_CONNECTOR_DANGLING)
    assert finding.severity == Severity.WARNING
    model, *_ = _build(joined=True)
    # MUTATION: units.py drops `joined_ports(model)` from connected_ports (the connector warns)
    assert _codes(model, UNIT_CONNECTOR_DANGLING) == []


def test_the_current_graph_holds_a_plain_wire_for_the_join() -> None:
    """`raw_of` holds one `Wire` from the header port to the function port; the twin none."""
    model, first, second = _build(joined=True)
    # MUTATION: current_graph `raw_of` leaves out `port_joins(model)` (no wire)
    assert Wire(first, second) in raw_of(model).wires
    twin, *_ = _build(joined=False)
    assert raw_of(twin).wires == ()
