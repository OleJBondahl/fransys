"""Task 6 (Part 5b): facade wiring of `fransys_pdf.check` and PDF export (spec F6, P1, P11)."""

import fransys as fr
import fransys_author
import pytest
from fransys.pipeline import BuildErrors

from fransys_model.vocab import DocumentPreset, PageKind


@pytest.fixture
def parts():
    return fr.parts("demo_parts")


@pytest.fixture
def design(parts):
    d = fransys_author.Design(parts)
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
    c1 = design.location("C1", "Demo cabinet")
    document_draft = fr.document(
        DocumentPreset.CABINET_SCHEMATIC,
        c1,
        cover=_cover(tmp_path),
        remove=(PageKind.SCHEMATIC,),
    )
    result = fr.build(parts, design.draft(), document_draft)
    out_dir, intermediates = tmp_path / "out", tmp_path / "intermediates"

    written = fr.write(result, out_dir, intermediates=intermediates)

    pdfs = [path for path in written if path.suffix == ".pdf"]
    assert len(pdfs) == 1
    assert pdfs[0].name == "DEMO-PDF-1-v1.1-C1.pdf"
    assert pdfs[0].read_bytes().startswith(b"%PDF-")
    typs = list(intermediates.glob("*.typ"))
    assert len(typs) == 1
    assert typs[0].name == "cabinet.typ"
    assert typs[0].stat().st_size > 0


def test_write_compiles_a_pdf_with_no_project_record(parts, tmp_path):
    """No `Project` record: the compile still succeeds (spec P1, P3)."""
    design = fransys_author.Design(parts)
    c1 = design.location("C1", "Demo cabinet")
    document_draft = fr.document(
        DocumentPreset.CABINET_SCHEMATIC,
        c1,
        cover=_cover(tmp_path),
        remove=(PageKind.SCHEMATIC,),
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
    0011 and pdf-0001's P11 amendment hold together at the facade seam (spec F5, P11).
    """
    c1 = design.location("C1", "Demo cabinet")
    document_draft = fr.document(DocumentPreset.CABINET_SCHEMATIC, c1, cover=_cover(tmp_path))
    result = fr.build(parts, design.draft(), document_draft)
    out_dir, intermediates = tmp_path / "out", tmp_path / "intermediates"

    with pytest.raises(BuildErrors) as excinfo:
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
    d = fransys_author.Design(parts)
    d.project(title="Demo", number="DEMO-PDF-2", customer="Demo Co", revision=1, author="demo")
    d.revision(1, date=date, text="First issue", created="XX")
    c1 = d.location("C1", "Demo cabinet")
    document_draft = fr.document(
        DocumentPreset.CABINET_SCHEMATIC,
        c1,
        cover=_cover(tmp_path),
        remove=(PageKind.SCHEMATIC,),
    )
    result = fr.build(parts, d.draft(), document_draft)
    intermediates = tmp_path / "intermediates"
    written = fr.write(result, tmp_path / "out", intermediates=intermediates)
    pdf = next(path for path in written if path.suffix == ".pdf").read_bytes()
    typ = next(intermediates.glob("*.typ")).read_text(encoding="utf-8")
    return typ, pdf


def test_the_printed_date_and_the_embedded_timestamp_are_the_current_entrys(parts, tmp_path):
    """Change the current `Revision` entry's date and both the title block and the PDF's
    `CreationDate` move with it (schema spec SC4: the date lives on the entry alone)."""
    typ_a, pdf_a = _export_dated(parts, tmp_path / "a", "2026-09-22")
    typ_b, pdf_b = _export_dated(parts, tmp_path / "b", "2026-11-05")
    assert 'text("2026-09-22")' in typ_a
    assert "datetime(year: 2026, month: 9, day: 22)" in typ_a
    assert b"CreationDate(D:20260922000000Z)" in pdf_a
    assert 'text("2026-11-05")' in typ_b
    assert "datetime(year: 2026, month: 11, day: 5)" in typ_b
    assert b"CreationDate(D:20261105000000Z)" in pdf_b


def test_a_unit_documents_embedded_date_is_the_unit_revisions_date_not_the_projects(
    parts, tmp_path
):
    """A unit document prints and embeds its unit revision's date (UNIT-ID I2); a project
    document beside it in the same build keeps the project's (the two dates differ).

    The embedded date is the source's own `#set document(date: ...)` line
    (`fransys_pdf._geometry.document_metadata`); the facade passes no compile timestamp
    (decision 0030)."""
    d = fransys_author.Design(parts)
    d.project(title="Demo", number="DEMO-PDF-4", customer="Demo Co", revision=1, author="demo")
    d.revision(1, date="2026-09-22", text="First issue", created="XX")
    c1 = d.location("C1", "Demo cabinet")
    unit = d.scope("cab").unit("demo-unit", revision=1, interface="1", title="Unit", number="U-1")
    unit.revision(1, date="2026-03-04", text="First release", created="XX")
    unit_document = fr.document(
        DocumentPreset.CABINET_SCHEMATIC,
        unit,
        cover=_cover(tmp_path, "unit-doc.md"),
        remove=(PageKind.SCHEMATIC,),
    )
    project_document = fr.document(
        DocumentPreset.CABINET_SCHEMATIC,
        c1,
        cover=_cover(tmp_path, "project-doc.md"),
        remove=(PageKind.SCHEMATIC,),
    )
    result = fr.build(parts, d.draft(), unit_document, project_document)
    intermediates = tmp_path / "intermediates"
    written = fr.write(result, tmp_path / "out", intermediates=intermediates)
    pdfs = {path.name: path.read_bytes() for path in written if path.suffix == ".pdf"}
    assert set(pdfs) == {"demo-unit-v1.1.pdf", "DEMO-PDF-4-v1.1-C1.pdf"}
    unit_typ = (intermediates / "unit-doc.typ").read_text(encoding="utf-8")
    project_typ = (intermediates / "project-doc.typ").read_text(encoding="utf-8")

    assert b"CreationDate(D:20260304000000Z)" in pdfs["demo-unit-v1.1.pdf"]
    assert b"CreationDate(D:20260922000000Z)" not in pdfs["demo-unit-v1.1.pdf"]
    assert 'text("2026-03-04")' in unit_typ
    assert "datetime(year: 2026, month: 3, day: 4)" in unit_typ
    assert 'text("2026-09-22")' not in unit_typ
    assert b"CreationDate(D:20260922000000Z)" in pdfs["DEMO-PDF-4-v1.1-C1.pdf"]
    assert b"CreationDate(D:20260304000000Z)" not in pdfs["DEMO-PDF-4-v1.1-C1.pdf"]
    assert 'text("2026-09-22")' in project_typ
