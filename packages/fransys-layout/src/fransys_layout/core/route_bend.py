"""Which side of its two pins' levels a jog's bend row stands on, from the way the pins face (layout-0541)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .route_env import pin_point

if TYPE_CHECKING:
    from .route_env import Jog, RouteEnv
    from .values import XY, Side


def _facing(env: RouteEnv, jog: Jog, point: XY) -> Side | None:
    """The side the jog's pin at `point` faces, None when the jog names no placed pin there; a placed pin `env.sides` lacks raises KeyError."""
    ref = next((r for r in jog.ends if pin_point(env, r.sym, r.pin) == point), None)
    placed = None if ref is None else env.placed.get(ref.sym)
    return None if ref is None or placed is None else env.sides[(ref.sym, ref.pin, placed.orient)]


def bend_side(env: RouteEnv, jog: Jog) -> int | None:
    """+1 when the bend row lies below both pins, -1 above both, 0 between them; None when the pins face away from each other.

    A wire leaves a pin along its facing: two south pins bend below the lower one, two north pins above the upper one.
    """
    top, bottom = _facing(env, jog, jog.top), _facing(env, jog, jog.bottom)
    return {("S", "S"): 1, ("N", "N"): -1, ("N", "S"): None}.get((top, bottom), 0)
