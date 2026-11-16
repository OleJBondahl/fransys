"""The front matter's page count, compiled alone by Typst once per covered document and stored as a model value (model-0462)."""

from typing import TYPE_CHECKING, cast

import fransys_pdf
import fransys_render

from fransys_model.derive import (
    DiagramSheet,
    covered_documents,
    diagram_sheets,
    document_ids,
    document_sheets_of,
    is_system_document,
    pdf_texts,
)
from fransys_model.kernel import Origin, evolve
from fransys_model.layout import front_pages_records

from ._typst_compile import typst_compiler

if TYPE_CHECKING:
    from collections.abc import Mapping

    from electrical_symbols import Library
    from fransys_model.kernel import Model

    from .settings import Settings

__all__ = ["with_front_pages"]

_ORIGIN = Origin(file="fransys/_front_pages.py", line=0, note="the front matter's Typst page count")


def with_front_pages(model: Model, library: Library, settings: Settings, diagrams: tuple[DiagramSheet, ...]) -> Model:
    """`model` with one `FrontPages` record per document: its Typst front count (0 without a cover) and its diagram sheet count."""
    sheets = fransys_render.sheets(document_sheets_of(model, ()), library)
    compiler = typst_compiler(settings)
    pdf = cast("Mapping[str, float]", settings.pdf)
    counts = dict.fromkeys(document_ids(model), 0)
    for document in covered_documents(model):
        text = fransys_pdf.source(model, document, {}, sheets, None, links={}, diagrams=(), pdf=pdf, front_only=True, **pdf_texts(model))
        compiled = compiler.compile(input=text.encode("utf-8"), format="svg")
        # typst-py returns one `bytes` for a one-page document and a list of `bytes` for more (confirmed by compiling both)
        counts[document] = len(compiled) if isinstance(compiled, list) else 1
    found = {document: len(diagram_sheets(model, document, diagrams)) if is_system_document(model, document) else 0 for document in counts}
    return evolve(model, put=front_pages_records(counts, found), origin=_ORIGIN)
