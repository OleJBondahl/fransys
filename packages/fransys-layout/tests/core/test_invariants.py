"""Invariant checkers for the label stage (I8.1, I8.2, I8.3, I8.6) and for solve (IS.8, IS.9).

Each checker returns its messages, and [] when the invariant holds. Each message names the symbol
and the page. Only fransys_layout.core is imported at the top; the label modules load late.
"""

from __future__ import annotations

from collections import Counter
from itertools import pairwise
from typing import TYPE_CHECKING

from fransys_layout.core import natural_key
from fransys_layout.core.geometry import overlaps

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.core import AnnexBox, Box, Options, Placement, PlacementProblem, Size
    from fransys_layout.core.occupancy import Occupancy
    from fransys_layout.core.outputs import (
        Annotations,
        Marker,
        PagePlacement,
        Routes,
        Table,
        WireLabel,
    )
    from fransys_layout.core.values import Finding


def _flagged(findings: Sequence[Finding], page: int) -> set[str]:
    """The owners the stages reported as TEXT_OVERLAP or ANNEX_UNPLACED on the page."""
    return {
        f.subject
        for f in findings
        if f.code in ("TEXT_OVERLAP", "ANNEX_UNPLACED") and f.page == page and f.subject
    }


def _page_grid(  # noqa: PLR0913, PLR0917 - the grid takes the whole page context
    page: PagePlacement,
    routes: Routes,
    markers: Sequence[Marker],
    tables: Sequence[Table],
    area: Size,
    options: Options,
) -> Occupancy:
    """The obstacle grid of one page: bodies, wires, marker boxes and table boxes, no labels."""
    from fransys_layout.core.text_label_grid import page_grid, page_obstacles

    wires = {pr.page: pr.wires for pr in routes.pages}.get(page.page, ())
    on_page_markers = [m for m in markers if m.page == page.page]
    on_page_tables = [t for t in tables if t.page == page.page]
    obstacles = page_obstacles(page, on_page_markers, on_page_tables, options)
    return page_grid(page, wires, obstacles, area, options)


def check_one_label(placement: Placement, labels: Sequence[AnnexBox]) -> list[str]:
    """I8.1: exactly one label per placed symbol on each page; no label for anything else."""
    expected = {(pg.page, p.sym) for pg in placement.pages for p in pg.placed}
    got = Counter((lab.page, lab.owner) for lab in labels)
    msgs = [
        f"I8.1 {sym} on page {page}: {got[(page, sym)]} labels, want 1"
        for page, sym in sorted(expected)
        if got[(page, sym)] != 1
    ]
    msgs += [
        f"I8.1 {owner} on page {page}: {n} label(s) for no placed symbol"
        for (page, owner), n in sorted(got.items())
        if (page, owner) not in expected
    ]
    return msgs


def check_label_conflicts(  # noqa: PLR0913, PLR0917 - the checker takes the whole stage result
    placement: Placement,
    routes: Routes,
    markers: Sequence[Marker],
    tables: Sequence[Table],
    labels: Sequence[AnnexBox],
    findings: Sequence[Finding],
    area: Size,
    options: Options,
) -> list[str]:
    """I8.2: a label's cells are free of the page grid and of every other label, unless flagged."""
    msgs: list[str] = []
    for page in placement.pages:
        grid = _page_grid(page, routes, markers, tables, area, options)
        on_page = [lab for lab in labels if lab.page == page.page]
        flagged = _flagged(findings, page.page)
        msgs.extend(
            f"I8.2 {lab.owner} on page {page.page}: label is over the grid"
            for lab in on_page
            if lab.owner not in flagged and not grid.free(lab.box)
        )
        msgs.extend(
            f"I8.2 {a.owner} and {b.owner} on page {page.page}: labels overlap"
            for i, a in enumerate(on_page)
            for b in on_page[i + 1 :]
            if overlaps(a.box, b.box) and a.owner not in flagged and b.owner not in flagged
        )
    return msgs


def _cells(box: Box, step: int) -> set[tuple[int, int]]:
    """The grid cells of a box, as the stage counts them."""
    return {
        (i, j)
        for i in range(box.x // step, -(-(box.x + box.w) // step))
        for j in range(box.y // step, -(-(box.y + box.h) // step))
    }


def _first_free(  # noqa: PLR0913, PLR0917 - the checker passes the stage values
    cands: Sequence[tuple[str, Box]],
    grid: Occupancy,
    others: Sequence[AnnexBox],
    options: Options,
    area: Size,
    bodies: Sequence[Box],
    own: Box,
) -> Box | None:
    """The first candidate inside the area, free of grid, other labels, near wires and outlines."""
    from fransys_layout.core.text_labels import Cover

    held = set().union(*(_cells(o.box, grid.step) for o in others))
    near = Cover(grid, options.label_gap, area, bodies)
    for _corner, box in cands:
        if (
            not near.outside(box)
            and grid.free(box)
            and not held & _cells(box, grid.step)
            and not near.near_wires(box)
            and not near.on_outlines(box, own)
        ):
            return box
    return None


def check_first_free(  # noqa: PLR0913, PLR0917 - the checker takes the whole stage result
    placement: Placement,
    routes: Routes,
    markers: Sequence[Marker],
    tables: Sequence[Table],
    labels: Sequence[AnnexBox],
    findings: Sequence[Finding],
    problem: PlacementProblem,
    options: Options,
) -> list[str]:
    """I8.3: an unflagged label sits at the first candidate free of the grid and other labels."""
    from fransys_layout.core.annex import spot_box

    annexes = {a.owner: a for a in problem.annexes}
    msgs: list[str] = []
    for page in placement.pages:
        grid = _page_grid(page, routes, markers, tables, problem.area, options)
        placed = {p.sym: p for p in page.placed}
        bodies = [p.body for p in page.placed]
        flagged = _flagged(findings, page.page)
        on_page = [lab for lab in labels if lab.page == page.page]
        for lab in on_page:
            if lab.owner in flagged or lab.owner not in placed:
                continue
            mine, at = annexes[lab.owner], placed[lab.owner]
            cands = [(s.name, spot_box(at, mine.size, s, 0)) for s in mine.spots[at.orient]]
            others = [o for o in on_page if o is not lab]
            first = _first_free(
                cands, grid, others, options, problem.area, bodies, placed[lab.owner].body
            )
            if lab.box != first:
                msgs.append(
                    f"I8.3 {lab.owner} on page {page.page}: label at {lab.box}, "
                    f"first free candidate is {first}"
                )
    return msgs


def check_label_order(placement: Placement, labels: Sequence[AnnexBox]) -> list[str]:  # noqa: ARG001 - shared signature
    """I8.6: labels ascend by page, and within a page by owner in natural_key order."""
    keys = [(lab.page, natural_key(lab.owner)) for lab in labels]
    return [
        f"I8.6 {lab.owner} on page {lab.page}: out of order after the label before it"
        for prev, cur, lab in zip(keys, keys[1:], labels[1:], strict=False)
        if cur < prev  # ty: ignore[unsupported-operator] -- natural keys of ids compare
    ]


def check_wire_label_conflicts(  # noqa: PLR0913, PLR0917 - the checker takes the whole stage result
    placement: Placement,
    routes: Routes,
    notes: Annotations,
    wire_labels: Sequence[WireLabel],
    problem: PlacementProblem,
    options: Options,
) -> list[str]:
    """No wire label is over a body, a wire cell, a marker, a table, a label or another wire label.

    A net reported TEXT_OVERLAP has no wire label to check.
    """
    msgs: list[str] = []
    for page in placement.pages:
        grid = _page_grid(page, routes, notes.markers, notes.tables, problem.area, options)
        for lab in notes.annexes:
            if lab.page == page.page:
                grid.mark_box(lab.box)
        on_page = [w for w in wire_labels if w.page == page.page]
        msgs.extend(
            f"P5.3 {w.net} on page {page.page}: wire label is over the grid"
            for w in on_page
            if not grid.free(w.box)
        )
        msgs.extend(
            f"P5.3 {a.net} and {b.net} on page {page.page}: wire labels overlap"
            for i, a in enumerate(on_page)
            for b in on_page[i + 1 :]
            if overlaps(a.box, b.box)
        )
    return msgs


def check_marker_cells(routes: Routes, markers: Sequence[Marker], options: Options) -> list[str]:
    """IS.8: no cell a routed wire passes through, past its two ends, is a cell of a marker box.

    Only the routed wires (kind "routed") are checked: the lane, join and trunk wires are fixed
    before the markers exist and take no obstacle.
    """
    from fransys_layout.core.geometry import marker_box
    from fransys_layout.core.occupancy import cells_between

    step = options.wiring_grid
    msgs: list[str] = []
    for pr in routes.pages:
        boxes = [(m, marker_box(m, options)) for m in markers if m.page == pr.page]
        for m, box in boxes:
            hard = set(_cells_of(box, step))
            for w in (w for w in pr.wires if w.kind == "routed"):
                cells = [c for a, b in pairwise(w.points) for c in cells_between(a, b, step)]
                msgs.extend(
                    f"IS.8 {w.net} on page {pr.page}: wire cell {c} is in the box of the "
                    f"marker of {m.net} at ({m.x}, {m.y})"
                    for c in cells[1:-1]
                    if c in hard
                )
    return msgs


def _cells_of(box: Box, step: int) -> list[tuple[int, int]]:
    """The wiring-grid cells a box covers, as `Occupancy.mark_box` counts them."""
    return [
        (i, j)
        for i in range(box.x // step, -(-(box.x + box.w) // step))
        for j in range(box.y // step, -(-(box.y + box.h) // step))
    ]


def check_trade(options: Options) -> list[str]:
    """IS.9 (I6.9): the router's crossing and bend penalties are the scorer's weights in D units."""
    from fransys_layout.core.score import WEIGHTS

    want = {
        "crossing_penalty": round(WEIGHTS["x"] / WEIGHTS["d"]),
        "bend_penalty": round(WEIGHTS["b"] / WEIGHTS["d"]),
    }
    return [
        f"IS.9 Options.{name} is {getattr(options, name)}, the scorer's weights give {value}"
        for name, value in want.items()
        if getattr(options, name) != value
    ]
