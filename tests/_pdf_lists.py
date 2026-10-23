"""`fransys_pdf.source` and the flowing list pages with the house `[pdf]` list shares.

The facade passes these two values from `fr.settings().pdf`; tests call the pdf package directly.
"""

from functools import partial
from typing import cast

import fransys as fr
import fransys_pdf
from fransys_pdf import _lists

from fransys_model.derive.page_nav import reference_links
from fransys_model.layout import Page, layout_of

_FLOW = {
    "share_pct": cast("float", fr.settings().pdf["list_share_pct"]),
    "gutter_pct": cast("float", fr.settings().pdf["list_gutter_pct"]),
}


def source(model, document, svgs, sheets, bridges=None):
    """`fransys_pdf.source` with the house list shares and the model's reference links."""
    known = set(layout_of(model, Page))
    links = {page: reference_links(model, page, known) for page in known}
    return fransys_pdf.source(
        model,
        document,
        svgs,
        sheets,
        bridges,
        links=links,
        list_share_pct=_FLOW["share_pct"],
        list_gutter_pct=_FLOW["gutter_pct"],
    )


terminal_list_page = partial(_lists.terminal_list_page, **_FLOW)
connector_list_page = partial(_lists.connector_list_page, **_FLOW)
