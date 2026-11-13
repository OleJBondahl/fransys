"""`fransys_pdf.source` and the flowing list pages with the house `[pdf]` list shares.

The facade passes these two values from `fr.settings().pdf`; tests call the pdf package directly.
"""

from functools import partial
from typing import TYPE_CHECKING, cast

import fransys as fr
import fransys_pdf
from fransys_pdf import _lists

from fransys_model.derive import drawn_pages, pdf_texts
from fransys_model.derive.page_nav import reference_links

if TYPE_CHECKING:
    from collections.abc import Mapping

PDF = cast("Mapping[str, float]", fr.settings().pdf)
_FLOW = {
    "share_pct": cast("float", fr.settings().pdf["list_share_pct"]),
    "gutter_pct": cast("float", fr.settings().pdf["list_gutter_pct"]),
}


def source(model, document, svgs, sheets, bridges=None):
    """`fransys_pdf.source` with the house list shares and the model's reference links."""
    links = {page.id: reference_links(model, document, page.id, {}) for page in drawn_pages(model, document)}
    return fransys_pdf.source(
        model,
        document,
        svgs,
        sheets,
        bridges,
        links=links,
        pdf=PDF,
        **pdf_texts(model),
        diagrams=(),
    )


def bridge_inputs(model, bridges=None):
    """The Bridge word and pieces the terminal list builders take."""
    return pdf_texts(model)["words"]["bridge"], bridges, PDF["bridge_column_mm"]


def terminal_list_page(model, record, bridges=None):
    """`terminal_list_page` with the house shares and the model's Bridge word."""
    return _lists.terminal_list_page(model, record, bridge_inputs(model, bridges), **_FLOW)


connector_list_page = partial(_lists.connector_list_page, **_FLOW)
