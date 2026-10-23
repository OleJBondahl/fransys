"""Hand-built placement problems and readers of a Placement, for the stage 5 tests.

Each builder returns a PlacementProblem over the cut area; placed_of runs it through stages 1 to 5.
"""

from __future__ import annotations

from dataclasses import replace

from turn_fixtures import refit

from fransys_layout.core import Box, Bundle, Facts, Placement, PlacementProblem
lazy from fransys_layout.core.outputs import PagePlacement

from .cut_fixtures import AREA, box_sym, elem, free
from .flow_builders import net, poles


def _coil_card(coils: list[str], coil_width: int, north: int = 0) -> PlacementProblem:
    """A box with one pin per coil, net c<i> from pin p<i> to the n pin of coil i."""
    syms = [box_sym(len(coils), north), *(elem(k, coil_width) for k in coils)]
    nets = [net(f"c{i}", f"A1.p{i}", f"{k}.n") for i, k in enumerate(coils, 1)]
    return PlacementProblem(AREA, tuple(syms), tuple(nets), facts=Facts())


def card_with_coils(n: int = 4, coil_width: int = 84) -> PlacementProblem:
    """A box with n pins, each wired to its own coil, so the pins must spread to meet the coils."""
    return _coil_card([f"k{i}" for i in range(1, n + 1)], coil_width)


def two_edge_card(n: int = 16, coil_width: int = 94) -> PlacementProblem:
    """Sixteen coils by default, too wide for one edge, so the cut splits the pins over N and S."""
    return _coil_card([f"k{i:02d}" for i in range(1, n + 1)], coil_width, (n + 1) // 2)


def row_group_three(group: str | None) -> PlacementProblem:
    """Three hubs in row group `group` (or none); footprints rise 16, 32 and 48 G above origin."""
    hubs = [
        refit(free(f"h{k}"), row_group=group, footprint=Box(-8, -16 * (k + 1), 16, 16 * (k + 2)))
        for k in range(3)
    ]
    syms = [*hubs, *(elem(f"e{k}") for k in range(3))]
    nets = [net(f"a{k}", f"h{k}.s", f"e{k}.n") for k in range(3)]
    return PlacementProblem(AREA, tuple(syms), tuple(nets), facts=Facts())


def bundle_fan() -> PlacementProblem:
    """One driver M3 feeds three legs M9, M10 and M11 pole by pole, each pole net in bundle bd1."""
    syms = [poles("M3"), poles("M9"), poles("M10"), poles("M11")]
    nets = [
        net(f"bn{k}", f"M3.s{k}", f"M9.n{k}", f"M10.n{k}", f"M11.n{k}", bundle=Bundle("bd1", k))
        for k in range(3)
    ]
    return PlacementProblem(AREA, tuple(syms), tuple(nets), facts=Facts())


def wide_row() -> PlacementProblem:
    """One symbol 1400 G wide, wider than the 1312 G page, wired to a small element."""
    return PlacementProblem(
        AREA,
        (elem("wide", 1400), elem("e")),
        (net("w", "wide.s", "e.n"),),
        facts=Facts(),
    )


def all_pins(placement: Placement) -> dict[tuple[str, str], tuple[int, int]]:
    """Every placed pin over all pages, as (symbol, pin) -> (x, y)."""
    return {
        (p.sym, q.pin): (q.x, q.y)
        for page in placement.pages
        for p in page.placed
        for q in p.pin_xy
    }


def footprints(page: PagePlacement) -> dict[str, Box]:
    """Each symbol on one page with its absolute footprint."""
    return {p.sym: p.footprint for p in page.placed}


def card_with_label(grow: int, n: int = 4, coil_width: int = 40) -> PlacementProblem:
    """A card_with_coils box whose footprint reaches `grow` G past its body's right edge only."""
    prob = card_with_coils(n, coil_width)
    box = prob.symbols[0]
    b = box.body
    card = refit(box, footprint=Box(b.x, b.y, b.w + grow, b.h))
    return replace(prob, symbols=(card, *prob.symbols[1:]))
