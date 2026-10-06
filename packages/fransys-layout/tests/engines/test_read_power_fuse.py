"""D5, step 6 (Q8): a port beyond a fuse is another physical net, with no symbol from the supply.

A supply `PSU` (port `24`) feeds a fuse `F1` (ports `in`, `out`) by one wire, and `F1.out` feeds a
load `PLC` (port `p24`) by another. Nothing wires `in` to `out`, so the supply side and the load
side are two physical nets. Only the supply side declares a potential. Every name is invented.
"""

from decimal import Decimal

from fransys_layout.engines.schematic.read.power import power_ends
from fransys_model.derive import port_power_kind
from fransys_model.kernel import Draft, Origin, freeze, make_id
from fransys_model.vocab import (
    Conductor,
    ConductorKind,
    Current,
    Function,
    FunctionKind,
    Item,
    Net,
    NetClass,
    Port,
    PortRole,
    PowerKind,
    Rail,
    SupplySystem,
)

_ORIGIN = Origin(file="tests/engines/test_read_power_fuse.py", line=1, note="Q8 fused side")
_PORTS = (("psu", "24"), ("f1", "in"), ("f1", "out"), ("plc", "p24"), ("lamp", "p24"))


def _port(item: str, name: str) -> Port:
    key = (item, "f", name)
    return Port(
        id=make_id(Port, key),
        key=key,
        function=make_id(Function, (item, "f")),
        template=None,
        name=name,
        role=PortRole.GENERIC,
    )


def _wire(key: str, a: Port, b: Port) -> Conductor:
    return Conductor(
        id=make_id(Conductor, (key,)),
        key=(key,),
        a=a.id,
        b=b.id,
        kind=ConductorKind.WIRE,
        carrier=None,
    )


def _net(key: str, port: Port, potential: str | None) -> Net:
    return Net(
        id=make_id(Net, (key,)),
        key=(key,),
        name=None,
        net_class=NetClass.GENERIC,
        ports=(port.id,),
        potential=potential,
    )


def test_a_port_beyond_a_fuse_gets_no_end_while_the_supply_side_does() -> None:
    """The supply side (`PSU.24`, `F1.in`) is a supply; `F1.out` and `PLC.p24` are none."""
    # UNDO: model `closure._adjacency`: also join the two ports of each fuse function `F1` (one net)
    ports = {f"{item}.{name}": _port(item, name) for item, name in _PORTS}
    records: list = []
    for item in ("psu", "f1", "plc", "lamp"):
        records += [
            Item(
                id=make_id(Item, (item,)),
                key=(item,),
                part=None,
                parent=None,
                position=None,
                tag=item.upper(),
                description="",
                installed=True,
            ),
            Function(
                id=make_id(Function, (item, "f")),
                key=(item, "f"),
                item=make_id(Item, (item,)),
                template=None,
                name="f",
                kind=FunctionKind.GENERIC,
            ),
        ]
    key = ("s",)
    records += [
        *ports.values(),
        _wire("w-in", ports["psu.24"], ports["f1.in"]),
        _wire("w-out", ports["f1.out"], ports["plc.p24"]),
        _wire("w-lamp", ports["psu.24"], ports["lamp.p24"]),  # a third port (V3)
        _net("rail24", ports["psu.24"], "24V"),
        _net("fused", ports["plc.p24"], None),
        SupplySystem(
            id=make_id(SupplySystem, key),
            key=key,
            name="s",
            current=Current.DC,
            rails=frozendict({"24V": Rail(max_v=Decimal(24), phase=None)}),
        ),
    ]
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    model = freeze(draft)
    ends = {one.port: one for one in power_ends(model)}
    supply_side = [ports["psu.24"].id, ports["f1.in"].id, ports["lamp.p24"].id]
    beyond = [ports["f1.out"].id, ports["plc.p24"].id]
    for port in supply_side:
        assert (ends[port].kind, ends[port].symbol) == ("supply", "power-supply")
        assert port_power_kind(model, port) is PowerKind.SUPPLY
    for port in beyond:
        assert port not in ends
        assert port_power_kind(model, port) is PowerKind.NONE
