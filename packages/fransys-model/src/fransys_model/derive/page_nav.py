"""What the PDF's links and outline need from the model (NV2, NV3, PAGES-NAV).

Reached as `fransys_model.derive.page_nav.<name>`, never re-exported from `derive/__init__.py`.
Sheet numbers and titles come from `sheet_text`, `sheet_title_text` and `page_title`; nothing here
formats them again.
"""

from dataclasses import replace
lazy from collections.abc import Collection, Iterable

from fransys_model.layout import DiagramSheet, Label, LabelKind, LinkMarker, Page, layout_of
from fransys_model.vocab import functions
lazy from fransys_model.kernel import Id, Model
lazy from fransys_model.vocab import Item

from .contact_image import cross_reference_text
from .contact_rows import contact_rows
from .drawing_text import CONTACT_SLOTS, label_text
from .kinds import item_kind
from .marker_box import marker_box
from .order import designation_key, drawn_on_page
from .page_destination import page_destination, sheet_title_text
from .page_titles import page_title
from .rows import ItemKind
from .rows_nav import OutlineSheet, ReferenceLink
from .text_width import text_width

__all__ = ["OutlineSheet", "ReferenceLink", "outline_sheets", "reference_links"]

DIAGRAM_TITLE = "Block diagram"
_NO_ENTRY = (ItemKind.TERMINAL, ItemKind.CONNECTOR)  # NV3: terminals and pins get none


def reference_links(
    model: Model, page: Page, known: Collection[Id[Page]]
) -> tuple[ReferenceLink, ...]:
    """The links on `page`: its link markers' boxes, and one box per partner of each label (NV2).

    A marker links to the page of its partner marker; a shared box links from its lead only.
    A contact table links each row to the page of its contact (CR4, `_row_links`); a spare row and
    a row whose contact is on `page` get none.

    A label prints its partners left to right, each text once, joined by a space; a partner's
    box is that text's width (`text_width` at the label's height) from the label's own left edge.
    A partner on `page` itself or outside `known` (the pages of this PDF) gets no link.
    """
    links = list(_marker_links(model, page, known))
    for label in drawn_on_page(model, Label, page):
        if label.kind is not LabelKind.CROSS_REFERENCE:
            continue
        found = _row_links if label.slot in CONTACT_SLOTS else _label_links
        links.extend(found(model, label, known))
    return tuple(links)


def _marker_links(model: Model, page: Page, known: Collection[Id[Page]]) -> Iterable[ReferenceLink]:
    markers = layout_of(model, LinkMarker)
    pages = layout_of(model, Page)
    for marker in drawn_on_page(model, LinkMarker, page):
        target = markers[marker.partner].page
        if not marker.lead or target == marker.page or target not in known:
            continue
        x, y, width, height = marker_box(marker)
        yield ReferenceLink(
            x=x, y=y, width=width, height=height, target=page_destination(model, pages[target])
        )


def _label_links(
    model: Model, label: Label, known: Collection[Id[Page]]
) -> Iterable[ReferenceLink]:
    """The links of one label, partners in print order, equal texts sharing the first's box."""
    printed = ""
    seen = set()
    for partner in label.partners:
        text = cross_reference_text(model, replace(label, partners=(partner,)))
        if text in seen:
            continue
        seen.add(text)
        left = text_width(printed, height=label.height) if printed else 0
        printed = f"{printed} {text}" if printed else text
        if partner.page == label.page or partner.page not in known:
            continue
        gap = text_width(" ", height=label.height) if left else 0
        yield ReferenceLink(
            x=label.x + left + gap,
            y=label.y,
            width=text_width(text, height=label.height),
            height=label.height,
            target=page_destination(model, layout_of(model, Page)[partner.page]),
        )


def _row_links(model: Model, label: Label, known: Collection[Id[Page]]) -> Iterable[ReferenceLink]:
    """One link per row of a contact table whose contact is drawn on another page of the PDF."""
    pages = layout_of(model, Page)
    on = {partner.port: partner.page for partner in label.partners}
    for row in contact_rows(model, label):
        target = None if row.partner is None else on[row.partner]
        if target is None or target == label.page or target not in known:
            continue
        yield ReferenceLink(
            x=row.x,
            y=row.y,
            width=row.width,
            height=row.height,
            target=page_destination(model, pages[target]),
        )


def _designations(model: Model, page: Page) -> tuple[str, ...]:
    """The designations the page's item labels print, once each, in designation order."""
    records = functions(model)
    found: dict[str, Id[Item]] = {}
    for label in drawn_on_page(model, Label, page):
        if (
            label.kind is not LabelKind.TAG
            or label.slot == "outline_title"
            or label.function is None
        ):
            continue
        record = records[label.function]
        if item_kind(model, record.item) in _NO_ENTRY or not (text := label_text(model, label)):
            continue
        found.setdefault(text, record.item)
    return tuple(sorted(found, key=lambda text: (designation_key(model, found[text]), text)))


def outline_sheets(model: Model, sheets: Iterable[Page | DiagramSheet]) -> tuple[OutlineSheet, ...]:
    """One entry per sheet, in the order given: "Sheet 3: Pump 1" and its designations (NV3)."""
    out = []
    for sheet in sheets:
        if isinstance(sheet, DiagramSheet):
            title, entries = DIAGRAM_TITLE, ()
        else:
            title, entries = page_title(model, sheet), _designations(model, sheet)
        out.append(
            OutlineSheet(
                destination=page_destination(model, sheet),
                title=sheet_title_text(model, sheet, title),
                entries=entries,
            )
        )
    return tuple(out)
