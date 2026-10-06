"""A generic box's pin x: a fixed channel pitch, widened by the texts of each pin's contact (V5)."""

from typing import TYPE_CHECKING

from fransys_model.kernel import value

from .units import TEXT_GAP, snap_up

if TYPE_CHECKING:
    from collections.abc import Mapping


@value
class Row:
    """One text or body of a pin's contact: its height span and its reach either side of the pin."""

    top: int
    bottom: int
    left: int
    right: int


@value
class Reach:
    """One box pin's attached contact, as the rows it fills below the pin, in G."""

    name: str
    rows: tuple[Row, ...] = ()


def _need(left: Reach, right: Reach) -> int:
    """The x distance two pins need: the widest same-height pair of their rows plus the text gap."""
    need = 0
    for a in left.rows:
        for b in right.rows:
            if a.top < b.bottom and b.top < a.bottom:  # the two texts share a height
                need = max(need, a.right + TEXT_GAP + b.left)
    return need


def spread(
    base: Mapping[str, tuple[str, int]], reach: tuple[Reach, ...], pitch: int
) -> dict[str, int]:
    """Each side's pins left to right: `pitch` apart, and clear of every earlier pin's text rows."""
    room = {one.name: one for one in reach}
    placed = {name: x for name, (_, x) in base.items()}
    for side in sorted({side for side, _ in base.values()}):
        names = sorted((n for n in base if base[n][0] == side), key=lambda n: base[n][1])
        if not any(name in room for name in names):
            continue
        for at, name in enumerate(names[1:], 1):
            wanted = [placed[names[at - 1]] + pitch]
            wanted += [
                placed[o] + _need(room[o], room[name])
                for o in names[:at]
                if o in room and name in room
            ]
            placed[name] = int(snap_up(max(wanted)))
    return placed


def extent(pins: Mapping[str, int], reach: tuple[Reach, ...]) -> tuple[int, int]:
    """V5: the x span of a box's pins and the rows hung under them; keep-out and fit read it."""
    low = min(pins.values())
    high = max(pins.values())
    for one in reach:
        for row in one.rows:
            low = min(low, pins[one.name] - row.left)
            high = max(high, pins[one.name] + row.right)
    return low, high
