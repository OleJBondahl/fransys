"""`fransys_author.surface.added_unit` names the unit instance `d.add` built (R363, R633)."""

from typing import NamedTuple

import fransys_parts
from fransys_author.surface import Design, Device, added_unit, design, unit


class _Io(NamedTuple):
    X1: Device


@unit("demo-io-board", revision=1, interface_version=1, date="2026-02-02", text="First", by="XX")
def _board(u: Design) -> _Io:
    return _Io(u.device("X1", "DEMO-CONN-2P", interface=True))


def test_each_added_instance_names_its_own_unit_and_a_stranger_none() -> None:
    d = design(fransys_parts.load("demo_parts"))
    first, second = d.add(_board, "U1"), d.add(_board, "U2")
    assert added_unit(first) is not None
    assert added_unit(first) != added_unit(second)
    assert added_unit(_Io(first.X1)) is None
