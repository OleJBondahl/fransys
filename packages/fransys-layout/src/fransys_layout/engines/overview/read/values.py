"""The overview engine's values: one view's boxes and lines as the reader reads them."""

from typing import Any

from fransys_layout.engines.diagram.values import DiagramFacts
from fransys_model.kernel import Id, value
from fransys_model.layout import BoxKey, OverviewMode, OverviewRef
from fransys_model.vocab.core import Unit

Ident = Id[Any]  # a placer box ident made by `box_ident`, or a line carrier


def box_ident(key: BoxKey) -> Ident:
    """The placer ident of a box: its key's token, the one the box record's key holds."""
    return Id(kind="ovbox", value=key.token)


@value
class BoxSpec:
    """One box: its placer ident and key, text lines and dash."""

    box: Ident
    key: BoxKey
    lines: tuple[str, ...]
    dashed: bool


@value
class LineSpec:
    """One line between two boxes: carrier ident, ends, link kind, cable, strip, text and tabs.

    `tab_a` and `tab_b` are the texts of the tabs it ends on at its `a` and `b` box, or `None`.
    """

    carrier: Ident
    a: Ident
    b: Ident
    kind: str
    via: Id[Any] | None
    strip: Id[Any] | None
    text: str
    tab_a: str | None = None
    tab_b: str | None = None


@value
class LaneHead:
    """The text a lane prints, by its group's node: the line and its measured width."""

    owner: Ident
    text: str
    width: int


@value
class ViewFacts:
    """One view to place: its level (`unit`, `level`), `mode` and the one `open` thing.

    `diagram` holds the measured rows; `boxes` and `lines` add what the records need. The lanes
    fields: `lanes`, `heads`, `west` stubs, `power` lines, `join` terminal place (-1: none), `rank`.
    """

    unit: Id[Unit] | None
    level: OverviewRef | None
    mode: OverviewMode
    open: OverviewRef | None
    boxes: tuple[BoxSpec, ...]
    lines: tuple[LineSpec, ...]
    diagram: DiagramFacts
    lanes: tuple[int, ...] = ()
    heads: tuple[LaneHead, ...] = ()
    west: tuple[bool, ...] = ()
    power: tuple[bool, ...] = ()
    join: tuple[int, ...] = ()
    rank: tuple[int, ...] = ()


@value
class LanePlan:
    """What the model gives a lanes view.

    Per box its lane and whether it is a west stub, per line whether it is a power line, and the
    owner and text of each grouped lane.
    """

    lanes: tuple[int, ...] = ()
    head_owners: tuple[Ident, ...] = ()
    head_texts: tuple[str, ...] = ()
    west: tuple[bool, ...] = ()
    power: tuple[bool, ...] = ()
    join: tuple[int, ...] = ()
    rank: tuple[int, ...] = ()
