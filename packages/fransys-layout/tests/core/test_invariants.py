"""Invariant checkers for the label stage (I8.1, I8.2, I8.3, I8.6) and for solve (IS.8, IS.9).

Each checker returns its messages, and [] when the invariant holds. Each message names the symbol
and the page. Only fransys_layout.core is imported at the top; the label modules load late.
"""

from __future__ import annotations

from collections import Counter
from itertools import pairwise
from typing import TYPE_CHECKING, Any

from fransys_layout.core import Box, natural_key
from fransys_layout.core.clearance import Keep, clear
from fransys_layout.core.geometry import inside, overlaps

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fransys_layout.core import AnnexBox, Options, Placement, PlacementProblem, Size
    from fransys_layout.core.outputs import (
        Marker,
        PagePlacement,
        Routes,
        Wire,
    )
    from fransys_layout.core.values import Finding


def _flagged(findings: Sequence[Finding], page: int) -> set[str]:
    """The owners the stages reported as ANNEX_UNPLACED on the page."""
    return {f.subject for f in findings if f.code == "ANNEX_UNPLACED" and f.page == page and f.subject}


def _solids(page: PagePlacement, markers: Sequence[Marker], options: Options) -> list[Box]:
    """The bodies and marker boxes of one page: what a label shares no interior with."""
    from fransys_layout.core.geometry import marker_drawn_box

    return [p.body for p in page.placed] + [marker_drawn_box(m, options) for m in markers if m.page == page.page]


def check_one_label(placement: Placement, labels: Sequence[AnnexBox]) -> list[str]:
    """I8.1: exactly one label per placed symbol on each page; no label for anything else."""
    expected = {(pg.page, p.sym) for pg in placement.pages for p in pg.placed}
    got = Counter((lab.page, lab.owner) for lab in labels)
    msgs = [f"I8.1 {sym} on page {page}: {got[(page, sym)]} labels, want 1" for page, sym in sorted(expected) if got[(page, sym)] != 1]
    msgs += [
        f"I8.1 {owner} on page {page}: {n} label(s) for no placed symbol" for (page, owner), n in sorted(got.items()) if (page, owner) not in expected
    ]
    return msgs


def check_label_conflicts(  # noqa: PLR0913, PLR0917 - the checker takes the whole stage result
    placement: Placement,
    routes: Routes,
    markers: Sequence[Marker],
    labels: Sequence[AnnexBox],
    findings: Sequence[Finding],
    area: Size,
    options: Options,
) -> list[str]:
    """I8.2: a label shares no interior with a body, marker, wire or other label, and stands in the content box, unless flagged."""

    msgs: list[str] = []
    for page in placement.pages:
        wires = {pr.page: pr.wires for pr in routes.pages}.get(page.page, ())
        solid = _solids(page, markers, options)
        on_page = [lab for lab in labels if lab.page == page.page]
        flagged = _flagged(findings, page.page)
        msgs.extend(
            f"I8.2 {lab.owner} on page {page.page}: label is over the grid"
            for lab in on_page
            if lab.owner not in flagged and not free(lab.box, solid, wires, area)
        )
        msgs.extend(
            f"I8.2 {a.owner} and {b.owner} on page {page.page}: labels overlap"
            for i, a in enumerate(on_page)
            for b in on_page[i + 1 :]
            if overlaps(a.box, b.box) and a.owner not in flagged and b.owner not in flagged
        )
    return msgs


def free(box: Box, solids: Sequence[Box], wires: Sequence[Wire], area: Size | None) -> bool:
    """The oracle of a free label: inside `area`, and no solid or wire segment shares interior with `box` (clearance.clear on its inner box)."""
    keeps = [Keep("", s, "body", "") for s in solids] + [
        Keep("", Box(min(a[0], b[0]), min(a[1], b[1]), abs(b[0] - a[0]), abs(b[1] - a[1])), "wire", w.net)
        for w in wires
        for a, b in pairwise(w.points)
    ]
    return (area is None or inside(box, area)) and not clear(Box(box.x + 1, box.y + 1, box.w - 2, box.h - 2), keeps, {})


def check_first_free(  # noqa: PLR0913, PLR0917 - the checker takes the whole stage result
    placement: Placement,
    routes: Routes,  # noqa: ARG001 - shared signature
    markers: Sequence[Marker],  # noqa: ARG001 - shared signature
    labels: Sequence[AnnexBox],
    findings: Sequence[Finding],
    problem: PlacementProblem,
    options: Options,  # noqa: ARG001 - shared signature
) -> list[str]:
    """I8.3 (LABEL-PLACE ruling 5, R1867): an unflagged label stands at a candidate its annex was given."""
    from fransys_layout.core.annex import _candidates

    annexes = {a.owner: a for a in problem.annexes}
    msgs: list[str] = []
    for page in placement.pages:
        placed = {p.sym: p for p in page.placed}
        flagged = _flagged(findings, page.page)
        on_page = [x for x in labels if x.page == page.page and x.owner not in flagged and x.owner in placed]
        msgs.extend(
            f"I8.3 {lab.owner} on page {page.page}: label at {lab.box} is none of its annex's candidates"
            for lab in on_page
            if lab.box not in [c.box for c in _candidates([annexes[lab.owner]], {lab.owner: placed[lab.owner]})[0]]
        )
    return msgs


def check_label_order(placement: Placement, labels: Sequence[AnnexBox]) -> list[str]:  # noqa: ARG001 - shared signature
    """I8.6: labels ascend by page, and within a page by owner in natural_key order."""
    keys: list[tuple[int, Any]] = [(lab.page, natural_key(lab.owner)) for lab in labels]
    return [
        f"I8.6 {lab.owner} on page {lab.page}: out of order after the label before it"
        for prev, cur, lab in zip(keys, keys[1:], labels[1:], strict=False)
        if cur < prev
    ]


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
                    f"IS.8 {w.net} on page {pr.page}: wire cell {c} is in the box of the marker of {m.net} at ({m.x}, {m.y})"
                    for c in cells[1:-1]
                    if c in hard
                )
    return msgs


def _cells_of(box: Box, step: int) -> list[tuple[int, int]]:
    """The wiring-grid cells a box covers, as `Occupancy.mark_box` counts them."""
    return [(i, j) for i in range(box.x // step, -(-(box.x + box.w) // step)) for j in range(box.y // step, -(-(box.y + box.h) // step))]


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
