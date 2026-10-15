"""Printed positions: the frame grid, a location path and a partner's place (model-0032)."""

lazy from decimal import Decimal

from fransys_model.derive.sheet_forms import set_page_text
from fransys_model.derive.text_width import G_PER_MODULE
from fransys_model.derive.unit_nodes import chain_up
from fransys_model.kernel import Id, Model
from fransys_model.layout import (
    DrawingSet,
    Page,
    layout_of,
    sheet_format_of,
)
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.tables import aspect_nodes

# A location's root-to-leaf path: each node's identity paired with its own label, root first
# (the units rule). The identity half is what a nearest-common-ancestor walk compares -- never
# the label, so two nodes that happen to share label text at different tree positions are
# never mistaken for one.
type LocationPath = tuple[tuple[Id[AspectNode], str], ...]
type Seat = tuple[int, int, LocationPath]


def frame_column(content_width: int, frame_columns: int, x: int) -> int:
    """The frame-grid column `x` falls in: the content box divided evenly, clamped to the sheet.

    `content_width` and `frame_columns` are grid units and the column count of a page's
    sheet (decision model-0032). It takes the two plain grid-unit values, not a `SheetFormat`
    object: `fransys_model.layout.SheetFormat` is millimetre-based.
    """
    return min(max(x * frame_columns // content_width + 1, 1), frame_columns)


def row_letter(index: int) -> str:
    """The letter for a 0-based frame-grid row index, A first.

    `fransys_pdf`'s own printed reference grid (`_frame.py::_row_strip`) calls this too, so
    the grid and a position text can never disagree on what a row is called (DESIGN 4, root
    CLAUDE.md's "one rule computed in two places").
    """
    return chr(ord("A") + index)


def frame_row(content_height: int, frame_rows: int, y: int) -> str:
    """The frame-grid row `y` falls in, as a letter: the content box divided evenly, clamped.

    `content_height` and `frame_rows` are grid units and the row count of a page's sheet.
    It is the row twin of `frame_column`. Row A is at the top (the smallest `y`), matching the
    printed grid's own top-to-bottom order.
    """
    return row_letter(min(max(y * frame_rows // content_height + 1, 1), frame_rows) - 1)


def position_text(  # noqa: PLR0913 -- one form for every position; own_page is the keyword (model-0136)
    page_number: int,
    column: int | None,
    row: str | None,
    location_labels: tuple[str, ...],
    set_number: int | None = None,
    *,
    own_page: int | None = None,
) -> str:
    """`p<page_number>:<column><row>`, prefixed by `+<label>` for each of `location_labels`.

    The one form for every printed position; `row` is `frame_row`'s letter. A caller passes `()`
    for `location_labels` in the same set. `own_page` equal to `page_number` prints the cell.
    With no `column` and `row` it names the page alone, `p3`: a finding about a whole page.
    """
    cell = "" if column is None else f":{column}{row}"
    if own_page == page_number and cell and not location_labels and set_number is None:
        return cell[1:]
    if not location_labels and set_number is not None:
        # A place in another drawing set with no location
        # prefix still names its set, "p3.2:1A" (set.page, then cell), so it is never ambiguous
        return f"p{set_page_text(set_number, page_number)}{cell}"
    prefix = "".join(f"+{label}" for label in location_labels)
    return f"{prefix}p{page_number}{cell}"


def location_prefix(own_path: LocationPath, partner_path: LocationPath) -> tuple[str, ...]:
    """The partner's location labels below the nearest common ancestor, root first.

    Empty when nothing is left below it -- the two ends share their whole path, or the
    partner has none at all. The common-ancestor walk compares each path entry's identity
    half, never its label, so two nodes that happen to share label text at different tree
    positions are never mistaken for one. Feed the result straight to `position_text`.
    """
    common = 0
    for own_node, partner_node in zip(own_path, partner_path, strict=False):
        if own_node[0] != partner_node[0]:
            break
        common += 1
    return tuple(label for _, label in partner_path[common:])


def content_extent(millimetres: int, module_mm: Decimal) -> int:
    """Whole grid units that fit in `millimetres`: `floor(mm / (module_mm / 8))`.

    Sheet sizes are not multiples of G (297 mm is 950.4 G), so a sheet format stores integer
    millimetres and this is the one place they become grid units. Decimal `//` truncates toward
    zero, which is the floor for the positive size of a sheet.
    """
    return int(millimetres * G_PER_MODULE // module_mm)


def cell(model: Model, page: Page, x: int, y: int) -> tuple[int, str]:
    """The frame-grid `(column, row letter)` the point `x`, `y` falls in on `page`'s sheet."""
    sheet = sheet_format_of(model, page.sheet_format)
    wide = content_extent(sheet.content_width_mm, sheet.module_mm)
    high = content_extent(sheet.content_height_mm, sheet.module_mm)
    return frame_column(wide, sheet.frame_columns, x), frame_row(high, sheet.frame_rows, y)


def location_path(model: Model, node: Id[AspectNode] | None) -> LocationPath:
    """`node`'s root-to-leaf path, empty for `None` (no location).

    The one walk is `kernel.parent_chain` (via `chain_up`), reversed to root first, with each
    node's label kept alongside its id. Every location text is built from it.
    """
    nodes = aspect_nodes(model)
    return tuple((found, nodes[found].label) for found in reversed(list(chain_up(nodes, node))))


def partner_position_text(own: Seat, partner: Seat, column: int, row: str) -> str:
    """A partner's position as `own` reads it, on plain values.

    A seat is (set number, page, location path). The same set prints the cell, `own`'s page
    kept (model-0136); another adds the prefix below the common ancestor, else its set
    number. The one place that text is built.
    """
    (own_set, own_page, own_path), (set_number, page, path) = own, partner
    if own_set == set_number:
        return position_text(page, column, row, (), own_page=own_page)
    return position_text(page, column, row, location_prefix(own_path, path), set_number)


def _seat(model: Model, page: Page) -> Seat:
    """`page` as a `Seat`: its drawing set's number, its number and its location path."""
    drawing_set = layout_of(model, DrawingSet)[page.drawing_set]
    return drawing_set.number, page.number, location_path(model, drawing_set.location)


def position_between(model: Model, own_page: Page, partner_page: Page, x: int, row: str) -> str:
    """The position at `x`/`row` on `partner_page`, read from `own_page`: the lookups."""
    column = cell(model, partner_page, x, 0)[0]
    return partner_position_text(_seat(model, own_page), _seat(model, partner_page), column, row)


def place_text(model: Model, own_page: Page, partner_page: Page, x: int, y: int) -> str:
    """The cell at `x`, `y` on `partner_page` as `own_page` reads it: derive's one text."""
    return position_between(model, own_page, partner_page, x, cell(model, partner_page, x, y)[1])
