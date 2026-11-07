"""`write_layout` writes one `layout.power_symbol` per drawn stand pin (el-0020, P1-P5)."""

from typing import TYPE_CHECKING

import fransys as fr
import pytest
from conventions_fixtures import house
from fransys.colours import BU
from fransys_el import (
    ProblemError,
    build,
    lay_out_drawn,
    placement_anchors,
    symbol_kit,
)
from symdef import Orientation as SymdefOrientation
from symdef import measure

from electrical_symbols import LIBRARY
from fransys_layout import Facing
from fransys_model.derive import port_power_text, stands
from fransys_model.layout import PowerSymbol, layout_of

if TYPE_CHECKING:
    from fransys_model.kernel import Model

KEYS = {"supply": "power-supply", "ground": "ground", "pe": "protective-earth"}


def _rails(*, loads: int) -> fr.Design:
    d = fr.design("demo_parts")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24").output)
    with d.function("CTRL", "Relay control"):
        for n in range(loads):
            s = d.device(f"S{n}", "DEMO-PB-NO")
            k = d.device(f"K{n}", "DEMO-RLY-2CO-24")
            d.series(dc.plus, s.sw, k.coil, dc.minus, wire=(BU, 0.75))
    return d


def _earth() -> fr.Design:
    d = fr.design("demo_parts")
    g1 = d.device("G1", "DEMO-PSU-24-PE")
    g2 = d.device("G2", "DEMO-PSU-24-PE")
    d.earth(g1.input["PE"], g2.input["PE"])
    return d


def _laid(design: fr.Design) -> tuple[Model, list[PowerSymbol]]:
    model = fr.build(design).model
    kit = symbol_kit(model, LIBRARY)
    problem, _ = build(model, kit, house(), LIBRARY)
    laid, *_ = lay_out_drawn(model, kit, problem, house(), LIBRARY)
    return model, list(layout_of(laid, PowerSymbol).values())


def test_each_kind_is_drawn_with_its_key_and_every_stand_port_gets_one() -> None:
    """P1, P2, P5: a load pin on the rail has one record too; no port has two."""
    for design in (_rails(loads=2), _earth()):
        model, records = _laid(design)
        kinds = stands(model)
        assert {r.port for r in records} == set(kinds)
        assert len(records) == len(kinds)
        assert {KEYS[kinds[r.port].value] for r in records} == {r.symbol for r in records}
        assert all(r.symbol == KEYS[kinds[r.port].value] for r in records)
    assert {r.symbol for r in _laid(_rails(loads=2))[1]} == {"power-supply", "ground"}
    assert {r.symbol for r in _laid(_earth())[1]} == {"protective-earth"}


def test_only_the_supply_prints_text() -> None:
    """P3: derive gives text for the supply and none for ground or PE."""
    for design in (_rails(loads=2), _earth()):
        model, records = _laid(design)
        for r in records:
            text = port_power_text(model, r.port)
            assert (text is not None) == (r.symbol == "power-supply")


def test_a_two_port_net_draws_no_power_symbol() -> None:
    """P4: one load between the rails is two-port nets, so nothing stands."""
    assert _laid(_rails(loads=1))[1] == []


def test_a_power_symbol_with_no_turn_facing_its_pin_refuses_with_the_fix() -> None:
    """A symbol whose port faces one way in every turn is refused naming the symbol and the fix."""
    one_way = dict.fromkeys(placement_anchors._TURNS, ("N", 0, 0))
    with pytest.raises(ProblemError, match=r"symbol 'ground' has no turn.*use a one-port symbol"):
        placement_anchors._pose("ground", Facing.N, 0, 1, ({}, one_way))  # a pin facing N needs a port facing S


def test_a_supply_pose_holds_the_box_symdef_measures_around_its_text_in_every_turn() -> None:
    """TEXT-BOX-MEASURED: the pose box of a supply bar is its keep-out with the rail's text measured in, so a long text widens it."""
    model, records = _laid(_rails(loads=2))
    port = next(r.port for r in records if r.symbol == "power-supply")
    plain = placement_anchors._keeps(model, "power-supply", port, LIBRARY, 8)
    text = port_power_text(model, port)
    assert text
    for turn, keep in plain.items():
        slot = measure(LIBRARY.get("power-supply"), SymdefOrientation[turn.name], LIBRARY, {"marking.supply": text}, 1.0).slots["marking.supply"]
        assert keep.x <= slot.min.x
        assert slot.max.x <= keep.x + keep.w
        assert keep.y <= slot.min.y
        assert slot.max.y <= keep.y + keep.h
