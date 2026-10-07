"""The diagram engine's values: the reader's facts of a reading and the placer's geometry (BD5)."""

from typing import Any

from fransys_layout.geometry import Facing, Point
from fransys_model.kernel import Id, value

Ident = Id[Any]  # a box subject (a unit instance or an item) or a cable item


@value
class BoxFacts:
    """One box: its subject, the width of each text line it prints, and whether it is dashed."""

    box: Ident
    text_widths: tuple[int, ...]
    dashed: bool


@value
class LineFacts:
    """One line `(cable, a, b)`: its label's width and the text width of each end's tab, if any."""

    cable: Ident
    a: Ident
    b: Ident
    label_width: int
    tab_a: int | None
    tab_b: int | None


@value
class DiagramFacts:
    """One reading's diagram to place: boxes in text order, lines in line order, the sheet in G."""

    unit: Ident | None
    boxes: tuple[BoxFacts, ...]
    lines: tuple[LineFacts, ...]
    text_height: int
    turn_penalty: int
    crossing_penalty: int
    width: int
    height: int


@value
class PlacedTab:
    """A tab outside a box edge: the line's cable, the edge, the centre `y`, its text's width."""

    cable: Ident
    side: Facing
    y: int
    text_width: int


@value
class PlacedBox:
    """A box in G from the sheet's content corner; `tabs` are in the order they were placed."""

    box: Ident
    dashed: bool
    x: int
    y: int
    width: int
    height: int
    tabs: tuple[PlacedTab, ...]


@value
class PlacedLine:
    """A line on one sheet; its identity is `(cable, a, b)`.

    `points` start at the box that lies on this sheet. A line cut between sheets is one
    `PlacedLine` per sheet, each ending at its marker. `text_x`, `text_y` is the label's centre.
    """

    cable: Ident
    a: Ident
    b: Ident
    points: tuple[Point, ...]
    text_x: int
    text_y: int


@value
class PlacedMarker:
    """The marker ending a cut line's half: the line's identity, the other sheet, its place."""

    cable: Ident
    a: Ident
    b: Ident
    at_sheet: int
    x: int
    y: int


@value
class PlacedSheet:
    """One sheet of a diagram, numbered from 1 left to right."""

    number: int
    boxes: tuple[PlacedBox, ...]
    lines: tuple[PlacedLine, ...]
    markers: tuple[PlacedMarker, ...]


@value
class PlacedDiagram:
    """The placed diagram of one reading (`unit`, `None` for the system)."""

    unit: Ident | None
    sheets: tuple[PlacedSheet, ...]
