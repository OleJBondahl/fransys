"""`d.layout.side` hints the edge a unit's interface stands on (HL14, author-0030)."""

from typing import NamedTuple

import pytest
from fransys_author import AuthorError
from fransys_author.surface import ABOVE, BELOW, Design, Device, design, unit

from fransys_model.layout import Side, SideHint

from ..equivalence.series_parts import pair_library  # noqa: TID252 -- importlib mode puts tests/ on no path


class _Io(NamedTuple):
    X1: Device
    X2: Device
    ROW: tuple[Device, Device]


@unit("demo-side-board", revision=1, interface_version=1, date="d", text="t", by="XX")
def _board(d: Design) -> _Io:
    return _Io(
        d.device("X1", "DEMO-CONN-2P", interface=True),
        d.device("X2", "DEMO-CONN-2P"),
        tuple(d.device(f"R{n}", "DEMO-CONN-2P", interface=True) for n in (1, 2)),
    )


def _hints(d):
    return [r for r in d.draft().records() if isinstance(r, SideHint)]


def _two():
    d = design(pair_library(), place="C1")
    return d, d.add(_board, "U1"), d.add(_board, "U2")


def test_above_and_below_are_the_models_north_and_south() -> None:
    assert ABOVE is Side.N
    assert BELOW is Side.S


def test_a_device_field_writes_one_hint_for_its_boundary_function() -> None:
    d, io, _ = _two()
    d.layout.side(io.X1, ABOVE)
    (hint,) = _hints(d)
    assert (hint.function, hint.side) == (io.X1._item.functions[0].id, Side.N)


def test_a_tuple_field_writes_a_hint_for_every_function_it_holds() -> None:
    d, io, _ = _two()
    d.layout.side(io.ROW, BELOW)
    assert {h.function for h in _hints(d)} == {r._item.functions[0].id for r in io.ROW}
    assert {h.side for h in _hints(d)} == {Side.S}


def test_a_hint_on_one_instance_leaves_the_other_alone() -> None:
    d, io1, io2 = _two()
    d.layout.side(io1.X1, ABOVE)
    assert {h.function for h in _hints(d)} == {io1.X1._item.functions[0].id}
    d.layout.side(io2.X1, BELOW)
    assert len(_hints(d)) == 2


def test_a_target_that_is_no_unit_boundary_raises() -> None:
    d, io, _ = _two()
    with pytest.raises(AuthorError, match="no unit boundary"):
        d.layout.side(io.X2, ABOVE)
    assert not _hints(d)


def test_a_target_that_is_no_handle_raises() -> None:
    d, _, _ = _two()
    with pytest.raises(AuthorError, match="a field of a unit's interface"):
        d.layout.side("X1", ABOVE)


@pytest.mark.parametrize("side", [Side.E, Side.W, "above", None])
def test_a_side_other_than_above_or_below_raises(side) -> None:
    d, io, _ = _two()
    with pytest.raises(AuthorError, match=r"fr\.ABOVE or fr\.BELOW"):
        d.layout.side(io.X1, side)
    assert not _hints(d)


def test_a_second_hint_on_one_interface_raises() -> None:
    d, io, _ = _two()
    d.layout.side(io.X1, ABOVE)
    with pytest.raises(AuthorError, match="already has a side hint"):
        d.layout.side(io.X1, BELOW)
    assert len(_hints(d)) == 1


def test_a_second_hint_through_a_tuple_field_raises_and_writes_nothing() -> None:
    d, io, _ = _two()
    d.layout.side(io.ROW[0], ABOVE)
    with pytest.raises(AuthorError, match="already has a side hint"):
        d.layout.side(io.ROW, BELOW)
    assert len(_hints(d)) == 1
