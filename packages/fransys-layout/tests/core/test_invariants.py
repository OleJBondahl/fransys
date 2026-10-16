"""Invariant checkers for the label stage (I8.1, I8.2, I8.3, I8.6).

Each checker returns its messages, and [] when the invariant holds. Each message names the symbol
and the page. Only fransys_layout.core is imported at the top; the label modules load late.
"""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from fransys_layout.core import natural_key
from fransys_layout.core.geometry import overlaps

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.core import Box, Options, Placement, PlacementProblem, Size
    from fransys_layout.core.occupancy import Occupancy
    from fransys_layout.core.outputs import Label, Marker, PagePlacement, Routes, Table
    from fransys_layout.core.values import Finding


def _flagged(findings: Sequence[Finding], page: int) -> set[str]:
    """The owners the stage reported as TEXT_OVERLAP on the page."""
    return {
        f.subject for f in findings if f.code == "TEXT_OVERLAP" and f.page == page and f.subject
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
    return page_grid(page, wires, obstacles, area, options.wiring_grid)


def check_one_label(placement: Placement, labels: Sequence[Label]) -> list[str]:
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
    labels: Sequence[Label],
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


def _first_free(
    cands: Sequence[tuple[str, Box]], grid: Occupancy, others: Sequence[Label]
) -> Box | None:
    """The first candidate box free of the grid and of every other label, or None."""
    held = set().union(*(_cells(o.box, grid.step) for o in others))
    for _corner, box in cands:
        if grid.free(box) and not held & _cells(box, grid.step):
            return box
    return None


def check_first_free(  # noqa: PLR0913, PLR0917 - the checker takes the whole stage result
    placement: Placement,
    routes: Routes,
    markers: Sequence[Marker],
    tables: Sequence[Table],
    labels: Sequence[Label],
    findings: Sequence[Finding],
    problem: PlacementProblem,
    options: Options,
) -> list[str]:
    """I8.3: an unflagged label sits at the first candidate free of the grid and other labels."""
    from fransys_layout.core.text_label_cands import candidates

    syms = {s.id: s for s in problem.symbols}
    msgs: list[str] = []
    for page in placement.pages:
        grid = _page_grid(page, routes, markers, tables, problem.area, options)
        placed = {p.sym: p for p in page.placed}
        flagged = _flagged(findings, page.page)
        on_page = [lab for lab in labels if lab.page == page.page]
        for lab in on_page:
            if lab.owner in flagged or lab.owner not in placed:
                continue
            cands = candidates(syms[lab.owner], placed[lab.owner], options)
            others = [o for o in on_page if o is not lab]
            first = _first_free(cands, grid, others)
            if lab.box != first:
                msgs.append(
                    f"I8.3 {lab.owner} on page {page.page}: label at {lab.box}, "
                    f"first free candidate is {first}"
                )
    return msgs


def check_label_order(placement: Placement, labels: Sequence[Label]) -> list[str]:  # noqa: ARG001 - shared signature
    """I8.6: labels ascend by page, and within a page by owner in natural_key order."""
    keys = [(lab.page, natural_key(lab.owner)) for lab in labels]
    return [
        f"I8.6 {lab.owner} on page {lab.page}: out of order after the label before it"
        for prev, cur, lab in zip(keys, keys[1:], labels[1:], strict=False)
        if cur < prev  # ty: ignore[unsupported-operator] -- natural keys of ids compare
    ]
