"""The title block from data: `symbols/title-block*.toml`, stretched by symdef to a sheet's band.

`symdef` draws one font size per fragment, so the stretched block is split into layers that
share its grid: the lines with the body-size values, the bold title and the field labels. The
notice is a table of `title-block-notice-line` at the block's `notice` anchor; the logo cell is
`title-block-logo`. These functions only pass the caller's values to symdef and pick slots.
"""

from dataclasses import dataclass, replace

from symdef import Symbol, body_box, stretch, table, translate

from electrical_symbols._library import LIBRARY
from electrical_symbols.sheet import Corner, sized

# The authored size: a band or a title width under it gives no title block (a stretch never
# shrinks). Both variants are authored at the same size.
TITLE_BLOCK_MIN_BAND_MM = body_box(LIBRARY.get("title-block")).height
TITLE_BLOCK_MIN_WIDTH_MM = body_box(LIBRARY.get("title-block")).width
_LABEL = "label."
_BOLD = "title"


@dataclass(frozen=True)
class TitleBlock:
    """The title block's layers, one font each: `lines` (body), `bold` (body, bold), `labels`.

    `lines` holds the cell lines, every value slot but `title`, the `notice` box and its anchor;
    `bold` the `title` slot; `labels` a `label.<field>` slot per cell.
    """

    lines: Symbol
    bold: Symbol
    labels: Symbol


def title_block(corner: Corner, width: float, band: float, *, notice: bool) -> TitleBlock:
    """The title block `width` by `band` mm at `corner`; `notice` takes the notice's columns."""
    key = "title-block-notice" if notice else "title-block"
    whole = translate(sized(key, width, band), *corner)
    slots = whole.slots
    return TitleBlock(
        lines=replace(
            whole, slots=tuple(s for s in slots if s.id != _BOLD and not s.id.startswith(_LABEL))
        ),
        bold=replace(
            whole, elements=(), anchors=(), slots=tuple(s for s in slots if s.id == _BOLD)
        ),
        labels=replace(
            whole, elements=(), anchors=(), slots=tuple(s for s in slots if s.id.startswith(_LABEL))
        ),
    )


def title_logo(corner: Corner, band: float) -> Symbol:
    """The square logo cell, `band` mm a side, at `corner`; pdf fills its `logo` slot."""
    return translate(sized("title-block-logo", band, band), *corner)


def notice_table(block: TitleBlock, pitch: float, count: int) -> Symbol:
    """`count` notice lines `pitch` mm apart from the block's `notice` anchor; slots `<k>.line`."""
    anchor = next(a.position for a in block.lines.anchors if a.id == "notice")
    row = stretch(LIBRARY.get("title-block-notice-line"), "y", pitch)
    return translate(table(row, count, "y"), anchor.x, anchor.y)
