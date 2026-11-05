"""Decision model-0344: the sides a box's power decides (supply N, ground S, a wired supply all N).

Built from `examples/demo-parts` only. Can-fail probes: raise `_POTENTIALS` to 3 and the wired
supply test fails; put a ground pin on N and the symbol-pin test fails; make a supply pin "s" and
"""

import fransys as fr
import pytest
from fransys.colours import BU

from fransys_model.derive import pinned_box_sides
from fransys_model.vocab.tables import functions, items, ports


def _model() -> fr.Model:
    """Box A1 has only power pins (P on 24 V, M on 0 V); A2 has those and a loose pin S."""
    d = fr.design("demo_parts")
    with d.function("G", "Group"):
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 2).run("L", 2, bridged=True, rail=True)
        zero = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("L", 2, bridged=True, rail=True)
        d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
        only = d.device("A1", None, pins=("P", "M"), external=True)
        mixed = d.device("A2", None, pins=("P", "M", "S"), external=True)
        d.series(live[1].outer, only["P"], wire=(BU, 0.5))
        d.series(zero[1].outer, only["M"], wire=(BU, 0.5))
        d.series(live[2].outer, mixed["P"], wire=(BU, 0.5))
        d.series(zero[2].outer, mixed["M"], wire=(BU, 0.5))
    return fr.build(d).model


def _supply_model() -> fr.Model:
    """A 24 V PSU whose + and - are each one wire to a lamp: two-port nets, not rails."""
    d = fr.design("demo_parts")
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        d.dc_supply("S", psu)
        lamp = d.device("H1", "DEMO-LAMP-24")
        d.series(psu.output["+"], lamp.lamp["1"], wire=(BU, 0.5))
        d.series(psu.output["-"], lamp.lamp["2"], wire=(BU, 0.5))
    return fr.build(d).model


def _heater_model() -> fr.Model:
    """The SO7 probe: a heater whose only pins are + and -, wired to a PSU."""
    d = fr.design("demo_parts")
    with d.function("G", "Group"):
        psu = d.device("T1", "DEMO-PSU-24")
        d.dc_supply("S", psu)
        heater = d.device("H1", "DEMO-HEATER-24")
        d.series(psu.output["+"], heater["+"], wire=(BU, 0.5))
        d.series(psu.output["-"], heater["-"], wire=(BU, 0.5))
    return fr.build(d).model


def _signal_model() -> fr.Model:
    """A3 has two loose pins on no power net."""
    d = fr.design("demo_parts")
    with d.function("G", "Group"):
        d.device("A3", None, pins=("X", "Y"), external=True)
    return fr.build(d).model


def _sides(model: fr.Model, tag: str) -> dict[str, str | None]:
    """The pinned side of each port of the item `tag`, by port name."""
    (item,) = (i for i in items(model).values() if i.tag == tag)
    own = [p for p in ports(model).values() if functions(model)[p.function].item == item.id]
    found = pinned_box_sides(model, [p.id for p in own])
    return {p.name: found[p.id] for p in own}


@pytest.mark.rule("CROSS-HALF-TAGS")
def test_a_box_of_power_pins_only_has_every_pin_on_n() -> None:
    """Class: all-power boxes stand every pin on N; mixed and signal-only keep theirs."""
    model = _model()
    assert _sides(model, "A1") == {"P": "n", "M": "n"}
    assert _sides(model, "A2") == {"P": "n", "M": "s", "S": None}
    assert _sides(_heater_model(), "H1") == {"+": "n", "-": "n"}
    assert set(_sides(_signal_model(), "A3").values()) == {None}


def test_a_supply_with_each_pin_on_a_wire_has_both_on_n() -> None:
    model = _supply_model()
    (output,) = (f for f in functions(model).values() if f.name == "output")
    found = pinned_box_sides(model, [p.id for p in ports(model).values() if p.function == output.id])
    assert set(found.values()) == {"n"}
    assert len(found) == 2


def test_a_box_with_a_signal_pin_keeps_supply_n_and_ground_s() -> None:
    assert _sides(_model(), "A2") == {"P": "n", "M": "s", "S": None}
