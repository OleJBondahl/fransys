"""The rows of every overview view: its boxes and lines with the text each prints (model-0202).

They sit beside `rows_overview.py`. A box is keyed by `BoxKey`, a line by its kind, carrier, strip
and the keys of its ends, as the `layout.overview_*` records are (`fransys_model.layout`).
"""

from fransys_model.kernel import Id, value
from fransys_model.layout import BoxKey, OverviewMode, OverviewRef
from fransys_model.vocab.core import Item, Unit


@value
class ViewMember:
    """One member of a fold: the far end, its text lines and its row text.

    It has no position. `text` is the whole row as a stub label, carrier first
    (`overview_member_text`): `-W11 → +EXT-M1:PE`.
    """

    ref: OverviewRef
    lines: tuple[str, ...]
    text: str


@value
class ViewBox:
    """One box of a view: its key, its text lines and its dash.

    `members` are a fold's member rows, which the page lists when the fold is open; empty
    for any other box.
    """

    key: BoxKey
    lines: tuple[str, ...]
    dashed: bool
    members: tuple[ViewMember, ...] = ()


@value
class ViewLine:
    """One line of a view: its ends, kind, cable, strip and text; `tab_a`, `tab_b` end tabs.

    `tab_a` and `tab_b` are the texts of the tabs the line ends on at its `a` and `b` box, else
    `None`.
    """

    a: BoxKey
    b: BoxKey
    kind: str
    via: Id[Item] | None
    strip: Id[Item] | None
    text: str
    tab_a: str | None = None
    tab_b: str | None = None


@value
class ViewRows:
    """One view: its level (`unit`, `level`), `mode`, the one open strip, boxes and lines.

    Boxes come in the level's text order, then the stub boxes; lines likewise.
    """

    unit: Id[Unit] | None
    level: OverviewRef | None
    mode: OverviewMode
    open: OverviewRef | None
    boxes: tuple[ViewBox, ...]
    lines: tuple[ViewLine, ...]


Rows = tuple[tuple[ViewBox, ...], tuple[ViewLine, ...]]
