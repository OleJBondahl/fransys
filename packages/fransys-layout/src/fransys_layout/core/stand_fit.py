"""The one fit test of a marker box: every keep, with the page and the row band as hard limits (R1331, R1333)."""

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

from .clearance import blocked, clear
from .geometry import inside
from .occupancy import cells_between
from .values import Box, Size

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from .clearance import Keep


class Limits(NamedTuple):
    """The hard limits of a marker box: the page `area` less a `margin` each side (OUT_OF_PAGE's `inside`) and the y-`band` of its row (R1333)."""

    area: Size
    band: tuple[int, int] | None = None
    margin: tuple[int, int] = (0, 0)


def _within(box: Box, limits: Limits) -> bool:
    """Whether `box` lies in the page less its `margin` on all four sides (closed once a margin is set) and in the row band."""
    (mx, my), (top, bottom) = limits.margin, limits.band or (box.y, box.y + box.h)
    shifted, room = Box(box.x - mx, box.y - my, box.w, box.h), Size(limits.area.w - 2 * mx, limits.area.h - 2 * my)
    return inside(shifted, room, edge="closed" if mx or my else "open") and top <= box.y and box.y + box.h <= bottom


def fit(
    box: Box,
    keeps: Sequence[Keep],
    own: Collection[str],
    limits: Limits | None,
    origin: tuple[int, int] | None = None,
) -> tuple[Keep, ...] | None:
    """None when `box` leaves the `limits`; else the keeps it hits, `()` when it fits.

    Keeps owned by `own` are skipped; a wire with an end at `origin` is the marker's own.
    """
    if limits and not _within(box, limits):
        return None
    return clear(box, keeps, {}, own=frozenset(own)) if origin is None else blocked(box, keeps, frozenset(own), origin)


def _across(k: Keep, run: Box) -> bool:
    """Whether the wire `k` runs across `run` (horizontal or vertical alike), not along it and not ending on it."""
    b = k.box
    if k.kind != "wire":
        return False
    if run.h == 0:
        return b.w == 0 and b.y < run.y < b.y + b.h
    return b.h == 0 and b.x < run.x < b.x + b.w


def _inside(k: Keep, end: tuple[int, int], grid: int) -> bool:
    """Whether `end` stands in a grid cell of the foreign wire `k`: Occupancy's end-cell rule, for either orientation."""
    b = k.box
    return k.kind == "wire" and (end[0] // grid, end[1] // grid) in cells_between((b.x, b.y), (b.x + b.w, b.y + b.h), grid)


def may_cross(run: Box, end: tuple[int, int], keeps: Sequence[Keep], own: Collection[str], grid: int) -> bool:
    """True when the run may be drawn to `end` (R1023): it meets only foreign wires across it, and `end` stands a cell clear of every foreign wire."""
    foreign = [k for k in keeps if k.owner not in own]
    if any(not _across(k, run) for k in clear(run, foreign, {})):
        return False
    return not any(_inside(k, end, grid) for k in foreign)
