"""POWER-NET: a trunk leaves the room an anchored item on a card's pin row reaches (R510)."""

from __future__ import annotations

from dataclasses import replace

import pytest
from turn_fixtures import refit

from fransys_layout.core import Facts, Hints, PlacementProblem
from fransys_layout.core.geometry import overlaps
from fransys_layout.core.hangings import Hanging
from fransys_layout.core.node_names import box_y_node
from fransys_layout.core.place_trunk import box_at, trunk_node
from fransys_layout.core.place_x import place_x
from fransys_layout.core.place_y import place_y
from fransys_layout.core.solve import solve
from fransys_layout.core.values import Anchor, Box, PinRef, Pose

from .cut_fixtures import AREA, box_sym, elem
from .flow_builders import net
from .pipeline_fixtures import solved_of
from .place_fixtures import _coil_card
from .test_outline import _ROOM, _opts
from .test_place_x import env_of

REACH = 40


def _card_leg(*, anchored: bool, held: tuple[str, ...] = ("A1.p1", "A1.p3")) -> PlacementProblem:
    """Elements k1 and k3 drive the card pins in `held`; pin p2 carries a 0V-like item."""
    syms = (box_sym(4, north=4), elem("k1"), elem("k3"))
    nets = [net("v", "k1.s", "k3.s", *held), net("zero", "A1.p2")]
    pose = Pose("R0", (0, -REACH), Box(-8, -REACH, 16, REACH - 8), (0, -8))
    anchors = (Anchor(PinRef("A1", "p2"), (("N", pose),)),) if anchored else ()
    return replace(PlacementProblem(AREA, syms, tuple(nets), Facts()), anchors=anchors)


def _gap(prob: PlacementProblem, hung: str | None = None) -> int:
    """The y from the trunk to the card's pin row, with a `hung`-kind hanging of REACH over pin p2 when given."""
    env = env_of(prob)
    if hung:
        box = Box(-6, -REACH, 12, REACH)
        env = replace(env, hangings={("A1", "p2", "R0"): (Hanging(PinRef("A1", "p2"), "N", box, hung),)})
    x, _ = place_x(env)
    y, findings = place_y(env, x)
    assert findings == ()
    (fan,) = env.flow.fans
    at = box_at(env, "A1")
    assert at is not None
    return y[box_y_node("A1")] - y[trunk_node(fan.id, at[1])]


@pytest.mark.rule("POWER-NET")
def test_a_trunk_leaves_a_card_rows_anchored_item_room() -> None:
    assert _gap(_card_leg(anchored=True)) >= REACH


@pytest.mark.rule("POWER-NET")
def test_a_card_row_with_no_anchored_item_keeps_its_gap() -> None:
    assert _gap(_card_leg(anchored=False)) < REACH


@pytest.mark.rule("POWER-NET")
def test_a_trunk_that_ends_before_the_anchored_item_keeps_its_gap() -> None:
    """The trunk stops at p1, so the item on p2 stands beyond its end and asks no room."""
    assert _gap(_card_leg(anchored=True, held=("A1.p1",))) < REACH


@pytest.mark.rule("PAGE-CUT")
def test_a_trunk_clears_a_lead_hanging_but_not_a_tag_hanging() -> None:
    """The lead hanging spans a cut pin's lead and its tag (CND-D-FIX); the other kinds wait (KI-333)."""
    prob = _card_leg(anchored=False)
    assert _gap(prob, "lead") >= REACH
    assert _gap(prob, "tag") < REACH


def test_a_column_driver_clears_a_step_out_cell_only_when_its_cell_has_no_pin_beside_it() -> None:
    """R1313: a two-pin element (pins on one line) steps out along the trunk's way; a free-sided cell steps out sideways."""
    from fransys_layout.core.flow_values import Cell
    from fransys_layout.core.place_trunk import _steps_out

    from .cut_fixtures import free

    two, four = elem("k1"), free("t1")
    assert _steps_out(two, Cell("k1", "R0", "n", "s"), "s")
    assert not _steps_out(four, Cell("t1", "R0", "n", "s"), "s")


def test_a_frame_members_placed_footprint_is_its_bare_join_grown_by_the_frame_room_once() -> None:
    """Anchored outline joins bare (reserved), then `framed` adds the margin and label room once. Probe: reserved adds the margin too."""
    pose = Pose("R0", (0, -REACH), Box(-8, -REACH, 16, REACH - 8), (0, -8))
    syms = (elem("k1"), elem("k2"))
    nets = (net("v", "k1.s", "k2.n"),)
    base = replace(PlacementProblem(AREA, syms, nets, Facts()), anchors=(Anchor(PinRef("k1", "n"), (("N", pose),)),))
    room = _ROOM
    got = {}
    for tag, hints in (("bare", Hints()), ("framed", Hints(frames=(("u", frozenset({"k1"})),)))):
        layout = solve(replace(base, hints=hints), _opts(outline=room))
        p = next(p for pg in layout.placement.pages for p in pg.placed if p.sym == "k1")
        got[tag] = Box(p.footprint.x - p.body.x, p.footprint.y - p.body.y, p.footprint.w, p.footprint.h)
    b, top = got["bare"], room.label.y + room.label.h
    assert got["framed"] == Box(b.x - room.margin, b.y - top, b.w + 2 * room.margin, b.h + top + room.margin)


@pytest.mark.parametrize("north", [0, 1])
def test_a_column_with_a_hanging_attached_to_a_framed_card_stands_clear_of_its_frame(north: int) -> None:
    """The frame is the card's footprint grown by the margin and label room; a cell with a hanging stands off that, not off the body."""
    base = _coil_card(["k1"], 16, north)
    coil = refit(next(s for s in base.symbols if s.id == "k1"), footprint=Box(-8, -40, 16, 80))
    prob = replace(base, symbols=(base.symbols[0], coil), hints=Hints(frames=(("u", frozenset({"A1"})),)))
    placement = solved_of(prob, _opts(outline=_ROOM)).placement
    (frame,) = placement.outlines
    assert [p.sym for p in placement.pages[0].placed if overlaps(frame.box, p.footprint) and p.sym != "A1"] == []
