"""Origins: every record's file and line is the calling test line.

The frame walk finds the first frame outside `fransys_author`, comparing module
names, not paths; this test file's own lines are what every assertion checks against.
"""

import os
from typing import TYPE_CHECKING, Any

from caller_line import here
from fransys_author.design import Design

if TYPE_CHECKING:
    from fransys_model.kernel import Draft, Id, Origin


def _origin_of(draft: Draft, target: Id[Any]) -> Origin:
    origin = draft.origin_of(target)
    assert origin is not None
    return origin


def _same_file(origin_file: str, this_file: str) -> bool:
    """Path equality on this OS, not as strings.

    `caller_origin()` records `frame.f_code.co_filename` exactly as Python reports it, which
    on Windows is spelled with whatever letter case the process's cwd had when the module was
    """
    return os.path.normcase(origin_file) == os.path.normcase(this_file)


def _assert_at(d, target: Id[Any], line: int) -> None:
    origin = _origin_of(d.draft(), target)
    assert _same_file(origin.file, __file__)
    assert origin.line == line


def test_project_origin_is_the_calling_line(parts):
    d = Design(parts)
    line = here() + 1
    d.project(
        title="T",
        number="P-1",
        customer="C",
        revision=1,
        author="me",
    )
    record = d.draft().records()[0]
    _assert_at(d, record.id, line)


def test_location_origin_is_the_calling_line(parts):
    d = Design(parts)
    line = here() + 1
    c1 = d.location("C1", "cabinet")
    _assert_at(d, c1.id, line)


def test_group_origin_is_the_calling_line(parts):
    d = Design(parts)
    line = here() + 1
    g1 = d.group("G1")
    _assert_at(d, g1.id, line)


def test_item_and_its_functions_and_ports_share_the_calling_line(parts):
    d = Design(parts)
    line = here() + 1
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    for record in d.draft().records():
        origin = _origin_of(d.draft(), record.id)
        assert _same_file(origin.file, __file__)
        assert origin.line == line
    assert k1.functions


def test_strip_origin_is_the_calling_line(parts):
    d = Design(parts)
    line = here() + 1
    x1 = d.strip("X1")
    _assert_at(d, x1.id, line)


def test_terminal_origin_is_the_calling_line(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    line = here() + 1
    t1 = x1.terminal("TEST-TB")
    _assert_at(d, t1.id, line)


def test_cable_origin_is_the_calling_line(parts):
    d = Design(parts)
    line = here() + 1
    w1 = d.cable("TEST-CBL-2", tag="W1")
    _assert_at(d, w1.id, line)


def test_cable_core_origin_is_the_calling_line(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    w1 = d.cable("TEST-CBL-2", tag="W1")
    line = here() + 1
    w1.core(1, t1.outer, t2.outer)
    from fransys_model.vocab import CoreFacet

    core = next(r for r in d.draft().records() if isinstance(r, CoreFacet))
    _assert_at(d, core.id, line)


def test_wire_origin_is_the_calling_line(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    wire = d.wiring(colour="BU", gauge="0.75")
    line = here() + 1
    wire(t1.inner, t2.inner)
    from fransys_model.vocab.connectivity import Conductor

    conductor = next(r for r in d.draft().records() if isinstance(r, Conductor))
    _assert_at(d, conductor.id, line)


def test_net_origin_is_the_calling_line(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    line = here() + 1
    d.net("P24", t1.outer, t2.outer)
    from fransys_model.vocab import Net

    net = next(r for r in d.draft().records() if isinstance(r, Net))
    _assert_at(d, net.id, line)


def test_mate_origin_is_the_calling_line(parts):
    d = Design(parts)
    housing = d.item("TEST-CONN-2P", tag="X1")
    edge = d.item("TEST-EDGE-2P", tag="J1")
    line = here() + 1
    d.mate(housing, edge)
    from fransys_model.vocab import Mate

    mate = next(r for r in d.draft().records() if isinstance(r, Mate))
    _assert_at(d, mate.id, line)


def test_bridge_origin_is_the_calling_line(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2, t3 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    line = here() + 1
    d.bridge(t1, t2, t3)
    from fransys_model.vocab.connectivity import Conductor

    for conductor in (r for r in d.draft().records() if isinstance(r, Conductor)):
        origin = _origin_of(d.draft(), conductor.id)
        assert _same_file(origin.file, __file__)
        assert origin.line == line


def test_profile_origin_is_its_own_calling_line(parts):
    from fransys_model.layout import Profile as ModelProfile

    d = Design(parts)
    profile_line = here() + 1
    d.profile(hide_unused_pins=True)
    profile = next(r for r in d.draft().records() if isinstance(r, ModelProfile))
    assert _origin_of(d.draft(), profile.id).line == profile_line


def test_plc_facet_origin_is_its_own_calling_line(parts):
    from fransys_model.vocab import PlcRequestFacet

    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    plc_line = here() + 1
    k1.fn("coil").plc("do", "SIG")
    plc = next(r for r in d.draft().records() if isinstance(r, PlcRequestFacet))
    assert _origin_of(d.draft(), plc.id).line == plc_line


def _hidden_local(d):
    __tracebackhide__ = True
    return d.group("G1")


def _shown_local(d):
    __tracebackhide__ = False
    return d.group("G1")


def test_a_helper_with_a_local_tracebackhide_gives_its_callers_line(parts):
    d = Design(parts)
    line = here() + 1
    g1 = _hidden_local(d)
    _assert_at(d, g1.id, line)


def test_a_module_with_a_global_tracebackhide_gives_its_callers_line(parts):
    import importlib.util
    from pathlib import Path

    path = Path(__file__).with_name("tracebackhide_helper.py")
    spec = importlib.util.spec_from_file_location("tracebackhide_helper", path)
    assert spec is not None
    assert spec.loader is not None
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    d = Design(parts)
    line = here() + 1
    g1 = helper.build_group(d)
    _assert_at(d, g1.id, line)


def test_a_falsy_tracebackhide_does_not_hide_the_frame(parts):
    d = Design(parts)
    g1 = _shown_local(d)
    origin = _origin_of(d.draft(), g1.id)
    assert origin.line == _shown_local.__code__.co_firstlineno + 2
