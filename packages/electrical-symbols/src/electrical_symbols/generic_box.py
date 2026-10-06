"""The labelled-box placeholder for a function with no matching symbol rule or choice.

A real toolkit symbol, not a consumer's private struct (decision layout-0042, D41).
"""

import math

from graphical_symbols.geometry import Direction, Point, Polyline
from graphical_symbols.model import Port, Reference, Slot, Status, Symbol, SymbolKind

# `SymbolGeometry.key` (`fransys_layout`) is this symbol's `reference.number`.
GENERIC_BOX_KEY = "generic-box"

# Geometry, in module units (M, DESIGN 6.1): a port every 2 M, a body 4 M tall and at least 4 M
# wide, and a 6 M x 1 M `tag` slot 0.5 M to the body's right.
_PORT_PITCH = 2.0
_BODY_HEIGHT = 4.0
_MIN_BODY_WIDTH = 4.0
_TAG_WIDTH = 6.0
_TAG_HEIGHT = 1.0
_TAG_GAP = 0.5
# R7 B3 (deep dive): a marking per port, E of its wire, just inside the body edge
_MARK_OFFSET_X = 0.25
_MARK_OFFSET_Y = 0.75
_MARK_WIDTH = 1.5


def _pitch(port_names: tuple[str, ...]) -> float:
    """R7 B3: the port pitch in whole M, wide enough for the longest marking beside its wire."""
    # A marking is the port name after the last "." (an item view names a port
    # `<function>.<port>`): about 0.65 M per character at the house text height, plus the
    # 0.25 M wire offset and a gap, rounded up to whole M so ports stay on the grid.
    longest = max((len(name.rsplit(".", 1)[-1]) for name in port_names), default=0)
    return float(max(_PORT_PITCH, math.ceil(0.65 * longest + 0.5)))


def generic_box(
    port_names: tuple[str, ...],
    sides: tuple[str, ...] = (),
    offsets: tuple[float, ...] = (),
) -> Symbol:
    """A labelled box with one port per name: N side (even index), S side (odd index).

    Args:
        port_names: Port names in drawing order (the caller sorts; this factory does not).
        sides: "n" or "s" per port, overriding the alternating rule (R7 C5); empty alternates.
        offsets: each port's x in M, one per name; empty runs each side at the pitch. The body
            then ends one pitch past the last offset (model-0129).

    Returns:
        A `Symbol` with `reference.number` `GENERIC_BOX_KEY`, a `tag` slot and `pole_pitch=None`.
    """
    pitch = _pitch(port_names)
    # R7 C5 (deep dive): `sides` ("n" or "s" per port) overrides the alternating rule; each
    # side's ports then run left to right at the pitch
    sides = sides or tuple("n" if i % 2 == 0 else "s" for i in range(len(port_names)))
    north = [name for name, side in zip(port_names, sides, strict=True) if side == "n"]
    south = [name for name, side in zip(port_names, sides, strict=True) if side == "s"]
    pairs = max(len(north), len(south))
    body_x = -_PORT_PITCH
    body_top = -_BODY_HEIGHT / 2
    body_bottom = body_top + _BODY_HEIGHT
    if offsets and len(offsets) != len(port_names):
        msg = f"offsets are one per port name, got {len(offsets)} for {len(port_names)}"
        raise ValueError(msg)
    body_width = max(
        _MIN_BODY_WIDTH, (max(offsets) + pitch - body_x) if offsets else pitch * pairs + pitch
    )
    body_right = body_x + body_width
    ports = tuple(
        Port(
            id=name,
            position=Point(
                x=offsets[i]
                if offsets
                else pitch * (north.index(name) if side == "n" else south.index(name)),
                y=body_top if side == "n" else body_bottom,
            ),
            direction=Direction.N if side == "n" else Direction.S,
        )
        for i, (name, side) in enumerate(zip(port_names, sides, strict=True))
    )
    outline = Polyline(
        points=(
            Point(body_x, body_top),
            Point(body_right, body_top),
            Point(body_right, body_bottom),
            Point(body_x, body_bottom),
        ),
        closed=True,
    )
    tag = Slot(
        id="tag",
        position=Point(x=body_right + _TAG_GAP, y=0),
        side=Direction.E,
        box=(_TAG_WIDTH, _TAG_HEIGHT),
    )
    marks = tuple(
        Slot(
            id=f"marking.{port.id}",
            position=Point(
                x=port.position.x + _MARK_OFFSET_X,
                y=port.position.y
                + (_MARK_OFFSET_Y if port.direction is Direction.N else -_MARK_OFFSET_Y),
            ),
            side=Direction.E,
            box=(_MARK_WIDTH, _TAG_HEIGHT),
        )
        for port in ports
    )
    return Symbol(
        name="Generic box",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference(standard="fransys", number=GENERIC_BOX_KEY),
        elements=(outline,),
        ports=ports,
        slots=(tag, *marks),
        pole_pitch=None,
    )
