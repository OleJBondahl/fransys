"""A page's background: render's sheet SVG, with the page counter and the logo set in their cells.

The frame, the grid and the title block are drawn by render (render-0019). Two cells hold what
only Typst or the consumer knows: the page number, known after the flow, and the logo image.
The boxes they sit in are the symbol's, handed over as values; pdf draws no line and no cell.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import sheet_key_text

from ._labels import LAST_PAGE
from ._sizes import font_mm, sizes_of
from ._typst import literal

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import DocumentRow, SheetBackground, SheetKey
    from fransys_model.kernel import Model

PAGE_COUNTER_LABEL = "fransys-page-counter"
"""The label on the title block's document-counter value, for `typst query`."""


def physical_page(position: str = "here()") -> str:
    """Typst for the physical PDF page at `position`: the one source of "Page m" and the index."""
    return f"{position}.page()"


_LAST = physical_page(f"locate(<{LAST_PAGE}>)")
_PAGE_COUNTER = f'context (str({physical_page()}) + " of " + str({_LAST}))'
_Box = tuple[float, float, float, float]


def _place(box: _Box, content: str) -> str:
    x, y, width, height = box
    return (
        f"#place(top+left, dx: {x:g}mm, dy: {y:g}mm, "
        f"box(width: {width:g}mm, height: {height:g}mm, align(center+horizon, {content})))"
    )


def sheet_of(sheets: Mapping[SheetKey, SheetBackground], key: SheetKey) -> SheetBackground:
    """The background render drew for page `key`; a missing key is a caller error, never a blank."""
    if key not in sheets:
        msg = (
            f"no sheet background for {sheet_key_text(key)!r}: pass `fransys_render.sheets` of "
            "the same model's `derive.document_sheets_of` to `fransys_pdf.source`"
        )
        raise KeyError(msg)
    return sheets[key]


def page_background(
    model: Model, record: DocumentRow, sheets: Mapping[SheetKey, SheetBackground], key: SheetKey
) -> str:
    """The `#page` background of page `key`: the sheet SVG, the page counter and the logo."""
    sheet = sheet_of(sheets, key)
    parts = [f'#place(top+left, image(bytes({literal(sheet.svg)}), format: "svg"))']
    if sheet.counter_box is not None:
        size = font_mm(sizes_of(model, record.id).body)
        value = f"text(size: {size}, {_PAGE_COUNTER})"
        parts.append(_place(sheet.counter_box, f"[#{value}<{PAGE_COUNTER_LABEL}>]"))
    if sheet.logo_box is not None and record.logo is not None:
        image = (
            f'image(bytes({literal(record.logo)}), format: "svg", '
            'width: 100%, height: 100%, fit: "contain")'
        )
        parts.append(_place(sheet.logo_box, image))
    return "[" + "\n".join(parts) + "]"
