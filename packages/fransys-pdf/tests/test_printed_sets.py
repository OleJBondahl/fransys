"""The drawing sets a document prints are one fact, `derive.document_drawing_sets` (model-0201)."""

from _build import document, drawing_set, layout_page, location, model, unit
from fransys_pdf._drawings import schematic_pages

from fransys_model.derive import (
    document_drawing_sets,
    document_pages,
    document_row,
    printed_drawing_sets,
)
from fransys_model.vocab import DocumentPreset, PageKind

K = PageKind


def _fixture():
    """A cabinet's unit prints set 2; the top-level set 1 has no document."""
    c1 = location("C1", "Demo cabinet")
    u = unit("u1", name="cab")
    top = drawing_set("top", location=c1, number=1)
    own = drawing_set("own", location=c1, unit=u, number=2)
    p_top = layout_page("p_top", drawing_set=top, number=1)
    p_own = layout_page("p_own", drawing_set=own, number=1)
    doc = document("d1", preset=DocumentPreset.CABINET_SCHEMATIC, subject=u, cover="# c")
    m = model(c1, u, top, own, p_top, p_own, doc)
    return m, document_row(m, doc.id), top, own, p_own


def test_the_printed_sets_leave_out_a_set_no_document_prints():
    m, record, top, own, _ = _fixture()
    assert [s.id for s in document_drawing_sets(m, record.id)] == [own.id]
    assert [s.id for s in printed_drawing_sets(m)] == [own.id]
    assert top.id not in {s.id for s in printed_drawing_sets(m)}


def test_the_pdf_takes_its_sets_from_the_derive_function(monkeypatch):
    m, record, _, _, p_own = _fixture()
    assert list(schematic_pages(m, record, (K.SCHEMATIC,))) == [p_own.id]
    monkeypatch.setattr(document_pages, "document_drawing_sets", lambda *_: ())
    assert schematic_pages(m, record, (K.SCHEMATIC,)) == ()
