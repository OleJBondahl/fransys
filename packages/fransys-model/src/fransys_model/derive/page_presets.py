"""What each document preset contains by default (root DESIGN 9), and a document's page kinds.

The one home of the page list: pdf assembles exactly these pages and render draws their sheets.
"""

from fransys_model.kernel import ModelError
from fransys_model.vocab import DocumentPreset, PageKind
from fransys_model.vocab.page_forms import PAGE_FORMS
from fransys_model.vocab.tables import documents
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import Document

from .rows_page import PagePreset

__all__ = ["PRESET_PAGES", "document_page_kinds", "page_kinds", "page_preset"]

_K = PageKind

PRESET_PAGES: frozendict[DocumentPreset, tuple[PageKind, ...]] = frozendict(
    {
        DocumentPreset.CABINET_SCHEMATIC: (
            _K.COVER,
            _K.NOTES,
            _K.SHEET_INDEX,
            _K.SCHEMATIC,
            _K.PLC_LIST,
            _K.TERMINAL_LIST,
            _K.CONNECTOR_LIST,
            _K.BOM,
        ),
        DocumentPreset.SYSTEM: (
            _K.COVER,
            _K.NOTES,
            _K.SHEET_INDEX,
            _K.BLOCK_DIAGRAM,
            _K.HARNESS_DRAWING,
            _K.CABLE_LIST,
            _K.BOM,
        ),
    }
)


def page_kinds(preset: DocumentPreset) -> tuple[PageKind, ...]:
    """The pages of a preset, in canonical order."""
    return tuple(kind for kind in PageKind if kind in PRESET_PAGES[preset])


def document_page_kinds(model: Model, document: Id[Document]) -> tuple[PageKind, ...]:
    """The pages one document will contain, in order.

    `page_kinds` of the document record's preset, with NOTES dropped when the record has no
    notes text. `fransys_pdf.source` assembles exactly these pages.
    """
    record = documents(model)[document]
    resolved = page_kinds(record.preset)
    if record.notes is None:
        resolved = tuple(kind for kind in resolved if kind is not PageKind.NOTES)
    return resolved


def page_preset(kind: PageKind) -> PagePreset:
    """What `kind` is: its `PageForm`, its `ListKey` (lists only) and whether it frames itself.

    Pure data from `vocab.page_forms`; `fransys_pdf` builds each page from it. A kind with no
    entry raises a `ModelError` naming the kind, never a default.

    Example: `page_preset(PageKind.BOM)` has form `LIST` and list key `BOM`.
    """
    if kind not in PAGE_FORMS:
        msg = f"no page preset for {kind!r}"
        raise ModelError(msg)
    form, list_key, self_framed = PAGE_FORMS[kind]
    return PagePreset(kind=kind, form=form, list_key=list_key, self_framed=self_framed)
