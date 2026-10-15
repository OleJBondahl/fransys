"""The drawn-short check over plain strokes and bodies (render-0012): what joins two nets."""

from typing import Any

from fransys_render._drawn_shorts import Body, Stroke, drawn_shorts

A: Any = "net-a"
B: Any = "net-b"
W1: Any = "W1"


def _stroke(kind: str, net: Any, a: tuple[int, int], b: tuple[int, int], **more: Any) -> Stroke:
    return Stroke(kind, ("net", net), net, a, b, **more)


def _body(kind: str, nets: tuple[Any, ...], box: tuple[int, int, int, int], **more: Any) -> Body:
    return Body(kind, frozenset(("net", one) for one in nets), nets[0], box, **more)


def _joined(strokes: list[Stroke], bodies: list[Body] | None = None) -> list[tuple[Any, ...]]:
    return [short.subjects for short in drawn_shorts(strokes, bodies or [])]


def test_a_stub_on_another_nets_route_joins_them_and_on_its_own_does_not() -> None:
    route = _stroke("route", A, (0, 8), (40, 8))
    assert _joined([route, _stroke("stub", B, (16, 8), (32, 8))]) == [(A, B)]
    assert _joined([route, _stroke("stub", A, (16, 8), (32, 8))]) == []


def test_a_wire_end_on_another_nets_wire_joins_them() -> None:
    assert _joined([_stroke("route", A, (0, 8), (40, 8)), _stroke("route", B, (16, 8), (16, 40))])


def test_two_wires_cross_clean_but_a_stub_or_rail_crossing_a_wire_joins_it() -> None:
    upright = _stroke("route", A, (16, 0), (16, 40))
    assert _joined([upright, _stroke("route", B, (0, 8), (40, 8))]) == []
    assert _joined([upright, _stroke("stub", B, (0, 8), (40, 8))]) == [(A, B)]
    assert _joined([upright, _stroke("rail", B, (0, 8), (40, 8))]) == [(A, B)]


def test_legs_of_one_fan_out_meet_where_they_leave_their_line_and_nowhere_else() -> None:
    fan = (8, 8)
    one = _stroke("leg", A, fan, (0, 24), bundle="W1", fan=fan)
    two = _stroke("leg", B, fan, (16, 24), bundle="W1", fan=fan)
    assert _joined([one, two]) == []
    crossing_end = _stroke("leg", B, (0, 24), (16, 40), bundle="W1", fan=(0, 24))
    assert _joined([one, crossing_end]) == [(A, B)]
    alongside = _stroke("leg", B, fan, (8, 24), bundle="W1", fan=fan)
    assert _joined([_stroke("leg", A, fan, (8, 16), bundle="W1", fan=fan), alongside]) == [(A, B)]


def test_a_line_keeps_its_own_legs_and_stubs_but_joins_another_wire_on_it() -> None:
    line = Stroke("line", ("harness", W1), W1, (0, 8), (40, 8), bundle=W1)
    assert _joined([line, _stroke("stub", A, (16, 8), (32, 8), bundle="W1")]) == []
    assert _joined([line, _stroke("route", A, (16, 8), (32, 8))]) == [(W1, A)]


def test_a_wire_into_another_nets_flag_box_joins_but_a_mate_into_its_shared_box_does_not() -> None:
    box = (8, 0, 20, 40)
    stub = _stroke("stub", B, (12, 48), (12, 40))
    assert _joined([stub], [_body("flag", (A,), box)]) == [(A, B)]
    assert _joined([stub], [_body("flag", (A, B), box)]) == []


def test_a_power_symbol_touching_another_nets_power_symbol_joins_them() -> None:
    plus, minus = _body("power", (A,), (0, 0, 16, 8)), _body("power", (B,), (16, 0, 32, 8))
    assert _joined([], [plus, minus]) == [(A, B)]
    apart = _body("power", (B,), (24, 0, 40, 8))
    assert _joined([], [plus, apart]) == []
    assert _joined([], [plus, _body("symbol", (B,), (0, 8, 32, 40))]) == []


def test_a_wire_through_a_symbol_joins_it_unless_it_ends_on_its_port_or_is_a_stub() -> None:
    symbol = _body("symbol", (B,), (0, 0, 16, 16), ports=frozenset({(8, 0)}))
    assert _joined([_stroke("route", A, (8, -8), (8, 24))], [symbol]) == [(A, B)]
    assert _joined([_stroke("route", A, (8, -8), (8, 0))], [symbol]) == []
    assert _joined([_stroke("route", A, (0, -8), (0, 24))], [symbol]) == []
    assert _joined([_stroke("stub", A, (8, -8), (8, 24))], [symbol]) == []
