"""Field case: a pin behind a switch carries its rail's rank but draws no power bar.

The engineering shape: a 24 V DC supply feeds three lamps through two make-contact switches, one
switch feeding two lamps. Each switch's input is wired to a rail terminal row on 24 V, its output
to the lamps, and the lamps' other pins to a 0 V row.

The bug: a pin was ranked through the physical net, which stops at a switched link, so a pin
behind a switch (a lamp, a box pin) lost its rank and its place beside the supply pins.

The rule (CONVENTIONS-V06 V11, decision model-0121): a pin's rank follows the rail closure through
CONDUCTIVE and SWITCHED links, so the pin behind the switch ranks as 24 V. Power-symbol eligibility
(V3) keeps the physical net: the switch's output is not on the 24 V net while the contact is open,
so it draws no 24 V bar.
"""

import fransys as fr
from fransys.colours import BU

from fransys_layout.engines.schematic.read import read_inputs
from fransys_model.derive import net_of, port_potential_rank, port_power_kind
from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab import PowerKind
from fransys_model.vocab.tables import functions, items, ports


def _build(tmp_path) -> fr.BuildResult:
    """Switch S0 feeds lamps P0 and P1 from 24 V, switch S1 feeds lamp P2; 0 V is a rail row."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        lamps = [d.device(f"P{i}", "DEMO-LAMP-24") for i in range(3)]
        switches = [d.device(f"S{i}", "DEMO-SWITCH-2P") for i in range(2)]
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 2).run("L", 2, bridged=True)
        zero = d.terminal_strip("X2", "DEMO-TB-2.5", 3).run("L", 3, bridged=True)
        d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
        for number, switch in enumerate(switches, start=1):
            d.wire(live[number].outer, switch.sw["A"], wire=(BU, 0.5))
        d.wire(switches[0].sw["B"], lamps[0].lamp["1"], wire=(BU, 0.5))
        d.wire(switches[0].sw["B"], lamps[1].lamp["1"], wire=(BU, 0.5))
        d.wire(switches[1].sw["B"], lamps[2].lamp["1"], wire=(BU, 0.5))
        for number, lamp in enumerate(lamps, start=1):
            d.wire(lamp.lamp["2"], zero[number].outer, wire=(BU, 0.5))
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def _port(model, tag: str, function: str, name: str):
    (item,) = (i for i in items(model).values() if i.tag == tag)
    (fn,) = (f for f in functions(model).values() if f.item == item.id and f.name == function)
    return next(p.id for p in ports(model).values() if p.function == fn.id and p.name == name)


def test_a_pin_behind_a_switch_ranks_as_its_rail(tmp_path) -> None:
    model = _build(tmp_path).model
    ahead = _port(model, "S0", "sw", "A")
    behind = _port(model, "S0", "sw", "B")
    lamp_pin = _port(model, "P0", "lamp", "1")
    assert port_potential_rank(model, ahead) is not None
    assert port_potential_rank(model, behind) == port_potential_rank(model, ahead)
    assert port_potential_rank(model, lamp_pin) == port_potential_rank(model, ahead)
    assert {s.port: s.rank for f in read_inputs(model).functions for s in f.ports}[
        behind
    ] == port_potential_rank(model, ahead)


def test_the_pin_ahead_of_the_switch_draws_a_bar_and_the_pins_behind_it_do_not(tmp_path) -> None:
    model = _build(tmp_path).model
    ahead = _port(model, "S0", "sw", "A")
    behind = _port(model, "S0", "sw", "B")
    lamp_pin = _port(model, "P0", "lamp", "1")
    assert net_of(model, ahead) != net_of(model, behind)  # the physical net stops at the switch
    assert port_power_kind(model, ahead) is PowerKind.SUPPLY
    assert port_power_kind(model, behind) is PowerKind.NONE
    bars = {s.port for s in layout_of(model, PowerSymbol).values() if s.symbol == "power-supply"}
    assert ahead in bars
    assert not bars & {behind, lamp_pin}
