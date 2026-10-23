"""The annex stage: boxes printed beside a placed symbol, set after the symbols and wires (R345).

An `Annex` is a box of known size with named spots relative to its owner's placed body. The stage
takes the first spot that is free of every body, anchor, wire and earlier annex; it adds no room.
Annexes with the same `stack` and spot name stack by `grow`, in the order given. The core sorts
nothing and invents no size or spot: the caller measures both.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .annex_values import AnnexBox
from .errors import CoreError
from .text_label_grid import page_grid, page_obstacles
from .text_labels import Cover, descend, first_pass, own_counts
from .values import Box, Finding

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from .annex_values import Annex, Spot
    from .occupancy import Occupancy
    from .outputs import Annotations, PagePlacement, Placed, Placement, Routes
    from .values import Options, PlacementProblem, Size

__all__ = ("place_annexes",)


def _wire_x(placed: Placed, spot: Spot) -> int | None:
    """The x of the wire the box keeps beside: the outermost pin on the spot's body edge."""
    body = placed.body
    edge = body.y + body.h if spot.corner[0] == "B" else body.y
    xs = [p.x for p in placed.pin_xy if p.y == edge]
    return (max(xs) if spot.corner[1] == "R" else min(xs)) if xs else None


def spot_box(placed: Placed, size: Size, spot: Spot, used: int) -> Box:
    """The annex's box at `spot`; `used` is the height the stack holds before it."""
    body = placed.body
    right = spot.corner[1] == "R"
    x = body.x + (body.w if right else 0) + spot.dx
    y = body.y + (body.h if spot.corner[0] == "B" else 0) + spot.dy
    y += used if spot.grow == "down" else -used
    wire = _wire_x(placed, spot) if spot.clear else None
    if wire is not None:
        x = max(x, wire + spot.clear) if right else min(x, wire - spot.clear - size.w)
    return Box(x, y, size.w, size.h)


def _candidates(
    annexes: Sequence[Annex], owners: Mapping[str, Placed]
) -> list[list[tuple[str, Box]]]:
    """(spot, box) per annex in preference order; stacked annexes sit past the heights before."""
    held: dict[tuple[str, str | None, str], int] = {}
    out = []
    for annex in annexes:
        placed = owners[annex.owner]
        spots = annex.spots.get(placed.orient)
        if not spots:
            msg = f"annex of {annex.owner} has no spot at {placed.orient}: pass spots for each turn"
            raise CoreError(msg)
        keys = [(annex.owner, annex.stack, s.name) for s in spots]
        used = [held.get(k, 0) if annex.stack is not None else 0 for k in keys]
        out.append(
            [(s.name, spot_box(placed, annex.size, s, u)) for s, u in zip(spots, used, strict=True)]
        )
        for k, u in zip(keys, used, strict=True):
            held[k] = u + annex.size.h
    return out


def _page(
    page: PagePlacement,
    annexes: Sequence[Annex],
    grid: Occupancy,
    options: Options,
    bounds: Size,
) -> tuple[list[AnnexBox], list[Finding]]:
    """The annexes of one page on its grid: the first pass, the descent, and what stays blocked."""
    owners = {p.sym: p for p in page.placed}
    cands = _candidates(annexes, owners)
    cover = Cover(
        grid,
        options.label_gap,
        bounds,
        [owners[a.owner].body for a in annexes],
        [p.body for p in page.placed],
    )
    first_pass(cover, cands)
    descend(cover, cands)
    boxes: list[AnnexBox] = []
    found: list[Finding] = []
    for i, (annex, spots, pick) in enumerate(zip(annexes, cands, cover.choice, strict=True)):
        name, box = spots[pick]
        boxes.append(AnnexBox(annex.owner, page.page, box, name))
        left = own_counts(cover, [box], box, i)[0]
        if left:
            text = f"annex of {annex.owner} on page {page.page} has {left} blocked cells"
            found.append(Finding("ANNEX_UNPLACED", text, page.page, annex.owner))
    return boxes, found


def place_annexes(
    placement: Placement,
    routes: Routes,
    notes: Annotations,
    problem: PlacementProblem,
    options: Options,
) -> tuple[tuple[AnnexBox, ...], tuple[Finding, ...]]:
    """One AnnexBox per annex of a placed owner; ANNEX_UNPLACED (a WARNING) for each left blocked.

    An annex whose owner is not placed is skipped. Annexes of one page are placed in the order
    given, each round the bodies, wires, markers, tables and the annexes before it.
    """
    annexes = problem.annexes
    wires = {r.page: r.wires for r in routes.pages}
    done: dict[int, AnnexBox] = {}
    findings: list[Finding] = []
    for page in placement.pages:
        mine = {p.sym for p in page.placed}
        picked = [(i, a) for i, a in enumerate(annexes) if a.owner in mine]
        if not picked:
            continue
        obstacles = page_obstacles(page, notes.markers, notes.tables, options, notes.anchored)
        grid = page_grid(page, wires.get(page.page, ()), obstacles, problem.area, options)
        boxes, found = _page(page, [a for _, a in picked], grid, options, problem.area)
        done.update({i: b for (i, _), b in zip(picked, boxes, strict=True)})
        findings += found
    return tuple(done[i] for i in range(len(annexes)) if i in done), tuple(findings)
