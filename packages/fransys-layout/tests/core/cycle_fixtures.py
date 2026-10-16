"""Ring and acyclic problems for the y-cycle tests, built from cut_fixtures' elements and nets."""

from __future__ import annotations

from itertools import pairwise

from fransys_layout.core import PlacementProblem

from .cut_fixtures import AREA, elem, net


def ring_problem(extra: int = 0) -> PlacementProblem:
    """The t01 ring: lamp, a, b, c, d in a loop, a source s in a fan, and extra parts lamp to a."""
    chain = ["lamp", *(f"x{i}" for i in range(1, extra + 1)), "a"]
    nets = [net(f"n{i}", f"{p}.s", f"{q}.n") for i, (p, q) in enumerate(pairwise(chain), 1)]
    k = len(nets)
    nets += [
        net(f"n{k + 1}", "a.s", "b.n"),
        net(f"n{k + 2}", "b.s", "s.s", "c.n"),
        net(f"n{k + 3}", "c.s", "d.n"),
        net(f"n{k + 4}", "d.s", "lamp.n"),
    ]
    names = (*chain, "b", "c", "d", "s")
    return PlacementProblem(AREA, tuple(elem(i, 60) for i in names), tuple(nets))


def acyclic_problem() -> PlacementProblem:
    """A chain p, q, r and a fan: source s feeds the net between b and c, and no loop closes."""
    syms = tuple(elem(i) for i in ("p", "q", "r", "a", "b", "c", "s"))
    nets = (
        net("w1", "p.s", "q.n"),
        net("w2", "q.s", "r.n"),
        net("f1", "a.s", "b.n"),
        net("f2", "b.s", "s.s", "c.n"),
    )
    return PlacementProblem(AREA, syms, nets)
