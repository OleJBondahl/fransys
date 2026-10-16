"""`document_rows`, `document_row` and `revision_rows` equal the records' fields (model-0305)."""

import fransys as fr
import pytest

from fransys_model.derive import (
    document_row,
    document_rows,
    revision_history,
    revision_rows,
)
from fransys_model.vocab.tables import documents


@pytest.fixture(scope="module")
def model(tmp_path_factory):
    """One location document with notes and a logo, one system document without, two revisions."""
    root = tmp_path_factory.mktemp("docs")
    d = fr.design("demo_parts")
    c1 = d.location("C1", "Cabinet")
    d.revision(1, date="2026-01-02", text="First issue", created="XX")
    d.revision(2, date="2026-02-03", text="Second", created="YY", checked="ZZ", approved="WW")
    cover = root / "cab.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    (root / "cab.notes.md").write_text("Some notes.\n", encoding="utf-8")
    logo = root / "logo.svg"
    logo.write_text('<svg xmlns="http://www.w3.org/2000/svg"/>', encoding="utf-8")
    plain = root / "sys.md"
    plain.write_text("# System\n", encoding="utf-8")
    drafts = (
        fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, c1, cover=cover, logo=logo),
        fr.document(fr.DocumentPreset.SYSTEM, None, cover=plain),
    )
    return fr.build(d, *drafts).model


def test_rows_equal_the_record_fields_in_table_order(model):
    records = tuple(documents(model).values())
    rows = document_rows(model)
    assert len(rows) == 2
    for row, rec in zip(rows, records, strict=True):
        assert (row.id, row.preset, row.location, row.item) == (
            rec.id,
            rec.preset,
            rec.location,
            rec.item,
        )
        assert (row.cover, row.notes, row.logo) == (rec.cover, rec.notes, rec.logo)
        assert document_row(model, rec.id) == row


def test_a_notes_text_and_a_logo_reach_the_row(model):
    cab = next(r for r in document_rows(model) if r.location is not None)
    assert cab.notes == "Some notes.\n"
    assert cab.logo is not None
    assert cab.logo.startswith("<svg")
    system = next(r for r in document_rows(model) if r.location is None)
    assert (system.notes, system.logo) == (None, None)


def test_revision_rows_equal_the_history(model):
    history = revision_history(model)
    rows = revision_rows(model)
    assert len(rows) == 2
    for row, entry in zip(rows, history, strict=True):
        assert (row.version, row.revision, row.date, row.text) == (
            entry.version,
            entry.revision,
            entry.date,
            entry.text,
        )
        assert (row.created, row.checked, row.approved) == (
            entry.created,
            entry.checked,
            entry.approved,
        )
    assert rows[1].checked == "ZZ"
