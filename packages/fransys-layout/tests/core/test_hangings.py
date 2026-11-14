"""PageEnv.hangings: one Hanging per drawn thing at a pin, built once per page (layout-0395)."""

from __future__ import annotations

from dataclasses import replace

import pytest
from options_fixtures import core_options

from fransys_layout.core import Facts, PlacementProblem
from fransys_layout.core.cut_drawn import stand_pins
from fransys_layout.core.flow_values import Attach, Fan
from fransys_layout.core.geometry import marker_box, marker_box_at, marker_drawn_box, shift
from fransys_layout.core.hang_build import page_hangings
from fransys_layout.core.hangings import hanging_keep
from fransys_layout.core.outputs import Marker
from fransys_layout.core.place_env import page_envs
from fransys_layout.core.route_env import pin_sides
from fransys_layout.core.sides import SIDE_STEP
from fransys_layout.core.text_ends import abut
from fransys_layout.core.values import (
    Anchor,
    Box,
    Options,
    PinRef,
    Pose,
    Ref,
    RefEnd,
    RefKind,
    Side,
)

from .conftest import MARKER
from .cut_fixtures import AREA, box_sym, elem, free
from .cut_fixtures import cut_of as cut_of_syms
from .cut_fixtures import net as cut_net
from .flow_builders import net, poles
from .pipeline_fixtures import cut_of

OPTIONS = core_options(
    marker=MARKER,
)


def _env():
    syms = (box_sym(1), poles("L", 2))
    nets = (net("n1", "A1.p1", "L.n0"), net("n2", "A1.p1", "L.n1"))
    prob = PlacementProblem(AREA, syms, nets, facts=Facts(far_ends=()))
    (env,) = page_envs(cut_of(prob, OPTIONS), prob, OPTIONS)
    return env


def _tag(pin: PinRef, page: int) -> Ref:
    return Ref("n1", RefKind.TAG, (RefEnd(page, None, pin),))


def test_a_one_tag_page_has_one_tag_hanging_on_the_pins_side() -> None:
    env = _env()
    pin = PinRef("L", "n0")
    found = page_hangings([_tag(pin, env.plan.page)], env.problem, OPTIONS, (env.plan.page, frozenset()))
    sides = pin_sides(env.problem)
    assert found
    assert {key[:2] for key in found} == {("L", "n0")}
    for key, (only,) in found.items():
        assert (only.kind, only.pin, only.side) == ("tag", pin, sides[key])


def test_a_page_with_no_ref_and_no_anchor_has_no_hangings() -> None:
    env = _env()
    assert env.hangings == {}


def _kind_boxes(kind: RefKind, options: Options) -> dict[tuple[str, str, str], tuple[Side, Box]]:
    """For a free symbol's pins n and e: (sym, pin, orient) -> (side, box_rel) of its hanging."""
    prob = PlacementProblem(AREA, (free("H"),), (), facts=Facts(far_ends=()))
    ends = tuple(RefEnd(1, None, PinRef("H", p)) for p in ("n", "e"))
    found = page_hangings([Ref("n1", kind, ends)], prob, options, (1, frozenset()))
    return {key: (hs[0].side, hs[0].box_rel) for key, hs in found.items()}


def _marker_at(key: tuple[str, str, str], side: Side, kind: RefKind) -> Box:
    """The marker box turned to face `side`, its near edge at the pin: the test's own arithmetic."""
    sym, pin, _ = key
    box = marker_box_at(0, 0, OPTIONS, OPTIONS.marker_facing[side], (PinRef(sym, pin), str(kind)))
    depth = {"E": -box.x, "W": box.x + box.w, "S": -box.y, "N": box.y + box.h}[side]
    dx, dy = SIDE_STEP[side]
    return shift(box, dx * depth, dy * depth)


@pytest.mark.parametrize("open_stub", [0, 40])
def test_a_stub_marker_moves_out_by_open_stub_along_each_side(open_stub: int) -> None:
    boxes = _kind_boxes(RefKind.STUB, replace(OPTIONS, open_stub=open_stub))
    assert {side for side, _ in boxes.values()} == {"N", "E", "S", "W"}
    for key, (side, box) in boxes.items():
        dx, dy = SIDE_STEP[side]
        assert box == shift(_marker_at(key, side, RefKind.STUB), open_stub * dx, open_stub * dy)


def test_a_tag_does_not_move_with_open_stub() -> None:
    boxes = _kind_boxes(RefKind.TAG, replace(OPTIONS, open_stub=40))
    for key, (side, box) in boxes.items():
        assert box == _marker_at(key, side, RefKind.TAG)


def _pose(i: int) -> Pose:
    return Pose("R0", (0, 0), Box(i, 2 * i, 7, 9), (0, 0))


POSES: tuple[tuple[Side, Pose], ...] = (
    ("N", _pose(0)),
    ("E", _pose(1)),
    ("S", _pose(2)),
    ("W", _pose(3)),
)


def _b2_hangings(options: Options = OPTIONS):
    """A tag (twice), copy, star, stub and an arrow on page 1, a tag on page 2, one anchor."""
    pin = {k: PinRef("H", k) for k in "nesw"}
    page = 1

    def ref(kind: RefKind, *ends: RefEnd) -> Ref:
        return Ref("n1", kind, ends)

    refs = [
        ref(RefKind.TAG, RefEnd(page, None, pin["n"]), RefEnd(2, None, pin["n"])),
        ref(RefKind.TAG, RefEnd(page, None, pin["n"])),
        ref(RefKind.COPY, RefEnd(page, None, pin["e"])),
        ref(RefKind.STAR, RefEnd(page, None, pin["s"])),
        ref(RefKind.STUB, RefEnd(page, None, pin["w"])),
        ref(RefKind.ARROW, RefEnd(page, None, pin["e"])),
    ]
    prob = PlacementProblem(AREA, (free("H"),), (), facts=Facts(far_ends=()), anchors=(Anchor(pin["n"], POSES),))
    return prob, refs, page_hangings(refs, prob, options, (page, frozenset({"H"})))


def test_every_drawn_thing_has_exactly_one_hanging() -> None:
    prob, _, found = _b2_hangings()
    sides = pin_sides(prob)
    kinds = {"n": ["tag", "tag", "anchor"], "e": ["copy"], "s": ["star"], "w": ["stub"]}
    for (sym, pin, orient), side in sides.items():
        assert [h.kind for h in found.get((sym, pin, orient), ())] == kinds[pin], (pin, orient)
        assert all(h.side == side and h.pin == PinRef(sym, pin) for h in found[(sym, pin, orient)])


def test_each_box_is_its_marker_box_or_its_pose_outline_and_keeps_at_the_pin() -> None:
    _, _, found = _b2_hangings()
    for key, hs in found.items():
        for h in hs:
            if h.kind == "anchor":
                assert h.box_rel == dict(POSES)[h.side].outline
            else:
                assert h.box_rel == _marker_at(key, h.side, RefKind(h.kind))
            keep = hanging_keep(h, (10, 20), "H", None)
            assert keep.box == shift(h.box_rel, 10, 20)


def test_every_drawn_marker_has_its_hanging_so_the_skip_hides_none() -> None:
    prob, refs, found = _b2_hangings()
    drawn = [(e.pin, str(r.kind)) for r in refs if r.kind is not RefKind.ARROW for e in r.ends if e.page == 1]
    for sym, pin, orient in pin_sides(prob):
        have = [h.kind for h in found.get((sym, pin, orient), ()) if h.kind != "anchor"]
        assert have == [k for p, k in drawn if (p.sym, p.pin) == (sym, pin)]


def test_an_arrow_and_another_pages_end_get_no_hanging() -> None:
    _, _, found = _b2_hangings()
    assert "arrow" not in {h.kind for hs in found.values() for h in hs}
    assert [h.kind for h in found[("H", "n", "R0")]].count("tag") == 2


def test_a_missing_marker_size_skips_the_marker_but_not_the_anchor() -> None:
    _, _, found = _b2_hangings(replace(OPTIONS, marker=None))
    assert {h.kind for hs in found.values() for h in hs} == {"anchor"}


def test_page_hangings_over_a_real_cut_count_the_non_arrow_ends_and_anchors() -> None:
    syms = [free("t0"), elem("k1", 700, 400), elem("k2", 600, 400), elem("k3", 600, 400)]
    nets = [cut_net("feed", "t0.e", "k1.n", "k2.n", "k3.n")]
    prob = PlacementProblem(AREA, tuple(syms), tuple(nets), facts=Facts(far_ends=()))
    cut = cut_of_syms(syms, nets, options=OPTIONS)
    envs = page_envs(cut, prob, OPTIONS)
    assert len(envs) == 2
    counts = []
    for env in envs:
        ends = [e for r in env.refs if r.kind is not RefKind.ARROW for e in r.ends]
        drawn = sum(e.page == env.plan.page for e in ends)
        found = sum(len(hs) for (_, _, o), hs in env.hangings.items() if o == "R0")
        counts.append((found, drawn))
    assert all(f == d for f, d in counts)
    assert sum(d for _, d in counts) > 0


def test_a_tags_hanging_box_is_the_route_obstacle_box_of_the_marker_standing_there() -> None:
    """layout-0406: one tag box for the hanging and the route obstacle, both the stretched one."""
    wide = {o: Box(b.x, b.y, b.w + 20, b.h + 20) for o, b in MARKER.items()}
    options = replace(OPTIONS, link_fit=wide)
    boxes = _kind_boxes(RefKind.TAG, options)
    assert boxes
    for (sym, pin, _), (side, box) in boxes.items():
        end = PinRef(sym, pin)
        stand = abut(options, side, 0, 0, (end, "tag"))
        tag = Marker("n1", RefKind.TAG, 1, "c", stand.x, stand.y, end, stand.orient)
        assert box == marker_drawn_box(tag, options)
        assert box != marker_box(tag, options)


def test_a_mixed_pins_hanging_stands_at_a_vertical_sibling_and_stays_at_a_horizontal_one() -> None:
    """R548, R829: `Hanging.pin` is the xy pin; `stand_pins` keeps the sibling's side only where it is vertical."""
    pin = {k: PinRef("H", k) for k in "news"}
    far = {k: PinRef("F", k) for k in "news"}
    refs = [Ref("n1", RefKind.STUB, (RefEnd(1, None, pin["w"]),))]
    prob = PlacementProblem(AREA, (free("H"),), (), facts=Facts(far_ends=()))
    undrawn = [(pin["w"], far["w"])]
    vertical = stand_pins([*undrawn, (pin["w"], far["e"])], ([(pin["w"], far["e"])], (), ()), prob.symbols)
    placed = page_hangings(refs, prob, OPTIONS, (1, frozenset({"H"})), vertical)
    assert {(k[1], h.pin.pin, h.side in "NS") for k, hs in placed.items() for h in hs} == {("n", "n", True)}
    pairs = [(pin[k], far[k]) for k in "nsw"]
    horizontal = stand_pins([*pairs, (pin["w"], far["e"])], (pairs, (), ()), prob.symbols)
    placed = page_hangings(refs, prob, OPTIONS, (1, frozenset({"H"})), horizontal)
    assert {(k[1], h.pin.pin) for k, hs in placed.items() for h in hs} == {("w", "w")}


def test_a_mixed_pin_stands_at_the_first_free_vertical_pin_though_a_horizontal_one_comes_first() -> None:
    """R829: with `n` and `w` drawn, `e` (horizontal) comes before `s` in pin order; the stand takes `s`, not the pin itself."""
    pin = {k: PinRef("H", k) for k in "news"}
    far = {k: PinRef("F", k) for k in "news"}
    prob = PlacementProblem(AREA, (free("H"),), (), facts=Facts(far_ends=()))
    pairs = [(pin["n"], far["n"]), (pin["w"], far["w"])]
    got = stand_pins([*pairs, (pin["w"], far["e"])], (pairs, (), ()), prob.symbols)
    assert got[pin["w"]]["R0"] == pin["s"]


def test_a_fan_wired_pin_with_a_stub_is_mixed_on_every_symbol_free_sided_or_plain() -> None:
    """R971: a fan-wired pin that stands a stub stands at the free vertical pin, else has none (a ONE-SIDED-PIN leg)."""
    syms = (free("H"), elem("P"))
    attach = {sym: Attach(None, 0, 0, PinRef(sym, "n" if sym == "H" else "s"), net="n1") for sym in ("H", "P")}
    fan = Fan("f", ("n1",), tuple(attach.values()), (), None, 1, "N")
    far = PinRef("F", "x")
    got = stand_pins([(a.pin, far) for a in attach.values()], ((), (fan,), {a.pin for a in attach.values()}), syms)
    assert set(got) == {a.pin for a in attach.values()}
    assert got[attach["H"].pin]["R0"] == PinRef("H", "s")
    assert got[attach["P"].pin] == {"R0": None, "R180": None}
    assert stand_pins([(a.pin, far) for a in attach.values()], ((), (fan,), ()), syms) == {}
    pair = (PinRef("H", "n"), PinRef("G", "y"))
    sibling_fan = Fan("g", ("n2",), (Attach(None, 0, 0, PinRef("H", "s"), net="n2"),), (), None, 1, "N")
    got = stand_pins([pair, (pair[0], far)], ([pair], (sibling_fan,), ()), (free("H"),))
    assert got[pair[0]]["R0"] == PinRef("H", "s")  # a paired mixed pin stands at the sibling the pairs leave free, a fan pin or not
