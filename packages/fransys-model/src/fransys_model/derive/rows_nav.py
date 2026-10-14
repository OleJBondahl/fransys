"""Row shapes of `derive.page_nav`: an invisible link's box and a sheet's outline entry (NV2, NV3).

They sit beside `rows.py`, which is at its ceiling (model-0199).
"""

from fransys_model.kernel import Id, value
from fransys_model.vocab.core import Port

__all__ = ["ContactRow", "OutlineSheet", "ReferenceLink", "TableGeometry"]


@value
class ReferenceLink:
    """A rectangle of a page, in grid units, that jumps to the destination label `target`."""

    x: int
    y: int
    width: int
    height: int
    target: str


@value
class OutlineSheet:
    """One sheet's outline entry: its `title` and the `entries` beneath it."""

    destination: str
    title: str
    entries: tuple[str, ...]


@value
class TableGeometry:
    """Where a contact table's lines sit, in G from the top of its box (model-0216, CR2).

    `heading`, `columns`, `titles`, `rule` and `first_row` are tops of the heading, the columns,
    the "NO"/"NC" texts, the rule under them and row 0; `height` is the whole table.
    """

    heading: int
    columns: int
    titles: int
    rule: int
    first_row: int
    height: int


@value
class ContactRow:
    """One printed row of a coil's contact table (model-0216, CR1).

    `column` is `"NO"` or `"NC"`; `text` is the printed row; `partner` is the port of the contact
    it names, `None` for a spare. `x`, `y`, `width`, `height` are its box in G, one row step high.
    """

    column: str
    text: str
    partner: Id[Port] | None
    x: int
    y: int
    width: int
    height: int
