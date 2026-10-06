"""Field case: a unit's own lists name a far end outside the unit with its location.

The engineering shape: a cabinet unit holds a terminal strip `X1` and a connector `J1`, both on
its boundary, at location `C1`; the system places the cabinet at `EXT`. A strip `X0` and a
connector `P1`, at `EXT` and outside the cabinet, are wired and mated to them.

The bug: the cabinet's own terminal list printed the far end `-X0:1`, and its own connector
list the mated pin `-P1:1`, while the stub on its own drawing prints the same ends `+EXT-X0`
and `+EXT-P1`. The list dropped a location the cabinet's document does not state: `X0` is not
at `+C1`. One printed fact was computed two ways.

The rule: the owner's shortest-designation rule drops only the location the document itself
states, so a far end outside the unit prints its location, as the stub does.

The decision that fixes it: model-0143.
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
def _cab(u: Any) -> _Cab:
    u.location("C1", "Cabinet")
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5", 1, place="C1", interface=True)
    return _Cab(x1, u.device("J1", "DEMO-CONN-2P", place="C1", interface=True))


@cache
def _build() -> tuple[fr.Model, Any]:
    d = fr.design("demo_parts", place="EXT")
    d.location("EXT", "External")
    cab = d.add(_cab, "U1")
    x0 = d.terminal_strip("X0", "DEMO-TB-2.5", 1, external=True)
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
    """The off stub's text for the port `pin` of the item (or terminal of the strip) `name`."""
    port = next(
        p
        for p, rec in ports(model).items()
        if items(model)[functions(model)[rec.function].item].key[0] == name and rec.name == pin
    )
    return "".join(stub_far_end(model, port))


def test_the_terminal_list_names_the_far_end_as_the_stub_does() -> None:
    model, unit = _build()
    (row,) = fr.derive.terminal_rows(model, _item(model, "X1"), unit=unit)
    assert row.external_ends == (_stub(model, "X0", "external"),)
    assert row.external_ends == ("+EXT-X0:1",)


def test_the_connector_list_names_the_mated_pin_as_the_stub_does() -> None:
    model, unit = _build()
    (row,) = fr.derive.connector_rows(model, _item(model, "J1"), unit=unit)
    assert [p.mate_port_designation for p in row.pins] == [
        _stub(model, "P1", "1"),
        _stub(model, "P1", "2"),
    ]


def test_the_system_list_keeps_its_far_end() -> None:
    model, _ = _build()
    (row,) = fr.derive.terminal_rows(model, _item(model, "X0"))
    assert row.external_ends == ("+EXT+C1-U1-X1:1",)
