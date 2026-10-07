"""The labelled-box placeholder for a function with no matching symbol rule or choice.

A real toolkit symbol, not a consumer's private struct (decision layout-0042, D41).
"""

import math

from graphical_symbols.geometry import Direction, Point, Polyline
from graphical_symbols.model import Port, Reference, Slot, Status, Symbol, SymbolKind

from electrical_symbols.box_ports import (
    G_PER_MODULE,
    GENERIC_BOX_KEY,
    NORTH,
    PORT_PITCH,
    SOUTH,
    box_port_marking,
    default_sides,
)
from electrical_symbols.text import text_width

# Geometry, in module units (M, DESIGN 6.1): a port every 2 M, a body 4 M tall and at least 4 M
# wide, and a 6 M x 1 M `tag` slot 0.5 M to the body's right.
_BODY_HEIGHT = 4.0
_MIN_BODY_WIDTH = 4.0
_TAG_WIDTH = 6.0
_TAG_HEIGHT = 1.0
_TAG_GAP = 0.5
# R7 B3 (deep dive): a marking per port, E of its wire, just inside the body edge
_MARK_OFFSET_X = 0.25
_MARK_OFFSET_Y = 0.75
_MARK_WIDTH = 1.5


def box_pitch(port_names: tuple[str, ...], stand: int = 0) -> float:
    """R7 B3: the port pitch in whole M: wide enough for the longest marking and for `stand`.

    A marking is the port name after the last "." (an item view names a port `<function>.<port>`),
    measured by the one text width at the house text height (1 M). `stand` is the width in G of
    the widest power symbol or its text standing at a port (layout-0132). Either, plus the 0.25 M
    wire offset and a gap, rounds up to whole M so ports stay on the grid.
    """
    longest = max(
        (text_width(box_port_marking(name), height=G_PER_MODULE) for name in port_names), default=0
    )
    return float(max(PORT_PITCH, math.ceil(max(longest, stand) / G_PER_MODULE + 0.5)))


def _ports(
    port_names: tuple[str, ...],
    sides: tuple[str, ...],
    offsets: tuple[float, ...],
    pitch: float,
) -> tuple[Port, ...]:
    """One port per name: at its offset, else its place in its side's row at the pitch."""
    if bad := sorted(set(sides) - {NORTH, SOUTH}):
        msg = f"sides are {NORTH!r} or {SOUTH!r}, got {bad[0]!r}"
        raise ValueError(msg)
    row = {
        side: [name for name, one in zip(port_names, sides, strict=True) if one == side]
        for side in set(sides)
    }
    top, bottom = -_BODY_HEIGHT / 2, _BODY_HEIGHT / 2
    return tuple(
        Port(
            id=name,
            position=Point(
                x=offsets[i] if offsets else pitch * row[side].index(name),
                y=top if side == NORTH else bottom,
            ),
            direction=Direction.N if side == NORTH else Direction.S,
        )
        for i, (name, side) in enumerate(zip(port_names, sides, strict=True))
    )


def _body_width(ports: tuple[Port, ...], plain: float, pairs: int, *, spread: bool) -> float:
    """The body's width: past the last port by the plain pitch when spread, else per row pair."""
    if not spread:
        return max(_MIN_BODY_WIDTH, plain * pairs + plain)
    return max(_MIN_BODY_WIDTH, max(p.position.x for p in ports) + plain + PORT_PITCH)


def _marks(ports: tuple[Port, ...]) -> tuple[Slot, ...]:
    """A `marking.<port>` slot per port, E of its wire and just inside the body."""
    return tuple(
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


def generic_box(
    port_names: tuple[str, ...],
    sides: tuple[str, ...] = (),
    offsets: tuple[float, ...] = (),
    stand: int = 0,
) -> Symbol:
    """A labelled box with one port per name: N side (even index), S side (odd index).

    Args:
        port_names: Port names in drawing order (the caller sorts; this factory does not).
        sides: "n" or "s" per port, overriding the alternating rule (R7 C5); empty alternates.
        offsets: each port's x in M, one per name; empty runs each side at the pitch. The body
            then ends one pitch past the last offset (model-0129).
        stand: the width in G of a power symbol or text standing at a port (layout-0132): the
            ports run at the pitch that fits it, the body keeps the plain pitch's margin.

    Returns:
        A `Symbol` with `reference.number` `GENERIC_BOX_KEY`, a `tag` slot and `pole_pitch=None`.
    """
    if offsets and len(offsets) != len(port_names):
        msg = f"offsets are one per port name, got {len(offsets)} for {len(port_names)}"
        raise ValueError(msg)
    plain = box_pitch(port_names)
    pitch = box_pitch(port_names, stand)
    # R7 C5 (deep dive): `sides` overrides the alternating rule; each side's ports then run
    # left to right at the pitch
    sides = sides or default_sides(len(port_names))
    pairs = max(sides.count(NORTH), len(sides) - sides.count(NORTH))
    body_x, body_top = -PORT_PITCH, -_BODY_HEIGHT / 2
    body_bottom = body_top + _BODY_HEIGHT
    ports = _ports(port_names, sides, offsets, pitch)
    body_right = body_x + _body_width(ports, plain, pairs, spread=bool(offsets) or pitch != plain)
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
    return Symbol(
        name="Generic box",
        kind=SymbolKind.SYMBOL,
        status=Status.UNVERIFIED,
        reference=Reference(standard="fransys", number=GENERIC_BOX_KEY),
        elements=(outline,),
        ports=ports,
        slots=(tag, *_marks(ports)),
        pole_pitch=None,
    )
