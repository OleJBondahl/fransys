"""Field case: two identical boards from one release sit at one place in a cabinet, each under its own tag.
The bug: an instance printed no identity, so both boards printed the one root tag (-U9-J1 twice), a false duplicate.
Fixed by model-0134 and author-0019, d.add writes the instance tag, which an item prints before its designation."""

from functools import cache
from typing import Any, NamedTuple

import fransys as fr
from _demo_board import Io, demo_board
from _expected_codes import expect_codes

from fransys_model.vocab.tables import items, ports


class _Cab(NamedTuple):
    X1: fr.TerminalStrip
    B: Io


_board = cache(demo_board)


@cache
def _cabinet() -> Any:
    @fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
    def cab(u: Any) -> _Cab:
        strip = u.terminal_strip("X1", "DEMO-TB-2.5", 3, interface=True, unused=True)
        strip.run("L1", 2)
        u.device("M1", "DEMO-LAMP-24")
        return _Cab(strip, u.add(_board(), "U3"))

    return cab


def _design() -> Any:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    return d


def _unit_id(model: fr.Model, name: str) -> Any:
    return next(u for u in fr.derive.units(model) if fr.derive.unit_release(model, u).name == name)


def _codes(result: fr.BuildResult) -> list[str]:
    return [f.code for f in fr.check(result)]


def test_twin_boards_at_one_place_print_their_own_tags() -> None:
    d = _design()
    a = d.add(_board(), "U1")
    b = d.add(_board(), "U2")
    result = fr.build(d)
    model = result.model
    assert "PRODUCT_DESIGNATION_DUPLICATE" not in _codes(result)
    assert fr.derive.printed_designation(model, a.J1.id) == "-U1-J1"
    assert fr.derive.printed_designation(model, b.J1.id) == "-U2-J1"
    root_a, root_b = (items(model)[x.J1.id].parent for x in (a, b))
    assert root_a is not None
    assert root_b is not None
    assert fr.derive.printed_designation(model, root_a) == "-U1"
    assert fr.derive.printed_designation(model, root_b) == "-U2"


def test_one_tag_twice_at_one_place_gives_the_duplicate_finding() -> None:
    d = _design()
    with d.function("F1", "First"):
        d.add(_board(), "U1")
    with d.function("F2", "Second"):
        d.add(_board(), "U1")
    expect_codes(fr.build(d), "PRODUCT_DESIGNATION_DUPLICATE", "DESIGNATION_DUPLICATE")


def test_a_unit_with_several_roots_prints_the_tag_before_each() -> None:
    d = _design()
    d.add(_cabinet(), "U1")
    model = fr.build(d).model
    texts = {fr.derive.port_designation(model, p) for p in ports(model)}
    assert "-U1-X1:L1:1" in texts
    assert "-U1-M1:1" in texts
    cab = _unit_id(model, "demo-cab")
    own = {fr.derive.port_designation(model, p, unit=cab) for p in ports(model)}
    assert {"-X1:L1:1", "-M1:1"} <= own


def test_a_board_instance_inside_a_cabinet_instance_prints_both_tags() -> None:
    d = _design()
    cab = d.add(_cabinet(), "U1")
    model = fr.build(d).model
    assert fr.derive.printed_designation(model, cab.B.J1.id) == "-U1-U3-J1"
    cabinet_unit = _unit_id(model, "demo-cab")
    assert fr.derive.printed_designation(model, cab.B.J1.id, unit=cabinet_unit) == "-U3-J1"
    board_unit = _unit_id(model, "demo-board")
    assert fr.derive.printed_designation(model, cab.B.J1.id, unit=board_unit) == "-J1"
