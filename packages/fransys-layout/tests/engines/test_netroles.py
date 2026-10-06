"""Roles and physical-net handles read from declared nets (engine.md 7, decision layout-0027)."""

from typing import TYPE_CHECKING

import pytest

from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.roles import ROLE_ORDER, physical_net, strongest
from fransys_layout.geometry import LayoutError
from fransys_layout.stages import Role
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.vocab import (
    Conductor,
    ConductorKind,
    FunctionKind,
    FunctionTemplate,
    Net,
    NetClass,
    Part,
    PartBundle,
    PartCategory,
    PartLibrary,
    Port,
    PortRole,
    PortTemplate,
    instantiate,
)

if TYPE_CHECKING:
    from fransys_layout.engines.schematic.read import StageInputs
    from fransys_model.kernel import Id, Record

_ORIGIN = Origin(file="tests/engines/test_netroles.py", line=1, note="net role tests")

type Ports = dict[tuple[str, str], Id[Port]]


def test_a_port_the_model_does_not_hold_has_no_physical_net() -> None:
    """Every port the engine reads comes from the model's own table: any other is a fault."""
    with pytest.raises(LayoutError):
        physical_net(freeze(Draft()), make_id(Port, ("nowhere",)))


def test_the_role_order_is_the_declaration_order_of_role() -> None:
    """The stages read `tuple(Role)` (columns, partition); the engine's order must agree."""
    assert tuple(Role) == ROLE_ORDER
    assert set(ROLE_ORDER) == set(Role)


@pytest.mark.parametrize(
    ("roles", "expected"),
    [
        ((Role.POWER, Role.CONTROL), Role.POWER),
        ((Role.CONTROL, Role.POWER), Role.POWER),
        ((Role.POWER, Role.SIGNAL), Role.POWER),
        ((Role.SIGNAL, Role.POWER), Role.POWER),
        ((Role.CONTROL, Role.SIGNAL), Role.CONTROL),
        ((Role.SIGNAL, Role.CONTROL), Role.CONTROL),
        ((Role.SIGNAL, Role.SIGNAL), Role.SIGNAL),
    ],
)
def test_strongest_prefers_power_then_control_then_signal(
    roles: tuple[Role, Role], expected: Role
) -> None:
    """Whatever the order the roles arrive in."""
    assert strongest(roles) is expected


def _cabinet() -> tuple[StageInputs, Ports, dict[str, Id[Net]]]:
    """Devices `k1` to `k3`, each one function `f` with pins `1` and `2` and no internal link.

    Nets: `pow` POWER on k1.1 and k2.1; `sig` SIGNAL on k1.1 and k2.2; `open` CONTROL on
    k3.1 and k3.2, with no conductor and nothing joining its two ports. Conductors: `a`
    k2.1 - k2.2; `b` k1.1 - k2.2, the two ports `sig` declares.
    """
    library = PartLibrary(
        id=make_id(PartLibrary, ("part_library", "invented")),
        key=("part_library", "invented"),
        name="invented",
        version="1.0.0",
    )
    part = Part(
        id=make_id(Part, ("device",)),
        key=("device",),
        mpn="EX-DEVICE",
        manufacturer="Example Co",
        description="Invented device",
        category=PartCategory.GENERIC,
        class_code="K",
        library=library.id,
    )
    template = FunctionTemplate(
        id=make_id(FunctionTemplate, ("device", "f")),
        key=("device", "f"),
        part=part.id,
        name="f",
        kind=FunctionKind.GENERIC,
    )
    pins = tuple(
        PortTemplate(
            id=make_id(PortTemplate, ("device", "f", pin)),
            key=("device", "f", pin),
            function=template.id,
            name=pin,
            role=PortRole.GENERIC,
        )
        for pin in ("1", "2")
    )
    bundle = PartBundle(
        part=part, function_templates=(template,), port_templates=pins, internal_links=()
    )
    records: list[Record] = [library, part, template, *pins]
    ports: Ports = {}
    for item in ("k1", "k2", "k3"):
        stamped = instantiate(
            bundle,
            (item,),
            tag=item.upper(),
            parent=None,
            description=part.description,
            installed=True,
        )
        records.extend(stamped)
        ports.update({(item, r.name): r.id for r in stamped if isinstance(r, Port)})
    net_ids = {name: make_id(Net, (name,)) for name in ("pow", "sig", "open")}
    nets = (
        Net(
            id=net_ids["pow"],
            key=("pow",),
            name="POW",
            net_class=NetClass.POWER,
            ports=(ports["k1", "1"], ports["k2", "1"]),
        ),
        Net(
            id=net_ids["sig"],
            key=("sig",),
            name="SIG",
            net_class=NetClass.SIGNAL,
            ports=(ports["k1", "1"], ports["k2", "2"]),
        ),
        Net(
            id=net_ids["open"],
            key=("open",),
            name="OPEN",
            net_class=NetClass.CONTROL,
            ports=(ports["k3", "1"], ports["k3", "2"]),
        ),
    )
    conductors = (
        Conductor(
            id=make_id(Conductor, ("a",)),
            key=("a",),
            a=ports["k2", "1"],
            b=ports["k2", "2"],
            kind=ConductorKind.WIRE,
            carrier=None,
        ),
        Conductor(
            id=make_id(Conductor, ("b",)),
            key=("b",),
            a=ports["k1", "1"],
            b=ports["k2", "2"],
            kind=ConductorKind.WIRE,
            carrier=None,
        ),
    )
    draft = Draft()
    draft.extend((*records, *nets, *conductors), origin=_ORIGIN)
    return read_inputs(freeze(draft)), ports, net_ids


def test_a_conductor_takes_the_strongest_role_of_its_two_ports() -> None:
    """`a` joins k2.1 (in the POWER net) and k2.2 (in the SIGNAL net): POWER."""
    inputs, _, _ = _cabinet()
    (connection,) = (c for c in inputs.connections if c.handle == make_id(Conductor, ("a",)))
    assert connection.role is Role.POWER


def test_a_conductor_along_a_net_takes_its_role_from_its_ports_not_from_that_net() -> None:
    """`b` runs between the two ports of `sig` (SIGNAL) but k1.1 is also in `pow`: POWER."""
    inputs, _, _ = _cabinet()
    (connection,) = (c for c in inputs.connections if c.handle == make_id(Conductor, ("b",)))
    assert connection.role is Role.POWER


def test_a_net_a_conductor_runs_along_still_has_its_net_group() -> None:
    """No conductor names a net, so no net is 'realised' away: `sig` keeps its group and role."""
    inputs, ports, net_ids = _cabinet()
    (group,) = (g for g in inputs.net_groups if g.net == net_ids["sig"])
    assert group.role is Role.SIGNAL
    assert {ref.port for ref in group.ports} == {ports["k1", "1"], ports["k2", "2"]}


def test_a_port_role_is_its_strongest_net_and_control_when_it_is_in_none() -> None:
    """k1.1 is in a POWER and a SIGNAL net: POWER. k1.2 is in no net: CONTROL."""
    inputs, ports, _ = _cabinet()
    role = {port.port: port.role for spec in inputs.functions for port in spec.ports}
    assert role[ports["k1", "1"]] is Role.POWER
    assert role[ports["k1", "2"]] is Role.CONTROL


def test_an_unrealised_net_group_takes_the_smallest_closure_handle_of_its_ports() -> None:
    """`open`'s two ports are joined by nothing, so each is a closure net of its own."""
    inputs, ports, net_ids = _cabinet()
    (group,) = (g for g in inputs.net_groups if g.net == net_ids["open"])
    low, high = sorted((ports["k3", "1"], ports["k3", "2"]))
    assert group.physical_net == low
    assert group.physical_net != high
    assert group.role is Role.CONTROL
