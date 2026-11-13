"""The labelled-box placeholder for a function with no matching symbol rule or choice.

A real toolkit symbol, not a consumer's private struct (decision layout-0042).
"""

import math

from symdef import Direction, Point, Polyline, Port, Reference, Slot, Status, Symbol, SymbolKind

from electrical_symbols.box_ports import (
    G_PER_MODULE,
    GENERIC_BOX_KEY,
    NORTH,
    PORT_PITCH,
    SOUTH,
    default_sides,
    marking_slot,
)
from electrical_symbols.errors import SymbolsError

# Geometry, in module units (M, DESIGN 6.1): a port every 2 M, a body 4 M tall and at least 4 M
# wide, and a 6 M x 1 M `tag` slot 0.5 M to the body's right.
_BODY_HEIGHT = 4.0
_MIN_BODY_WIDTH = 4.0
_TAG_WIDTH = 6.0
_TAG_HEIGHT = 1.0
_TAG_GAP = 0.5
# A marking per port, E of its wire, just inside the body edge
_MARK_OFFSET_X = 0.25
_MARK_OFFSET_Y = 0.75
# A turned marking stands beside its wire (1 M wide, centred 0.75 M right) and starts 0.25 M inside the edge
_MARK_TURN_X = 0.75
_MARK_TURN_EDGE = 0.25


def box_pitch(marking_widths: tuple[int, ...]) -> float:
    """The port pitch in whole M: wide enough for the longest marking.

    `marking_widths` are the widths in G of each port's marking (`box_port_marking`: the name
    after the last "."), measured by the caller at the house text height (1 M). The longest,
    plus the 0.25 M wire offset and a gap, rounds up to whole M so ports stay on the grid.
    """
    return float(max(PORT_PITCH, math.ceil(max(marking_widths, default=0) / G_PER_MODULE + 0.5)))


def _ports(
    port_names: tuple[str, ...],
    sides: tuple[str, ...],
    offsets: tuple[float, ...],
    pitch: float,
    height: float,
) -> tuple[Port, ...]:
    """One port per name: at its offset, else its place in its side's row at the pitch."""
    if bad := set(sides) - {NORTH, SOUTH}:
        msg = f"sides are {NORTH!r} or {SOUTH!r}, got {min(bad)!r}"
        raise SymbolsError(msg)
    row = {side: [name for name, one in zip(port_names, sides, strict=True) if one == side] for side in set(sides)}
    top, bottom = -height / 2, height / 2
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


def _marks(ports: tuple[Port, ...], widths: tuple[int, ...], *, turn: bool) -> tuple[Slot, ...]:
    """A `marking.<port>` slot per port, as wide as its measured text (TEXT-BOX-MEASURED).

    Flat: E of its wire, just inside the body. Turned (PIN-MARK-PITCH): 1 M wide beside its wire, reading bottom-up along the body from its edge.
    """
    return tuple(_mark(port, width, turn=turn) for port, width in zip(ports, widths, strict=True))


def _mark(port: Port, width: int, *, turn: bool) -> Slot:
    north = port.direction is Direction.N
    x, edge = port.position.x, port.position.y
    if not turn:
        box, at, side = (
            (width / G_PER_MODULE, _TAG_HEIGHT),
            Point(x + _MARK_OFFSET_X, edge + (_MARK_OFFSET_Y if north else -_MARK_OFFSET_Y)),
            Direction.E,
        )
        return Slot(id=marking_slot(port.id), position=at, side=side, box=box)
    at = Point(x + _MARK_TURN_X, edge + (_MARK_TURN_EDGE if north else -_MARK_TURN_EDGE))
    side = Direction.S if north else Direction.N
    return Slot(id=marking_slot(port.id), position=at, side=side, box=(_TAG_HEIGHT, width / G_PER_MODULE), turn=True)


def _height(marking_widths: tuple[int, ...], *, turn: bool) -> float:
    """The body height: 4 M, or for turned markings room for one from each edge, in whole even M."""
    if not turn:
        return _BODY_HEIGHT
    return max(_BODY_HEIGHT, 2.0 * math.ceil(max(marking_widths, default=0) / G_PER_MODULE + 0.5))


def generic_box(
    port_names: tuple[str, ...],
    sides: tuple[str, ...] = (),
    offsets: tuple[float, ...] = (),
    *,
    marking_widths: tuple[int, ...],
    turn: bool = False,
) -> Symbol:
    """A labelled box with one port per name: N side (even index), S side (odd index).

    Args:
        port_names: Port names in drawing order (the caller sorts; this factory does not).
        sides: "n" or "s" per port, overriding the alternating rule; empty alternates.
        offsets: each port's x in M, one per name; empty runs each side at the pitch. The body
            then ends one pitch past the last offset (model-0129).
        marking_widths: the width in G of each port's marking, measured by the caller (the one
            text width); the pitch fits the longest.
        turn: the markings read bottom-up along the body, so the pitch is the plain one and the body grows to hold them.

    Returns:
        A `Symbol` with `reference.number` `GENERIC_BOX_KEY`, a `tag` slot and `pole_pitch=None`.
    """
    if offsets and len(offsets) != len(port_names):
        msg = f"offsets are one per port name, got {len(offsets)} for {len(port_names)}"
        raise SymbolsError(msg)
    pitch = box_pitch(() if turn else marking_widths)
    height = _height(marking_widths, turn=turn)
    # `sides` overrides the alternating rule; each side's ports then run
    # left to right at the pitch
    sides = sides or default_sides(len(port_names))
    pairs = max(sides.count(NORTH), len(sides) - sides.count(NORTH))
    body_x, body_top = -PORT_PITCH, -height / 2
    body_bottom = body_top + height
    ports = _ports(port_names, sides, offsets, pitch, height)
    body_right = body_x + _body_width(ports, pitch, pairs, spread=bool(offsets))
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
        reference=Reference(standard="generic", number=GENERIC_BOX_KEY),
        elements=(outline,),
        ports=ports,
        slots=(tag, *_marks(ports, marking_widths, turn=turn)),
        pole_pitch=None,
    )
