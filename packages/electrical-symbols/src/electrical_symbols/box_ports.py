"""A generic box's ports: their names, order and sides, and the grid they stand on (D47).

Layout and render both draw the box from these, so a name, a side or a pitch has one spelling.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

# `SymbolGeometry.key` (`fransys_layout`) is the generic box's `reference.number`.
GENERIC_BOX_KEY = "generic-box"

G_PER_MODULE = 8  # grid units in one module unit (M, DESIGN 6.1): a G is 0.125 M
WIRING_GRID = 8  # G: ports and wire segments sit on multiples of this (the libraries' 1 M grid)
PORT_PITCH = 2.0  # M: a box's port every PORT_PITCH, and its body's left edge that far from pin 0
PORT_PITCH_G = int(PORT_PITCH * G_PER_MODULE)

NORTH, SOUTH = "n", "s"


def is_generic_box(key: str) -> bool:
    """Whether the symbol `key` is the labelled-box placeholder."""
    return key == GENERIC_BOX_KEY


def box_port_name(function: str, port: str) -> str:
    """An item view's box port: `<function>.<port>`, the one place that name is built."""
    return f"{function}.{port}"


def box_port_marking(name: str) -> str:
    """The marking printed beside a box port: `name` after the last `.` (an item view's port)."""
    return name.rsplit(".", 1)[-1]


def default_sides(count: int) -> tuple[str, ...]:
    """The sides `count` ports take when none are chosen: N, S, N, S, ... in drawing order."""
    return tuple(NORTH if i % 2 == 0 else SOUTH for i in range(count))


def draw_order(x: float, side: str) -> tuple[float, bool]:
    """A port's sort key in drawing order: left to right, N before S at one x."""
    return (x, side != NORTH)


def default_order(names: Iterable[str]) -> tuple[str, ...]:
    """The drawing order of box ports nobody ordered: by name (R7 B2)."""
    return tuple(sorted(names))
