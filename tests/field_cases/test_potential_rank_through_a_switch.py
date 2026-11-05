"""Field case: a 24 V DC supply feeding three lamps through two make-contact switches, with the lamps' other pins on a 0 V row.
The bug: a pin was ranked through the physical net, which stops at a switched link, so a pin behind a switch lost its rank.
Fixed by model-0121, a pin's rank follows the rail closure through conductive and switched links; power symbols keep the physical net."""

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BU

from fransys_model.derive import net_of, port_potential_rank, port_power_kind
from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab import PowerKind
from fransys_model.vocab.tables import functions, items, ports


def _build() -> fr.BuildResult:
    """Switch S0 feeds lamps P0 and P1 from 24 V, switch S1 feeds lamp P2; 0 V is a rail row."""
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        lamps = [d.device(f"P{i}", "DEMO-LAMP-24") for i in range(3)]
        switches = [d.device(f"S{i}", "DEMO-SWITCH-2P") for i in range(2)]
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 2).run("L", 2, bridged=True, rail=True)
        zero = d.terminal_strip("X2", "DEMO-TB-2.5", 3).run("L", 3, bridged=True, rail=True)
        d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
        for number, switch in enumerate(switches, start=1):
            d.series(live[number].outer, switch.sw["A"], wire=(BU, 0.5))
        d.series(switches[0].sw["B"], lamps[0].lamp["1"], wire=(BU, 0.5))
        d.series(switches[0].sw["B"], lamps[1].lamp["1"], wire=(BU, 0.5))
        d.series(switches[1].sw["B"], lamps[2].lamp["1"], wire=(BU, 0.5))
        for number, lamp in enumerate(lamps, start=1):
            d.series(lamp.lamp["2"], zero[number].outer, wire=(BU, 0.5))
    doc = unit_document(cab)
    return fr.build(d, doc)


def _port(model, tag: str, function: str, name: str):
    (item,) = (i for i in items(model).values() if i.tag == tag)
    (fn,) = (f for f in functions(model).values() if f.item == item.id and f.name == function)
    return next(p.id for p in ports(model).values() if p.function == fn.id and p.name == name)


def test_a_pin_behind_a_switch_ranks_as_its_rail() -> None:
    model = _build().model
    ahead = _port(model, "S0", "sw", "A")
    behind = _port(model, "S0", "sw", "B")
    lamp_pin = _port(model, "P0", "lamp", "1")
    assert port_potential_rank(model, ahead) is not None
    assert port_potential_rank(model, behind) == port_potential_rank(model, ahead)
    assert port_potential_rank(model, lamp_pin) == port_potential_rank(model, ahead)


def test_the_pin_ahead_of_the_switch_draws_a_bar_and_the_pins_behind_it_do_not() -> None:
    model = _build().model
    ahead = _port(model, "S0", "sw", "A")
    behind = _port(model, "S0", "sw", "B")
    lamp_pin = _port(model, "P0", "lamp", "1")
    assert net_of(model, ahead) != net_of(model, behind)  # the physical net stops at the switch
    assert port_power_kind(model, ahead) is PowerKind.SUPPLY
    assert port_power_kind(model, behind) is PowerKind.NONE
    bars = {s.port for s in layout_of(model, PowerSymbol).values() if s.symbol == "power-supply"}
    assert ahead in bars
    assert not bars & {behind, lamp_pin}
