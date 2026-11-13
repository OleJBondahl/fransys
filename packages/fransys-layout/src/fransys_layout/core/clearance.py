"""One clearance predicate: which keep boxes a probe box hits (layout-0394)."""

from __future__ import annotations

from fractions import Fraction
from typing import TYPE_CHECKING, Literal, NamedTuple

from .values import Box

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping, Sequence
    from collections.abc import Set as AbstractSet

    from .flow_values import Fan
    from .outputs import Placed


class Keep(NamedTuple):
    """A box to keep clear of; `node` is the y node it hangs on, "" means y is absolute.

    `port` is the owner's port point on a marker or anchor box: the one cell the owner may enter.
    `ends` are the two end points of the wire a segment keep belongs to; a wire ending at a marker's origin is its own (own_end).
    """

    node: str
    box: Box
    kind: str
    owner: str
    net: str | None = None
    port: tuple[int, int] | None = None
    ends: tuple[tuple[int, int], ...] = ()


def own_end(port: tuple[int, int], point: tuple[int, int]) -> bool:
    """True when `point` is the symbol's port point `port` (R535, layout-0395).

    The one test of where a wire of the owner's net may enter the owner's hard box: at its own port
    point only, never along the body. Test a wire's first or last point, not a point it passes.
    """
    return point == port


def closed_cells(box: Box, step: int = 1) -> tuple[range, range]:
    """The x and y cells a box covers on a `step` grid, far edges included (R535, layout-0395)."""
    return (
        range(box.x // step, (box.x + box.w) // step + 1),
        range(box.y // step, (box.y + box.h) // step + 1),
    )


def _shrunk(lo: int, size: int, *, open_: bool) -> tuple[int, int]:
    """One axis of a keep; "open" takes one off each side, but a thin keep keeps its true extent (layout-0523)."""
    return (lo + 1, size - 2) if open_ and size > 1 else (lo, size)


def _hits(probe: Box, k: Keep, top: int, *, open_: bool) -> bool:
    """Edges closed on both axes: touching counts as a hit, unless `open_`."""
    b = k.box
    (x, w), (y, h) = _shrunk(b.x, b.w, open_=open_), _shrunk(top, b.h, open_=open_)
    kx, ky = closed_cells(Box(x, y, w, h))
    px, py = closed_cells(probe)
    return kx.start < px.stop and px.start < kx.stop and ky.start < py.stop and py.start < ky.stop


def clear(
    probe: Box,
    keeps: Sequence[Keep],
    y: Mapping[str, int],
    *,
    edge: Literal["closed", "open", "tags"] = "closed",
    own: AbstractSet[str] = frozenset(),
) -> tuple[Keep, ...]:
    """The keeps the probe hits, in input order; keeps owned by `own` are skipped.

    "open" lets touching edges clear (a thin keep keeps its extent); "tags" does so for a marker box only (layout-0591).
    """
    return tuple(
        k
        for k in keeps
        if k.owner not in own
        and _hits(probe, k, k.box.y + (y[k.node] if k.node else 0), open_=edge == "open" or (edge == "tags" and k.kind == "marker"))
    )


def blocked(box: Box, keeps: Sequence[Keep], own: frozenset[str], origin: tuple[int, int]) -> tuple[Keep, ...]:
    """The keeps `box` hits, but not a wire with an end at the marker's origin: that wire is the marker's own (own_end)."""
    return tuple(k for k in clear(box, keeps, {}, own=own, edge="tags") if not any(own_end(origin, e) for e in k.ends))


def _clip(lo: Fraction, hi: Fraction, p: int, q: int) -> tuple[Fraction, Fraction] | None:
    """Narrow the parameter span [lo, hi] of a segment by one box side (Liang-Barsky): None when it lies outside that side."""
    if p == 0:
        return (lo, hi) if q >= 0 else None
    r = Fraction(q, p)
    return (max(lo, r), hi) if p < 0 else (lo, min(hi, r))


def _meets(a: tuple[int, int], b: tuple[int, int], box: Box) -> bool:
    """True when the segment a-b has a positive-length part in the closed `box`; a corner or point touch has none."""
    span: tuple[Fraction, Fraction] | None = (Fraction(0), Fraction(1))
    (x1, y1), (x2, y2) = a, b
    for p, q in ((x1 - x2, x1 - box.x), (x2 - x1, box.x + box.w - x1), (y1 - y2, y1 - box.y), (y2 - y1, box.y + box.h - y1)):
        span = span and _clip(*span, p, q)
    return span is not None and span[0] < span[1]


def through(a: tuple[int, int], b: tuple[int, int], box: Box, ends: tuple[tuple[int, int], ...], pins: Iterable[tuple[int, int]]) -> bool:
    """True when the wire run a-b (a wire with `ends`) passes the body `box`: through its interior or along its outline, at any angle.

    A zero-length touch is looks, and so is an edge run only at the run's own end pin (R1135, R1164); `pins` are the body's pin points.
    """
    if not _meets(a, b, box):
        return False
    x0, x1 = max(min(a[0], b[0]), box.x), min(max(a[0], b[0]), box.x + box.w)
    y0, y1 = max(min(a[1], b[1]), box.y), min(max(a[1], b[1]), box.y + box.h)
    edge = (x0 == x1 and x0 in (box.x, box.x + box.w)) or (y0 == y1 and y0 in (box.y, box.y + box.h))
    return not (edge and (hit := [p for p in pins if x0 <= p[0] <= x1 and y0 <= p[1] <= y1]) and all(p in ends for p in hit))


def through_keeps(
    probe: Box, keeps: Sequence[Keep], ends: tuple[tuple[int, int], ...], own: frozenset[str], pins: Mapping[str, Sequence[tuple[int, int]]]
) -> tuple[Keep, ...]:
    """The keeps a wire run (`probe`, with the wire's `ends`) passes; `pins` maps a body's owner to its pin points.

    Own footprints are skipped, never a body (R533); a body is met as `through` says.
    """
    a, b = (probe.x, probe.y), (probe.x + probe.w, probe.y + probe.h)
    return tuple(
        k for k in clear(probe, keeps, {}) if (k.owner not in own if k.kind != "body" else through(a, b, k.box, ends, pins.get(k.owner, ())))
    )


def reach(pin_y: int, keeps: Iterable[Keep], side: str, gap: int, kind: str | None = None) -> int:
    """Distance from a pin to the far edge of the farthest keep on `side`, plus gap; 0 for none.

    `kind` limits the keeps read to those of that kind (R510 reads the anchors only).
    """
    below = side == "below"
    far = [max(0, k.box.y + k.box.h - pin_y) if below else max(0, pin_y - k.box.y) for k in keeps if kind in (None, k.kind)]
    return max(far) + gap if far else 0


def fan_own(fan: Fan, columns: Iterable[Iterable[str]] = ()) -> frozenset[str]:
    """The symbols a fan attaches to (R515), plus the cells of any `columns` given."""
    return frozenset(a.pin.sym for a in (*fan.drivers, *fan.legs)).union(*map(frozenset, columns))


def footprint_keeps(cells: Iterable[tuple[str, str]], box: Box) -> Iterator[Keep]:
    """One footprint keep of `box` for each (y node, owner symbol) of `cells` (layout-0395)."""
    for node, owner in cells:
        yield Keep(node, box, "footprint", owner)


def pin_points(placed: Mapping[str, Placed]) -> dict[str, tuple[tuple[int, int], ...]]:
    """Each placed symbol's pin points (`Placed.pin_xy`), for `through` (R1239)."""
    return {s: tuple((q.x, q.y) for q in p.pin_xy) for s, p in placed.items()}
