"""The overview's folded levels: function groups as boxes, pass-through lines, folded stubs.

Row shapes of `derive.overview_fold` (model-0199, extending model-0197). They sit beside
`rows.py` and import its overview shapes; `rows.py` is at its ceiling and cannot import them back.
"""

from enum import Enum
from typing import Any

from fransys_model.kernel import Id, register_enum, value
from fransys_model.layout import OverviewRef
from fransys_model.vocab.aspects import AspectNode
from fransys_model.vocab.core import Item, Unit
from fransys_model.vocab.enums import ItemKind

from .rows import LineRef, OverviewLinkKind, OverviewStub


@value
class FoldBox:
    """One box of a folded level.

    `lines` is its text. A `GROUP` counts its `items`, nested `units` and `strips`, and
    `inner_lines`, the connections between its own boxes. `STRIPS` counts the `strips` it holds.
    `item_kind` is an item box's kind, `terminals` a strip box's or `STRIPS`' terminal count.
    """

    key: OverviewRef
    lines: tuple[str, ...]
    tabs: tuple[str, ...]
    dashed: bool
    item_kind: ItemKind | None
    terminals: int
    items: int
    units: int
    strips: int
    inner_lines: int


@value
class FoldLine:
    """One line of a folded level, per pair of boxes and kind, or per strip passed through.

    `count` is the connections it stands for, `vias` the cable items of a cable line. A line
    drawn through a strip has `strip` set, `terminals` the terminals it stands for and `label` as
    `-X3 x 3`; otherwise `label` joins the cable designations, "" for none.
    """

    a: OverviewRef
    b: OverviewRef
    kind: OverviewLinkKind
    count: int
    vias: tuple[Id[Item], ...]
    label: str
    strip: Id[Item] | None
    terminals: int


@register_enum
class StubPlace(Enum):
    """Where a stub's far end lies: a group or box of the unit, a far unit, a location, one end."""

    GROUP = "group"
    BOX = "box"
    UNIT = "unit"
    LOCATION = "location"
    FIELD = "field"
    END = "end"


@value
class FoldStub:
    """The outside end of connections at a box, folded by far end.

    `far` names the group, box, unit or location, or for `END` the far device as `stub_far_end`
    prints it; `end` is the same far end as a reference (a group, a box's own, a unit, a place or
    the far item). `kind` and `via` are the line's: a stub folds per kind, and `via` is set only
    for `END`. `count` is the connections. `members` are the single stubs it opens to:
    those of an outside fold, the stub itself for `END`, empty inside the unit.
    """

    box: OverviewRef
    place: StubPlace
    far: str
    end: OverviewRef
    kind: OverviewLinkKind
    via: Id[Item] | None
    count: int
    members: tuple[OverviewStub, ...]


@value
class StubWire:
    """A terminal's share of a stub it holds with the other terminals of the open strip.

    `stub` is the shared stub, hung on the first terminal wired to its far end; `part` is the
    connections of one terminal to it, with `box` that terminal. Both name the same far end.
    """

    stub: FoldStub
    part: FoldStub


@value
class StripNote:
    """A strip beside a level: `terminals` of it held (a box) or passed through (lines)."""

    strip: Id[Item]
    terminals: int
    held: bool


@value
class FoldLevel:
    """A unit level folded to function groups, or one group or the strips box opened.

    `opened` is the `GROUP` or `STRIPS` box opened as the level, `None` for the folded level and
    for a unit with fewer than two groups, which opens straight (`folded` false) with all its
    boxes. `strips` lists each strip the level holds or passes through, in designation order.
    `wires` is, for the strip opened in it, each terminal's share of the stubs its terminals hold
    together; empty with no strip open.
    """

    unit: Id[Unit]
    opened: OverviewRef | None
    folded: bool
    boxes: tuple[FoldBox, ...]
    lines: tuple[FoldLine, ...]
    stubs: tuple[FoldStub, ...]
    strips: tuple[StripNote, ...]
    wires: tuple[StubWire, ...] = ()


@value
class TerminalStubs:
    """The stubs of one terminal of an open strip: its connections that leave the unit."""

    terminal: Id[Item]
    stubs: tuple[OverviewStub, ...]


@value
class LineTab:
    """The tab text at each end of one cable line, on the box border; `None` for none."""

    ref: LineRef
    tab_a: str | None
    tab_b: str | None


@value
class LocationBox:
    """One top place of the location fold: its text and the system boxes in it.

    `place` is the top location node, `None` for the boxes in no place.
    """

    place: Id[AspectNode] | None
    lines: tuple[str, ...]
    boxes: tuple[Id[Any], ...]


@value
class LocationLine:
    """The cables between two places: `count` distinct cables, `a` before `b` in box order."""

    a: Id[AspectNode] | None
    b: Id[AspectNode] | None
    count: int
    cables: tuple[Id[Item], ...]


@value
class LocationFold:
    """The system level folded by top place; present only with two or more top places."""

    boxes: tuple[LocationBox, ...]
    lines: tuple[LocationLine, ...]


@value
class FieldJoin:
    """One lifted line of a field box to its unit: a kind, its cables and its count."""

    kind: OverviewLinkKind
    count: int
    cables: tuple[Id[Item], ...]


@value
class FieldFold:
    """One unit's field devices folded into a box beside it: its text, members and cables.

    `unit` is the top-level unit box all their connections land in; `cables` join them to it, and
    `joins` are the lifted lines of the fold to it, one per kind.
    """

    unit: Id[Unit]
    lines: tuple[str, ...]
    devices: tuple[Id[Item], ...]
    cables: tuple[Id[Item], ...]
    joins: tuple[FieldJoin, ...]


@value
class TreeRow:
    """One row of the parts tree: a `unit` or an `item` (the other `None`), its `label`.

    `parent` is the index of the row it hangs under, `None` for a top row. Rows come in display
    order: units first, then items, strips last.
    """

    parent: int | None
    unit: Id[Unit] | None
    item: Id[Item] | None
    label: str
