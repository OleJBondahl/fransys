"""One page background of a document and the overflow of its printed fields."""

from dataclasses import dataclass
from typing import Literal

from fransys_model.kernel import value
lazy from fransys_model.kernel import Id
lazy from fransys_model.layout import SheetFormat
lazy from fransys_model.vocab import PageKind

lazy from .rows_sheet import SheetKey, Sizes, TitleBlockFields


@dataclass(frozen=True)  # plain: it holds a record, which a value may not
class SheetPage:
    """One page background: its key, paper and title-block fields (render draws it, pdf places it).

    `group` and `where` name the page in a `TITLE_BLOCK_TEXT_OVERFLOW` message; `group` is `""`
    for a page whose page-level fields are not checked (a diagram sheet, a no-drawings page).
    """

    key: SheetKey
    kind: PageKind
    sheet: SheetFormat
    fields: TitleBlockFields
    group: str
    where: str


@dataclass(frozen=True)  # plain: the closed value set bans float
class FrameStrip:
    """One reference strip of a sheet frame in mm: its corner, one cell's size and its labels.

    `side` is `top`, `bottom`, `left` or `right`; the cells run along `axis`, one per label.
    """

    side: str
    x: float
    y: float
    cell_width: float
    cell_height: float
    axis: Literal["x", "y"]
    labels: tuple[str, ...]


@dataclass(frozen=True)  # plain: the closed value set bans float
class SheetFrame:
    """A sheet's frame in mm from the page corner: border, reference strips and title-block band.

    `border` is x, y, width and height. The band is `band` high from `band_top`; the title block
    is `title_width` wide from the border's left, and the square logo cell starts at `logo_x`.
    """

    border: tuple[float, float, float, float]
    strips: tuple[FrameStrip, ...]
    band: float
    band_top: float
    title_width: float
    logo_x: float


@value
class TitleBlockText:
    """A title block's words: each printed cell's label in the record's order, and the cut mark."""

    labels: frozendict[str, str]
    ellipsis: str


@dataclass(frozen=True)  # plain: it holds a record, which a value may not
class DocumentSheets:
    """A document's paper, its sizes, its pages' title blocks in page order, each paper's frame."""

    sheet: SheetFormat
    sizes: Sizes
    pages: tuple[SheetPage, ...]
    frames: frozendict[Id[SheetFormat], SheetFrame]
    title_text: TitleBlockText


@value
class TitleBlockOverflow:
    """One one-line field whose text missed its cell: the field, where it sits and its base text."""

    field: str
    where: str
    shown: str


@dataclass(frozen=True)  # plain: the closed value set bans float
class SheetBackground:
    """One page background and the two boxes pdf fills, in mm from the page corner.

    `svg` is the frame, grid and title block; `counter_box` and `logo_box` are x, y, width and
    height of the Page cell's value and of the logo cell, `None` when the band holds no title
    block; `title_room_mm` is the width a page title is cut to, `ellipsis` the mark it is cut with.
    """

    svg: str
    counter_box: tuple[float, float, float, float] | None
    logo_box: tuple[float, float, float, float] | None
    title_room_mm: float | None
    ellipsis: str
