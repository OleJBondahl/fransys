"""V3 (layout-0099): `read/rails.py` drops rail terminals and rail wires and names the pin ends.

Each case builds one invented circuit through the public API and reads it. The four cases pin the
rules from both sides: a bridged DC strip and a power pin pair are dropped, an unbridged strip and
an AC strip are kept as before.
"""

import fransys as fr
import fransys_author

from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.lint.codes import CONNECTION_TO_UNDRAWN


def _read(*, current: str, rails: dict, bridged: bool, strip: bool = True, pin_pair: bool = False):
    parts = fr.parts("demo_parts")
    d = fransys_author.Design(parts)
    d.supply("S", current=current, rails=rails)
    cab = d.location("CAB", "Cabinet")
    g = d.group("G", "Group")
    wire = d.wiring(colour="BU", gauge="0.5")
    lamps = [
        d.item("DEMO-LAMP-24", tag=f"P{i}", at=cab, group=g) for i in range(3 if pin_pair else 2)
    ]
    potential = next(iter(rails))
    if pin_pair:  # three pins: a physical net of two ports is a wire, not a rail (V3)
        wire(lamps[0]["1"], lamps[1]["1"])
        wire(lamps[1]["1"], lamps[2]["1"])
        d.net(potential, *(lamp["1"] for lamp in lamps), cls="power", potential=potential)
    if strip:
        x = d.strip("X1", at=cab)
        terminals = [
            x.terminal("DEMO-TB-2.5", f"T{i}", group=g) for i in range(3 if pin_pair else 2)
        ]
        for lamp, terminal in zip(lamps, terminals, strict=True):
            wire(lamp["1"], terminal.outer)
        if bridged:
            d.link(terminals[0].inner, terminals[1].inner, kind="rail")
        d.net(potential, *(t.outer for t in terminals), cls="power", potential=potential)
    return read_inputs(fr.build(parts, d.draft()).model)


def _codes(inputs) -> set[str]:
    return {f.code for f in inputs.read_findings}


def test_a_rail_terminal_leaves_the_page_and_its_wires_become_rail_ends() -> None:
    inputs = _read(current="dc", rails={"24V": ("24", None)}, bridged=True)
    assert [s.kind for s in inputs.functions] == ["load", "load"]
    assert inputs.connections == ()
    assert len(inputs.rail_ends) == 2
    assert CONNECTION_TO_UNDRAWN not in _codes(inputs)


def test_two_power_pins_wired_together_are_a_rail_wire() -> None:
    inputs = _read(
        current="dc", rails={"24V": ("24", None)}, bridged=False, strip=False, pin_pair=True
    )
    assert inputs.connections == ()
    assert len(inputs.rail_ends) == 4  # the middle pin ends both wires
    assert inputs.net_groups == ()


def test_a_terminal_that_is_not_bridged_is_drawn_and_its_wires_kept() -> None:
    inputs = _read(current="dc", rails={"24V": ("24", None)}, bridged=False)
    assert [s.kind for s in inputs.functions].count("terminal") == 2
    assert len(inputs.connections) == 2
    assert inputs.rail_ends == ()


def test_an_ac_rail_is_unchanged() -> None:
    inputs = _read(current="ac", rails={"L1": ("230", 0)}, bridged=True)
    assert [s.kind for s in inputs.functions].count("terminal") == 2
    assert len(inputs.connections) == 3  # two wires and the rail link, all kept
    assert inputs.rail_ends == ()
