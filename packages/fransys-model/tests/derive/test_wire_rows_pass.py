"""`resolve_wire_rows` (model-0260): a hinted wire takes its row from what its nets carry."""

import dataclasses
from decimal import Decimal
from typing import TYPE_CHECKING

from plant import Plant
from rating_plant import AC_400, supply
from test_plc_allocation_units_model import Site, _site

from fransys_model.derive import resolve_wire_rows
from fransys_model.kernel import Severity, make_id
from fransys_model.vocab import (
    Current,
    Rail,
    RowSpec,
    WireFacet,
    WireRowHint,
    WiringRow,
)
from fransys_model.vocab.tables import facets_of

if TYPE_CHECKING:
    from fransys_model.kernel import Id, Model
    from fransys_model.vocab.core import Port, Unit

_TABLE = {
    "DC_SUPPLY": RowSpec(colour="RD", gauge_mm2=None),
    "DC_GROUND": RowSpec(colour="BU", gauge_mm2=Decimal("1.5")),
    "DC_SIGNAL": RowSpec(colour="WH", gauge_mm2=None),
    "AC_L1": RowSpec(colour="BK", gauge_mm2=None),
    "AC_L2": RowSpec(colour="BN", gauge_mm2=None),
}
_DC = {"24V": Rail(max_v=Decimal(24), phase=None), "0V": Rail(max_v=Decimal(0), phase=None)}


def _hinted(plant: Plant, a: Id[Port], b: Id[Port], key: str, size: str | None = "0.75") -> None:
    """A wire `a`-`b` with a hint over `_TABLE` and the size `size` for every wire."""
    conductor = plant.wire(a, b, key=key)
    plant.add(
        WireRowHint(
            id=make_id(WireRowHint, (key, "hint")),
            key=(key, "hint"),
            subject=conductor,
            rows=frozendict(_TABLE),
            gauge_mm2=None if size is None else Decimal(size),
            label="W9",
        )
    )


def _dc_rail(plant: Plant, unit: Id[Unit] | None = None, *, key: str = "psu") -> Id[Port]:
    """A DC supply with a rail net on one port of its source item; returns that port."""
    item = plant.item(f"{key}-item", unit=unit)
    port = plant.port(plant.function(item, "out"), "plus")
    supply(plant, key, _DC, current=Current.DC, unit=unit, pins=[port])
    plant.net(f"{key}-24V", (port,), potential="24V")
    return port


def _load(plant: Plant, key: str, unit: Id[Unit] | None = None) -> Id[Port]:
    return plant.port(plant.function(plant.item(key, unit=unit), "f"), "1")


def _facet(model: Model) -> WireFacet:
    (found,) = facets_of(model, WireFacet).values()
    return found


def test_a_wire_on_a_dc_rail_takes_the_supply_row_and_the_hints_size_and_label() -> None:
    """Fails if the rail's row, the hint's size or its label do not reach the facet."""
    plant = Plant()
    _hinted(plant, _dc_rail(plant), _load(plant, "lamp"), "w")
    model, findings = resolve_wire_rows(plant.model())
    facet = _facet(model)
    assert (facet.colour, facet.gauge_mm2, facet.label, findings) == (
        "RD",
        Decimal("0.75"),
        "W9",
        (),
    )
    assert model.origins[facet.id] == model.origins[next(iter(facets_of(model, WireRowHint)))]


def test_a_row_size_is_used_when_the_hint_gives_none() -> None:
    """Fails if the table's size is ignored when no size is given for every wire."""
    plant = Plant()
    _dc_rail(plant)
    ground = plant.port(plant.function(plant.item("psu-minus"), "out"), "minus")
    plant.net("zero", (ground,), potential="0V")
    _hinted(plant, ground, _load(plant, "lamp"), "w", size=None)
    model, findings = resolve_wire_rows(plant.model())
    assert (_facet(model).gauge_mm2, findings) == (Decimal("1.5"), ())


def test_a_pin_that_states_a_source_row_gives_its_wire_that_row() -> None:
    """Fails if `Port.source_row` is not read for a net with no rail."""
    plant = Plant()
    out = plant.port(plant.function(plant.item("drive"), "out"), "U")
    plant.records[:] = [
        dataclasses.replace(r, source_row=WiringRow.AC_L2) if r.id == out else r
        for r in plant.records
    ]
    _hinted(plant, out, _load(plant, "motor"), "w")
    model, findings = resolve_wire_rows(plant.model())
    assert (_facet(model).colour, findings) == ("BN", ())


def test_a_plc_channel_net_takes_the_signal_row_even_when_a_rail_reaches_it() -> None:
    """Fails if the rail is read before the channel's signal: the net is fed from 24 V."""
    plant = Plant()
    (channel,) = _site(plant, Site("rack", "mod", "A1", 1))
    pin = plant.port(channel, "1")
    sensor = _load(plant, "sensor")
    feed = _dc_rail(plant)
    plant.wire(feed, pin, key="feed")  # a plain wire: 24 V is on the channel's net
    _hinted(plant, sensor, pin, "w")
    model, findings = resolve_wire_rows(plant.model())
    (hinted,) = (f for f in facets_of(model, WireFacet).values() if f.key[0] == "w")
    assert (hinted.colour, findings) == ("WH", ())


def test_a_net_with_no_rail_is_an_error_naming_the_net_and_the_fix() -> None:
    """Fails if an unresolved wire gets a facet or the finding drops the net or the fix."""
    plant = Plant()
    a, b = _load(plant, "a"), _load(plant, "b")
    plant.net("sig", (a, b), name="SIG1")
    _hinted(plant, a, b, "w")
    model, findings = resolve_wire_rows(plant.model())
    (finding,) = findings
    assert (finding.code, finding.severity) == ("WIRE_ROW_UNRESOLVED", Severity.ERROR)
    assert "SIG1" in finding.message
    assert "wire=" in finding.message
    assert not facets_of(model, WireFacet)


def test_a_row_with_no_size_anywhere_is_an_error() -> None:
    """Fails if a row with no size and no hint size writes a facet without one."""
    plant = Plant()
    _hinted(plant, _dc_rail(plant), _load(plant, "lamp"), "w", size=None)
    model, findings = resolve_wire_rows(plant.model())
    assert [f.code for f in findings] == ["WIRE_ROW_UNRESOLVED"]
    assert "size" in findings[0].message
    assert not facets_of(model, WireFacet)


def test_a_wire_whose_ends_carry_two_rows_is_an_error() -> None:
    """Fails if a net holding two rails of different rows picks one silently."""
    plant = Plant()
    ac = plant.port(plant.function(plant.item("ac"), "out"), "L1")
    dc = _dc_rail(plant)
    supply(plant, "mains", AC_400, pins=[ac])
    plant.net("mains-L1", (ac,), potential="L1")
    plant.wire(ac, dc, key="tie")
    _hinted(plant, dc, _load(plant, "x"), "w")
    _, findings = resolve_wire_rows(plant.model())
    assert [f.code for f in findings] == ["WIRE_ROW_UNRESOLVED"]


def test_a_container_rail_does_not_reach_a_nested_units_wire() -> None:
    """Fails if a rail crosses a unit boundary from its container into the nested unit."""
    plant = Plant()
    outer = plant.unit("outer")
    inner = plant.unit("inner", parent=outer)
    rail = _dc_rail(plant, outer)
    load = _load(plant, "lamp", inner)
    plant.wire(rail, load, key="boundary")  # the container's rail is on the nested unit's net
    _hinted(plant, load, _load(plant, "lamp2", inner), "w")
    model, findings = resolve_wire_rows(plant.model())
    assert [f.code for f in findings] == ["WIRE_ROW_UNRESOLVED"]
    assert not [f for f in facets_of(model, WireFacet).values() if f.key[0] == "w"]


def test_a_nested_units_rail_reaches_a_wire_in_its_container_and_in_the_unit_itself() -> None:
    """Fails if units below, or the unit's own rails, stop counting."""
    for wire_in_inner in (False, True):
        plant = Plant()
        outer = plant.unit("outer")
        inner = plant.unit("inner", parent=outer)
        rail = _dc_rail(plant, inner)
        _hinted(plant, rail, _load(plant, "lamp", inner if wire_in_inner else outer), "w")
        model, findings = resolve_wire_rows(plant.model())
        assert (_facet(model).colour, findings) == ("RD", ()), wire_in_inner


def test_a_second_run_changes_nothing() -> None:
    """Fails if the pass writes a facet twice or reports an already resolved wire."""
    plant = Plant()
    _hinted(plant, _dc_rail(plant), _load(plant, "lamp"), "w")
    once, _ = resolve_wire_rows(plant.model())
    twice, findings = resolve_wire_rows(once)
    assert twice is once
    assert findings == ()


def _inner_wire_rows(*, inside_container: bool) -> tuple[str, tuple[object, ...]]:
    """A nested unit's own wire row, built alone or in a container with an AC rail on its net."""
    plant = Plant()
    outer = plant.unit("outer") if inside_container else None
    inner = plant.unit("inner", parent=outer)
    rail = _dc_rail(plant, inner)
    load = _load(plant, "lamp", inner)
    if inside_container:
        mains = plant.port(plant.function(plant.item("ac", unit=outer), "out"), "L1")
        supply(plant, "mains", AC_400, unit=outer, pins=[mains])
        plant.net("mains-L1", (mains,), potential="L1")
        plant.wire(mains, load, key="boundary")  # the container's AC rail is on the unit's net
    _hinted(plant, rail, load, "w")
    model, findings = resolve_wire_rows(plant.model())
    return _facet(model).colour, findings


def test_a_nested_units_wire_rows_built_alone_equal_its_rows_in_a_container() -> None:
    """Fails if a rail crosses a unit boundary: the container's AC rail changes the unit's row."""
    assert _inner_wire_rows(inside_container=True) == _inner_wire_rows(inside_container=False)
