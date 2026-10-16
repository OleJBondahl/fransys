import fransys_render
import pytest
from fransys_el import REF_TINTS
from fransys_pdf import source
from fransys_render import pages

from fransys_model.derive import document_page_kinds, document_sheets_of
from fransys_model.kernel import Id
from fransys_model.vocab import PageKind

pytestmark = [pytest.mark.wp("pdf"), pytest.mark.skip(reason="the pdf package is not built yet")]

# Placeholder ids: a real one would come from `fransys.document(...)`, which stores a
# `fransys_model.vocab.Document` record.
_DOC = Id(kind="document", value="demo-cabinet-schematic")
_PCB_DOC = Id(kind="document", value="demo-board-schematic")


def test_document_source_is_typst(demo_cabinet):
    typst_source = source(
        demo_cabinet,
        _DOC,
        pages(demo_cabinet, tints=REF_TINTS),
        fransys_render.sheets(document_sheets_of(demo_cabinet)),
    )
    assert isinstance(typst_source, str)


def test_notes_page_dropped_when_no_notes_text(demo_cabinet):
    """A document record with no notes text produces no notes page."""
    assert PageKind.NOTES not in document_page_kinds(demo_cabinet, _DOC)


def test_bom_is_the_last_page(demo_harness_with_board):
    """Every document's page order ends with the BOM."""
    assert document_page_kinds(demo_harness_with_board, _PCB_DOC)[-1] is PageKind.BOM
