"""Field case: a cable that belongs to a unit builds and its unit's pages render.

The engineering shape: a unit holds two relays and one 4-core cable W1 whose cores run from
coil A1 to coil A1 and from coil A2 to coil A2. The design adds the unit as U1 and builds a
`CABINET_SCHEMATIC` document with a `CABLE_LIST` page added, and a `HARNESS_DRAWING` document.

The bug: `fr.build` raised `SchemaError: ... neither a harness nor a cable` from
`harness_line_ends`, whose cable lookup read only the cables with no unit, so the cable of a
unit was not found.

Rule: a cable's line ends are the same fact wherever the cable sits, at the top or in a unit.
The lookup reads the cable through the reading it belongs to (`top_level_cables` or `unit_cables`).
"""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr

from fransys_model.derive import harness_line_ends
from fransys_model.vocab.tables import items


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
    """Built in the tests' bodies, so a build error is a test FAILURE, not a fixture error."""
    with tempfile.TemporaryDirectory() as tmp:
        cover = Path(tmp) / "cover.md"
        cover.write_text("# Cabinet\n", encoding="utf-8")
        looms_cover = Path(tmp) / "looms.md"
        looms_cover.write_text("# Looms\n", encoding="utf-8")
        d = fr.design("demo_parts")
        d.location("CAB", "Cabinet")
        d.add(_cab, "U1", place="CAB")
        schematic = fr.document(
            fr.DocumentPreset.CABINET_SCHEMATIC,
            "demo-cab",
            cover=cover,
            add=(fr.PageKind.CABLE_LIST,),
        )
        looms = fr.document(fr.DocumentPreset.HARNESS_DRAWING, "demo-cab", cover=looms_cover)
        return fr.build(d, schematic, looms)


def test_the_unit_with_a_cable_builds_and_has_no_error() -> None:
    """The build raises nothing and `check` finds no ERROR."""
    errors = [f.code for f in fr.check(_built()) if f.severity.name == "ERROR"]
    assert errors == []


def test_the_cables_line_ends_are_found_inside_the_unit() -> None:
    """The unit's cable has two line ends, the two relays."""
    (cable,) = [
        i.id for i in items(_built().model).values() if i.unit is not None and i.tag == "W1"
    ]
    assert len(harness_line_ends(_built().model, cable)) == 2


def test_the_unit_pages_write(tmp_path: Path) -> None:
    """`write` renders the documents into PDF files."""
    assert any(p.suffix == ".pdf" for p in fr.write(_built(), tmp_path))
