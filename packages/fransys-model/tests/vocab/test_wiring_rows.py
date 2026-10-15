"""Wiring rows (model-0260): the one home of `rail_row`, the row a rail gives, `source_row`."""

import dataclasses
from decimal import Decimal
from pathlib import Path

import pytest
from examples import relay_part_bundle
from plant import Plant

from fransys_model.kernel import dumps, from_data, loads, make_id, to_data
from fransys_model.vocab import (
    ConductorMark,
    Current,
    Port,
    Rail,
    RowSpec,
    SupplySystem,
    WireRowHint,
    WiringRow,
    facets_of,
    instantiate,
    rail_row,
    supply_rail_row,
)

_M = ConductorMark


def _supply(current: Current, rails: dict[str, Rail]) -> SupplySystem:
    return SupplySystem(
        id=make_id(SupplySystem, ("s",)),
        key=("s",),
        name="s",
        current=current,
        rails=frozendict(rails),
    )


def _rail(volts: str, phase: int | None = None) -> Rail:
    return Rail(max_v=Decimal(volts), phase=phase)


def test_rail_row_maps_each_mark_and_reads_minus_by_the_mid() -> None:
    """Fails if a mark's row moves, or `L-` stops depending on a mid."""
    assert [rail_row(m) for m in (_M.L1, _M.L2, _M.L3, _M.N, _M.L_PLUS, _M.M)] == [
        WiringRow.AC_L1,
        WiringRow.AC_L2,
        WiringRow.AC_L3,
        WiringRow.AC_N,
        WiringRow.DC_SUPPLY,
        WiringRow.DC_GROUND,
    ]
    assert rail_row(_M.L_MINUS) is WiringRow.DC_GROUND
    assert rail_row(_M.L_MINUS, has_mid=True) is WiringRow.DC_SUPPLY


def test_a_three_phase_supply_with_n_gives_each_rail_its_phase_row() -> None:
    """Fails if a phase of 0, 120 or 240 degrees, or an AC rail at 0 V, reads as another row."""
    rails = {
        "L1": _rail("230", 0),
        "L2": _rail("230", 120),
        "L3": _rail("230", 240),
        "N": _rail("0"),
    }
    supply = _supply(Current.AC, rails)
    assert [supply_rail_row(supply, name) for name in rails] == [
        WiringRow.AC_L1,
        WiringRow.AC_L2,
        WiringRow.AC_L3,
        WiringRow.AC_N,
    ]


def test_a_dc_supply_without_a_mid_has_a_supply_rail_and_a_ground() -> None:
    """Fails if the 0 V rail of a two-rail DC supply stops being the ground row."""
    supply = _supply(Current.DC, {"24V": _rail("24"), "0V": _rail("0")})
    assert supply_rail_row(supply, "24V") is WiringRow.DC_SUPPLY
    assert supply_rail_row(supply, "0V") is WiringRow.DC_GROUND


def test_a_dc_supply_with_a_mid_has_two_supply_rails_and_the_mid_as_ground() -> None:
    """Fails if `-24V` stops being a supply row once the supply has a mid."""
    supply = _supply(Current.DC, {"24V": _rail("24"), "-24V": _rail("-24"), "0V": _rail("0")})
    assert supply_rail_row(supply, "24V") is WiringRow.DC_SUPPLY
    assert supply_rail_row(supply, "-24V") is WiringRow.DC_SUPPLY
    assert supply_rail_row(supply, "0V") is WiringRow.DC_GROUND


def test_a_rail_the_supply_does_not_declare_gives_no_row() -> None:
    """Fails if an unknown potential is given a row instead of `None`."""
    assert supply_rail_row(_supply(Current.DC, {"24V": _rail("24")}), "12V") is None


def test_a_hint_freezes_beside_its_conductor_and_survives_the_data_round_trip() -> None:
    """Fails if the hint cannot be frozen, is lost by `to_data`/`from_data`, or loses its table."""
    plant = Plant()
    conductor = plant.wire(plant.pin("a", "f", "1"), plant.pin("b", "f", "1"), key="w")
    hint = WireRowHint(
        id=make_id(WireRowHint, ("w", "hint")),
        key=("w", "hint"),
        subject=conductor,
        rows=frozendict({"AC_L1": RowSpec(colour="BK", gauge_mm2=None)}),
        gauge_mm2=Decimal("0.75"),
        label="W1",
    )
    plant.add(hint)
    model = plant.model()
    back = from_data(to_data(model))
    assert facets_of(back, WireRowHint) == facets_of(model, WireRowHint)
    (found,) = facets_of(back, WireRowHint).values()
    assert (found.subject, found.rows["AC_L1"].colour, found.gauge_mm2) == (
        conductor,
        "BK",
        Decimal("0.75"),
    )


def test_a_port_carries_the_source_row_its_template_states() -> None:
    """Fails if `instantiate` stops copying `PortTemplate.source_row` to the `Port`."""
    bundle = relay_part_bundle()
    stated = dataclasses.replace(bundle.port_templates[0], source_row=WiringRow.AC_L2)
    bundle = dataclasses.replace(bundle, port_templates=(stated, *bundle.port_templates[1:]))
    records = instantiate(bundle, ("items", "k1"))
    sourced = {p.name: p.source_row for p in records if isinstance(p, Port)}
    assert sourced[stated.name] is WiringRow.AC_L2
    assert {v for k, v in sourced.items() if k != stated.name} == {None}


@pytest.mark.parametrize("row", list(WiringRow))
def test_every_row_name_is_its_value(row: WiringRow) -> None:
    """Fails if a row's value differs from its name (tables key on the value)."""
    assert row.value == row.name


def test_a_stored_v20_text_loads_and_writes_back_byte_identical() -> None:
    """Fails if `source_row` is written as `null` (the stored text has no such key)."""
    stored = (Path(__file__).resolve().parent.parent / "golden" / "cabinet.json").read_text(
        encoding="utf-8"
    )
    assert '"schema_version": 20' in stored
    assert "source_row" not in stored
    assert dumps(loads(stored)) == stored


def test_a_port_with_a_source_row_writes_the_key_and_reads_it_back() -> None:
    """Fails if a set `source_row` is dropped on write or not read on load."""
    plant = Plant()
    port = plant.port(plant.function(plant.item("drive"), "out"), "U")
    plant.records[:] = [
        dataclasses.replace(r, source_row=WiringRow.AC_L2) if r.id == port else r
        for r in plant.records
    ]
    text = dumps(plant.model())
    assert text.count('"source_row": "AC_L2"') == 1
    loaded = loads(text).tables["port"][port]
    assert isinstance(loaded, Port)
    assert loaded.source_row is WiringRow.AC_L2
    assert dumps(loads(text)) == text
