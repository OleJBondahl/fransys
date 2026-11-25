"""A bundle's lanes that run to a cut end pair by the order of their nets across a reference (RAIL-LANES, READ-LANES, R1957).

Owner 2026-10-23: one arrow stands for the bundle; the other lanes pair k-th with k-th, and each foot's net is its piece's port's.
"""

from types import SimpleNamespace
from typing import Any

import pytest
from fransys_el import drawn_references
from fransys_el.drawn_lanes import join_lanes
from fransys_el.drawn_references import join_references

from fransys_model.kernel import Id, UnionFind
from fransys_model.layout import StarKind


def _side(
    union: UnionFind[Any], name: str, *lanes: tuple[str, int, int], style: str = "trunk", ports: bool = True, inked: int | None = None
) -> tuple[str, Any, dict[str, str]]:
    """A page `name` with a wire per `(net, y, x end)` from x 0, a port at its start (unless `ports` is off), a marker over `inked` lanes."""
    ys = [y for _, y, _ in lanes[:inked]]
    box = SimpleNamespace(x=0, w=max(x for _, _, x in lanes), y=min(ys) - 4, h=max(ys) - min(ys) + 8)
    marks = [SimpleNamespace(slots=(("ref", "#1"),), x=x, y=ys[0], outline=box) for x in {0, *(x for _, _, x in lanes)}]  # one flag per lane end x
    wires = [SimpleNamespace(points=((0, y), (x, y)), style=style) for _, y, x in lanes]
    for _, y, x in lanes:
        union.union((name, (0, y)), (name, (x, y)))
    held = {f"{name}{net}": (0, y) for net, y, _ in lanes} if ports else {}
    return name, SimpleNamespace(drawing=SimpleNamespace(wires=wires, symbols=marks), ports=held), {f"{name}{net}": net for net, _, _ in lanes}


def _join(
    *sides: tuple[str, Any, dict[str, str]], at: list[tuple[str, tuple[int, int]]], union: UnionFind[Any], stubs: dict[Any, set[str]] | None = None
):
    pages = {name: part for name, part, _ in sides}
    refs = SimpleNamespace(groups={0: at}, stubs=stubs or {})
    return join_lanes(union, pages, refs, {k: v for _, _, nets in sides for k, v in nets.items()}, 8)  # ty: ignore[invalid-argument-type] - doubles


def test_lanes_pair_across_the_ends_of_a_star_though_one_page_lacks_a_lane() -> None:
    union = UnionFind()
    a = _side(union, "A", ("L1", 8, 100))
    b = _side(union, "B", ("L1", 8, 50), ("L2", 16, 50))
    c = _side(union, "C", ("L1", 8, 60), ("L2", 16, 60))
    _join(a, b, c, at=[("A", (100, 8)), ("B", (50, 8)), ("C", (60, 8))], union=union)
    assert union.find(("B", (50, 8))) == union.find(("A", (100, 8)))
    assert union.find(("B", (50, 8))) != union.find(("B", (50, 16)))  # different nets stay apart


@pytest.mark.parametrize(
    ("outline_y", "outline_h", "foot_y", "pairs"),
    [(4, 8, 16, False), (8, 40, 48, False), (4, 20, 16, True)],
    ids=["off the ink", "port on the outline's end", "strictly inside"],
)
def test_a_foot_pairs_only_at_the_arrows_port_or_inside_its_ink(outline_y: int, outline_h: int, foot_y: int, *, pairs: bool) -> None:
    """R3541, R3568: the port's lane pairs even on its outline's end; another lane only where its end is inside the ink."""
    union = UnionFind()
    a = _side(union, "A", ("L1", 8, 100), ("L2", foot_y, 100), inked=1)
    for mark in a[1].drawing.symbols:
        mark.outline = SimpleNamespace(x=0, w=100, y=outline_y, h=outline_h)
    b = _side(union, "B", ("L1", 8, 50), ("L2", foot_y, 50))
    _join(a, b, at=[("A", (100, 8)), ("B", (50, 8))], union=union)
    assert union.find(("A", (100, 8))) == union.find(("B", (50, 8)))
    assert (union.find(("A", (100, foot_y))) == union.find(("B", (50, foot_y)))) is pairs


def test_lanes_the_other_side_reads_in_another_order_pair_nothing() -> None:
    """The k-th lane of one side is the k-th of the other: the same nets in the other order are no pairing."""
    union = UnionFind()
    a = _side(union, "A", ("L1", 8, 100), ("L2", 16, 100))
    b = _side(union, "B", ("L2", 8, 50), ("L1", 16, 50))
    lanes = _join(a, b, at=[("A", (100, 8)), ("B", (50, 8))], union=union)
    assert not lanes.joined
    assert union.find(("A", (100, 8))) != union.find(("B", (50, 16)))


def test_the_lanes_of_the_arrows_trunk_pair_at_the_arrows_x() -> None:
    """R903, R2714: the lanes of the arrow trunk end at the arrow's x, one pitch apart; a far trunk is not read."""
    union = UnionFind()
    a = _side(union, "A", ("L1", 8, 100), ("L2", 16, 100), ("L3", 24, 100), ("L9", 80, 100))
    b = _side(union, "B", ("L1", 8, 50), ("L2", 16, 50), ("L3", 24, 50), ("L9", 80, 50))
    _join(a, b, at=[("A", (100, 8)), ("B", (50, 8))], union=union)
    assert union.find(("A", (100, 16))) == union.find(("B", (50, 16)))
    assert union.find(("A", (100, 24))) == union.find(("B", (50, 24)))
    assert union.find(("A", (100, 80))) != union.find(("B", (50, 80)))


def test_a_foot_whose_piece_holds_no_port_is_bare_and_pairs_nothing() -> None:
    union = UnionFind()
    a = _side(union, "A", ("L1", 8, 100), ("L2", 16, 100), ports=False)
    b = _side(union, "B", ("L1", 8, 50), ("L2", 16, 50))
    lanes = _join(a, b, at=[("A", (100, 8)), ("B", (50, 8))], union=union)
    assert lanes.bare == {("A", (100, 8)), ("A", (100, 16))}
    assert not lanes.joined


def test_a_piece_of_two_nets_is_a_short_and_pairs_nothing() -> None:
    union = UnionFind()
    a = _side(union, "A", ("L1", 8, 100))
    b = _side(union, "B", ("L1", 8, 50))
    a[1].ports["Ax"] = (0, 8)  # a second port of another net on the same piece
    a[2]["Ax"] = "LX"
    lanes = _join(a, b, at=[("A", (100, 8)), ("B", (50, 8))], union=union)
    assert not lanes.joined
    assert not lanes.bare


def test_a_stub_meets_the_feet_whose_piece_holds_a_port_its_text_lists() -> None:
    """R1666: an off stub's text lists the conductors it ends; the lane of a listed port is met, the lane of an unlisted port is not."""
    union = UnionFind()
    a = _side(union, "A", ("L1", 8, 100), ("L2", 16, 100), ("L3", 24, 100))
    refs = SimpleNamespace(groups={}, stubs={("A", (100, 8)): {"AL1", "AL2"}})
    lanes = join_lanes(union, {"A": a[1]}, refs, a[2], 8)  # ty: ignore[invalid-argument-type] - doubles
    assert lanes.joined == {("A", (100, 8)), ("A", (100, 16))}


def _pass_through(near: str, far: str, *, far_read: bool = True):
    """Page T holds a lane with no port from one arrow to another; each arrow's reference leads to a page whose first lane has a port."""
    union = UnionFind()
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


def _short(chain: int, reach: int):
    """P1's lane of net L ends at x `reach`, its arrow stands at x 100; `chain` portless lanes T0.. lead on to P2, whose lane meets its arrow."""
    union = UnionFind()
    ts = [_side(union, f"T{i}", ("L", 16, 100), ports=False) for i in range(chain)]
    p1, p2 = _side(union, "P1", ("L", 16, reach)), _side(union, "P2", ("L", 16, 50))
    stops = [("P1", (100, 8)), *((f"T{i}", x) for i in range(chain) for x in ((0, 8), (100, 8))), ("P2", (0, 8))]
    groups = {i: [stops[2 * i], stops[2 * i + 1]] for i in range(chain + 1)}
    pages = {name: part for name, part, _ in (*ts, p1, p2)}
    nets = {k: v for _, _, found in (p1, p2) for k, v in found.items()}
    return join_lanes(union, pages, SimpleNamespace(groups=groups, stubs={}), nets, 8)  # ty: ignore[invalid-argument-type] - doubles


def test_witness_a_chain_whose_lane_stops_short_of_its_arrow_stays_bare() -> None:
    lanes = _short(2, 50)
    assert lanes.bare == {(f"T{i}", (x, 16)) for i in range(2) for x in (0, 100)}


def test_witness_one_lane_whose_neighbour_stops_short_of_its_arrow_stays_bare() -> None:
    lanes = _short(1, 50)
    assert lanes.bare == {("T0", (0, 16)), ("T0", (100, 16))}


def test_control_a_chain_whose_lanes_reach_their_arrows_is_met() -> None:
    assert not _short(2, 100).bare


def _bundle_beside(*other: tuple[str, int, int], own: tuple[tuple[str, int], ...] = (("L1", 8),), drop: tuple[str, ...] = ()):
    """Page A holds the arrow's own lanes and `other` lanes of a second bundle (portless where named in `drop`); page B holds the own lanes."""
    union = UnionFind()
    a = _side(union, "A", *((n, y, 100) for n, y in own), *other)
    b = _side(union, "B", *((n, y, 50) for n, y in own))
    for net in drop:
        a[1].ports.pop(f"A{net}")
    return union, _join(a, b, at=[("A", (100, own[0][1])), ("B", (50, own[0][1]))], union=union)


def test_a_neighbour_one_and_two_pitches_below_that_ends_short_of_the_arrow_is_not_read() -> None:
    """R3372: a lane of another bundle on the same span that does not end at the arrow's x is no foot."""
    _, lanes = _bundle_beside(("M1", 16, 90), ("M2", 24, 90), drop=("M1", "M2"))
    assert not lanes.bare


def test_an_own_lane_after_one_empty_row_is_read_with_no_other_trunk_on_the_page() -> None:
    """R3372: a net with no lane leaves a row empty: the chain steps two pitches."""
    union, _ = _bundle_beside(own=(("L1", 8), ("L3", 24)))
    assert union.find(("A", (100, 24))) == union.find(("B", (50, 24)))


def test_a_really_dropped_lane_stays_bare_beside_a_flush_neighbour_three_pitches_away() -> None:
    """R3372: the dropped lane stays bare; the neighbour at three pitches is not read in."""
    union, lanes = _bundle_beside(("M1", 48, 100), own=(("L1", 8), ("L2", 16), ("L3", 24)), drop=("L3", "M1"))
    assert lanes.bare == {("A", (100, 24))}
    assert union.find(("A", (100, 24))) != union.find(("B", (50, 24)))


def test_a_flush_neighbour_one_pitch_away_is_read_in_the_documented_limit() -> None:
    """READ-LANES-2 C1, C2: a lane of another bundle flush at one pitch is the arrow's by ink; the P1 check (bundle_of) reports it."""
    _, lanes = _bundle_beside(("M1", 16, 100), drop=("M1",))
    assert lanes.bare == {("A", (100, 16))}


def test_a_portless_chain_beside_a_far_flush_neighbour_keeps_its_k() -> None:
    """R2065: a lane of another bundle far above the arrow's on the page does not shift the k-th lane of a pass-through chain."""
    union = UnionFind()
    t = _side(union, "T", ("L", 16, 100), ("M", -40, 100), ports=False)
    t[1].ports["TM"] = (0, -40)
    p1, p2 = _side(union, "P1", ("L", 16, 50)), _side(union, "P2", ("L", 16, 50))
    groups = {1: [("T", (0, 8)), ("P1", (0, 8))], 2: [("T", (100, 8)), ("P2", (0, 8))]}
    pages = {name: part for name, part, _ in (t, p1, p2)}
    nets = {k: v for _, _, found in (t, p1, p2) for k, v in found.items()}
    lanes = join_lanes(union, pages, SimpleNamespace(groups=groups, stubs={}), nets, 8)  # ty: ignore[invalid-argument-type] - doubles
    assert not lanes.bare
    assert union.find(("T", (0, 16))) == union.find(("P1", (0, 16))) == union.find(("P2", (0, 16)))


_GROUP = frozenset({"p"})  # one port set at all four ends: the ref15/ref31 shape (KI-1491)
_TEXTS = {1: "#1-1A <-> #1-7A", 4: "#4-8A <-> #4-4B"}


def _marked(union: UnionFind[Any], name: str, number: int, *lanes: tuple[str, int, int]) -> tuple[str, Any, dict[str, str]]:
    """A side whose one reference marker stands at the first lane's end, printing the text of reference `number`."""
    side = _side(union, name, *lanes)
    box = side[1].drawing.symbols[0].outline
    end, row = lanes[0][2], lanes[0][1]
    mark = SimpleNamespace(slots=(("ref", _TEXTS[number]),), x=end, y=row, outline=box, ports=(f"m{name}",))
    side[1].drawing.symbols, side[1].nodes = [mark], {(end, row)}
    return side


def _join_both(monkeypatch: pytest.MonkeyPatch, union: UnionFind[Any], *numbered: tuple[int, tuple[str, Any, dict[str, str]]]):
    """Read the markers of the sides through `join_references` (the model's reading doubled), then their lanes."""
    ends = {(name, (0, "cell")): ((Id(kind="m", value=name), number, _GROUP, _TEXTS[number]),) for number, (name, _, _) in numbered}
    markers = {Id(kind="m", value=name): SimpleNamespace(port=SimpleNamespace(value=f"m{name}"), star=StarKind.REF) for _, (name, _, _) in numbered}
    monkeypatch.setattr(drawn_references, "reference_targets", lambda _: ends)
    monkeypatch.setattr(drawn_references, "layout_of", lambda *_: markers)
    monkeypatch.setattr(drawn_references, "_ambiguous", lambda _: [])
    monkeypatch.setattr(drawn_references, "_stands", lambda *_: True)
    pages = {name: part for _, (name, part, _) in numbered}
    nets = {k: v for _, (_, _, found) in numbered for k, v in found.items()}
    refs = join_references(None, pages, None, union)  # ty: ignore[invalid-argument-type] - doubles
    return refs, join_lanes(union, pages, refs, nets, 8)  # ty: ignore[invalid-argument-type] - doubles


@pytest.mark.rule("READ-REFERENCES")
def test_markers_on_equal_ports_with_different_numbers_are_two_references_and_both_pair_their_lanes(monkeypatch: pytest.MonkeyPatch) -> None:
    """KI-1491: a reference is its port set and its number; one group of four ends pairs only its first side, so the second pair stayed apart."""
    union = UnionFind()
    a, b = (_marked(union, n, 1, ("L1", 8, 100), ("L2", 16, 100)) for n in "AB")
    c, d = (_marked(union, n, 4, ("L2", 8, 100), ("L1", 16, 100)) for n in "CD")
    refs, lanes = _join_both(monkeypatch, union, (1, a), (1, b), (4, c), (4, d))
    assert set(refs.groups) == {(_GROUP, 1), (_GROUP, 4)}
    assert not lanes.bare
    assert union.find(("A", (100, 16))) == union.find(("B", (100, 16)))
    assert union.find(("C", (100, 16))) == union.find(("D", (100, 16)))  # the second lane of the second reference: no DANGLING_WIRE_END
    assert union.find(("A", (100, 16))) != union.find(("C", (100, 16)))


@pytest.mark.rule("READ-REFERENCES")
def test_the_same_shape_with_a_lane_cut_short_leaves_its_end_unmet_and_unpaired(monkeypatch: pytest.MonkeyPatch) -> None:
    """KI-1491: keying by number hides no real miss; a lane that stops short is no foot, so it stays unpaired with and without the key."""
    union = UnionFind()
    a, b = (_marked(union, n, 1, ("L1", 8, 100), ("L2", 16, 100)) for n in "AB")
    c, d = _marked(union, "C", 4, ("L2", 8, 100), ("L1", 16, 100)), _marked(union, "D", 4, ("L2", 8, 100), ("L1", 16, 60))
    _, lanes = _join_both(monkeypatch, union, (1, a), (1, b), (4, c), (4, d))
    assert ("C", (100, 16)) not in lanes.joined
    assert ("D", (60, 16)) not in lanes.joined
    assert union.find(("C", (100, 16))) != union.find(("D", (60, 16)))
