"""Placement problems and y readers for the stage 5 alignment tests (bands, mates, row groups)."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from fransys_layout.core import Box, Facts, PinRef, PlacementProblem, Sym
from fransys_layout.core.geometry import pin_xy
from fransys_layout.core.pack import cell_node

from .cut_fixtures import AREA, box_sym, chain, elem, free, net

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from fransys_layout.core import Net
    from fransys_layout.core.place_env import PageEnv

WIDE = 500


def _band(sym_id: str, band: int, height: int = 32) -> Sym:
    return replace(elem(sym_id, height=height), band=band)


def _wide(sym_id: str, band: int | None = None) -> Sym:
    return replace(elem(sym_id, WIDE), band=band)


def _padded(sym: Sym, extra: int) -> Sym:
    """The symbol with `extra` G more footprint above its body."""
    fp = sym.footprint
    return replace(sym, footprint=Box(fp.x, fp.y - extra, fp.w, fp.h + extra))


def _problem(syms: list[Sym], nets: list[Net], facts: Facts | None = None) -> PlacementProblem:
    return PlacementProblem(AREA, tuple(syms), tuple(nets), facts or Facts())


def two_band_columns() -> PlacementProblem:
    """Column A: tall a0, a1 (band 1), a2 (band 2); column B: b1 (band 1), bs, b2 (band 2)."""
    syms = [elem("a0", height=48), _band("a1", 1), _band("a2", 2), _band("b1", 1)]
    syms += [elem("bs", height=80), _band("b2", 2)]
    return _problem(syms, chain(["a0", "a1", "a2"], "a") + chain(["b1", "bs", "b2"], "b"))


def lane_two_of_a_rank() -> PlacementProblem:
    """Column A: a1 (band 1), m, a1b (band 1); column B: b1 (band 1). One band spans two of A."""
    syms = [_band("a1", 1), elem("m", height=48), _band("a1b", 1), _band("b1", 1)]
    syms.append(elem("b2"))
    return _problem(syms, chain(["a1", "m", "a1b"], "a") + chain(["b1", "b2"], "b"))


def two_rows_equal_ranks() -> PlacementProblem:
    """Three wide columns of band 1: A and B wrap into row 0, C into row 1."""
    syms = [_wide("a1", 1), elem("a2"), _wide("b1", 1), elem("b2"), _wide("c1", 1), elem("c2")]
    nets = chain(["a1", "a2"], "a") + chain(["b1", "b2"], "b") + chain(["c1", "c2"], "c")
    return _problem(syms, nets)


def mate_columns() -> PlacementProblem:
    """Columns P and Q: p is 48 tall, so its s pin sits 24 G below its origin; q n is 16 above."""
    facts = Facts(mates=((PinRef("p", "s"), PinRef("q", "n")),))
    syms = [elem("gp"), elem("p", height=48), elem("q"), elem("gq")]
    nets = chain(["gp", "p"], "a") + chain(["q", "gq"], "b")
    return _problem(syms, nets, facts)


def mate_across_rows() -> PlacementProblem:
    """Wide P and Q share row 0, wide R wraps to row 1; the mate joins P's s pin to R's n pin.

    Row 1 starts below row 0's bottom, so the mate cannot hold as an equality.
    """
    facts = Facts(mates=((PinRef("p", "s"), PinRef("r", "n")),))
    syms = [elem("pa"), _wide("p"), _wide("q"), elem("qb"), _wide("r"), elem("ra")]
    nets = chain(["pa", "p"], "a") + chain(["q", "qb"], "b") + chain(["r", "ra"], "c")
    return _problem(syms, nets, facts)


def mate_with_box() -> PlacementProblem:
    """Box A1, pins p1 and p2 each wired to a coil; a mate joins p1 to free column K's n pin."""
    facts = Facts(mates=((PinRef("A1", "p1"), PinRef("k3", "n")),))
    syms = [box_sym(2), elem("k1"), elem("k2"), elem("k3"), elem("k4")]
    nets = [net("c1", "A1.p1", "k1.n"), net("c2", "A1.p2", "k2.n")]
    return _problem(syms, [*nets, *chain(["k3", "k4"], "k")], facts)


def _trunk_parts(group: str | None) -> tuple[list[Sym], list[Net]]:
    """Hub h drops a fan onto l1, l2, l3; chains u1-u2 and v1-v2, v1 with 24 G more footprint."""
    syms = [replace(free("h"), band=1), elem("l1"), _band("l2", 1), elem("l3")]
    syms += [replace(elem("u1"), row_group=group), elem("u2")]
    syms += [replace(_padded(elem("v1"), 24), row_group=group), elem("v2")]
    nets = [net("bus", "h.s", "l1.n", "l2.n", "l3.n"), net("nu", "u1.s", "u2.n")]
    nets += [net("nv", "v1.s", "v2.n")]
    return syms, nets


def band_against_trunk(group: str | None) -> PlacementProblem:
    """A band over h and l2 would put the hub on its own trunk; the row group of u and v holds."""
    return _problem(*_trunk_parts(group))


def band_squeezes_driver() -> PlacementProblem:
    """Driver x2 feeds legs y1 (band 1) and z1 from one fan; a band over x2 and y1 fails."""
    syms = [elem("x1"), _band("x2", 1), _band("y1", 1), elem("z1")]
    nets = [*chain(["x1", "x2"], "x"), net("f", "x2.s", "y1.n", "z1.n")]
    return _problem(syms, nets)


def band_trunk_refuses() -> PlacementProblem:
    """Legs y1 and z1 (64 tall, band 1) hang under one trunk; a band over them fails."""
    syms = [elem("x1"), _band("y1", 1), _band("z1", 1, 64)]
    return _problem(syms, [net("bus", "x1.s", "y1.n", "z1.n")])


def all_three_contradict() -> PlacementProblem:
    """A row group, a band and a mate, each against the stacks or the fan trunk of one page.

    The fan from x2 to y1 and z hangs a trunk under x2 and over y1. So x1 (above x2) with y2
    (below y1) is a cycle, the row group heads x1 and y1 disagree, and the mate pins clash.
    """
    head = replace(_band("x1", 1), row_group="R1")
    syms = [head, elem("x2"), replace(elem("y1"), row_group="R1")]
    syms += [_band("y2", 1), elem("z"), elem("gp"), elem("p", height=48)]
    nets = chain(["x1", "x2"], "x") + chain(["y1", "y2"], "y") + chain(["gp", "p"], "a")
    nets = [*nets, net("f", "x2.s", "y1.n", "z.n")]
    facts = Facts(mates=((PinRef("p", "s"), PinRef("gp", "n")),))
    return _problem(syms, nets, facts)


def _cells_of(env: PageEnv, sym: str) -> Iterator[tuple[str, int, int]]:
    """(column, lane, index) of every cell holding symbol sym."""
    for pc in env.pcs.values():
        for li, cells in enumerate(pc.lanes):
            for i, cell in enumerate(cells):
                if cell.sym == sym:
                    yield pc.id, li, i


def cell_ys(env: PageEnv, y: Mapping[str, int], col: str) -> tuple[int, ...]:
    """The y of each cell of column col, lane 0, in order."""
    return tuple(y[cell_node(col, 0, i)] for i in range(len(env.pcs[col].lanes[0])))


def pin_y(env: PageEnv, y: Mapping[str, int], sym: str, pin: str) -> int:
    """The absolute y of pin `pin` of symbol `sym`: its cell's y plus the pin's offset there."""
    col, li, i = next(_cells_of(env, sym))
    cell = env.pcs[col].lanes[li][i]
    return y[cell_node(col, li, i)] + pin_xy(env.syms[sym], cell, pin)[1]
