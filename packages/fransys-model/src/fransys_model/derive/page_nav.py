"""What the PDF's links and outline need from the model (NV2, NV3, PAGES-NAV).

Reached as `fransys_model.derive.page_nav.<name>`, never re-exported from `derive/__init__.py`.
Page numbers and titles come from `pdf_page`, `sheet_title_text` and `page_title`; nothing here
formats them again.
"""

lazy from collections.abc import Collection, Iterable, Mapping

from fransys_model.layout import LinkMarker, Page, layout_of
lazy from fransys_model.kernel import Id, Model

from .order import drawn_on_page
from .page_destination import page_destination, sheet_title_text
from .page_headings import diagram_title
from .page_titles import page_title
from .rows_nav import OutlineSheet, ReferenceLink
from .rows_sheet import DiagramSheet

__all__ = ["OutlineSheet", "ReferenceLink", "outline_sheets", "reference_links"]


type Boxes = Mapping[Id[LinkMarker], tuple[int, int, int, int]]


def reference_links(model: Model, page_id: Id[Page], known: Collection[Id[Page]], boxes: Boxes) -> tuple[ReferenceLink, ...]:
    """The links on page `page_id`: its link markers' `boxes`, each `(x, y, width, height)` in G (NV2).

    The facade measures each box from the drawn marker (SY7); this picks which markers link where.
    A marker links to the page of its partner marker; a shared box links from its lead only.
    A partner on `page` itself or outside `known` (the pages of this PDF) gets no link.
    """
    page = layout_of(model, Page)[page_id]
    return tuple(_marker_links(model, page, known, boxes))


def _marker_links(model: Model, page: Page, known: Collection[Id[Page]], boxes: Boxes) -> Iterable[ReferenceLink]:
    markers = layout_of(model, LinkMarker)
    pages = layout_of(model, Page)
    for marker in drawn_on_page(model, LinkMarker, page):
        target = markers[marker.partner].page
        if not marker.lead or target == marker.page or target not in known:
            continue
        x, y, width, height = boxes[marker.id]
        yield ReferenceLink(x=x, y=y, width=width, height=height, target=page_destination(model, pages[target]))


def outline_sheets(model: Model, sheets: Iterable[Id[Page] | DiagramSheet]) -> tuple[OutlineSheet, ...]:
    """One entry per sheet (a page id or a diagram sheet), in order: "3: Pump 1" (NV3)."""
    out = []
    for given in sheets:
        if isinstance(given, DiagramSheet):
            sheet, title, entries = given, diagram_title(model), ()
        else:
            sheet = layout_of(model, Page)[given]
            title, entries = page_title(model, sheet), ()
        out.append(
            OutlineSheet(
                destination=page_destination(model, sheet),
                title=sheet_title_text(model, sheet, title),
                entries=entries,
            )
        )
    return tuple(out)
