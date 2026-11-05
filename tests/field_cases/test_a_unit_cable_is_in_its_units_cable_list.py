"""Field case: a unit holds two relays and a cable between their coils, with a CABLE_LIST page of its own.
The bug: cable_list_rows listed only top-level cables, so the unit's CABLE_LIST page and cables.csv lacked the cable.
Fixed by model-0191, a unit's documents list the unit's own cables; the system list keeps the top-level cables only."""

from typing import TYPE_CHECKING

import fransys as fr
from _field_shared import relay_cab_with_cable_list

from fransys_model.derive import cable_list_rows_of
from fransys_model.vocab.tables import units as units_table

if TYPE_CHECKING:
    from pathlib import Path


def test_the_unit_cable_list_has_the_units_cable() -> None:
    """`cable_list_rows(model, unit=U1)` lists W1."""
    model = relay_cab_with_cable_list().model
    (unit,) = units_table(model)
    assert [row.designation for row in fr.derive.cable_list_rows(model, unit=unit)] == ["-W1"]


def test_the_system_cable_list_has_no_unit_cable() -> None:
    """The unit=None list is the top-level cables: W1 is not one of them."""
    assert fr.derive.cable_list_rows(relay_cab_with_cable_list().model) == ()


def test_the_units_cables_csv_has_the_units_cable(tmp_path: Path) -> None:
    """The write scoped to the unit puts W1 in its `cables.csv`."""
    written = fr.write(relay_cab_with_cable_list(), tmp_path, unit="demo-cab")
    (csv,) = [p for p in written if p.name.endswith("cables.csv")]
    assert "W1" in csv.read_text(encoding="utf-8")


def test_cable_list_rows_of_gives_the_listed_row_in_its_own_unit() -> None:
    """`cable_list_rows_of(model, {W1})` equals the unit list's row for W1."""
    model = relay_cab_with_cable_list().model
    (unit,) = units_table(model)
    listed = fr.derive.cable_list_rows(model, unit=unit)
    assert cable_list_rows_of(model, {row.cable for row in listed}) == listed
    assert cable_list_rows_of(model, set()) == ()
