"""Field case: a cable inside a unit is in that unit's cable list, not in the system's.

The engineering shape: a unit holds two relays and one cable W1 between their coils. The design
adds the unit as U1 and builds a `CABINET_SCHEMATIC` document with a `CABLE_LIST` page.

The bug: `cable_list_rows(model)` listed the top-level cables only, so W1 was missing from the
unit's CABLE_LIST page and from the unit's `cables.csv`: a silently missing cable.

Rule: a unit's documents list the unit's own cables, the scope `harness_cables_for` reads; the
system list keeps the top-level cables only (decision model-0191).
"""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr

from fransys_model.derive import cable_list_rows_of
from fransys_model.vocab.tables import units as units_table


class _Open(NamedTuple):
    pass


@fr.unit("demo-cab", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _cab(u: Any) -> _Open:
    k1 = u.device("K1", "DEMO-RLY-2CO-24")
    k2 = u.device("K2", "DEMO-RLY-2CO-24")
    cable = u.cable("W1", "DEMO-CBL-4G1.5", length_m=1)
    cable.core(1, k1.coil["A1"], k2.coil["A1"])
    cable.core(2, k1.coil["A2"], k2.coil["A2"])
    return _Open()


@cache
def _built() -> fr.BuildResult:
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Cabinet\n", encoding="utf-8")
        d = fr.design("demo_parts")
        d.location("CAB", "Cabinet")
        d.add(_cab, "U1", place="CAB")
        schematic = fr.document(
            fr.DocumentPreset.CABINET_SCHEMATIC,
            "demo-cab",
            cover=cover,
            add=(fr.PageKind.CABLE_LIST,),
        )
        return fr.build(d, schematic)


def test_the_unit_cable_list_has_the_units_cable() -> None:
    """`cable_list_rows(model, unit=U1)` lists W1."""
    model = _built().model
    (unit,) = units_table(model)
    assert [row.designation for row in fr.derive.cable_list_rows(model, unit=unit)] == ["-W1"]


def test_the_system_cable_list_has_no_unit_cable() -> None:
    """The unit=None list is the top-level cables: W1 is not one of them."""
    assert fr.derive.cable_list_rows(_built().model) == ()


def test_the_units_cables_csv_has_the_units_cable(tmp_path: Path) -> None:
    """The write scoped to the unit puts W1 in its `cables.csv`."""
    written = fr.write(_built(), tmp_path, unit="demo-cab")
    (csv,) = [p for p in written if p.name.endswith("cables.csv")]
    assert "W1" in csv.read_text(encoding="utf-8")


def test_cable_list_rows_of_gives_the_listed_row_in_its_own_unit() -> None:
    """`cable_list_rows_of(model, {W1})` equals the unit list's row for W1."""
    model = _built().model
    (unit,) = units_table(model)
    listed = fr.derive.cable_list_rows(model, unit=unit)
    assert cable_list_rows_of(model, {row.cable for row in listed}) == listed
    assert cable_list_rows_of(model, set()) == ()
