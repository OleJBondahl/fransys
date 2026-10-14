"""The page frame, grid and title block: the Typst page background, on every page.

Page-frame rules, as amended by the owner's second appearance pass.
`fransys_pdf` draws the frame border, the grid reference and the title block once, from
the document's `SheetFormat` alone; `fransys_render` draws none of it.
Appearance -- stroke widths, font sizes, the title-block cell layout -- is the default set,
amended by the one-grid title block, 5 mm margins, logo cell, notice cell and one-line
fields; the owner's appearance pass accepted the weights and sizes as the chosen
design, so the byte-equality golden encodes it, not an unfinished look.
"""

from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING

from fransys_model.derive.drawing_text import row_letter
from fransys_model.derive.text_width import UNITS_PER_EM, text_units

from ._sizes import THICK_STROKE, THIN_STROKE, Sizes, font_mm
from ._typst import literal

if TYPE_CHECKING:
    from fransys_model.layout import SheetFormat

_BORDER_STROKE = THICK_STROKE
_GRID_STROKE = THIN_STROKE
_PADDING_MM = 5  # non-drawing pages' inner padding inside the content box
_BAND_MIN_MM = 20  # a band under this gives no title block, and TITLE_BLOCK_NO_ROOM
_CELL_INSET_MM = 2  # clearance (both sides) a one-line field's text is cut to fit inside
_NOTICE_INSET_MM = 1  # clearance (all sides) the notice cell's wrapped text is padded by
_LINE_HEIGHT_EM = 1.2  # a standard typographic leading, close to Typst's own default paragraph
# spacing at this size -- documented approximation, same status as `_wrap_lines`' own.

PAGE_COUNTER_LABEL = "fransys-page-counter"
"""The label on the title block's document-counter cell, for `typst query`."""

_PAGE_COUNTER = (
    'context (str(counter(page).get().first()) + " of " + str(counter(page).final().first()))'
)

# The house column widths, c1-c7, left to right (mm, exact on the 410 mm house frame
# width once the 20 mm square logo column is set aside): the defaults for the
# owner's look, "not the numbers". `title_columns` scales them to any other sheet.
_TITLE_COL_WEIGHTS = (60, 60, 100, 55, 35, 35, 45)

# One-line field name -> which title-block column(s) it lives in, `title_columns`' own index
# order (c1..c7); `"title"` alone spans three (colspan 3). Used by both
# `_title_block` (what is drawn) and `checks.py` (what `TITLE_BLOCK_TEXT_OVERFLOW` checks),
# so the two can never disagree about a field's own cell width (the same shared-predicate
# pattern `title_block_fits`/`TITLE_BLOCK_NO_ROOM` already uses).
_FIELD_COLUMNS: dict[str, tuple[int, ...]] = {
    "title": (0, 1, 2),
    "number": (3,),
    "revision": (4,),
    "revision_date": (5,),
    "customer": (0,),
    "author": (1,),
    "page_title": (2,),
    "scope": (3,),
    "sheet_counter": (4,),
}


@dataclass(frozen=True)
class TitleBlockFields:
    """One page's title-block content (pdf-0010); `sheet_counter` `""` off `SCHEMATIC`."""

    title: str
    number: str
    customer: str
    revision: str
    revision_date: str
    author: str
    page_title: str
    scope: str
    sheet_counter: str
    notice: str = ""
    logo: str | None = None
    page_title_fallback: str = ""


def band_height_mm(sheet: SheetFormat) -> int:
    """The title-block band: frame border bottom minus content box bottom."""
    frame_bottom = sheet.height_mm - sheet.content_y_mm
    content_bottom = sheet.content_y_mm + sheet.content_height_mm
    return frame_bottom - content_bottom


def title_block_fits(sheet: SheetFormat) -> bool:
    """Whether the band is at least 20 mm and gets a title block."""
    return band_height_mm(sheet) >= _BAND_MIN_MM


def text_margin(sheet: SheetFormat) -> str:
    """A `#set page(margin: ...)`: content box plus 5 mm padding; harness too (pdf-0009)."""
    return _margin(sheet, padding=_PADDING_MM)


def _mm(value: float) -> str:
    """`value` as a Typst mm length: `10` not `10.0`, `8.5` kept, deterministic (source purity)."""
    return f"{value:g}"


def _margin(sheet: SheetFormat, *, padding: int) -> str:
    left = sheet.content_x_mm + padding
    top = sheet.content_y_mm + padding
    right = (sheet.width_mm - sheet.content_x_mm - sheet.content_width_mm) + padding
    bottom = (sheet.height_mm - sheet.content_y_mm - sheet.content_height_mm) + padding
    return f"(left: {left}mm, top: {top}mm, right: {right}mm, bottom: {bottom}mm)"


def _frame_border(sheet: SheetFormat) -> str:
    """The frame border rectangle, from `(content_x, content_y)` to `(width - x, height - y)`."""
    x0, y0 = sheet.content_x_mm, sheet.content_y_mm
    width = sheet.width_mm - 2 * x0
    height = sheet.height_mm - 2 * y0
    return (
        f"#place(top+left, dx: {x0}mm, dy: {y0}mm, "
        f"rect(width: {width}mm, height: {height}mm, stroke: {_BORDER_STROKE}))"
    )


def _grid_cell(label: str, sizes: Sizes) -> str:
    return f"align(center+horizon, text(size: {font_mm(sizes.label)}, {literal(label)}))"


def _column_strip(sheet: SheetFormat, sizes: Sizes, *, y_top: int) -> str:
    """One numbered strip (top or bottom margin): `1fr` row, inner ticks only."""
    n = sheet.frame_columns
    depth = sheet.content_y_mm
    cells = [_grid_cell(str(i + 1), sizes) for i in range(n)]
    columns = ", ".join("1fr" for _ in range(n))
    ticks = [f"grid.vline(x: {i}, stroke: {_GRID_STROKE})" for i in range(1, n)]
    children = ", ".join(ticks + cells)
    return (
        f"#place(top+left, dx: {sheet.content_x_mm}mm, dy: {y_top}mm, "
        f"block(width: {sheet.content_width_mm}mm, height: {depth}mm, "
        f"grid(columns: ({columns}), rows: (1fr,), stroke: none, {children})))"
    )


def _row_strip(sheet: SheetFormat, sizes: Sizes, *, x_left: int) -> str:
    """One lettered strip (left or right margin), `_column_strip`'s twin."""
    n = sheet.frame_rows
    depth = sheet.content_x_mm
    cells = [_grid_cell(row_letter(i), sizes) for i in range(n)]
    rows = ", ".join("1fr" for _ in range(n))
    ticks = [f"grid.hline(y: {i}, stroke: {_GRID_STROKE})" for i in range(1, n)]
    children = ", ".join(ticks + cells)
    return (
        f"#place(top+left, dx: {x_left}mm, dy: {sheet.content_y_mm}mm, "
        f"block(width: {depth}mm, height: {sheet.content_height_mm}mm, "
        f"grid(columns: (1fr,), rows: ({rows}), stroke: none, {children})))"
    )


def _grid(sheet: SheetFormat, sizes: Sizes) -> str:
    """The reference grid on every margin, counted as `derive.drawing_text.frame_column`."""
    right_x = sheet.width_mm - sheet.content_x_mm  # the frame border's right edge
    bottom_y = sheet.height_mm - sheet.content_y_mm
    return "\n".join(
        [
            _column_strip(sheet, sizes, y_top=0),
            _column_strip(sheet, sizes, y_top=bottom_y),
            _row_strip(sheet, sizes, x_left=0),
            _row_strip(sheet, sizes, x_left=right_x),
        ]
    )


def text_width_mm(text: str, *, size_mm: float, bold: bool = False) -> float:
    """The width of `text` in DejaVu Sans Condensed at `size_mm`, from the one table."""
    return text_units(text, bold=bold) / UNITS_PER_EM * size_mm


def fits(text: str, *, size_mm: float, bold: bool = False, width_mm: float) -> bool:
    """Whether `text` set at `size_mm` (bold or not) is no wider than `width_mm`."""
    return text_width_mm(text, size_mm=size_mm, bold=bold) <= width_mm


def cut_to_width(
    text: str, *, size_mm: float, bold: bool = False, width_mm: float
) -> tuple[str, bool]:
    """`(shown, was_cut)`: `text` if it fits, else cut by character plus `…`."""
    if fits(text, size_mm=size_mm, bold=bold, width_mm=width_mm):
        return text, False
    ellipsis_width = text_width_mm("…", size_mm=size_mm, bold=bold)
    budget = width_mm - ellipsis_width
    kept = ""
    for ch in text:
        candidate = kept + ch
        if text_width_mm(candidate, size_mm=size_mm, bold=bold) > budget:
            break
        kept = candidate
    return kept + "…", True


def one_line_field(
    preferred: str,
    *,
    size_mm: float,
    bold: bool = False,
    width_mm: float,
    fallback: str | None = None,
) -> tuple[str, bool]:
    """`(text, fits)`: `preferred` if it fits, else `fallback` if it fits, else the base.

    The one rule for which text a one-line cell prints and whether it needs the cut; the base is
    `fallback` when given, else `preferred`.
    """
    if fits(preferred, size_mm=size_mm, bold=bold, width_mm=width_mm):
        return preferred, True
    base = preferred if fallback is None else fallback
    return base, fits(base, size_mm=size_mm, bold=bold, width_mm=width_mm)


def title_columns(
    sheet: SheetFormat,
) -> tuple[float, float, float, float, float, float, float, float]:
    """The 8 column widths (mm): c1..c7 by `_TITLE_COL_WEIGHTS`, then a square logo."""
    frame_width = sheet.width_mm - 2 * sheet.content_x_mm
    logo = float(band_height_mm(sheet))
    remaining = frame_width - logo
    total_weight = sum(_TITLE_COL_WEIGHTS)
    c1, c2, c3, c4, c5, c6, c7 = (remaining * w / total_weight for w in _TITLE_COL_WEIGHTS)  # ty: ignore[division-by-zero] weights sum to 390; ty types a tuple sum as int | 0
    return (c1, c2, c3, c4, c5, c6, c7, logo)


def title_block_field_width_mm(sheet: SheetFormat, field: str) -> float:
    """A one-line field's cell width (mm), shared with `TITLE_BLOCK_TEXT_OVERFLOW`."""
    cols = title_columns(sheet)
    span = sum(cols[i] for i in _FIELD_COLUMNS[field])
    return span - _CELL_INSET_MM


def field_cell(
    sheet: SheetFormat, sizes: Sizes, field: str, text: str, *, fallback: str | None = None
) -> tuple[str, bool, str]:
    """`(base, fits, printed)` of a title-block field's one-line cell.

    `one_line_field` at the field's own cell; `printed` is the base, cut if it misses.
    """
    metrics = {
        "size_mm": sizes.body,
        "bold": field == "title",
        "width_mm": title_block_field_width_mm(sheet, field),
    }
    base, ok = one_line_field(text, fallback=fallback, **metrics)
    return base, ok, base if ok else cut_to_width(base, **metrics)[0]


def _one_line(
    sheet: SheetFormat, sizes: Sizes, field: str, text: str, *, fallback: str | None = None
) -> str:
    return field_cell(sheet, sizes, field, text, fallback=fallback)[2]


def notice_cell_size_mm(sheet: SheetFormat) -> tuple[float, float]:
    """The notice cell's inner (width, height) mm, shared with `notice_fits`."""
    c7 = title_columns(sheet)[6]
    band = float(band_height_mm(sheet))
    return (c7 - 2 * _NOTICE_INSET_MM, band - 2 * _NOTICE_INSET_MM)


def _wrap_lines(text: str, *, size_mm: float, width_mm: float) -> list[str]:
    """Greedy word-wrap at `size_mm`: an approximation of Typst's wrap, enough for `notice_fits`."""
    words = text.split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if text_width_mm(candidate, size_mm=size_mm) <= width_mm:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def notice_fits(text: str, sizes: Sizes, *, width_mm: float, height_mm: float) -> bool:
    """Whether `text` wrapped at the label size fits `height_mm` (overflow check)."""
    if not text:
        return True
    lines = _wrap_lines(text, size_mm=sizes.label, width_mm=width_mm)
    line_height_mm = sizes.label * _LINE_HEIGHT_EM
    if line_height_mm <= 0:
        return False
    max_lines = int(height_mm // line_height_mm)
    return len(lines) <= max_lines


def _cell(
    label: str,
    value: str,
    sizes: Sizes,
    *,
    bold: bool = False,
    mark: str | None = None,
) -> str:
    """One title-block cell: 1.8 mm label over a Typst value; `mark` is a `typst query` label."""
    rendered = f"strong({value})" if bold else value
    value_text = f"text(size: {font_mm(sizes.body)}, {rendered})"
    if mark is not None:
        # A label attaches to markup content, not a bare code-mode call: `[...]` wraps it
        # into a content block first, the same trick `_frame.background`'s own docstring
        # example (and every `#place([...])` block in this module) already relies on.
        value_text = f"[#{value_text}<{mark}>]"
    return (
        f"align(center+horizon, stack(dir: ttb, spacing: 1mm, "
        f"text(size: {font_mm(sizes.label)}, {literal(label)}), {value_text}))"
    )


def _value(text: str) -> str:
    return f"text({literal(text)})"


def _notice_cell(notice: str, sizes: Sizes, *, width_mm: float, height_mm: float) -> str:
    """The IP-notice cell: label size, wrapped, clipped (not ellipsised) to its inner box."""
    body = f"text(size: {font_mm(sizes.label)}, {literal(notice)})"
    return (
        f"pad(x: {_NOTICE_INSET_MM}mm, y: {_NOTICE_INSET_MM}mm, "
        f"block(width: {_mm(width_mm)}mm, height: {_mm(height_mm)}mm, clip: true, {body}))"
    )


def _logo_cell(logo: str | None, *, size_mm: float) -> str:
    """The square logo cell: the SVG fitted inside, aspect kept; empty with no logo."""
    if logo is None:
        content = "[]"
    else:
        content = (
            f"box(width: {_mm(size_mm)}mm, height: {_mm(size_mm)}mm, "
            f'image(bytes({literal(logo)}), format: "svg", '
            f'width: 100%, height: 100%, fit: "contain"))'
        )
    return f"align(center+horizon, {content})"


_LABELS = {
    "title": "Title",
    "number": "Number",
    "revision": "Revision",
    "revision_date": "Revision date",
    "customer": "Customer",
    "author": "Author",
    "page_title": "Page title",
    "scope": "Scope",
    "sheet_counter": "Sheet",
}


def _field_cell(
    sheet: SheetFormat, sizes: Sizes, name: str, value: str, *, fallback: str | None = None
) -> str:
    shown = _value(_one_line(sheet, sizes, name, value, fallback=fallback))
    return _cell(_LABELS[name], shown, sizes, bold=name == "title")


def _title_rows(
    sheet: SheetFormat, fields: TitleBlockFields, sizes: Sizes, extra: tuple[str, str]
) -> list[str]:
    """The two grid rows' cells; `extra` is the notice and logo cells, spanning both rows."""
    text = partial(_field_cell, sheet, sizes)
    fallback = fields.page_title_fallback or None
    return [
        f"grid.cell(colspan: 3, {text('title', fields.title)})",
        text("number", fields.number),
        text("revision", fields.revision),
        text("revision_date", fields.revision_date),
        f"grid.cell(rowspan: 2, {extra[0]})",
        f"grid.cell(rowspan: 2, {extra[1]})",
        text("customer", fields.customer),
        text("author", fields.author),
        text("page_title", fields.page_title, fallback=fallback),
        text("scope", fields.scope),
        text("sheet_counter", fields.sheet_counter),
        _cell("Page", _PAGE_COUNTER, sizes, mark=PAGE_COUNTER_LABEL),
    ]


def _title_block(sheet: SheetFormat, fields: TitleBlockFields, sizes: Sizes) -> str:
    """The title block: one `grid()`, one-line fields cut with `…`."""
    x0 = sheet.content_x_mm
    width = sheet.width_mm - 2 * x0
    band_top = sheet.content_y_mm + sheet.content_height_mm
    row_height = band_height_mm(sheet) / 2
    widths = title_columns(sheet)
    notice_w, notice_h = notice_cell_size_mm(sheet)
    notice_cell = _notice_cell(fields.notice, sizes, width_mm=notice_w, height_mm=notice_h)
    logo_cell = _logo_cell(fields.logo, size_mm=widths[7])
    children = ", ".join(_title_rows(sheet, fields, sizes, (notice_cell, logo_cell)))
    columns = ", ".join(f"{_mm(w)}mm" for w in widths)
    rows = f"{_mm(row_height)}mm, {_mm(row_height)}mm"
    return (
        f"#place(top+left, dx: {x0}mm, dy: {_mm(band_top)}mm, "
        f"block(width: {width}mm, height: {_mm(2 * row_height)}mm, "
        f"grid(columns: ({columns}), rows: ({rows}), stroke: {_BORDER_STROKE}, {children})))"
    )


def background(sheet: SheetFormat, fields: TitleBlockFields, sizes: Sizes) -> str:
    """The `#page` background: border, grid, and the title block if `title_block_fits`."""
    parts = [_frame_border(sheet), _grid(sheet, sizes)]
    if title_block_fits(sheet):
        parts.append(_title_block(sheet, fields, sizes))
    return "[" + "\n".join(parts) + "]"
