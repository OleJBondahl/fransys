"""`Boundary.name` is the interface field `d.add` found; a bare `s.boundary()` leaves it None."""

from typing import NamedTuple

from fransys_author.surface import Device, TerminalStrip, design, unit

from fransys_model.vocab import Boundary

from .equivalence.series_parts import pair_library


class _Io(NamedTuple):
    pwr_estop: Device
    X1: Device


@unit("demo-name-board", revision=1, interface_version=1, date="d", text="t", by="XX")
def _board(d):
    return _Io(
        d.device("K1", "DEMO-CONN-2P", interface=True),
        d.device("X1", "DEMO-CONN-2P", interface=True),
    )


class _Many(NamedTuple):
    row: tuple[Device, Device]
    strip: TerminalStrip


@unit("demo-name-many", revision=1, interface_version=1, date="d", text="t", by="XX")
def _many(d):
    row = tuple(d.device(f"X{n}", "DEMO-CONN-2P", interface=True) for n in (1, 2))
    return _Many(row, d.terminal_strip("T1", "DEMO-TB-2.5", 2, interface=True))


def _names(d) -> dict:
    return {r.function: r.name for r in d.draft().records() if isinstance(r, Boundary)}


def test_a_device_field_names_its_boundary() -> None:
    d = design(pair_library(), place="C1")
    io = d.add(_board, "U1")
    names = _names(d)
    assert names[io.pwr_estop._item.functions[0].id] == "pwr_estop"
    assert names[io.X1._item.functions[0].id] == "X1"


def test_a_tuple_and_a_strip_field_name_each_of_their_functions() -> None:
    d = design(pair_library(), place="C1")
    io = d.add(_many, "U1")
    names = _names(d)
    assert len(names) == 4
    assert names[io.row[0]._item.functions[0].id] == "row"
    assert names[io.row[1]._item.functions[0].id] == "row"
    assert sorted(names.values()) == ["row", "row", "strip", "strip"]


def test_a_boundary_called_outside_add_has_no_name() -> None:
    d = design(pair_library(), place="C1")
    s = d._engine.scope("u1").unit("demo-unit", revision=1, interface="1")
    s.boundary(s.item("DEMO-CONN-2P", tag="X1"))
    assert list(_names(d).values()) == [None]
