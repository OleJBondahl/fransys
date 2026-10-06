"""Origins: every record's file and line is the calling test line (spec A10).

The frame walk finds the first frame outside `fransys_author`, comparing module
names, not paths; this test file's own lines are what every assertion checks against.
"""

import inspect
import os
from typing import TYPE_CHECKING

from fransys_author import Design

if TYPE_CHECKING:
    from fransys_model.kernel import Draft, Id, Origin


def _origin_of(draft: Draft, target: Id) -> Origin:
    origin = draft.origin_of(target)
    assert origin is not None
    return origin


def _same_file(origin_file: str, this_file: str) -> bool:
    """Path equality on this OS, not as strings.

    `caller_origin()` records `frame.f_code.co_filename` exactly as Python reports it, which
    on Windows is spelled with whatever letter case the process's cwd had when the module was
    first imported. A session whose cwd is spelled differently from this file's own `__file__`
    (both name the same file) must not fail these tests over that.
    """
    return os.path.normcase(origin_file) == os.path.normcase(this_file)


def _here() -> int:
    """The line number of the caller's own call to this helper, for `+ 1` arithmetic."""
    frame = inspect.currentframe()
    assert frame is not None
    assert frame.f_back is not None
    return frame.f_back.f_lineno


def test_project_origin_is_the_calling_line(parts):
    d = Design(parts)
    line = _here() + 1
    d.project(
        title="T",
        number="P-1",
        customer="C",
        revision=1,
        author="me",
    )
    record = d.draft().records()[0]
    origin = _origin_of(d.draft(), record.id)
    assert _same_file(origin.file, __file__)
    assert origin.line == line


def test_location_origin_is_the_calling_line(parts):
    d = Design(parts)
    line = _here() + 1
    c1 = d.location("C1", "cabinet")
    origin = _origin_of(d.draft(), c1.id)
    assert _same_file(origin.file, __file__)
    assert origin.line == line


def test_group_origin_is_the_calling_line(parts):
    d = Design(parts)
    line = _here() + 1
    g1 = d.group("G1")
    origin = _origin_of(d.draft(), g1.id)
    assert _same_file(origin.file, __file__)
    assert origin.line == line


def test_item_and_its_functions_and_ports_share_the_calling_line(parts):
    d = Design(parts)
    line = _here() + 1
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    for record in d.draft().records():
        origin = _origin_of(d.draft(), record.id)
        assert _same_file(origin.file, __file__)
        assert origin.line == line
    assert k1.functions


def test_strip_origin_is_the_calling_line(parts):
    d = Design(parts)
    line = _here() + 1
    x1 = d.strip("X1")
    origin = _origin_of(d.draft(), x1.id)
    assert _same_file(origin.file, __file__)
    assert origin.line == line


def test_terminal_origin_is_the_calling_line(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    line = _here() + 1
    t1 = x1.terminal("TEST-TB")
    origin = _origin_of(d.draft(), t1.id)
    assert _same_file(origin.file, __file__)
    assert origin.line == line


def test_cable_origin_is_the_calling_line(parts):
    d = Design(parts)
    line = _here() + 1
    w1 = d.cable("TEST-CBL-2", tag="W1")
    origin = _origin_of(d.draft(), w1.id)
    assert _same_file(origin.file, __file__)
    assert origin.line == line


def test_cable_core_origin_is_the_calling_line(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    w1 = d.cable("TEST-CBL-2", tag="W1")
    line = _here() + 1
    w1.core(1, t1.outer, t2.outer)
    from fransys_model.vocab import CoreFacet

    core = next(r for r in d.draft().records() if isinstance(r, CoreFacet))
    origin = _origin_of(d.draft(), core.id)
    assert _same_file(origin.file, __file__)
    assert origin.line == line


def test_wire_origin_is_the_calling_line(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    wire = d.wiring(colour="BU", gauge="0.75")
    line = _here() + 1
    wire(t1.inner, t2.inner)
    from fransys_model.vocab.connectivity import Conductor

    conductor = next(r for r in d.draft().records() if isinstance(r, Conductor))
    origin = _origin_of(d.draft(), conductor.id)
    assert _same_file(origin.file, __file__)
    assert origin.line == line


def test_net_origin_is_the_calling_line(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    line = _here() + 1
    d.net("P24", t1.outer, t2.outer)
    from fransys_model.vocab import Net

    net = next(r for r in d.draft().records() if isinstance(r, Net))
    origin = _origin_of(d.draft(), net.id)
    assert _same_file(origin.file, __file__)
    assert origin.line == line


def test_mate_origin_is_the_calling_line(parts):
    d = Design(parts)
    housing = d.item("TEST-CONN-2P", tag="X1")
    edge = d.item("TEST-EDGE-2P", tag="J1")
    line = _here() + 1
    d.mate(housing, edge)
    from fransys_model.vocab import Mate

    mate = next(r for r in d.draft().records() if isinstance(r, Mate))
    origin = _origin_of(d.draft(), mate.id)
    assert _same_file(origin.file, __file__)
    assert origin.line == line


def test_bridge_origin_is_the_calling_line(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2, t3 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    line = _here() + 1
    d.bridge(t1, t2, t3)
    from fransys_model.vocab.connectivity import Conductor

    for conductor in (r for r in d.draft().records() if isinstance(r, Conductor)):
        origin = _origin_of(d.draft(), conductor.id)
        assert _same_file(origin.file, __file__)
        assert origin.line == line


def test_chain_origin_is_the_calling_line(parts):
    d = Design(parts)
    x1 = d.strip("X1")
    t1, t2 = x1.terminal("TEST-TB"), x1.terminal("TEST-TB")
    line = _here() + 1
    d.chain(t1, t2)
    from fransys_model.layout import Chain

    chain = next(r for r in d.draft().records() if isinstance(r, Chain))
    origin = _origin_of(d.draft(), chain.id)
    assert _same_file(origin.file, __file__)
    assert origin.line == line


def test_symbol_choice_origin_is_the_calling_line(parts):
    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    line = _here() + 1
    d.symbol(k1.fn("coil"), "operating-device")
    from fransys_model.layout import SymbolChoice

    choice = next(r for r in d.draft().records() if isinstance(r, SymbolChoice))
    origin = _origin_of(d.draft(), choice.id)
    assert _same_file(origin.file, __file__)
    assert origin.line == line


def test_sheet_and_profile_origins_are_their_own_calling_lines(parts):
    from decimal import Decimal

    d = Design(parts)
    sheet_line = _here() + 1
    sheet = d.sheet(
        "A3",
        width_mm=420,
        height_mm=297,
        content_x_mm=10,
        content_y_mm=10,
        content_width_mm=400,
        content_height_mm=277,
        frame_columns=8,
        frame_rows=6,
        module_mm=Decimal("2.5"),
    )
    assert _origin_of(d.draft(), sheet).line == sheet_line

    from fransys_model.layout import Profile as ModelProfile

    profile_line = _here() + 1
    d.profile(
        sheet=sheet,
        column_gap=4,
        row_gap=4,
        route_margin=2,
        text_height=3,
        marker_padding=1,
        route_turn_penalty=1,
        route_crossing_penalty=2,
    )
    profile = next(r for r in d.draft().records() if isinstance(r, ModelProfile))
    assert _origin_of(d.draft(), profile.id).line == profile_line


def test_plc_and_scale_facet_origins_are_their_own_calling_lines(parts):
    from fransys_model.vocab import PlcRequestFacet, ScalingFacet

    d = Design(parts)
    k1 = d.item("TEST-RLY-2CO", tag="K1")
    plc_line = _here() + 1
    k1.fn("coil").plc("do", "SIG")
    plc = next(r for r in d.draft().records() if isinstance(r, PlcRequestFacet))
    assert _origin_of(d.draft(), plc.id).line == plc_line

    scale_line = _here() + 1
    k1.fn("coil").scale("m", raw=(0, 10), eng=("0", "1"))
    scaling = next(r for r in d.draft().records() if isinstance(r, ScalingFacet))
    assert _origin_of(d.draft(), scaling.id).line == scale_line
