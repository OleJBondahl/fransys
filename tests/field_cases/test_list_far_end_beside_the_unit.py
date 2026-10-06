"""Field case: a unit's own lists name a far end beside the unit with its whole path.

The engineering shape: a cabinet unit holds a terminal strip `X1` and a connector `J1`, both on
its boundary, at the system's location `EXT` (the unit states no location of its own). A strip
`X0` and a connector `P1`, outside the cabinet and at the same `EXT`, are wired and mated to them.

The bug: the cabinet's own terminal and connector lists printed the far end `-X0:1`
and the mate `-P1`, dropping `+EXT` because the end sits at the unit's own location, while the
stub on the cabinet's drawing prints `+EXT-X0`. A unit's own document knows only what is below
it (owner 2026-09-24), so an end outside the unit is never short, wherever it sits.

The decision that fixes it: model-0143, amended by FAR-END-ONE-HOME.
"""

from functools import cache
from typing import Any, NamedTuple

import fransys as fr

from fransys_model.derive.drawing_text import stub_far_end
from fransys_model.vocab.tables import functions, items, ports


class _Cab(NamedTuple):
    X1: Any
    J1: Any


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> Any:
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True)
    return _Cab(x1, u.device("J1", "DEMO-CONN-2P", interface=True))


@cache
def _build() -> tuple[fr.Model, Any]:
    d = fr.design("demo_parts", place="EXT")
    d.location("EXT", "External")
    cab = d.add(_cab, "U1")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 2, external=True)
    d.cable("W1", "DEMO-CBL-4G1.5").core(1, x0[1].outer, cab.X1[1].outer)
    d.mate(d.device("P1", "DEMO-CONN-2P"), cab.J1)
    model = fr.build(d).model
    unit = next(
        u for u in fr.derive.units(model) if fr.derive.unit_release(model, u).name == "demo-cab"
    )
    return model, unit


def _item(model: fr.Model, name: str) -> Any:
    return next(i for i, item in items(model).items() if item.key[-1] == name)


def _stub(model: fr.Model, name: str, pin: str) -> str:
    port = next(
        p
        for p, rec in ports(model).items()
        if items(model)[functions(model)[rec.function].item].key[0] == name and rec.name == pin
    )
    return "".join(stub_far_end(model, port))


def test_the_terminal_list_prints_the_whole_path_of_an_end_beside_the_unit() -> None:
    model, unit = _build()
    rows = fr.derive.terminal_rows(model, _item(model, "X1"), unit=unit)
    assert rows[0].external_ends == ("+EXT-X0:1",)
    assert _stub(model, "X0", "external").startswith("+EXT-X0:")  # the stub names the strip alike


def test_the_connector_list_prints_the_whole_path_of_a_mate_beside_the_unit() -> None:
    model, unit = _build()
    (row,) = fr.derive.connector_rows(model, _item(model, "J1"), unit=unit)
    assert [p.mate_port_designation for p in row.pins] == [
        _stub(model, "P1", "1"),
        _stub(model, "P1", "2"),
    ]
    assert row.mate_designation == "+EXT-P1"
