"""D5, step 6 (B2a): `read` tells, for every port on a power net, its symbol key and its text.

A power supply `PSU` (ports `24`, `0`) feeds a load `PLC` (ports `p24`, `p0`, `q24`, `q0`, `pe`)
by two wires each, so that each rail has three ports and distributes (V3), with the supply
declared by `_model`. Every net is invented; nothing names a real plant.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.power import power_ends
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
    Rail,
    SupplySystem,
)

if TYPE_CHECKING:
    from fransys_layout.stages.types import PowerEnd

_ORIGIN = Origin(file="tests/engines/test_read_power.py", line=1, note="D5 power ends")


def _rails(current: Current) -> dict[str, Rail]:
    """24 V and 0 V; an AC rail needs a phase."""
    phase = 0 if current is Current.AC else None
    return {"24V": Rail(max_v=Decimal(24), phase=phase), "0V": Rail(max_v=Decimal(0), phase=None)}


def _item(key: str) -> Item:
    return Item(
        id=make_id(Item, (key,)),
        key=(key,),
        part=None,
        parent=None,
        position=None,
        tag=key.upper(),
        description="",
        installed=True,
    )


def _function(item: str) -> Function:
    return Function(
        id=make_id(Function, (item, "f")),
        key=(item, "f"),
        item=make_id(Item, (item,)),
        template=None,
        name="f",
        kind=FunctionKind.GENERIC,
    )


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


def _net(
    key: str, port: Port, *, potential: str | None = None, name: str | None = None, pe: bool = False
) -> Net:
    return Net(
        id=make_id(Net, (key,)),
        key=(key,),
        name=name,
        net_class=NetClass.PE if pe else NetClass.GENERIC,
        ports=(port.id,),
        potential=potential,
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


def _records(
    current: Current | None, *, net_name: str | None = None
) -> tuple[list, dict[str, Port]]:
    """The plant's records, and its ports by `item.name`; `current` `None` declares no supply."""
    names = (
        ("psu", "24"),
        ("psu", "0"),
        ("plc", "p24"),
        ("plc", "p0"),
        ("plc", "pe"),
        ("plc", "q24"),
        ("plc", "q0"),
    )
    ports = {f"{item}.{name}": _port(item, name) for item, name in names}
    records: list = [_item(i) for i in ("psu", "plc")]
    records += [_function(i) for i in ("psu", "plc")]
    records += [
        *ports.values(),
        _wire("w24", ports["psu.24"], ports["plc.p24"]),
        _wire("w0", ports["psu.0"], ports["plc.p0"]),
        _wire("w24b", ports["psu.24"], ports["plc.q24"]),  # a third port: a rail (V3)
        _wire("w0b", ports["psu.0"], ports["plc.q0"]),
        _net("rail24", ports["psu.24"], potential="24V", name=net_name),
        _net("rail0", ports["psu.0"], potential="0V"),
        _net("earth", ports["plc.pe"], pe=True),
    ]
    if current is not None:
        rails = frozendict(_rails(current))
        key = ("s",)
        records.append(
            SupplySystem(
                id=make_id(SupplySystem, key), key=key, name="s", current=current, rails=rails
            )
        )
    return records, ports


def _power(current: Current | None, *, net_name: str | None = None) -> dict[str, PowerEnd]:
    """The `PowerEnd` of each port by `item.name`, a port with none missing."""
    records, ports = _records(current, net_name=net_name)
    draft = Draft()
    draft.extend(records, origin=_ORIGIN)
    model = freeze(draft)
    assert read_inputs(model).power == power_ends(model)
    ends = {one.port: one for one in power_ends(model)}
    return {key: ends[port.id] for key, port in ports.items() if port.id in ends}


def _shape(end: PowerEnd) -> tuple[str, str, str | None]:
    return end.kind, end.symbol, end.text


def test_ports_of_a_dc_supply_get_the_supply_ground_and_earth_symbols() -> None:
    """24 V is the bar and prints its potential; 0 V is ground and PE is earth, both print none."""
    # UNDO: read/power.py `_SYMBOLS`: PowerKind.GROUND -> "power-supply" (the 0 V net: wrong key)
    ends = _power(Current.DC)
    assert _shape(ends["psu.24"]) == ("supply", "power-supply", "24V")
    assert _shape(ends["psu.0"]) == ("ground", "ground", None)
    assert _shape(ends["plc.pe"]) == ("pe", "protective-earth", None)


def test_a_load_pin_wired_to_the_supply_takes_its_end_though_no_net_lists_it() -> None:
    """`PLC` `p24` and `p0` are on no declared `Net`; their conductors reach the rails."""
    # UNDO: read/power.py `power_ends`: `physical.ports` -> `(port,)` (only the listed ports)
    ends = _power(Current.DC)
    assert _shape(ends["plc.p24"]) == _shape(ends["psu.24"])
    assert _shape(ends["plc.p0"]) == _shape(ends["psu.0"])


def test_a_net_name_is_the_text_before_the_potential() -> None:
    # UNDO: read/power.py `power_ends`: `power_text(model, net.id)` -> `net.potential`
    assert _power(Current.DC, net_name="+24")["psu.24"].text == "+24"


def test_an_ac_supply_and_no_supply_give_no_end_but_earth() -> None:
    """LD8: AC rails get references; a net in no declared supply gets references; PE needs none."""
    # UNDO: model `_potential_kind`: `supply.current is not Current.DC` -> `False` (AC: ends)
    for current in (Current.AC, None):
        ends = _power(current)
        assert set(ends) == {"plc.pe"}
