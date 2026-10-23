"""A sheet's frame, grid and title block drawn by the toolkit from derive's values (render-0019).

Each layer is one `symdef` fragment in mm; this module only picks a layer's texts and font size.
The symbols are `electrical_symbols`' data; the sizes, the words and the cuts are derive's.
"""

from decimal import Decimal
from typing import TYPE_CHECKING

from electrical_symbols import (
    bold_layer,
    frame_border,
    frame_strip,
    notice_table,
    slot_room,
    slot_widths,
    title_block,
    title_logo,
)
from fransys_model.derive import notice_line_count, notice_pitch_mm

from ._symbols import symbol_body

if TYPE_CHECKING:
    from collections.abc import Mapping

    from symdef import Symbol

    from electrical_symbols import Library, TitleBlock
    from fransys_model.derive import DocumentSheets, SheetFrame, Sizes, TitleBlockStrings

_MM = Decimal(1)  # the sheet symbols are authored in mm: one module is one mm


def _layer(library: Library, symbol: Symbol, texts: Mapping[str, str], font_mm: float) -> str:
    """One layer's fragment at one font size."""
    return symbol_body(library, symbol, _MM, Decimal(repr(font_mm)), texts=texts)


def frame_fragment(library: Library, frame: SheetFrame, sizes: Sizes) -> str:
    """The border, the ticks and the reference labels of a sheet frame."""
    x, y, width, height = frame.border
    parts = [_layer(library, frame_border((x, y), width, height), {}, sizes.label)]
    for strip in frame.strips:
        cell = (strip.cell_width, strip.cell_height)
        symbol = frame_strip(strip.side, (strip.x, strip.y), cell, len(strip.labels), strip.axis)
        texts = {f"{k}.label": text for k, text in enumerate(strip.labels, 1)}
        parts.append(_layer(library, symbol, texts, sizes.label))
    return "".join(parts)


def title_symbol(frame: SheetFrame, *, notice: bool) -> TitleBlock:
    """The title block's layers in a frame's band, with the notice's columns or without."""
    corner = (frame.border[0], frame.band_top)
    return title_block(corner, frame.title_width, frame.band, notice=notice)


def logo_symbol(frame: SheetFrame) -> Symbol:
    """The square logo cell at the end of a frame's band."""
    return title_logo((frame.logo_x, frame.band_top), frame.band)


def title_rooms(block: TitleBlock) -> dict[str, float]:
    """The width in mm of every value slot, by slot id."""
    return slot_widths(block.lines) | slot_widths(block.bold)


def notice_room(block: TitleBlock, sizes: Sizes) -> tuple[float, int]:
    """The notice cell's width in mm and how many lines of the label size it holds."""
    width, height = slot_room(block.lines, "notice")
    return width, notice_line_count(height, font_mm=sizes.label)


def title_fragment(
    library: Library,
    block: TitleBlock,
    logo: Symbol,
    strings: TitleBlockStrings,
    listing: DocumentSheets,
) -> str:
    """The title block of one page: lines and values, logo cell, bold title, labels and notice.

    `listing` gives the sizes and the cell labels.
    """
    sizes = listing.sizes
    body = {slot: text for slot, text in strings.printed.items() if slot != "title"}
    bold = _layer(library, block.bold, {"title": strings.printed["title"]}, sizes.body)
    labels = {f"label.{slot}": word for slot, word in listing.title_text.labels.items()}
    parts = [
        _layer(library, block.lines, body, sizes.body),
        _layer(library, logo, {}, sizes.body),
        bold_layer(bold),
        _layer(library, block.labels, labels, sizes.label),
    ]
    if strings.notice:
        lines = notice_table(block, notice_pitch_mm(sizes.label), len(strings.notice))
        notice = {f"{k}.line": line for k, line in enumerate(strings.notice, 1)}
        parts.append(_layer(library, lines, notice, sizes.label))
    return "".join(parts)
