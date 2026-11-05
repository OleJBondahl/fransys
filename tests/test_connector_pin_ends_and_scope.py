"""A unit's own connector items scope it.

Built through the facade from `examples/demo-parts`: a unit with a device connector `J1`;
a nested unit with its own connector that the outer unit's scope never lists.
"""

from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import BK

from fransys_model import derive
from fransys_model.derive import unit_connector_items
from fransys_model.vocab import items

_REL: dict[str, Any] = {"revision": 1, "interface_version": 1, "date": "2026-01-01"}


class _Open(NamedTuple):
    pass


@fr.unit("demo-pin-inner", text="first", by="AB", **_REL)
def _inner(u: Any) -> _Open:
    u.device("J7", "DEMO-HSG-4F", contacts="DEMO-CRIMP-F")
    return _Open()


@fr.unit("demo-pin-outer", text="first", by="AB", **_REL)
def _outer(u: Any) -> _Open:
    j1 = u.device("J1", "DEMO-HSG-4F", contacts="DEMO-CRIMP-F")
    lamp = u.device("H1", "DEMO-LAMP-24")
    u.series(j1[1], lamp["1"], wire=(BK, 0.5))
    psu = u.device("T1", "DEMO-PSU-24")
    u.dc_supply("S", psu)
    u.series(lamp["2"], psu.output["-"], wire=(BK, 0.5))
    u.add(_inner, "U2")
    return _Open()


def _model() -> Any:
    d = fr.design("demo_parts")
    d.add(_outer, "C1", place=None)
    return fr.build(d).model


def _units(model: Any) -> dict[str, Any]:
    return {derive.unit_release(model, u).name: u for u in derive.units(model)}


def test_a_units_connector_items_are_its_own_never_a_nested_units() -> None:
    model = _model()
    units = _units(model)
    outer = {items(model)[i].tag for i in unit_connector_items(model, units["demo-pin-outer"])}
    inner = {items(model)[i].tag for i in unit_connector_items(model, units["demo-pin-inner"])}
    assert outer == {"J1"}
    assert inner == {"J7"}
