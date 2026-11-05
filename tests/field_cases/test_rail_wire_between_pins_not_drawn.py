"""Field case: no wire joins two pins that each draw a rail's power symbol.
The bug: the wire J2:1 to K1:11 was drawn with the 24 V bar standing in its middle.
Fixed by layout-0120 (rule V3, owner 2026-10-02): each pin draws its own symbol and no wire is drawn between them."""

from itertools import pairwise

import fransys as fr
import pytest
from _drawn_pages import drawn_pages, markers_in
from _model_build_cover import unit_document
from fransys.colours import BU, WH

from fransys_model.layout import PowerSymbol, layout_of
from fransys_model.vocab.tables import ports


def _finish(d, cab) -> fr.BuildResult:
    doc = unit_document(cab)
    return fr.build(d, doc)


def _board() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        k1 = d.device("K1", "DEMO-RLY-2CO-24")
        k2 = d.device("K2", "DEMO-RLY-2CO-24")
        j1 = d.device("J1", "DEMO-CONN-2P")
        j2 = d.device("J2", "DEMO-CONN-2P")
        d.dc_supply("S", plus=j2.x1["1"], minus=j1.x1["1"], voltage=24)
        live = [j2.x1["1"], k1.co_1["11"], k2.co_1["11"]]
        zero = [j1.x1["1"], k1.coil["A2"], k2.coil["A2"]]
        for members in (live, zero):
            d.series(members[0], members[1], wire=(WH, 0.5))
            d.series(members[0], members[2], wire=(WH, 0.5))
        feed = d.terminal_strip("X1", "DEMO-TB-2.5", 2)
        for n, k in enumerate((k1, k2), 1):
            d.series(k.coil["A1"], feed[n].outer, wire=(WH, 0.5))
    return _finish(d, cab)


def _pump() -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        overload = d.device("F1", "DEMO-OVERLOAD-A2")
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 1)
        zero = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("G", 2, bridged=True, rail=True)
        d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
        d.series(overload.a2["A2"], zero[1].outer, wire=(BU, 0.5))
    return _finish(d, cab)


def _interior(point: tuple[int, int], points: tuple[tuple[int, int], ...]) -> bool:
    """Whether `point` lies on a segment of the polyline and is not one of its two ends."""
    ends = {points[0], points[-1]}
    x, y = point
    on_segment = any(min(p[0], q[0]) <= x <= max(p[0], q[0]) and min(p[1], q[1]) <= y <= max(p[1], q[1]) for p, q in pairwise(points))
    return on_segment and point not in ends


@pytest.fixture(scope="module")
def board():
    return _board().model


def _named(model, symbol: str) -> set[str]:
    found = layout_of(model, PowerSymbol).values()
    return {ports(model)[s.port].name for s in found if s.symbol == symbol}


def test_each_rail_pin_draws_its_symbol_and_no_wire_joins_two_of_them(board) -> None:
    assert _named(board, "power-supply") == {"1", "11"}
    assert _named(board, "ground") == {"1", "A2"}
    symbols = layout_of(board, PowerSymbol).values()
    assert len({s.port for s in symbols}) == 6


def test_no_power_symbol_anchor_is_an_interior_point_of_a_drawn_route(board) -> None:
    symbols = layout_of(board, PowerSymbol).values()
    assert symbols
    for symbol in symbols:
        for wire in drawn_pages(board)[symbol.page].wires:
            assert not _interior((symbol.x, symbol.y), wire.points)


def test_an_overload_a2_wired_to_a_rail_terminal_draws_ground_and_no_reference_pair() -> None:
    model = _pump().model
    assert _named(model, "ground") == {"A2"}
    assert not [m for d in drawn_pages(model).values() for m in markers_in(d)]
