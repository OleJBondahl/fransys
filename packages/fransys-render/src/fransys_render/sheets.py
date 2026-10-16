"""Every page background of every document: frame, grid and title block as SVG (render-0019).

One frame fragment per sheet format and size set, one title-block fragment per page. pdf lays
the SVG behind a page and fills the two boxes it returns with the page counter and the logo.
"""

from functools import partial
from typing import TYPE_CHECKING

from electrical_symbols import (
    TITLE_BLOCK_MIN_BAND_MM,
    TITLE_BLOCK_MIN_WIDTH_MM,
    sheet_svg,
    slot_box_mm,
)
from fransys_model.derive import SheetBackground, title_block_strings

from ._sheet_draw import (
    frame_fragment,
    logo_symbol,
    notice_room,
    title_fragment,
    title_rooms,
    title_symbol,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import DocumentSheets, SheetPage
    from fransys_model.kernel import Id
    from fransys_model.vocab import Document

__all__ = ["sheets"]


def _background(
    page: SheetPage, listing: DocumentSheets, frames: dict[tuple[object, object], str]
) -> SheetBackground:
    sizes = listing.sizes
    sheet = page.sheet
    frame = listing.frames[sheet.id]
    key = (sheet.id, sizes)
    if key not in frames:
        frames[key] = frame_fragment(frame, sizes)
    page_svg = partial(sheet_svg, sheet.width_mm, sheet.height_mm)
    if frame.band < TITLE_BLOCK_MIN_BAND_MM or frame.title_width < TITLE_BLOCK_MIN_WIDTH_MM:
        return SheetBackground(
            svg=page_svg(frames[key]), counter_box=None, logo_box=None, title_room_mm=None
        )
    block, logo = title_symbol(frame, notice=bool(page.fields.notice)), logo_symbol(frame)
    rooms = title_rooms(block)
    width, capacity = notice_room(block, sizes)
    strings = title_block_strings(
        page.fields, rooms, sizes, notice_width_mm=width, notice_capacity=capacity
    )
    return SheetBackground(
        svg=page_svg(frames[key] + title_fragment(block, logo, strings, sizes)),
        counter_box=slot_box_mm(block.lines, "page"),
        logo_box=slot_box_mm(logo, "logo"),
        title_room_mm=rooms["page_title"],
    )


def sheets(listings: Mapping[Id[Document], DocumentSheets]) -> frozendict[str, SheetBackground]:
    """The background of every page of every `Document`, by `derive.sheet_key`.

    Args:
        listings: `derive.document_sheets_of(model)`: each document's paper, sizes and pages.

    Returns:
        Page key to its SVG (frame, grid, title block) and the two boxes pdf fills. Pure.
    """
    frames: dict[tuple[object, object], str] = {}
    found = {}
    for listing in listings.values():
        for page in listing.pages:
            found[page.key] = _background(page, listing, frames)
    return frozendict(found)
