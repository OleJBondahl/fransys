"""Field case: no wire joins two pins that each draw a rail's power symbol (V3, 2026-10-02).

The engineering shape, twice. Board page: two relays K1 and K2 and two connectors J1 and J2; J2:1
feeds both contacts' common pins (11) on 24 V and both coils return on 0 V through J1:1. Pump page:
an overload relay's pass-through A2 wired to a bridged 0 V terminal row of the same page.

The bug: the wire J2:1 to K1:11 was drawn with the 24 V bar standing in its middle, and the pump
page's A2 and its 0 V terminal were two ends of a same-page `#n` reference pair.

The rule (CONVENTIONS-V06 V3, decision layout-0099): between two pins that both draw a rail's
power symbol no wire is drawn; each pin draws its own symbol, and the wire list keeps the wire. A
pin wired to a rail terminal draws the symbol, with no reference pair left.
"""

from itertools import pairwise

import fransys as fr
import pytest
from fransys.colours import BU, WH

from fransys_model.layout import LinkMarker, PowerSymbol, Route, RoutePoint, layout_of
from fransys_model.vocab.tables import ports


def _finish(tmp_path, d, cab) -> fr.BuildResult:
    cover = tmp_path / "cabinet.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cab, cover=cover)
    return fr.build(d, doc)


def _board(tmp_path) -> fr.BuildResult:
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
            d.wire(members[0], members[1], wire=(WH, 0.5))
            d.wire(members[0], members[2], wire=(WH, 0.5))
    return _finish(tmp_path, d, cab)


def _pump(tmp_path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="CAB")
    cab = d.location("CAB", "Cabinet")
    with d.function("G", "Group"):
        overload = d.device("F1", "DEMO-OVERLOAD-A2")
        live = d.terminal_strip("X1", "DEMO-TB-2.5", 1)
        zero = d.terminal_strip("X2", "DEMO-TB-2.5", 2).run("G", 2, bridged=True)
        d.dc_supply("S", plus=live[1], minus=zero[1], voltage=24)
        d.wire(overload.a2["A2"], zero[1].outer, wire=(BU, 0.5))
    return _finish(tmp_path, d, cab)


def _interior(point: tuple[int, int], points: tuple[RoutePoint, ...]) -> bool:
    """Whether `point` lies on a segment of the polyline and is not one of its two ends."""
    ends = {(points[0].x, points[0].y), (points[-1].x, points[-1].y)}
    x, y = point
    on_segment = any(
        min(p.x, q.x) <= x <= max(p.x, q.x) and min(p.y, q.y) <= y <= max(p.y, q.y)
        for p, q in pairwise(points)
    )
    return on_segment and point not in ends


@pytest.fixture(scope="module")
def board(tmp_path_factory):
    return _board(tmp_path_factory.mktemp("board")).model


def _named(model, symbol: str) -> set[str]:
    found = layout_of(model, PowerSymbol).values()
    return {ports(model)[s.port].name for s in found if s.symbol == symbol}


def test_each_rail_pin_draws_its_symbol_and_no_wire_joins_two_of_them(board) -> None:
    assert _named(board, "power-supply") == {"1", "11"}
    assert _named(board, "ground") == {"1", "A2"}
    ends = {s.port for s in layout_of(board, PowerSymbol).values()}
    assert len(ends) == 6
    assert [r for r in layout_of(board, Route).values() if r.a in ends and r.b in ends] == []


def test_no_power_symbol_anchor_is_an_interior_point_of_a_drawn_route(board) -> None:
    symbols = layout_of(board, PowerSymbol).values()
    assert symbols
    for symbol in symbols:
        for route in layout_of(board, Route).values():
            if route.page == symbol.page:
                assert not _interior((symbol.pin_x, symbol.pin_y), route.points)
                assert not _interior((symbol.x, symbol.y), route.points)


def test_an_overload_a2_wired_to_a_rail_terminal_draws_ground_and_no_reference_pair(
    tmp_path,
) -> None:
    model = _pump(tmp_path).model
    assert _named(model, "ground") == {"A2"}
    assert not layout_of(model, LinkMarker)
