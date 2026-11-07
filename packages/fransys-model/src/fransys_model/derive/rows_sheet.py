"""The row shapes of the sheet's text: font sizes, title-block fields and their printed strings."""

from dataclasses import dataclass

from fransys_kernel import render_id
from fransys_model.kernel import value
lazy from fransys_model.kernel import Id
lazy from fransys_model.vocab import Document, PageKind, Unit

__all__ = [
    "DiagramSheet",
    "FieldOverflow",
    "FrameLabels",
    "SheetKey",
    "Sizes",
    "TitleBlockFields",
    "TitleBlockStrings",
    "diagram_sheet_key",
    "sheet_key_text",
]


@dataclass(frozen=True)  # plain: the closed value set bans float
class Sizes:
    """The four roles' font sizes in mm, from the build's library heights.

    `title_band_mm` is the title-block band at which a label and its value clear each other.
    """

    label: float
    body: float
    heading_2: float
    heading_1: float
    title_band_mm: float


@dataclass(frozen=True)  # plain: positional callers, as before the move
class TitleBlockFields:
    """One page's title-block content."""

    title: str
    number: str
    customer: str
    revision: str
    revision_date: str
    author: str
    page_title: str
    scope: str
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
      `page_title`, `scope`) to the shown text, cut with `…` when it missed.
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


@dataclass(frozen=True, slots=True)
class SheetKey:
    """One page background's place: the document, the page kind and the page's ordinal in it.

    `ordinal` is `None` for a document's no-drawings fallback page.
    """

    document: Id[Document]
    kind: PageKind
    ordinal: int | None


def sheet_key_text(key: SheetKey) -> str:
    """The printed form of a `SheetKey`, for a message: `<document>#<KIND>#<ordinal or none>`."""
    match key:  # SheetKey is a value type; its `kind` is a PageKind, not a record kind
        case SheetKey(document, kind, ordinal):
            return f"{render_id(document)}#{kind.name}#{'none' if ordinal is None else ordinal}"


@value
class DiagramSheet:
    """One block diagram sheet: its reading (`None` is the absolute one) and its number 1..n.

    The facade builds one per sheet the diagram engine placed; `diagram_sheet_key` names it.
    """

    unit: Id[Unit] | None
    number: int


def diagram_sheet_key(sheet: DiagramSheet) -> str:
    """The key of a diagram sheet's SVG: render writes it, pdf looks it up."""
    reading = "" if sheet.unit is None else render_id(sheet.unit)
    return f"diagram:{reading}:{sheet.number}"
