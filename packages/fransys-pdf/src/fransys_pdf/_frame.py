"""The page frame, grid and title block: the Typst page background, on every page.

`docs/archive/specs/2026-09-22-page-frame.md`, R1-R6 and R11 (the owner's second appearance pass).
`fransys_pdf` draws the frame border, the grid reference and the title block once, from
the document's `SheetFormat` alone (R2); `fransys_render` draws none of it (R1).
Appearance -- stroke widths, font sizes, the title-block cell layout -- is R5's defaults,
amended by R11's one-grid title block, 5 mm margins, logo cell, notice cell and one-line
fields; the owner's appearance pass (R10) accepted R5's weights and sizes as the chosen
design, so the byte-equality golden encodes it, not an unfinished look.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fransys_model.derive.drawing_text import row_letter

from ._typst import literal

if TYPE_CHECKING:
    from fransys_model.layout import SheetFormat

_BORDER_STROKE = "0.5mm"
_GRID_STROKE = "0.25mm"
_GRID_LABEL_PT = "8pt"
_TITLE_LABEL_PT = "8pt"
_TITLE_VALUE_PT = "10pt"
_TITLE_HEADING_PT = "12pt"
_NOTICE_PT = "6pt"
_PADDING_MM = 5  # non-drawing pages' inner padding inside the content box (R4)
_BAND_MIN_MM = 20  # a band under this gives no title block, and TITLE_BLOCK_NO_ROOM (R2, R6)
_CELL_INSET_MM = 2  # clearance (both sides) a one-line field's text is cut to fit inside (R11.7)
_NOTICE_INSET_MM = 1  # clearance (all sides) the notice cell's wrapped text is padded by (R11.4)
_NOTICE_SIZE_PT = 6.0
_LINE_HEIGHT_EM = 1.2  # a standard typographic leading, close to Typst's own default paragraph
# spacing at this size -- documented approximation, same status as `_wrap_lines`' own.

PAGE_COUNTER_LABEL = "fransys-page-counter"
"""The label on the title block's document-counter cell (P10's `n of N`), for `typst query`."""

_PAGE_COUNTER = (
    'context (str(counter(page).get().first()) + " of " + str(counter(page).final().first()))'
)

# R11.2's house column widths, c1-c7, left to right (mm, exact on the 410 mm house frame
# width once the 20 mm square logo column is set aside): the designer's defaults for the
# owner's look, "not the numbers" (R11.2). `title_columns` scales them to any other sheet.
_TITLE_COL_WEIGHTS = (60, 60, 100, 55, 35, 35, 45)

# One-line field name -> which title-block column(s) it lives in, `title_columns`' own index
# order (c1..c7); `"title"` alone spans three (colspan 3, R11.2's table). Used by both
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

# Liberation Serif's own advance widths (fraction of em, `hmtx`/`unitsPerEm`), ASCII 0x20-0x7e,
# Regular and Bold: R11.7 needs a real "does this fit" oracle, not a character-count guess (the
# owner: "we do not do quick fixes, but write it properly"), and DESIGN 4 pins this package to
# no third-party dependency, so the table is data, generated once and committed here rather
# than read from a font file at run time (root CLAUDE.md invariant 4). Regenerate with:
# `uv run --with fonttools==4.55.3 python -c "from fontTools.ttLib import TTFont; ..."` reading
# `fonts/LiberationSerif-{Regular,Bold}.ttf`'s `hmtx` table, `width / unitsPerEm`, rounded to
# 4 places -- see decision pdf-0010 for the exact script.
_REGULAR_WIDTHS_EM: dict[str, float] = {
    " ": 0.25,
    "!": 0.333,
    '"': 0.4082,
    "#": 0.5,
    "$": 0.5,
    "%": 0.833,
    "&": 0.7778,
    "'": 0.1802,
    "(": 0.333,
    ")": 0.333,
    "*": 0.5,
    "+": 0.564,
    ",": 0.25,
    "-": 0.333,
    ".": 0.25,
    "/": 0.2778,
    "0": 0.5,
    "1": 0.5,
    "2": 0.5,
    "3": 0.5,
    "4": 0.5,
    "5": 0.5,
    "6": 0.5,
    "7": 0.5,
    "8": 0.5,
    "9": 0.5,
    ":": 0.2778,
    ";": 0.2778,
    "<": 0.564,
    "=": 0.564,
    ">": 0.564,
    "?": 0.4438,
    "@": 0.9209,
    "A": 0.7222,
    "B": 0.667,
    "C": 0.667,
    "D": 0.7222,
    "E": 0.6108,
    "F": 0.5562,
    "G": 0.7222,
    "H": 0.7222,
    "I": 0.333,
    "J": 0.3892,
    "K": 0.7222,
    "L": 0.6108,
    "M": 0.8892,
    "N": 0.7222,
    "O": 0.7222,
    "P": 0.5562,
    "Q": 0.7222,
    "R": 0.667,
    "S": 0.5562,
    "T": 0.6108,
    "U": 0.7222,
    "V": 0.7222,
    "W": 0.9438,
    "X": 0.7222,
    "Y": 0.7222,
    "Z": 0.6108,
    "[": 0.333,
    "\\": 0.2778,
    "]": 0.333,
    "^": 0.4692,
    "_": 0.5,
    "`": 0.333,
    "a": 0.4438,
    "b": 0.5,
    "c": 0.4438,
    "d": 0.5,
    "e": 0.4438,
    "f": 0.333,
    "g": 0.5,
    "h": 0.5,
    "i": 0.2778,
    "j": 0.2778,
    "k": 0.5,
    "l": 0.2778,
    "m": 0.7778,
    "n": 0.5,
    "o": 0.5,
    "p": 0.5,
    "q": 0.5,
    "r": 0.333,
    "s": 0.3892,
    "t": 0.2778,
    "u": 0.5,
    "v": 0.5,
    "w": 0.7222,
    "x": 0.5,
    "y": 0.5,
    "z": 0.4438,
    "{": 0.48,
    "|": 0.2002,
    "}": 0.48,
    "~": 0.541,
    "…": 0.75,  # not in the font's ASCII range; approximated as three periods (R11.7's cut)
}
_BOLD_WIDTHS_EM: dict[str, float] = {
    " ": 0.25,
    "!": 0.333,
    '"': 0.5552,
    "#": 0.5,
    "$": 0.5,
    "%": 1.0,
    "&": 0.833,
    "'": 0.2778,
    "(": 0.333,
    ")": 0.333,
    "*": 0.5,
    "+": 0.5698,
    ",": 0.25,
    "-": 0.333,
    ".": 0.25,
    "/": 0.2778,
    "0": 0.5,
    "1": 0.5,
    "2": 0.5,
    "3": 0.5,
    "4": 0.5,
    "5": 0.5,
    "6": 0.5,
    "7": 0.5,
    "8": 0.5,
    "9": 0.5,
    ":": 0.333,
    ";": 0.333,
    "<": 0.5698,
    "=": 0.5698,
    ">": 0.5698,
    "?": 0.5,
    "@": 0.9302,
    "A": 0.7222,
    "B": 0.667,
    "C": 0.7222,
    "D": 0.7222,
    "E": 0.667,
    "F": 0.6108,
    "G": 0.7778,
    "H": 0.7778,
    "I": 0.3892,
    "J": 0.5,
    "K": 0.7778,
    "L": 0.667,
    "M": 0.9438,
    "N": 0.7222,
    "O": 0.7778,
    "P": 0.6108,
    "Q": 0.7778,
    "R": 0.7222,
    "S": 0.5562,
    "T": 0.667,
    "U": 0.7222,
    "V": 0.7222,
    "W": 1.0,
    "X": 0.7222,
    "Y": 0.7222,
    "Z": 0.667,
    "[": 0.333,
    "\\": 0.2778,
    "]": 0.333,
    "^": 0.5811,
    "_": 0.5,
    "`": 0.333,
    "a": 0.5,
    "b": 0.5562,
    "c": 0.4438,
    "d": 0.5562,
    "e": 0.4438,
    "f": 0.333,
    "g": 0.5,
    "h": 0.5562,
    "i": 0.2778,
    "j": 0.333,
    "k": 0.5562,
    "l": 0.2778,
    "m": 0.833,
    "n": 0.5562,
    "o": 0.5,
    "p": 0.5562,
    "q": 0.5562,
    "r": 0.4438,
    "s": 0.3892,
    "t": 0.333,
    "u": 0.5562,
    "v": 0.5,
    "w": 0.7222,
    "x": 0.5,
    "y": 0.5,
    "z": 0.4438,
    "{": 0.394,
    "|": 0.2202,
    "}": 0.394,
    "~": 0.52,
    "…": 0.75,
}
_FALLBACK_WIDTH_EM = 0.7  # a character outside the tables (non-Latin-1): a conservative
# upper estimate (close to "M"/"W", the tables' own widest ordinary glyphs) so a field with
# one is more likely to be cut a little early than to silently overflow its cell.
_MM_PER_PT = 25.4 / 72


@dataclass(frozen=True)
class TitleBlockFields:
    """One page's title-block content (R3, R11, pdf-0010); `sheet_counter` `""` off `SCHEMATIC`."""

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
    """The title-block band: frame border bottom minus content box bottom (R2)."""
    frame_bottom = sheet.height_mm - sheet.content_y_mm
    content_bottom = sheet.content_y_mm + sheet.content_height_mm
    return frame_bottom - content_bottom


def title_block_fits(sheet: SheetFormat) -> bool:
    """Whether the band is at least 20 mm and gets a title block (R2, R6)."""
    return band_height_mm(sheet) >= _BAND_MIN_MM


def text_margin(sheet: SheetFormat) -> str:
    """A `#set page(margin: ...)`: content box plus 5 mm padding (R4); harness too (pdf-0009)."""
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


def _grid_cell(label: str) -> str:
    return f"align(center+horizon, text(size: {_GRID_LABEL_PT}, {literal(label)}))"


def _column_strip(sheet: SheetFormat, *, y_top: int) -> str:
    """One numbered strip (top or bottom margin) (R2, R9, R11.1): `1fr` row, inner ticks only."""
    n = sheet.frame_columns
    depth = sheet.content_y_mm
    cells = [_grid_cell(str(i + 1)) for i in range(n)]
    columns = ", ".join("1fr" for _ in range(n))
    ticks = [f"grid.vline(x: {i}, stroke: {_GRID_STROKE})" for i in range(1, n)]
    children = ", ".join(ticks + cells)
    return (
        f"#place(top+left, dx: {sheet.content_x_mm}mm, dy: {y_top}mm, "
        f"block(width: {sheet.content_width_mm}mm, height: {depth}mm, "
        f"grid(columns: ({columns}), rows: (1fr,), stroke: none, {children})))"
    )


def _row_strip(sheet: SheetFormat, *, x_left: int) -> str:
    """One lettered strip (left or right margin), `_column_strip`'s twin (R2, R9, R11.1)."""
    n = sheet.frame_rows
    depth = sheet.content_x_mm
    cells = [_grid_cell(row_letter(i)) for i in range(n)]
    rows = ", ".join("1fr" for _ in range(n))
    ticks = [f"grid.hline(y: {i}, stroke: {_GRID_STROKE})" for i in range(1, n)]
    children = ", ".join(ticks + cells)
    return (
        f"#place(top+left, dx: {x_left}mm, dy: {sheet.content_y_mm}mm, "
        f"block(width: {depth}mm, height: {sheet.content_height_mm}mm, "
        f"grid(columns: (1fr,), rows: ({rows}), stroke: none, {children})))"
    )


def _grid(sheet: SheetFormat) -> str:
    """The reference grid on every margin (R2), counted as `derive.drawing_text.frame_column`."""
    right_x = sheet.width_mm - sheet.content_x_mm  # the frame border's right edge
    bottom_y = sheet.height_mm - sheet.content_y_mm
    return "\n".join(
        [
            _column_strip(sheet, y_top=0),
            _column_strip(sheet, y_top=bottom_y),
            _row_strip(sheet, x_left=0),
            _row_strip(sheet, x_left=right_x),
        ]
    )


def _char_width_em(ch: str, *, bold: bool) -> float:
    table = _BOLD_WIDTHS_EM if bold else _REGULAR_WIDTHS_EM
    return table.get(ch, _FALLBACK_WIDTH_EM)


def text_width_mm(text: str, *, size_pt: float, bold: bool = False) -> float:
    """Summed per-glyph advance width of `text` in Liberation Serif at `size_pt` (R11.7)."""
    em = sum(_char_width_em(ch, bold=bold) for ch in text)
    return em * size_pt * _MM_PER_PT


def fits(text: str, *, size_pt: float, bold: bool = False, width_mm: float) -> bool:
    """Whether `text` set at `size_pt` (bold or not) is no wider than `width_mm` (R11.7)."""
    return text_width_mm(text, size_pt=size_pt, bold=bold) <= width_mm


def cut_to_width(
    text: str, *, size_pt: float, bold: bool = False, width_mm: float
) -> tuple[str, bool]:
    """`(shown, was_cut)`: `text` if it fits, else cut by character plus `…` (R11.7)."""
    if fits(text, size_pt=size_pt, bold=bold, width_mm=width_mm):
        return text, False
    ellipsis_width = text_width_mm("…", size_pt=size_pt, bold=bold)
    budget = width_mm - ellipsis_width
    kept = ""
    for ch in text:
        candidate = kept + ch
        if text_width_mm(candidate, size_pt=size_pt, bold=bold) > budget:
            break
        kept = candidate
    return kept + "…", True


def one_line_field(
    preferred: str,
    *,
    size_pt: float,
    bold: bool = False,
    width_mm: float,
    fallback: str | None = None,
) -> str:
    """One-line cell text (R11.7): `preferred` if it fits, else `fallback` if it fits, else cut."""
    if fits(preferred, size_pt=size_pt, bold=bold, width_mm=width_mm):
        return preferred
    if fallback is not None and fits(fallback, size_pt=size_pt, bold=bold, width_mm=width_mm):
        return fallback
    base = fallback if fallback is not None else preferred
    cut, _was_cut = cut_to_width(base, size_pt=size_pt, bold=bold, width_mm=width_mm)
    return cut


def title_columns(
    sheet: SheetFormat,
) -> tuple[float, float, float, float, float, float, float, float]:
    """The 8 column widths (mm): c1..c7 by `_TITLE_COL_WEIGHTS`, then a square logo (R11.2)."""
    frame_width = sheet.width_mm - 2 * sheet.content_x_mm
    logo = float(band_height_mm(sheet))
    remaining = frame_width - logo
    total_weight = sum(_TITLE_COL_WEIGHTS)
    c1, c2, c3, c4, c5, c6, c7 = (remaining * w / total_weight for w in _TITLE_COL_WEIGHTS)  # ty: ignore[division-by-zero] weights sum to 390; ty types a tuple sum as int | 0
    return (c1, c2, c3, c4, c5, c6, c7, logo)


def title_block_field_width_mm(sheet: SheetFormat, field: str) -> float:
    """A one-line field's cell width (mm), shared with `TITLE_BLOCK_TEXT_OVERFLOW` (R11.7)."""
    cols = title_columns(sheet)
    span = sum(cols[i] for i in _FIELD_COLUMNS[field])
    return span - _CELL_INSET_MM


def field_size_pt(field: str) -> float:
    """The point size a one-line field's value is set at (R5): 12 pt bold for `title`, else 10."""
    return 12.0 if field == "title" else 10.0


def _one_line(sheet: SheetFormat, field: str, text: str, *, fallback: str | None = None) -> str:
    width_mm = title_block_field_width_mm(sheet, field)
    return one_line_field(
        text,
        size_pt=field_size_pt(field),
        bold=(field == "title"),
        width_mm=width_mm,
        fallback=fallback,
    )


def notice_cell_size_mm(sheet: SheetFormat) -> tuple[float, float]:
    """The notice cell's inner (width, height) mm (R11.4), shared with `notice_fits`."""
    c7 = title_columns(sheet)[6]
    band = float(band_height_mm(sheet))
    return (c7 - 2 * _NOTICE_INSET_MM, band - 2 * _NOTICE_INSET_MM)


def _wrap_lines(text: str, *, size_pt: float, width_mm: float) -> list[str]:
    """Greedy word-wrap at `size_pt`: an approximation of Typst's wrap, enough for `notice_fits`."""
    words = text.split()
    if not words:
        return [""]
    lines = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if text_width_mm(candidate, size_pt=size_pt) <= width_mm:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def notice_fits(text: str, *, width_mm: float, height_mm: float) -> bool:
    """Whether `text` wrapped at `_NOTICE_SIZE_PT` fits `height_mm` (R11.4 overflow check)."""
    if not text:
        return True
    lines = _wrap_lines(text, size_pt=_NOTICE_SIZE_PT, width_mm=width_mm)
    line_height_mm = _NOTICE_SIZE_PT * _LINE_HEIGHT_EM * _MM_PER_PT
    if line_height_mm <= 0:
        return False
    max_lines = int(height_mm // line_height_mm)
    return len(lines) <= max_lines


def _cell(
    label: str,
    value: str,
    *,
    size: str = _TITLE_VALUE_PT,
    bold: bool = False,
    mark: str | None = None,
) -> str:
    """One title-block cell: 8 pt label over a Typst value (R5); `mark` is a `typst query` label."""
    rendered = f"strong({value})" if bold else value
    value_text = f"text(size: {size}, {rendered})"
    if mark is not None:
        # A label attaches to markup content, not a bare code-mode call: `[...]` wraps it
        # into a content block first, the same trick `_frame.background`'s own docstring
        # example (and every `#place([...])` block in this module) already relies on.
        value_text = f"[#{value_text}<{mark}>]"
    return (
        f"align(center+horizon, stack(dir: ttb, spacing: 1mm, "
        f"text(size: {_TITLE_LABEL_PT}, {literal(label)}), {value_text}))"
    )


def _value(text: str) -> str:
    return f"text({literal(text)})"


def _notice_cell(notice: str, *, width_mm: float, height_mm: float) -> str:
    """The IP-notice cell (R11.4): 6 pt, wrapped, clipped (not ellipsised) to its inner box."""
    body = f"text(size: {_NOTICE_PT}, {literal(notice)})"
    return (
        f"pad(x: {_NOTICE_INSET_MM}mm, y: {_NOTICE_INSET_MM}mm, "
        f"block(width: {_mm(width_mm)}mm, height: {_mm(height_mm)}mm, clip: true, {body}))"
    )


def _logo_cell(logo: str | None, *, size_mm: float) -> str:
    """The square logo cell (R11.3): the SVG fitted inside, aspect kept; empty with no logo."""
    if logo is None:
        content = "[]"
    else:
        content = (
            f"box(width: {_mm(size_mm)}mm, height: {_mm(size_mm)}mm, "
            f'image(bytes({literal(logo)}), format: "svg", '
            f'width: 100%, height: 100%, fit: "contain"))'
        )
    return f"align(center+horizon, {content})"


def _title_block(sheet: SheetFormat, fields: TitleBlockFields) -> str:
    """The title block (R3, R5, R11.2): one `grid()`, one-line fields cut with `…` (R11.7)."""
    x0 = sheet.content_x_mm
    width = sheet.width_mm - 2 * x0
    band_top = sheet.content_y_mm + sheet.content_height_mm
    row_height = band_height_mm(sheet) / 2
    c1, c2, c3, c4, c5, c6, c7, logo = title_columns(sheet)

    notice_w, notice_h = notice_cell_size_mm(sheet)
    title_cell = _cell(
        "Title",
        _value(_one_line(sheet, "title", fields.title)),
        size=_TITLE_HEADING_PT,
        bold=True,
    )
    notice_cell = _notice_cell(fields.notice, width_mm=notice_w, height_mm=notice_h)
    logo_cell = _logo_cell(fields.logo, size_mm=logo)
    row1 = [
        f"grid.cell(colspan: 3, {title_cell})",
        _cell("Number", _value(_one_line(sheet, "number", fields.number))),
        _cell("Revision", _value(_one_line(sheet, "revision", fields.revision))),
        _cell("Revision date", _value(_one_line(sheet, "revision_date", fields.revision_date))),
        f"grid.cell(rowspan: 2, {notice_cell})",
        f"grid.cell(rowspan: 2, {logo_cell})",
    ]
    row2 = [
        _cell("Customer", _value(_one_line(sheet, "customer", fields.customer))),
        _cell("Author", _value(_one_line(sheet, "author", fields.author))),
        _cell(
            "Page title",
            _value(
                _one_line(
                    sheet,
                    "page_title",
                    fields.page_title,
                    fallback=fields.page_title_fallback or None,
                )
            ),
        ),
        _cell("Scope", _value(_one_line(sheet, "scope", fields.scope))),
        _cell("Sheet", _value(_one_line(sheet, "sheet_counter", fields.sheet_counter))),
        _cell("Page", _PAGE_COUNTER, mark=PAGE_COUNTER_LABEL),
    ]
    children = ", ".join(row1 + row2)
    columns = ", ".join(f"{_mm(w)}mm" for w in (c1, c2, c3, c4, c5, c6, c7, logo))
    rows = f"{_mm(row_height)}mm, {_mm(row_height)}mm"
    return (
        f"#place(top+left, dx: {x0}mm, dy: {_mm(band_top)}mm, "
        f"block(width: {width}mm, height: {_mm(2 * row_height)}mm, "
        f"grid(columns: ({columns}), rows: ({rows}), stroke: {_BORDER_STROKE}, {children})))"
    )


def background(sheet: SheetFormat, fields: TitleBlockFields) -> str:
    """The `#page` background (R1): border, grid, and the title block if `title_block_fits` (R6)."""
    parts = [_frame_border(sheet), _grid(sheet)]
    if title_block_fits(sheet):
        parts.append(_title_block(sheet, fields))
    return "[" + "\n".join(parts) + "]"
