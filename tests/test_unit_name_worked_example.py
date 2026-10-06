"""spec unit-subject-by-name (UN1-UN4), Acceptance 1 and 2, against the units worked
example's real facade-built geometry (UNIT-NAME Part 7).

Does not modify `test_units_worked_example.py`'s shared fixture functions
(`pump_cabinet`/`_system_design`): only imports and calls them, the same pattern
`test_write_unit_worked_example.py` already uses for a sibling root test module.
"""

import sys
from pathlib import Path

import fransys as fr
import fransys_author
import fransys_parts

# `test_declared_dependencies.py`'s own pattern for importing a sibling root test module by
# name: `--import-mode=importlib` (root pyproject.toml) never puts `tests/` on `sys.path`.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_units_worked_example import _PROJECT, _system_design, pump_cabinet

from fransys_model.derive import unit_release
from fransys_model.vocab.tables import units as units_table
from fransys_model.vocab.unit_by_name import unit_name_unresolved
from fransys_model.vocab.validators.documents import DOCUMENT_UNIT_UNRESOLVED


def _cover(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _single_cabinet_design(parts, *, prefix="p", name="C1"):
    """A one-cabinet model, built the same five lines `_build_cabinet_own` uses internally
    (`test_units_worked_example.py`, ~lines 205-211), but returning the `Design` before it is
    built, so a document can be added to the same draft before `fr.build`."""
    d = fransys_author.Design(parts)
    d.project(**_PROJECT)
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    pump_cabinet(d.scope(prefix), name=name)
    return d


def _the_cabinet_unit_id(model):
    """The one `demo-pump-cabinet` unit id in a single-cabinet model."""
    return next(
        unit_id
        for unit_id in units_table(model)
        if unit_release(model, unit_id).name == "demo-pump-cabinet"
    )


def _codes(result):
    return [f.code for f in result.findings]


# -- Acceptance 1: the spec's own worked example, literally -------------------------------


def test_unit_name_subject_gives_the_same_pdf_and_bom_bytes_as_the_unit_id(tmp_path):
    """A one-cabinet model, where `demo-pump-cabinet` is unique: a document naming it by its
    release name resolves to the same unit a document naming it by `Id` does, so `write`
    produces the same file set and byte-identical PDF and `bom.csv` either way (UN1, UN2, UN4;
    spec's worked example and Acceptance 1). Probe (per spec): edit `derive.document_unit`'s
    `unit_name` branch to `return None`; the by-name write then drops `cabinet.pdf` from its
    export set (it no longer resolves to the unit at all), and the file-name-set assertion
    below fails.
    """
    parts = fransys_parts.load("demo_parts")
    cover = _cover(tmp_path, "cabinet.md", "# Cabinet\n")

    probe_model = fr.build(parts, _single_cabinet_design(parts).draft()).model
    cabinet_id = _the_cabinet_unit_id(probe_model)

    doc_a = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, cabinet_id, cover=cover)
    result_a = fr.build(parts, _single_cabinet_design(parts).draft(), doc_a)

    doc_b = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-pump-cabinet", cover=cover)
    result_b = fr.build(parts, _single_cabinet_design(parts).draft(), doc_b)

    written_a = fr.write(result_a, tmp_path / "by-id", unit=cabinet_id)
    written_b = fr.write(result_b, tmp_path / "by-name", unit="demo-pump-cabinet")

    assert {p.name for p in written_a} == {p.name for p in written_b}
    (pdf_a,) = (p for p in written_a if p.name.endswith(".pdf"))
    (pdf_b,) = (p for p in written_b if p.name.endswith(".pdf"))
    assert pdf_a.read_bytes() == pdf_b.read_bytes()
    assert (tmp_path / "by-id" / "demo-pump-cabinet-v1.2-bom.csv").read_bytes() == (
        tmp_path / "by-name" / "demo-pump-cabinet-v1.2-bom.csv"
    ).read_bytes()


# -- Acceptance 2: an unresolved unit_name is one DOCUMENT_UNIT_UNRESOLVED ----------------


def test_unit_name_subject_with_two_instances_gives_one_document_unit_unresolved(tmp_path):
    """The real two-cabinet system: `demo-pump-cabinet` names two instances, so a document
    subject naming it gives exactly one `DOCUMENT_UNIT_UNRESOLVED`, its message
    `unit_name_unresolved`'s own several-instances sentence naming both real cabinets, not a
    second copy of it (UN3)."""
    parts = fransys_parts.load("demo_parts")
    d, _field1, _field2 = _system_design(parts)
    cover = _cover(tmp_path, "cabinet.md", "# Cabinet\n")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-pump-cabinet", cover=cover)

    result = fr.build(parts, d.draft(), doc)

    unresolved = [f for f in result.findings if f.code == DOCUMENT_UNIT_UNRESOLVED]
    assert len(unresolved) == 1
    expected = unit_name_unresolved(result.model, "demo-pump-cabinet")
    assert unresolved[0].message == expected
    assert "2 units are instances of" in expected


def test_unit_name_subject_unknown_name_gives_one_document_unit_unresolved(tmp_path):
    """Same real two-cabinet system: an unknown release name gives exactly one
    `DOCUMENT_UNIT_UNRESOLVED`, case (a)'s "no unit release is named" sentence (UN3)."""
    parts = fransys_parts.load("demo_parts")
    d, _field1, _field2 = _system_design(parts)
    cover = _cover(tmp_path, "cabinet.md", "# Cabinet\n")
    doc = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "no-such-release", cover=cover)

    result = fr.build(parts, d.draft(), doc)

    unresolved = [f for f in result.findings if f.code == DOCUMENT_UNIT_UNRESOLVED]
    assert len(unresolved) == 1
    expected = unit_name_unresolved(result.model, "no-such-release")
    assert unresolved[0].message == expected
    assert expected.startswith("no unit release is named 'no-such-release'")
