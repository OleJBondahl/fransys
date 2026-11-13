"""A bundle's lanes that run to a cut end pair by the order of their nets across a reference (RAIL-LANES, READ-LANES, R1957).

Owner 2026-10-23: one arrow stands for the bundle; the other lanes pair k-th with k-th, and each foot's net is its piece's port's.
"""

from types import SimpleNamespace
from typing import Any

from fransys_el.drawn_graph import Union
from fransys_el.drawn_lanes import join_lanes


def _side(union: Union, name: str, *lanes: tuple[str, int, int], style: str = "trunk", ports: bool = True) -> tuple[str, Any, dict[str, str]]:
    """A page `name` with a wire per `(net, y, x end)` from x 0, and (unless `ports` is off) a port of the net at its start."""
    wires = [SimpleNamespace(points=((0, y), (x, y)), style=style) for _, y, x in lanes]
    for _, y, x in lanes:
        union.join((name, (0, y)), (name, (x, y)))
    held = {f"{name}{net}": (0, y) for net, y, _ in lanes} if ports else {}
    return name, SimpleNamespace(drawing=SimpleNamespace(wires=wires), ports=held), {f"{name}{net}": net for net, _, _ in lanes}


def _join(*sides: tuple[str, Any, dict[str, str]], at: list[tuple[str, tuple[int, int]]], union: Union, stubs: dict[Any, set[str]] | None = None):
    pages = {name: part for name, part, _ in sides}
    refs = SimpleNamespace(groups={0: at}, stubs=stubs or {})
    return join_lanes(union, pages, refs, {k: v for _, _, nets in sides for k, v in nets.items()}, 8)  # ty: ignore[invalid-argument-type] - doubles


def test_lanes_pair_across_the_ends_of_a_star_though_one_page_lacks_a_lane() -> None:
    union = Union()
    a = _side(union, "A", ("L1", 8, 100))
    b = _side(union, "B", ("L1", 8, 50), ("L2", 16, 50))
    c = _side(union, "C", ("L1", 8, 60), ("L2", 16, 60))
    _join(a, b, c, at=[("A", (100, 8)), ("B", (50, 8)), ("C", (60, 8))], union=union)
    assert union.find(("B", (50, 8))) == union.find(("A", (100, 8)))
    assert union.find(("B", (50, 8))) != union.find(("B", (50, 16)))  # different nets stay apart


def test_lanes_the_other_side_reads_in_another_order_pair_nothing() -> None:
    """The k-th lane of one side is the k-th of the other: the same nets in the other order are no pairing."""
    union = Union()
    a = _side(union, "A", ("L1", 8, 100), ("L2", 16, 60))
    b = _side(union, "B", ("L2", 8, 50), ("L1", 16, 50))
    lanes = _join(a, b, at=[("A", (100, 8)), ("B", (50, 8))], union=union)
    assert not lanes.joined
    assert union.find(("A", (100, 8))) != union.find(("B", (50, 16)))


def test_the_lanes_of_the_arrows_trunk_pair_though_the_arrow_lane_runs_past_their_cut_end() -> None:
    """R903: the arrow lane steps out past the legs; the other lanes end at the cut, one pitch apart; a far trunk is not read."""
    union = Union()
    a = _side(union, "A", ("L1", 8, 100), ("L2", 16, 60), ("L3", 24, 60), ("L9", 80, 60))
    b = _side(union, "B", ("L1", 8, 50), ("L2", 16, 50), ("L3", 24, 50), ("L9", 80, 50))
    _join(a, b, at=[("A", (100, 8)), ("B", (50, 8))], union=union)
    assert union.find(("A", (60, 16))) == union.find(("B", (50, 16)))
    assert union.find(("A", (60, 24))) == union.find(("B", (50, 24)))
    assert union.find(("A", (60, 80))) != union.find(("B", (50, 80)))


def test_a_foot_whose_piece_holds_no_port_is_bare_and_pairs_nothing() -> None:
    union = Union()
    a = _side(union, "A", ("L1", 8, 100), ("L2", 16, 60), ports=False)
    b = _side(union, "B", ("L1", 8, 50), ("L2", 16, 50))
    lanes = _join(a, b, at=[("A", (100, 8)), ("B", (50, 8))], union=union)
    assert lanes.bare == {("A", (100, 8)), ("A", (60, 16))}
    assert not lanes.joined


def test_a_piece_of_two_nets_is_a_short_and_pairs_nothing() -> None:
    union = Union()
    a = _side(union, "A", ("L1", 8, 100))
    b = _side(union, "B", ("L1", 8, 50))
    a[1].ports["Ax"] = (0, 8)  # a second port of another net on the same piece
    a[2]["Ax"] = "LX"
    lanes = _join(a, b, at=[("A", (100, 8)), ("B", (50, 8))], union=union)
    assert not lanes.joined
    assert not lanes.bare


def test_a_stub_meets_the_feet_whose_piece_holds_a_port_its_text_lists() -> None:
    """R1666: an off stub's text lists the conductors it ends; the lane of a listed port is met, the lane of an unlisted port is not."""
    union = Union()
    a = _side(union, "A", ("L1", 8, 100), ("L2", 16, 92), ("L3", 24, 92))
    refs = SimpleNamespace(groups={}, stubs={("A", (100, 8)): {"AL1", "AL2"}})
    lanes = join_lanes(union, {"A": a[1]}, refs, a[2], 8)  # ty: ignore[invalid-argument-type] - doubles
    assert lanes.joined == {("A", (100, 8)), ("A", (92, 16))}


def _pass_through(near: str, far: str, *, far_read: bool = True):
    """Page T holds a lane with no port from one arrow to another; each arrow's reference leads to a page whose first lane has a port."""
    union = Union()
    t = _side(union, "T", ("L", 16, 100), ports=False)
    p1, p2 = _side(union, "P1", (near, 16, 50)), _side(union, "P2", (far, 16, 50))
    groups = {1: [("T", (0, 8)), ("P1", (0, 8))], 2: [("T", (100, 8)), ("P2", (0, 8))] if far_read else [("T", (100, 8))]}
    pages = {name: part for name, part, _ in (t, p1, p2)}
    nets = {k: v for _, _, found in (p1, p2) for k, v in found.items()}
    return union, join_lanes(union, pages, SimpleNamespace(groups=groups, stubs={}), nets, 8)  # ty: ignore[invalid-argument-type] - doubles


def test_a_lane_between_two_arrows_is_met_when_both_references_lead_to_a_lane_of_one_net() -> None:
    """R2065: a pass-through lane has no port on its page; the k-th lane at each arrow's other end names its net."""
    union, lanes = _pass_through("L", "L")
    assert not lanes.bare
    assert {("T", (0, 16)), ("T", (100, 16))} <= lanes.joined
    assert union.find(("T", (0, 16))) == union.find(("P1", (0, 16))) == union.find(("P2", (0, 16)))


def test_a_lane_between_two_arrows_stays_dangling_when_one_reference_is_not_read_at_its_other_end() -> None:
    _, lanes = _pass_through("L", "L", far_read=False)
    assert lanes.bare == {("T", (0, 16)), ("T", (100, 16))}


def test_a_lane_between_two_arrows_whose_references_lead_to_two_nets_stays_dangling() -> None:
    union, lanes = _pass_through("L", "M")
    assert lanes.bare == {("T", (0, 16)), ("T", (100, 16))}
    assert union.find(("P1", (0, 16))) != union.find(("P2", (0, 16)))
