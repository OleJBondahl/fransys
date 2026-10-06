"""`derive.is_rail_terminal`: a terminal on a DC rail or PE net, bridged within its strip (0118)."""

from plant import Plant
from query_builders import Terminal, make_terminal
from rating_plant import rail, supply

from fransys_model.derive import is_rail_terminal
from fransys_model.kernel import make_id
from fransys_model.vocab import Net, NetClass
from fransys_model.vocab.enums import ConductorKind, Current

_DC24 = {"24V": rail("24"), "0V": rail("0")}


def _strip(
    rails: dict | None,
    current: Current = Current.DC,
    bridge: ConductorKind | None = ConductorKind.JUMPER,
) -> tuple[Plant, Terminal, Terminal]:
    """Strip `x1`, terminals `t1`, `t2` on one net; `bridge` joins them (rails None: no supply)."""
    plant = Plant()
    if rails is not None:
        supply(plant, "main", rails, current=current)
    plant.item("x1", designation="X1")
    t1 = make_terminal(plant, "x1", "t1", group="P", index=1)
    t2 = make_terminal(plant, "x1", "t2", group="P", index=2)
    potential = "24V" if current is Current.DC else "L1"
    plant.net("rail", (t1.external, t2.external), potential=potential if rails else None)
    if bridge is not None:
        plant.wire(t1.internal, t2.internal, key="bridge", kind=bridge)
    return plant, t1, t2


def test_a_bridged_terminal_on_a_dc_rail_is_a_rail_terminal() -> None:
    plant, t1, t2 = _strip(_DC24)
    model = plant.model()
    assert is_rail_terminal(model, t1.item)
    assert is_rail_terminal(model, t2.item)


def test_a_rail_link_bridges_like_a_jumper() -> None:
    plant, t1, _ = _strip(_DC24, bridge=ConductorKind.RAIL)
    assert is_rail_terminal(plant.model(), t1.item)


def test_an_unbridged_terminal_on_a_dc_rail_is_not() -> None:
    plant, t1, _ = _strip(_DC24, bridge=None)
    assert not is_rail_terminal(plant.model(), t1.item)


def test_a_bridged_terminal_on_an_ac_rail_is_not() -> None:
    plant, t1, _ = _strip({"L1": rail("230", 0), "N": rail("0")}, current=Current.AC)
    assert not is_rail_terminal(plant.model(), t1.item)


def test_a_bridged_terminal_on_a_pe_net_is_one() -> None:
    plant, t1, t2 = _strip(None)
    assert not is_rail_terminal(plant.model(), t1.item)
    pe = Net(
        id=make_id(Net, ("pe",)),
        key=("pe",),
        name=None,
        net_class=NetClass.PE,
        ports=(t1.internal, t2.internal),
    )
    plant.add(pe)
    assert is_rail_terminal(plant.model(), t1.item)


def test_a_bridged_terminal_on_no_rail_and_a_non_terminal_are_not() -> None:
    plant, _, _ = _strip(_DC24)
    strip = plant.item("other", designation="Y1")
    a = make_terminal(plant, "other", "a", group="Q", index=1)
    b = make_terminal(plant, "other", "b", group="Q", index=2)
    plant.wire(a.internal, b.internal, key="obridge", kind=ConductorKind.JUMPER)
    model = plant.model()
    assert not is_rail_terminal(model, a.item)
    assert not is_rail_terminal(model, strip)
