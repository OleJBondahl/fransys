"""The row shapes of the sheet's text: font sizes, title-block fields and their printed strings."""

from dataclasses import dataclass

from fransys_model.kernel import value

__all__ = ["FieldOverflow", "FrameLabels", "Sizes", "TitleBlockFields", "TitleBlockStrings"]


@dataclass(frozen=True)  # plain: the closed value set bans float
class Sizes:
    """The four roles' font sizes in mm, for one document's profile `text_height_mm`.

    `title_band_mm` is the title-block band at which a label and its value clear each other.
    """

    label: float
    body: float
    heading_2: float
    heading_1: float
    title_band_mm: float


@dataclass(frozen=True)  # plain: positional callers, as before the move
class TitleBlockFields:
    """One page's title-block content; `sheet_counter` `""` off `SCHEMATIC`."""

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
    page_title_shorter: tuple[str, ...] = ()


@value
class FieldOverflow:
    """One field whose text missed its cell: the field name and the base text that did not fit."""

    field: str
    shown: str


@value
class TitleBlockStrings:
    """What a title block prints, after the cut.

    - `printed`: slot id (`title`, `number`, `revision`, `revision_date`, `customer`, `author`,
      `page_title`, `scope`, `sheet`) to the shown text, cut with `…` when it missed.
    - `notice`: the notice's wrapped lines, no more than the cell holds.
    - `unfit`: each field that missed its cell; `notice_unfit`: the notice needs more lines.
    """

    printed: frozendict[str, str]
    notice: tuple[str, ...]
    unfit: tuple[FieldOverflow, ...]
    notice_unfit: bool


@value
class FrameLabels:
    """The reference labels of a frame: column numbers left to right, row letters top down."""

    columns: tuple[str, ...]
    rows: tuple[str, ...]
