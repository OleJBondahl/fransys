"""Facade wiring of `fransys_pdf.check` and PDF export."""

import fransys as fr
import pytest
from fransys.pipeline import BuildFailedError
from fransys_author.design import Design

from fransys_model.vocab import DocumentPreset


@pytest.fixture
def parts():
    return fr.parts("demo_parts")


@pytest.fixture
def design(parts):
    d = Design(parts)
    d.project(
        title="Demo cabinet",
        number="DEMO-PDF-1",
        customer="Demo Co",
        revision=1,
        author="demo",
    )
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    return d


def _cover(tmp_path, name="cabinet.md", text="# Demo\n"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_write_produces_a_pdf_and_a_typ_intermediate(parts, design, tmp_path):
    """A document with no drawing pages exports a real PDF and writes its Typst source."""
    document_draft = fr.document(
        DocumentPreset.SYSTEM,
        None,
        cover=_cover(tmp_path),
    )
    result = fr.build(parts, design.draft(), document_draft)
    out_dir, intermediates = tmp_path / "out", tmp_path / "intermediates"

    written = fr.write(result, out_dir, intermediates=intermediates)

    pdfs = [path for path in written if path.suffix == ".pdf"]
    assert len(pdfs) == 1
    assert pdfs[0].name == "DEMO-PDF-1-v1.1.pdf"
    assert pdfs[0].read_bytes().startswith(b"%PDF-")
    typs = list(intermediates.glob("*.typ"))
    assert len(typs) == 1
    assert typs[0].name == "DEMO-PDF-1-v1.1.typ"
    assert typs[0].stat().st_size > 0


def test_write_compiles_a_pdf_with_no_project_record(parts, tmp_path):
    """No `Project` record: the compile still succeeds."""
    design = Design(parts)
    document_draft = fr.document(
        DocumentPreset.SYSTEM,
        None,
        cover=_cover(tmp_path),
    )
    result = fr.build(parts, design.draft(), document_draft)
    out_dir = tmp_path / "out"

    written = fr.write(result, out_dir)

    pdfs = [path for path in written if path.suffix == ".pdf"]
    assert len(pdfs) == 1
    assert pdfs[0].read_bytes().startswith(b"%PDF-")


def test_document_no_drawings_blocks_every_export_but_the_typ_still_writes(parts, design, tmp_path):
    """`DOCUMENT_NO_DRAWINGS` blocks every export (decision 0011) but the intermediate still lands.

    The default `CABINET_SCHEMATIC` preset carries `SCHEMATIC`, and `fransys_render` is
    still a scaffold, so `fransys_pdf.check` finds no drawing set for it -- proving decision
    """
    c1 = design.location("C1", "Demo cabinet")
    document_draft = fr.document(DocumentPreset.CABINET_SCHEMATIC, c1, cover=_cover(tmp_path))
    result = fr.build(parts, design.draft(), document_draft)
    out_dir, intermediates = tmp_path / "out", tmp_path / "intermediates"

    with pytest.raises(BuildFailedError) as excinfo:
        fr.write(result, out_dir, intermediates=intermediates)

    assert any(finding.code == "DOCUMENT_NO_DRAWINGS" for finding in excinfo.value.findings)
    assert not out_dir.exists() or list(out_dir.iterdir()) == []
    typs = list(intermediates.glob("*.typ"))
    assert len(typs) == 1
    assert typs[0].stat().st_size > 0


def _export_dated(parts, tmp_path, date):
    """Write a no-drawings cabinet PDF whose project's current `Revision` entry has `date`.

    Returns the Typst source and the PDF bytes.
    """
    tmp_path.mkdir()
    d = Design(parts)
    d.project(title="Demo", number="DEMO-PDF-2", customer="Demo Co", revision=1, author="demo")
    d.revision(1, date=date, text="First issue", created="XX")
    document_draft = fr.document(
        DocumentPreset.SYSTEM,
        None,
        cover=_cover(tmp_path),
    )
    result = fr.build(parts, d.draft(), document_draft)
    intermediates = tmp_path / "intermediates"
    written = fr.write(result, tmp_path / "out", intermediates=intermediates)
    pdf = next(path for path in written if path.suffix == ".pdf").read_bytes()
    typ = next(intermediates.glob("*.typ")).read_text(encoding="utf-8")
    return typ, pdf


def test_the_printed_date_and_the_embedded_timestamp_are_the_current_entrys(parts, tmp_path):
    """Change the current `Revision` entry's date and both the title block and the PDF's
    `CreationDate` move with it (the date lives on the entry alone)."""
    typ_a, pdf_a = _export_dated(parts, tmp_path / "a", "2026-09-22")
    typ_b, pdf_b = _export_dated(parts, tmp_path / "b", "2026-11-05")
    assert 'text("2026-09-22")' in typ_a
    assert "datetime(year: 2026, month: 9, day: 22)" in typ_a
    assert b"CreationDate(D:20260922000000Z)" in pdf_a
    assert 'text("2026-11-05")' in typ_b
    assert "datetime(year: 2026, month: 11, day: 5)" in typ_b
    assert b"CreationDate(D:20261105000000Z)" in pdf_b


def test_two_documents_with_one_typ_stem_are_refused_naming_both(parts, design, tmp_path, monkeypatch):
    """Writing both to `<stem>.typ` would lose one: `write` refuses (R1441)."""
    from fransys._export_ledger import ExportNameClashError

    from fransys_model.derive import document_ids

    design.location("C1", "Demo cabinet")
    one = fr.document(DocumentPreset.SYSTEM, None, cover=_cover(tmp_path))
    two = fr.document(DocumentPreset.SYSTEM, None, cover=_cover(tmp_path, "other.md"))
    result = fr.build(parts, design.draft(), one, two)
    monkeypatch.setattr("fransys._exports.document_stems", lambda model: tuple((i, "cover") for i in document_ids(model)))
    with pytest.raises(ExportNameClashError, match=r"cover\.typ"):
        fr.write(result, tmp_path / "out", intermediates=tmp_path / "inter")
