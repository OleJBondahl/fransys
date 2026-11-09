"""A terminal wired from two drawing sets of one document is drawn in both (WHERE-WIRED, R652)."""

from dataclasses import replace
from typing import Any, NamedTuple

import fransys as fr
import pytest
from _model_build_cover import unit_document
from conventions_fixtures import house
from fransys.colours import BN
from fransys_el import build, symbol_kit
from fransys_el.placement_env import make_env
from fransys_el.placement_sets import drawing_scopes, frame_titles, restriction, scope_groups
from fransys_el.placement_syms import strip_tags

from electrical_symbols import LIBRARY
from fransys_layout.core import PagePlan
from fransys_model.derive import function_replicas, function_scopes, item_functions
from fransys_model.derive.tag_text import external_note


class _Io(NamedTuple):
    X1: fr.TerminalStrip


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Io:
    return _Io(u.terminal_strip("X1", "DEMO-TB-FUSE-2.5-TWIN", 1, interface=(1,)))


class _Open(NamedTuple):
    pass


@fr.unit("demo-skid", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _skid(u: Any) -> _Open:
    cab = u.add(_cab, "N")
    ends = (cab.X1[1].outer, cab.X1[1].outer)  # the point takes 2 (R1266): the second valve chains from the first
    for i in (1, 2):
        with u.function(f"V{i}", f"Valve {i}"):
            v = u.device(f"V{i}", "DEMO-ACT-4P-2SW")
            c = u.cable(f"W{i}", "DEMO-CBL-8G0.75", length_m=5)
            c.core(1, ends[0], v.power["1"])
            c.core(2, ends[1], v.power["2"])
            ends = (v.power["1"], v.power["2"])
    return _Open()


@pytest.fixture(scope="module")
def drawn():
    d = fr.design("demo_parts")
    d.add(_skid, "S1", place=None)

    model = fr.build(d, unit_document("demo-skid")).model
    kit = symbol_kit(model, LIBRARY)
    problem, _ = build(model, kit, house(), LIBRARY)
    return model, kit, problem


def test_the_scope_of_the_device_holds_a_replica_and_the_scope_of_the_strip_holds_none(drawn) -> None:
    model, kit, _ = drawn
    scopes = drawing_scopes(model, kit)
    assert [bool(s.replicas) for s in scopes].count(True) == 1
    (copied,) = (s for s in scopes if s.replicas)
    assert copied.replicas <= copied.symbols


def test_the_net_is_whole_in_the_set_that_draws_the_copy_and_cut_where_one_pin_is_left(drawn) -> None:
    model, kit, problem = drawn
    scopes = drawing_scopes(model, kit)
    tags = strip_tags(make_env(model, kit, house(), LIBRARY))
    (copied,) = (s for s in scopes if s.replicas)
    made = restriction(problem, copied, scopes=scopes, options=house().options, tags=tags)
    assert all(n.cut == () for n in made.problem.nets if {p.sym for p in n.pins} & copied.replicas)
    units = {s.id: (s.unit, s.labels) for s in problem.symbols}
    mine = [s for s in made.problem.symbols if s.id in copied.replicas]
    assert mine
    assert all(s.unit == ("" if copied.of_unit is None else copied.of_unit.value) and s.labels == units[s.id][1] for s in mine)
    assert all(units[s.id][0] != s.unit for s in mine)  # the replica leaves its home unit, keeps its printed label
    home = next(s for s in scopes if s is not copied and s.symbols & copied.replicas)
    alone = restriction(problem, home, scopes=scopes, options=house().options, tags=tags)
    lone = [n for n in alone.problem.nets if len(n.pins) == 1 and n.pins[0].sym in copied.replicas]
    assert lone
    assert all(n.cut for n in lone)


def _two_documents(top: Any, place: str | None = None) -> Any:
    d = fr.design("demo_parts", place=place)
    where = [d.location(place, "External")] if place else []
    top(d)
    documents = [unit_document(n) for n in ("demo-skid", "demo-cab", *where)]
    return fr.build(d, *documents).model


def test_a_terminal_wired_into_another_document_keeps_one_scope() -> None:
    """A top-level strip (no unit boundary) wired to a unit's device in another document stays in its own set."""

    def top(d: Any) -> None:
        d.add(_skid, "S1", place=None)
        strip = d.terminal_strip("X0", "DEMO-TB-2.5", 3)
        d.series(strip, d.cable("W9", "DEMO-CBL-4G1.5", length_m=5), d.device("M9", "DEMO-MOTOR-4KW").motor, wire=2.5)

    model = _two_documents(top, place="EXT")
    functions = [f for fs in item_functions(model).values() for f in fs]
    assert [f for f in functions if len(function_scopes(model, f)) > 1 and not function_replicas(model, f)] == []


def test_a_boundary_terminal_wired_into_another_document_is_still_drawn_in_the_enclosing_set() -> None:
    """R686: the boundary terminal of the nested unit takes the set of the unit that encloses it, whatever the document."""
    model = _two_documents(lambda d: d.add(_skid, "S1", place=None))
    boundary = [f for fs in item_functions(model).values() for f in fs if len(function_scopes(model, f)) > 1]
    assert len(boundary) == 1
    home, parent = function_scopes(model, boundary[0])
    assert home != parent
    assert function_replicas(model, boundary[0]) == {parent}


class _Mains(NamedTuple):
    L1: Any
    L2: Any
    L3: Any
    N: Any


@fr.unit("demo-rail", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _rail(u: Any) -> _Mains:
    w = {"wire": (BN, 1.5)}
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5-TWIN", interface=True)
    runs = [x1.run(k, 1) for k in ("L1", "L2", "L3", "N")]
    q1 = u.device("Q1", "DEMO-ISO-4P")
    for r, pin in zip(runs, "1357", strict=True):
        u.series(r[1].inner, q1.main[pin], **w)
    rail = u.terminal_strip("X01", "DEMO-TB-2.5").run("L1", 4, bridged=True)
    u.series(q1.main["2"], rail[1].inner, **w)
    f01, t1 = u.device("F01", "DEMO-MCB-3P"), u.device("T1", "DEMO-PSU-24")
    u.series(rail[2].inner, f01.element["1"], **w)
    u.series(f01.element["2"], t1.input["L"], **w)
    u.series(runs[3][1].inner, t1.input["N"], **w)
    x2 = u.terminal_strip("X2", "DEMO-TB-2.5")
    u.series(t1.output["+"], x2.run("24V", 1)[1].inner, **w)
    u.series(t1.output["-"], x2.run("GND", 1)[1].inner, **w)
    for n in (1, 2):
        k, m = u.device(f"Q{n + 1}", "DEMO-CTR-3P-24"), u.device(f"M{n}", "DEMO-MOTOR-4KW")
        u.series(rail[2 + n].inner, k.main["1"], **w)
        u.series(k.main["2"], m["U"], **w)
    return _Mains(*runs)


@pytest.fixture(scope="module")
def railed():
    d = fr.design("demo_parts", place="EXT")
    d.location("EXT", "External")
    cab = d.add(_rail, "U1", place=None)
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5", external=True)
    w1 = d.cable("W1", "DEMO-CBL-4G1.5", length_m=10)
    for i, k in enumerate(("L1", "L2", "L3", "N"), 1):
        w1.core(i, x0.run(k, 1)[1], cab[i - 1][1])
    return fr.build(d, unit_document("demo-rail"))


def test_a_rail_fed_from_copies_of_top_level_terminals_leaves_no_connection_undrawn(railed) -> None:
    """Pump-station shape: a copy keeping its home unit split the L1 rail across two unit lists (KI-178)."""
    missing = [f for f in fr.check(railed) if f.code == "CONNECTION_NOT_DRAWN"]
    assert len(missing) <= 5, "the N wire short of -T1:N and the four cable-core pairs with no wire or stub may stand (KI-132, MC-PROBE-1, R815)"


@pytest.mark.rule("PAGE-TITLE")
def test_a_terminal_copy_adds_no_group_to_a_page_title(drawn) -> None:
    """R734 G6, R733: a group only a copy carries is no title part of that page; a replica's group is."""
    model, kit, problem = drawn
    scopes = drawing_scopes(model, kit)
    (replicated,) = (s for s in scopes if s.replicas)
    grouped = replace(problem, symbols=tuple(replace(s, group="HOME") if s.id in replicated.replicas else s for s in problem.symbols))
    page = PagePlan(1, "", (), groups=("HOME", "V1", "V2"))
    (kept,) = scope_groups((page,), grouped, replicated)
    assert kept.groups == ("HOME", "V1", "V2")
    as_copy = replace(replicated, copies=replicated.replicas, replicas=frozenset())
    (dropped,) = scope_groups((page,), grouped, as_copy)
    assert dropped.groups == ("V1", "V2")


def test_a_unit_set_frames_its_replicas_and_a_place_set_frames_only_an_external_root(drawn, railed) -> None:
    """R833, R1093, R2047: the skid set frames the strip's unit; the set of no unit (a place) frames no unit, only the external strip as by others."""
    model, kit, _ = drawn
    (framed,) = (s for s in drawing_scopes(model, kit) if s.frames)
    assert framed.of_unit is not None
    assert framed.replicas == frozenset().union(*(members for _, members in framed.frames))
    rail_kit = symbol_kit(railed.model, LIBRARY)
    (place,) = (s for s in drawing_scopes(railed.model, rail_kit) if s.of_unit is None)
    assert place.replicas
    titles = frame_titles(railed.model, rail_kit)
    assert place.frames
    assert {titles[key] for key, _ in place.frames} == {("unit-outline-by-others", external_note())}
