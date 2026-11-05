"""Stage 6: the lead wire of a reference marker that stands out from its pin, a straight run along the pin's facing (R481, R1333, R1400)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .geometry import marker_box
from .outputs import Wire
from .route_env import Drawn, pin_point
from .sides import SIDE_STEP, step_out
from .values import RefKind, StandClass

if TYPE_CHECKING:
    from .route_env import RouteEnv
    from .values import XY, PinRef, Side


def _stand(env: RouteEnv, pin: PinRef, start: XY, side: Side) -> XY | None:
    """The near edge of the box of a pin-stand marker of `pin` that stands out on the pin's line, else None.

    An arrow stands at its trunk end and has its own wire; a marker of any other stand class is not a pin stand (layout-0544).
    """
    dx, dy = SIDE_STEP[side]
    for m in (m for m in env.markers if m.end == pin and m.kind is not RefKind.ARROW and m.stand is StandClass.PIN):
        box = marker_box(m, env.options)
        near = (start[0] if dx == 0 else box.x + (0 if dx > 0 else box.w), start[1] if dy == 0 else box.y + (0 if dy > 0 else box.h))
        if (near[0] - start[0]) * dx + (near[1] - start[1]) * dy > 0:
            return near
    return None


def lead_wires(env: RouteEnv) -> Drawn:
    """A straight wire from each lead pin, and each pin whose marker stands off it, to where that marker stands."""
    wires = []
    for pin, net in env.net_of.items():
        placed = env.placed.get(pin.sym)
        start = pin_point(env, pin.sym, pin.pin)
        side = None if placed is None else env.sides.get((pin.sym, pin.pin, placed.orient))
        if start is None or side is None:
            continue  # not on this page
        stop = _stand(env, pin, start, side) or (step_out(side, *start, env.options.wiring_grid) if pin in env.leads else None)
        if stop is not None:
            wires.append(Wire(net, env.page, (start, stop), "straight"))
    return Drawn(wires=tuple(wires))
