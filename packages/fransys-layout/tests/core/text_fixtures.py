"""Planted problems, one per reference kind, and counters of the references a cut plans or draws.

Each plant is a PlacementProblem over the cut area, built so the cut plans the kind it names
(KIND_OF). Sizes are in G, as in cut_fixtures.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
from typing import TYPE_CHECKING

from options_fixtures import core_options

from fransys_layout.core import Facts, Hints, Net, Options, PinRef, PlacementProblem, Unit
from fransys_layout.core.place import place_pages
from fransys_layout.core.values import CutResult, Ref, RefEnd, RefKind
lazy from fransys_layout.core.outputs import Marker

from . import pipeline_fixtures
from .conftest import MARKER
from .cut_fixtures import AREA, box_sym, chain, elem, free, net, side
from .flow_builders import poles

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


def plan_of(prob: PlacementProblem, options: Options | None = None) -> CutResult:
    """The cut (stages 1 to 4) of a problem, with its reference plan."""
    return pipeline_fixtures.cut_of(prob, options)


def marked_of(prob: PlacementProblem, options: Options | None = None) -> tuple[Marker, ...]:
    """The markers of a problem: stages 1 to 4, then place_pages, then mark_pages."""
    # mark_pages lands with the text markers; imported late so the other plants still load.
    from fransys_layout.core.text_markers import mark_pages

    opts = options or core_options(
        marker=MARKER,
        flip_turn="R180",
        tag_stagger=True,
        label_gap=8,
        driver_first=True,
        arrow_sides=("E", "W"),
    )
    cut = pipeline_fixtures.cut_of(prob, opts)
    return mark_pages(cut, place_pages(cut, prob, opts), prob, opts)


def tag_chain() -> PlacementProblem:
    """Three 300 G cells in one chain, 900 G tall: the cut folds the column, one tag on page 1.

    A plain two-page chain plants no tag; the tag comes from the tall-column fold (stage 4).
    """
    ids = [f"k{i:02d}" for i in range(3)]
    return PlacementProblem(
        AREA,
        tuple(elem(i, 40, 300) for i in ids),
        tuple(chain(ids)),
        facts=Facts(),
    )


def row_wrapped_fan() -> PlacementProblem:
    """A bundle driver M3 (three poles) and three 720 G legs: the trunk wraps, so the legs sit
    in rows 1 to 3 of page 1 and the arrows join columns in different rows of one page.

    RefEnd.row is None in the plan, so the rows are read from the page's rows.
    """
    syms = (poles("M3"), poles("M9", 30), poles("M10", 30), poles("M11", 30))
    legs = ("M9.n0", "M10.n0", "M11.n0")
    return PlacementProblem(AREA, syms, (net("bn0", "M3.s0", *legs),), facts=Facts())


def page_wrapped_fan() -> PlacementProblem:
    """A plain two-pin driver d0 heading three legs of 600 to 700 G: k1 on page 1, k2 and k3 on 2.

    The driver is no hub (not free-sided), so nothing is copied: the page cut stays an arrow.
    """
    syms = [elem("d0", 500, 400), elem("k1", 700, 400), elem("k2", 600, 400), elem("k3", 600, 400)]
    return PlacementProblem(
        AREA,
        tuple(syms),
        (net("feed", "d0.s", "k1.n", "k2.n", "k3.n"),),
        facts=Facts(),
    )


def unit_boundary_stubs() -> PlacementProblem:
    """Net m joins x, y and z on one page, crossing units with boundary pins x.e and z.e.

    The crossing flag with two boundary pins plans a stub, with one end at each pin. One page,
    so no arrow stands on a pin: an end that carries an arrow gets no stub.
    """
    syms = [
        replace(side(n, 200, 200), unit=u) for n, u in zip("xyz", ("U1", "U3", "U2"), strict=True)
    ]
    facts = Facts(
        units=(Unit("U1", None, (PinRef("x", "e"),)), Unit("U2", None, (PinRef("z", "e"),))),
    )
    nets = (net("m", "x.e", "y.e", "z.e", crosses_unit=True),)
    return PlacementProblem(AREA, tuple(syms), nets, facts)


def copied_hub() -> PlacementProblem:
    """One free-sided hub t2 feeding three 700 G legs on three pages: the hub is copied.

    The copy is the reference the cut plans for the hub onto pages 2 and 3.
    """
    syms = [free("t2"), *(elem(f"a2x{i}", 700, 400, "G2") for i in (1, 2, 3))]
    nets = (net("feed2", "t2.e", "a2x1.n", "a2x2.n", "a2x3.n"),)
    return PlacementProblem(
        AREA,
        tuple(syms),
        nets,
        hints=Hints(group_order=("G2",)),
        facts=Facts(),
    )


def stubs_in_a_row() -> PlacementProblem:
    """Twelve small elements side by side on one page, one net across a unit joining their pins.

    Twelve stub ends share a page and a row: only the natural order of their ids sorts them.
    """
    ids = [f"e{i}" for i in range(12)]
    pins = tuple(PinRef(i, "n") for i in ids)
    facts = Facts(units=(Unit("U1", None, pins),))
    nets = (Net("m", pins, crosses_unit=True),)
    return PlacementProblem(AREA, tuple(elem(i, 40, 32) for i in ids), nets, facts)


def spilled_tags() -> PlacementProblem:
    """A 40-pin box over 40 columns: the card keeps what fits, the rest leave it, a tag each."""
    syms = [box_sym(40), *(elem(f"k{i}", 64, 32, "CH") for i in range(1, 41))]
    nets = tuple(net(f"n{i}", f"A1.p{i}", f"k{i}.n") for i in range(1, 41))
    return PlacementProblem(AREA, tuple(syms), nets, facts=Facts())


def spilled_pair() -> PlacementProblem:
    """A 37-pin box whose first 19 pins carry a column: pins 18 and 19 leave the north edge.

    The pins past 19 carry no column, so the south edge has nothing to spill. Each spilled column
    gets one tag pair; the two box-side tags stand in one row, 16 G apart.
    """
    syms = [box_sym(37, 19), *(elem(f"k{i}", 64, 32, "CH") for i in range(1, 20))]
    nets = tuple(net(f"n{i}", f"A1.p{i}", f"k{i}.n") for i in range(1, 20))
    return PlacementProblem(AREA, tuple(syms), nets, facts=Facts())


def star_three() -> PlacementProblem:
    """Net m joins three 40 G elements x, y, z on one page, all three pins at the unit boundary.

    No planner in the cut makes a star (RefKind.STAR is read, never planned), so this plants the
    stub the boundary pins plan: one reference, three ends on one page, in one row.
    """
    ids = ("x", "y", "z")
    pins = tuple(PinRef(i, "n") for i in ids)
    facts = Facts(units=(Unit("U1", None, pins),))
    nets = (Net("m", pins, crosses_unit=True),)
    return PlacementProblem(AREA, tuple(elem(i, 40, 32) for i in ids), nets, facts)


def star_two_tied() -> Ref:
    """A star of exactly two ends in one page, one row and one column, listed in reverse id order.

    Nothing but the pin's id parts them, so the id's natural order (p2 before p10) decides.
    """
    return Ref(
        "m",
        RefKind.STAR,
        (RefEnd(1, "c", PinRef("S", "p10"), 0), RefEnd(1, "c", PinRef("S", "p2"), 0)),
    )


PLANTS: dict[str, Callable[[], PlacementProblem]] = {
    "tag_chain": tag_chain,
    "row_wrapped_fan": row_wrapped_fan,
    "page_wrapped_fan": page_wrapped_fan,
    "unit_boundary_stubs": unit_boundary_stubs,
    "copied_hub": copied_hub,
    "stubs_in_a_row": stubs_in_a_row,
    "spilled_tags": spilled_tags,
    "spilled_pair": spilled_pair,
    "star_three": star_three,
}

KIND_OF: dict[str, str] = {
    "tag_chain": "tag",
    "row_wrapped_fan": "arrow",
    "page_wrapped_fan": "arrow",
    "unit_boundary_stubs": "stub",
    "copied_hub": "copy",
    "stubs_in_a_row": "stub",
    "spilled_tags": "tag",
    "spilled_pair": "tag",
    "star_three": "stub",
}


def plan_counts(cut: CutResult) -> Counter[str]:
    """The number of reference ends per kind in the cut's reference plan: one marker per end."""
    return Counter(r.kind for r in cut.spec.reference_plan for _ in r.ends)


def marker_counts(markers: Iterable[Marker]) -> Counter[str]:
    """The number of markers per kind."""
    return Counter(m.kind for m in markers)
