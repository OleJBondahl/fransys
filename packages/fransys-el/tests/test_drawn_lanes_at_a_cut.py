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
    _lanes(union, pages, markers, records, 8)


def _page(*wires: tuple[str, tuple[int, int], tuple[int, int]], style: str = "wire") -> SimpleNamespace:
    return SimpleNamespace(drawing=SimpleNamespace(wires=[SimpleNamespace(net=n, points=(a, b), style=style) for n, a, b in wires]))


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


def test_the_lanes_of_the_arrows_trunk_join_though_the_arrow_lane_runs_past_their_cut_end() -> None:
    """R903: the arrow lane steps out past the legs; the other lanes end at the cut, one pitch apart; a far trunk is not joined."""
    here = _page(("L1", (0, 8), (100, 8)), ("L2", (0, 16), (60, 16)), ("L3", (0, 24), (60, 24)), ("L9", (0, 80), (60, 80)), style="trunk")
    there = _page(("L1", (0, 8), (50, 8)), ("L2", (0, 16), (50, 16)), ("L3", (0, 24), (50, 24)), ("L9", (0, 80), (50, 80)), style="trunk")
    markers = {"a": ("A", (100, 8)), "b": ("B", (50, 8))}
    records = {"a": _record(None, "b"), "b": _record(None, "a")}
    union = Union()
    _run(union, {"A": here, "B": there}, markers, records)
    assert union.find(("A", (60, 16))) == union.find(("B", (50, 16)))
    assert union.find(("A", (60, 24))) == union.find(("B", (50, 24)))
    assert union.find(("A", (60, 80))) != union.find(("B", (50, 80)))


def test_a_far_row_of_the_same_nets_ending_on_the_arrows_x_joins_nothing_of_the_arrows_trunk() -> None:
    """R903: lanes of the same nets on another row, one of them ending on the arrow's x, do not stand in for the arrow's own lanes."""
    here = _page(("L1", (0, 8), (100, 8)), ("L2", (0, 16), (60, 16)), ("L9", (0, 80), (100, 80)), ("L2", (0, 88), (100, 88)), style="trunk")
    there = _page(("L1", (0, 8), (50, 8)), ("L2", (0, 16), (50, 16)), style="trunk")
    markers = {"a": ("A", (100, 8)), "b": ("B", (50, 8))}
    records = {"a": _record(None, "b"), "b": _record(None, "a")}
    union = Union()
    _run(union, {"A": here, "B": there}, markers, records)
    assert union.find(("A", (60, 16))) == union.find(("B", (50, 16)))
    assert union.find(("A", (100, 88))) != union.find(("B", (50, 16)))
