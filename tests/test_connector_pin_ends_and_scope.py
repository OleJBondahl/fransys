"""A connector pin's ends are a terminal row's ends (`far_ends`); a unit's own items scope it.

Built through the facade from `examples/demo-parts`: a unit with a device connector `J1` mated to
a plug `P5`; a nested unit with its own connector that the outer unit's scope never lists.
"""

from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import BK

from fransys_model import derive
from fransys_model.derive import connector_rows, unit_connector_items
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
    u.wire(j1[1], lamp["1"], wire=(BK, 0.5))
    psu = u.device("T1", "DEMO-PSU-24")
    u.dc_supply("S", psu)
    harness = u.harness("W5")
    plug = u.device("P5", "DEMO-HSG-4M", parent=harness, contacts="DEMO-CRIMP-M")
    u.mate(plug, j1)
    u.wire(plug[3], psu.output["+"], wire=(BK, 0.5))
    u.add(_inner, "U2")
    return _Open()


def _model() -> Any:
    d = fr.design("demo_parts")
    d.add(_outer, "C1", place=None)
    return fr.build(d).model


def _units(model: Any) -> dict[str, Any]:
    return {derive.unit_release(model, u).name: u for u in derive.units(model)}


def test_a_pins_ends_are_its_own_and_its_mates_far_ends() -> None:
    """Pin 1 reaches `-H1:1`, pin 3 reaches `-T1:+` through its mate, pin 2 reaches nothing."""
    model = _model()
    outer = _units(model)["demo-pin-outer"]
    rows = {
        r.designation: r
        for i in unit_connector_items(model, outer)
        for r in connector_rows(model, i, unit=outer)
    }
    ends = {pin.marking: pin.ends for pin in rows["-J1"].pins}
    assert ends == {"1": ("-H1:1",), "2": (), "3": ("-T1:+",), "4": ()}


def test_a_units_connector_items_are_its_own_never_a_nested_units() -> None:
    model = _model()
    units = _units(model)
    outer = {items(model)[i].tag for i in unit_connector_items(model, units["demo-pin-outer"])}
    inner = {items(model)[i].tag for i in unit_connector_items(model, units["demo-pin-inner"])}
    assert outer == {"J1", "P5"}
    assert inner == {"J7"}
