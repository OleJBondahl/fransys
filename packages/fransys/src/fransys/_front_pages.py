"""The front matter's page count, compiled alone by Typst once per covered document and stored as a model value (model-0462)."""

from typing import TYPE_CHECKING, cast

import fransys_pdf
import fransys_render

from fransys_model.derive import covered_documents, document_sheets_of, pdf_texts
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


def with_front_pages(model: Model, library: Library, settings: Settings) -> Model:
    """`model` with one `FrontPages` record per document that keeps a cover: its Typst page count, before layout."""
    covered = covered_documents(model)
    if not covered:
        return model
    sheets = fransys_render.sheets(document_sheets_of(model, ()), library)
    compiler = typst_compiler(settings)
    pdf = cast("Mapping[str, float]", settings.pdf)
    counts = {}
    for document in covered:
        text = fransys_pdf.source(model, document, {}, sheets, None, links={}, diagrams=(), pdf=pdf, front_only=True, **pdf_texts(model))
        compiled = compiler.compile(input=text.encode("utf-8"), format="svg")
        # typst-py returns one `bytes` for a one-page document and a list of `bytes` for more (confirmed by compiling both)
        counts[document] = len(compiled) if isinstance(compiled, list) else 1
    return evolve(model, put=front_pages_records(counts), origin=_ORIGIN)
