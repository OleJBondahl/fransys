"""POWER-NET: a trunk leaves the room an anchored item on a card's pin row reaches (R510)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core import Facts, PlacementProblem
from fransys_layout.core.node_names import box_y_node
from fransys_layout.core.place_trunk import box_at, trunk_node
from fransys_layout.core.place_x import place_x
from fransys_layout.core.place_y import place_y
from fransys_layout.core.values import Anchor, Box, PinRef, Pose

from .cut_fixtures import AREA, box_sym, elem
from .flow_builders import net
from .test_place_x import env_of

REACH = 40


def _card_leg(*, anchored: bool, held: tuple[str, ...] = ("A1.p1", "A1.p3")) -> PlacementProblem:
    """Elements k1 and k3 drive the card pins in `held`; pin p2 carries a 0V-like item."""
    syms = (box_sym(4, north=4), elem("k1"), elem("k3"))
    nets = [net("v", "k1.s", "k3.s", *held), net("zero", "A1.p2")]
    pose = Pose("R0", (0, -REACH), Box(-8, -REACH, 16, REACH - 8), (0, -8))
    anchors = (Anchor(PinRef("A1", "p2"), (("N", pose),)),) if anchored else ()
    return replace(PlacementProblem(AREA, syms, tuple(nets), Facts()), anchors=anchors)


def _gap(prob: PlacementProblem) -> int:
    """The y from the trunk to the card's pin row."""
    env = env_of(prob)
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
