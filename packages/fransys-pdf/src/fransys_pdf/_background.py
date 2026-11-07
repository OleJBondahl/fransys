"""A page's background: render's sheet SVG, with the page counter and the logo set in their cells.

The frame, the grid and the title block are drawn by render (render-0019). Two cells hold what
only Typst or the consumer knows: the page number of a flowing section (pdf-0054), and the logo image.
The boxes they sit in are the symbol's, handed over as values; pdf draws no line and no cell.
"""

from typing import TYPE_CHECKING

from fransys_model.derive import sheet_key_text

from ._sizes import font_mm, sizes_of
from ._typst import literal
from .errors import PdfError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from fransys_model.derive import DocumentRow, SheetBackground, SheetKey
    from fransys_model.kernel import Model

PAGE_COUNTER_LABEL = "fransys-page-counter"
"""The label on the title block's document-counter value, for `typst query`."""


LAST_PAGE = "fr-last"
"""The label of the end marker `document.source` appends: the title block's "of N" is its page."""

_PAGE_COUNTER = f'context (str(here().page()) + " of " + str(locate(<{LAST_PAGE}>).page()))'
"""The title block's page cell, `m of N`: the physical PDF page and the PDF's page count, which a flowing list only Typst can count."""
_Box = tuple[float, float, float, float]


def _place(box: _Box, content: str) -> str:
    x, y, width, height = box
    return f"#place(top+left, dx: {x:g}mm, dy: {y:g}mm, box(width: {width:g}mm, height: {height:g}mm, align(center+horizon, {content})))"


def sheet_of(sheets: Mapping[SheetKey, SheetBackground], key: SheetKey) -> SheetBackground:
    """The background render drew for page `key`; a missing key is a caller error, never a blank."""
    if key not in sheets:
        msg = (
            f"no sheet background for {sheet_key_text(key)!r}: pass `fransys_render.sheets` of "
            "the same model's `derive.document_sheets_of` to `fransys_pdf.source`"
        )
        raise PdfError(msg)
    return sheets[key]


def page_background(model: Model, record: DocumentRow, sheets: Mapping[SheetKey, SheetBackground], key: SheetKey) -> str:
    """The `#page` background of page `key`: the sheet SVG, the page counter and the logo."""
    sheet = sheet_of(sheets, key)
    parts = [f'#place(top+left, image(bytes({literal(sheet.svg)}), format: "svg"))']
    if sheet.counter_box is not None:
        size = font_mm(sizes_of(model).body)
        value = f"text(size: {size}, {_PAGE_COUNTER})"
        parts.append(_place(sheet.counter_box, f"[#{value}<{PAGE_COUNTER_LABEL}>]"))
    if sheet.logo_box is not None and record.logo is not None:
        image = f'image(bytes({literal(record.logo)}), format: "svg", width: 100%, height: 100%, fit: "contain")'
        parts.append(_place(sheet.logo_box, image))
    return "[" + "\n".join(parts) + "]"
