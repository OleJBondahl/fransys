"""Tests for core/topology_fans.py: attachments, fan ends, and the hub rule."""

from __future__ import annotations

from dataclasses import replace

import pytest

from fransys_layout.core.errors import CoreError
from fransys_layout.core.flow_values import Cell
from fransys_layout.core.topology_elements import Elem
from fransys_layout.core.topology_fans import (
    Att,
    FanDraft,
    LaneDraft,
    attached_pin,
    classify,
    deal,
    resolve,
    turn_foot_hub,
)
from fransys_layout.core.topology_nets import FanEnv, fans_of
from fransys_layout.core.values import PinRef

from .flow_builders import elem, free, net
from .topology_fixtures import box, read

_JOINED = tuple((PinRef(h, "n"), PinRef(h, "s")) for h in ("h2", "h3"))  # a hub passes its net through


def _lane(column: str, *syms: str) -> LaneDraft:
    return LaneDraft(column, 0, [Cell(s, "R0", "n", "s") for s in syms])


def _hub(name: str) -> Elem:
    return Elem(f"{name}#0", name, "free", "n", "s")


def test_a_two_end_net_of_a_box_pin_and_a_lane_end_is_an_attachment() -> None:
    syms = [elem("a"), box("c"), elem("b"), elem("d")]
    r = read(syms, [net("x", "a.n", "c.s"), net("y", "b.s", "d.n"), net("z", "a.s", "b.n", "c.n")])
    assert attached_pin(r.ends_by_net["x"]) == PinRef("c", "s")
    assert attached_pin(r.ends_by_net["y"]) is None
    assert attached_pin(r.ends_by_net["z"]) is None


def test_a_box_pin_and_a_through_end_is_an_attachment_but_two_throughs_are_not() -> None:
    """RL-W2 PORT-LINE: a terminal wired to a card pin stands on that pin."""
    r = read([box("c"), elem("h2"), elem("h3")], [net("x", "c.s", "h2.n", "h2.s")], _JOINED)
    assert attached_pin(r.ends_by_net["x"]) == PinRef("c", "s")
    r = read([box("c"), elem("h2"), elem("h3")], [net("x", "c.s", "h2.n", "h2.s", "h3.n", "h3.s")], _JOINED)
    assert attached_pin(r.ends_by_net["x"]) is None


def test_drivers_are_foot_ends_and_south_box_pins_and_legs_are_head_ends_and_north_ones() -> None:
    syms = [elem("a"), elem("b"), elem("c"), box("p"), box("q")]
    r = read(syms, [net("t", "a.s", "b.n", "c.n", "p.s", "q.n")])
    la, lb, lc = _lane("A", "a"), _lane("B", "b"), _lane("C", "c")
    slot = {("a@s", "s"): (la, "foot"), ("b@n", "n"): (lb, "head"), ("c@n", "n"): (lc, "head")}
    drivers, legs, throughs, cross = classify(r.ends_by_net["t"], slot, r.syms)
    assert drivers == [Att(la, "foot"), Att(None, "boxpin", PinRef("p", "s"))]
    assert legs == [Att(lb, "head"), Att(lc, "head"), Att(None, "boxpin", PinRef("q", "n"))]
    assert (throughs, cross) == ([], False)


def test_an_end_off_a_lane_end_is_a_cross_link_and_a_hub_is_a_through() -> None:
    r = read([elem("a"), elem("b"), elem("c")], [net("t", "a.s", "b.s", "c.n")])
    slot = {("a@s", "s"): (_lane("A", "a"), "foot")}
    _, _, throughs, cross = classify(r.ends_by_net["t"], slot, r.syms)
    assert cross
    assert throughs == []
    r = read([elem("a"), elem("h2")], [net("t", "a.s", "h2.n", "h2.s")], _JOINED)
    assert classify(r.ends_by_net["t"], {}, r.syms)[2] == ["h2#0"]


def test_hub_with_no_driver_heads_the_first_leg_and_others_stay() -> None:
    l1, l2 = _lane("L1", "x"), _lane("L2", "y")
    fan = FanDraft("f", ["t"], [], [Att(l1, "head"), Att(l2, "head")])
    new = deal(fan, ["h#0"], {"h#0": _hub("h")}, "c:")
    assert [c.sym for c in l1.cells] == ["h", "x"]
    assert [c.sym for c in l2.cells] == ["y"]
    assert (fan.hub, new) == ("h", ())
    assert fan.drivers == [Att(l1, "hub-head")]
    assert fan.legs == [Att(l1, "after-hub"), Att(l2, "head")]


def test_hub_with_no_leg_foots_the_first_driver() -> None:
    d = _lane("D", "x")
    fan = FanDraft("f", ["t"], [Att(d, "foot")], [])
    deal(fan, ["h#0"], {"h#0": _hub("h")}, "c:")
    assert [c.sym for c in d.cells] == ["x", "h"]
    assert fan.hub == "h"
    assert fan.drivers == [Att(d, "before-hub")]
    assert fan.legs == [Att(d, "hub-foot")]


def test_the_rest_are_dealt_one_per_leg_in_the_order_given_then_to_new_lanes() -> None:
    d, l1, l2 = _lane("D", "x"), _lane("L1", "y"), _lane("L2", "z")
    fan = FanDraft("f", ["t"], [Att(d, "foot")], [Att(l1, "head"), Att(l2, "head")])
    elems = {f"{n}#0": _hub(n) for n in ("h10", "h2", "h3")}
    new = deal(fan, list(elems), elems, "c:")
    assert [c.sym for c in l1.cells] == ["h10", "y"]
    assert [c.sym for c in l2.cells] == ["h2", "z"]
    assert [lane.column for lane in new] == ["c:h3"]
    assert fan.legs[-1] == Att(new[0], "head")
    assert fan.hub is None


def test_resolve_gives_final_indexes_and_pins_after_a_hub_is_dealt() -> None:
    l1 = _lane("L1", "x")
    fan = FanDraft("f", ["t"], [], [Att(l1, "head")])
    deal(fan, ["h#0"], {"h#0": _hub("h")}, "c:")
    fan.drivers = [replace(a, net="t") for a in fan.drivers]
    fan.legs = [replace(a, net="t") for a in fan.legs]
    assert resolve(fan.drivers[0]).cell == 0
    assert resolve(fan.drivers[0]).pin == PinRef("h", "s")
    assert resolve(fan.legs[0]).cell == 1
    assert resolve(fan.legs[0]).pin == PinRef("x", "n")


def test_resolve_refuses_an_attachment_with_no_net() -> None:
    with pytest.raises(CoreError, match="no net"):
        resolve(Att(_lane("L1", "x"), "head"))


def test_a_hub_at_a_lanes_foot_turns_to_stand_with_its_net_pin_toward_the_lane() -> None:
    d = _lane("D", "x")
    fan = FanDraft("f", ["t"], [Att(d, "foot")], [])
    deal(fan, ["h#0"], {"h#0": _hub("h")}, "c:")
    turn_foot_hub(fan, {"h": "s"})
    hub = d.cells[1]
    assert (hub.sym, hub.orient, hub.top_pin) == ("h", "R180", "s")


def test_a_leg_head_turns_to_have_its_facing_pin_on_top() -> None:
    """R924: the cell dealt to a leg head has the facing pin on top."""
    leg = _lane("L", "x")
    fan = FanDraft("f", ["t"], [Att(_lane("D", "y"), "foot")], [Att(leg, "head")])
    deal(fan, ["h#0"], {"h#0": _hub("h")}, "c:")
    turn_foot_hub(fan, {"h": "s"})
    assert (leg.cells[0].orient, leg.cells[0].top_pin) == ("R180", "s")


def test_a_through_end_of_a_net_that_becomes_a_cross_link_is_dealt_a_cell_and_the_link_keeps_it() -> None:
    """layout-0486: a net role places a symbol, it never withholds one; the terminal wired on one side stands on that pin."""
    r = read([elem("a"), elem("b"), free("h2")], [net("t", "a.s", "b.s", "h2.n")])
    env = FanEnv({}, [], r.elems, r.syms, {})
    _, links, _, _ = fans_of(r.ends_by_net, {}, env)
    assert [(k[0].split("#")[0], k[1]) for k in env.slot] == [("h2", "n")]
    assert len(env.lanes) == 1
    assert {a.pin.sym for a in links[0].ends} == {"a", "b", "h2"}


def test_an_element_wired_to_a_cross_net_by_one_pin_and_a_fan_by_the_other_is_dealt_once() -> None:
    """One slot key (the n pin) for a dealt through element, whichever pin the first net to deal it uses."""
    syms = [elem("a"), elem("b"), free("h"), elem("src"), elem("l1"), elem("l2")]
    r = read(syms, [net("x", "a.s", "b.s", "h.s"), net("y", "src.s", "h.n", "l1.n", "l2.n")])
    slot = {("src@s", "s"): (_lane("S", "src"), "foot"), ("l1@n", "n"): (_lane("L1", "l1"), "head"), ("l2@n", "n"): (_lane("L2", "l2"), "head")}
    env = FanEnv(slot, [], r.elems, r.syms, {})
    fans, links, _, _ = fans_of(r.ends_by_net, {}, env)
    lanes = {id(lane): lane for lane in (*env.lanes, *(v[0] for v in slot.values()))}
    standing = [c.sym for lane in lanes.values() for c in lane.cells]
    assert (len(links), len(fans), standing.count("h")) == (1, 1, 1)
