"""Field case: a unit's own lists name a far end beside the unit, at the system's location EXT, with its whole path.
The bug: the cabinet's terminal list printed -X0:1, dropping +EXT, while its stub printed +EXT-X0.
Fixed by model-0143 (amended by a later rule on far ends), an end outside the unit is never short."""

from functools import cache
from typing import Any, NamedTuple

import fransys as fr
from _far_end import item_named, stub_text


class _Cab(NamedTuple):
    X1: Any


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Cab:
    return _Cab(u.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True))


@cache
def _build() -> tuple[fr.Model, Any]:
    d = fr.design("demo_parts", place="EXT")
    d.location("EXT", "External")
    cab = d.add(_cab, "U1")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 2, external=True)
    w1 = d.cable("W1", "DEMO-CBL-4G1.5")
    w1.core(1, x0[1].outer, cab.X1[1].outer)
    w1.core(2, x0[2].outer, cab.X1[2].outer)
    model = fr.build(d).model
    unit = next(u for u in fr.derive.units(model) if fr.derive.unit_release(model, u).name == "demo-cab")
    return model, unit


def test_the_terminal_list_prints_the_whole_path_of_an_end_beside_the_unit() -> None:
    model, unit = _build()
    rows = fr.derive.terminal_rows(model, item_named(model, "X1"), unit=unit)
    assert rows[0].external_ends == ("+EXT-X0:1",)
    assert stub_text(model, "X0", "external").startswith("+EXT-X0:")  # the stub names the strip alike
