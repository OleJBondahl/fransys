"""Hand-written symbols for core tests: every view turned from one R0 view with symdef's `orient`.

The core holds no turn rule (SB4). A test that needs a symbol at several orientations builds
its views here, where symdef turns them; a test of the core's pick-and-move writes a `Turned`
by hand instead (test_views.py).
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

import symdef

from fransys_layout.core.sym_values import PinTurn, Sym, Turned
from fransys_layout.core.values import Box, Orientation, Pin

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

ALL_EIGHT: tuple[Orientation, ...] = ("R0", "R90", "R180", "R270", "MR0", "MR90", "MR180", "MR270")


def turn_box(box: Box, orient: Orientation) -> Box:
    """The box turned about the symbol origin by symdef's `orient_box` (ints, no unit change)."""
    corners = symdef.Box(symdef.Point(box.x, box.y), symdef.Point(box.x + box.w, box.y + box.h))
    turned = symdef.orient_box(corners, symdef.Orientation(orient))
    x, y = round(turned.min.x), round(turned.min.y)
    return Box(x, y, round(turned.max.x) - x, round(turned.max.y) - y)


def turn_pin(pin: Pin, orient: Orientation) -> PinTurn:
    """The pin's offset and facing turned by symdef's `orient_point` and `orient_direction`."""
    where = symdef.orient_point(symdef.Point(pin.dx, pin.dy), symdef.Orientation(orient))
    facing = symdef.orient_direction(symdef.Direction[pin.side], symdef.Orientation(orient))
    return PinTurn(round(where.x), round(where.y), facing.name)  # type: ignore[arg-type]


def turned(  # noqa: PLR0913, PLR0917 -- the R0 symbol's parts and the orient, as Sym holds them
    body: Box,
    keepout: Box,
    footprint: Box,
    pins: Iterable[Pin],
    row_footprint: Box | None,
    orient: Orientation,
) -> Turned:
    """One R0 view turned to orient."""
    return Turned(
        turn_box(body, orient),
        turn_box(keepout, orient),
        turn_box(footprint, orient),
        tuple(turn_pin(p, orient) for p in pins),
        None if row_footprint is None else turn_box(row_footprint, orient),
    )


def views_of(  # noqa: PLR0913, PLR0917 -- the R0 symbol's parts, as Sym holds them
    body: Box,
    keepout: Box,
    footprint: Box,
    pins: Iterable[Pin] = (),
    orients: Iterable[Orientation] = ("R0",),
    row_footprint: Box | None = None,
) -> Mapping[Orientation, Turned]:
    """The views of a symbol given at R0, one per orientation in orients."""
    held = tuple(pins)
    return frozendict(
        {o: turned(body, keepout, footprint, held, row_footprint, o) for o in orients}
    )


def marker_views(box: Box, orients: Iterable[Orientation] = ALL_EIGHT) -> Mapping[Orientation, Box]:
    """A marker symbol's keepout box at each orientation, for `Options.marker`."""
    return frozendict({o: turn_box(box, o) for o in orients})


def refit(sym: Sym, **changes: Any) -> Sym:
    """`replace` with the views rebuilt from the R0 geometry, at the same orientations.

    `body`, `keepout`, `footprint` and `row_footprint` are the R0 view's parts, not Sym fields.
    """
    flat = {
        k: changes.pop(k) for k in ("body", "keepout", "footprint", "row_footprint") if k in changes
    }
    new = replace(sym, **changes)
    views = views_of(
        flat.get("body", sym.body),
        flat.get("keepout", sym.keepout),
        flat.get("footprint", sym.footprint),
        new.pins,
        tuple(sym.views),
        flat.get("row_footprint", sym.row_footprint),
    )
    return replace(new, views=views)
