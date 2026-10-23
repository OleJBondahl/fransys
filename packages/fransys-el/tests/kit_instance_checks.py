"""What the kit must hold for any model it draws: one pick per drawn view row (el-0014)."""

from typing import TYPE_CHECKING

from conventions_fixtures import house
from fransys_el import build, lay_out, symbol_kit

from electrical_symbols import LIBRARY
from fransys_model.derive import (
    connected_ports,
    connector_pin_views,
    pole_gangs,
    schematic_functions,
)
from fransys_model.vocab import FunctionKind, functions

if TYPE_CHECKING:
    from fransys_el import SymbolKit

    from fransys_model.kernel import Model

__all__ = ["built", "check_channels", "check_gangs", "check_pins", "laid_out"]


def built(model: Model) -> SymbolKit:
    """The kit of `model`, after `fransys_el.build` took it: no `ProblemError`."""
    kit = symbol_kit(model, LIBRARY)
    build(model, kit, house(), LIBRARY)
    return kit


def check_pins(model: Model, kit: SymbolKit) -> int:
    """The port-keyed picks are the drawn rows of `connector_pin_views`; returns their count."""
    rows = connector_pin_views(model, frozenset(), connected_ports(model))
    drawn = {row.port for row in rows if row.drawn}
    assert {k for k in kit if k.kind == "port"} == drawn
    return len(drawn)


def check_channels(model: Model, kit: SymbolKit) -> int:
    """Every PLC channel is a pick or a member of one; returns the channel count."""
    held = {m for pick in kit.values() for m in pick.members}
    channels = [
        f
        for f in schematic_functions(model)
        if functions(model)[f].kind is FunctionKind.PLC_CHANNEL
    ]
    assert {f for f in channels if f in kit or f in held} == set(channels)
    return len(channels)


def check_gangs(model: Model, kit: SymbolKit) -> int:
    """Each pole gang's lead holds the other members; returns the gang count."""
    gangs = pole_gangs(model, frozenset(schematic_functions(model)))
    for gang in gangs:
        assert kit[gang.lead].members == gang.members[1:]
    return len(gangs)


def laid_out(model: Model, kit: SymbolKit) -> int:
    """`lay_out` writes the instance's layout: every scope and table read takes a pin's key."""
    conventions = house()
    problem, _ = build(model, kit, conventions, LIBRARY)
    laid, _ = lay_out(model, kit, problem, conventions, LIBRARY)
    assert laid is not model
    return len(problem.symbols)
