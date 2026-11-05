"""Field case: a cable that belongs to a unit builds and its unit's pages render.
The bug: `fr.build` raised `SchemaError` in `harness_line_ends`, which read only cables outside any unit.
Fixed by the rule, no record named: a cable's line ends are one fact wherever it sits (`unit_cables`)."""

import tempfile
from functools import cache
from pathlib import Path

import fransys as fr
from _field_shared import relay_cab

from fransys_model.derive import harness_line_ends
from fransys_model.vocab.tables import items


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
        d.add(relay_cab, "U1", place="CAB")
        schematic = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-cab", cover=cover)
        looms = fr.document(fr.DocumentPreset.SYSTEM, None, cover=looms_cover)
        return fr.build(d, schematic, looms)


def test_the_unit_with_a_cable_builds_and_has_no_error() -> None:
    """The build raises nothing and `check` finds no ERROR."""
    errors = [f.code for f in fr.check(_built()) if f.severity.name == "ERROR"]
    assert errors == []


def test_the_cables_line_ends_are_found_inside_the_unit() -> None:
    """The unit's cable has two line ends, the two relays."""
    (cable,) = [i.id for i in items(_built().model).values() if i.unit is not None and i.tag == "W1"]
    assert len(harness_line_ends(_built().model, cable)) == 2


def test_the_unit_pages_write(tmp_path: Path) -> None:
    """`write` renders the documents into PDF files."""
    assert any(p.suffix == ".pdf" for p in fr.write(_built(), tmp_path))
