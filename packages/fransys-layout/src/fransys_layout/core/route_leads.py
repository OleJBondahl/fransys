"""Stage 6: the lead wire of a stub, one wiring step out of a pin no other pin joins (R481)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .outputs import Wire
from .route_env import Drawn, pin_point
from .sides import step_out

if TYPE_CHECKING:
    from .route_env import RouteEnv


def lead_wires(env: RouteEnv) -> Drawn:
    """A straight wire from each lead pin on this page to where its stub marker stands."""
    wires = []
    for pin, net in env.net_of.items():
        if pin not in env.leads:
            continue
        placed = env.placed.get(pin.sym)
        start = pin_point(env, pin.sym, pin.pin)
        side = None if placed is None else env.sides.get((pin.sym, pin.pin, placed.orient))
        if start is None or side is None:
            continue  # not on this page
        stop = step_out(side, *start, env.options.wiring_grid)
        wires.append(Wire(net, env.page, (start, stop), "straight"))
    return Drawn(wires=tuple(wires))
