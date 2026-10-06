import pytest
from fransys_pdf import document_pages, source
from fransys_render import pages

from fransys_model.kernel import Id
from fransys_model.vocab import PageKind

pytestmark = [pytest.mark.wp("pdf"), pytest.mark.skip(reason="work package: pdf")]

# Placeholder ids: a real one would come from `fransys.document(...)`, which stores a
# `fransys_model.vocab.Document` record.
_DOC = Id(kind="document", value="demo-cabinet-schematic")
_PCB_DOC = Id(kind="document", value="demo-board-schematic")


def test_document_source_is_typst(demo_cabinet):
    typst_source = source(demo_cabinet, _DOC, pages(demo_cabinet))
    assert isinstance(typst_source, str)


def test_notes_page_dropped_when_no_notes_text(demo_cabinet):
    """A document record with no notes text produces no notes page."""
    assert PageKind.NOTES not in document_pages(demo_cabinet, _DOC)


def test_bom_is_the_last_page(demo_harness_with_board):
    """Every document's page order ends with the BOM (spec section 9)."""
    assert document_pages(demo_harness_with_board, _PCB_DOC)[-1] is PageKind.BOM
