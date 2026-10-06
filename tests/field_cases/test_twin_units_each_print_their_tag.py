"""Field case: two instances of one unit release each print their own instance tag.

The engineering shape: a cabinet holds two identical I/O boards, built from one board release
and placed at one place. A cabinet unit with a terminal-strip root and a second root device
sits in a system; a board instance also sits inside that cabinet.

The bug: an instance had no printed identity. Two boards at one place printed the one tag the
unit's own document gives its root (`-U9-J1` twice), so the build reported a duplicate for a
circuit with nothing wrong in it, and the system pages of a cabinet printed `-X1:L1` with no
sign of which cabinet.

The rule (UT1, UT2): `d.add(definition, tag)` writes the instance's tag. In its container an
item prints the instance tag, then the designation the unit's own document prints, behind one
dash: `-U1-J1`. A sole board root prints as the tag alone (`-U1`); a unit with several roots
prints the tag before each (`-U1-X1:L1:1`). The unit's own document does not change. One tag
twice at one place gives `PRODUCT_DESIGNATION_DUPLICATE`.

The decision that fixes it: model-0134 (instance tag, rendering, numbering) and author-0019
(`d.add`'s tag).
"""

from functools import cache
from typing import Any, NamedTuple

import fransys as fr

from fransys_model.vocab.tables import items, ports


class _Io(NamedTuple):
    J1: fr.Device


class _Cab(NamedTuple):
    X1: fr.TerminalStrip
    B: _Io


@cache
def _board() -> Any:
    @fr.unit(
        "demo-board", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB"
    )
    def board(u: Any) -> _Io:
        root = u.device("U9", "DEMO-PCB-IO")
        return _Io(u.device("J1", "DEMO-CONN-2P", parent=root, interface=True, unused=True))

    return board


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
    assert "PRODUCT_DESIGNATION_DUPLICATE" in _codes(fr.build(d))


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
