"""Field case: a marker whose partner stands on a page of another document's PDF that has the same page number as a page of this PDF.
The bug (KI-879): the link kept its `p<n>` label, which this PDF also prints, so it jumped to this PDF's page n. Closed by `same_pdf` (PDF-LINKS)."""

import dataclasses
import tempfile
from pathlib import Path

import fransys as fr
import pypdfium2
import pytest
from pypdfium2 import raw
from test_end_to_end import _two_documents

from fransys_model.derive import document_export_name, documents, scope_path
from fransys_model.derive.document_pages import drawn_pages
from fransys_model.kernel import Origin, evolve
from fransys_model.layout import LinkMarker, layout_of


def _link_count(pdf: pypdfium2.PdfDocument) -> int:
    """The /Link annotations of every page of `pdf`."""
    return sum(raw.FPDFPage_GetAnnotCount(page.raw) for page in pdf)


@pytest.mark.rule("PDF-LINKS")
def test_a_marker_whose_partner_is_in_another_pdf_has_no_link() -> None:
    root = Path(tempfile.mkdtemp())
    result = _two_documents(root)
    model = result.model
    markers = layout_of(model, LinkMarker)
    pages = {scope_path(model, r.id): {p.id for p in drawn_pages(model, r.id)} for r in documents(model).values()}
    near = next(m for m in markers.values() if m.page in pages["+CAB"])
    far = next(m for m in markers.values() if m.page in pages["+FLD"])
    pointing_out = dataclasses.replace(near, partner=far.id, star=None, pairs=())  # a plain marker: an off stub names no end
    cut = evolve(model, remove=[near.id], put=[pointing_out], origin=Origin(file="<field case>", line=1, note="partner in the other PDF"))
    fr.write(dataclasses.replace(result, model=cut), root / "out")
    cab = next(r for r in documents(cut).values() if scope_path(cut, r.id) == "+CAB")
    assert _link_count(pypdfium2.PdfDocument(root / "out" / document_export_name(cut, None, cab))) == 0
