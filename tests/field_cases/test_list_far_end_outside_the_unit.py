"""Field case: a unit's own lists name a far end outside the unit with its location.
The bug: the cabinet's terminal list printed -X0:1 while its stub printed +EXT-X0, so one fact was computed two ways.
Fixed by model-0143, the shortest-designation rule drops only the location the document itself states."""

from functools import cache
from typing import Any, NamedTuple

import fransys as fr
from _far_end import item_named, stub_text


class _Cab(NamedTuple):
    X1: Any


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Cab:
    u.location("C1", "Cabinet")
    return _Cab(u.terminal_strip("X1", "DEMO-TB-2.5", 1, place="C1", interface=True))


@cache
def _build() -> tuple[fr.Model, Any]:
    d = fr.design("demo_parts", place="EXT")
    d.location("EXT", "External")
    cab = d.add(_cab, "U1")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 1, external=True)
    d.cable("W1", "DEMO-CBL-4G1.5").core(1, x0[1].outer, cab.X1[1].outer)
    model = fr.build(d).model
    unit = next(u for u in fr.derive.units(model) if fr.derive.unit_release(model, u).name == "demo-cab")
    return model, unit


def test_the_terminal_list_names_the_far_end_as_the_stub_does() -> None:
    model, unit = _build()
    (row,) = fr.derive.terminal_rows(model, item_named(model, "X1"), unit=unit)
    assert row.external_ends == (stub_text(model, "X0", "external"),)
    assert row.external_ends == ("+EXT-X0:1",)


def test_the_system_list_keeps_its_far_end() -> None:
    model, _ = _build()
    (row,) = fr.derive.terminal_rows(model, item_named(model, "X0"))
    assert row.external_ends == ("+EXT+C1-U1-X1:1",)
