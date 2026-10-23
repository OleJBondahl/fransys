"""A bundle's lanes that run to a cut end join the same net's end at the reference's other markers.

RAIL-LANES, owner 2026-10-23: one arrow stands for the bundle; the other lanes join by net.
"""

from types import SimpleNamespace
from typing import Any

from fransys_el.drawn_graph import Union
from fransys_el.drawn_netlist import _lanes

from fransys_model.layout import StarKind


def _run(union: Union, pages: Any, markers: Any, records: Any) -> None:
    """The fakes stand in for pages and markers; the typed door is not under test."""
    _lanes(union, pages, markers, records)


def _page(*wires: tuple[str, tuple[int, int], tuple[int, int]]) -> SimpleNamespace:
    return SimpleNamespace(
        drawing=SimpleNamespace(wires=[SimpleNamespace(net=n, points=(a, b)) for n, a, b in wires])
    )


def _record(star: StarKind | None, partner: str) -> SimpleNamespace:
    return SimpleNamespace(star=star, partner=SimpleNamespace(value=partner))


def _star():
    """Three pages; the REF is on A, branches on B and C; lane L2 is absent on A."""
    pages = {
        "A": _page(("L1", (0, 8), (100, 8))),
        "B": _page(("L1", (0, 8), (50, 8)), ("L2", (0, 16), (50, 16))),
        "C": _page(("L1", (0, 8), (60, 8)), ("L2", (0, 16), (60, 16))),
    }
    markers = {"r": ("A", (100, 8)), "b1": ("B", (50, 8)), "b2": ("C", (60, 8))}
    records = {
        "r": _record(StarKind.REF, "b1"),
        "b1": _record(StarKind.BRANCH, "r"),
        "b2": _record(StarKind.BRANCH, "r"),
    }
    return pages, markers, records


def test_lanes_join_across_the_branches_of_a_star_though_the_ref_page_lacks_one() -> None:
    pages, markers, records = _star()
    union = Union()
    _run(union, pages, markers, records)
    assert union.find(("B", (50, 16))) == union.find(("C", (60, 16)))
    assert union.find(("B", (50, 8))) == union.find(("A", (100, 8)))
    assert union.find(("B", (50, 8))) != union.find(("B", (50, 16)))  # different nets stay apart


def test_a_plain_pair_joins_the_lanes_of_its_two_ends() -> None:
    pages = {"A": _page(("L2", (0, 16), (10, 16))), "B": _page(("L2", (0, 16), (20, 16)))}
    markers = {"a": ("A", (10, 8)), "b": ("B", (20, 8))}
    records = {"a": _record(None, "b"), "b": _record(None, "a")}
    union = Union()
    _run(union, pages, markers, records)
    assert union.find(("A", (10, 16))) == union.find(("B", (20, 16)))
