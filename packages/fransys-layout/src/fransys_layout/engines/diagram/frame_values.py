"""The diagram placer's frame (BD5): boxes, line ends, channels and cuts per sheet, all in G.

Coordinates are from a sheet's content corner (0, 0) and multiples of `WIRING_GRID`. Lines are
indexes into `DiagramFacts.lines`; columns are numbered from 0 over the whole diagram.
"""

from fransys_layout.engines.diagram.sizes import TRACK_PITCH, tab_reach
from fransys_layout.engines.diagram.values import Ident
from fransys_layout.geometry import Facing
from fransys_model.kernel import value


@value
class FrameEnd:
    """A line's end on a box edge: `y` is where the line attaches, `tab` the tab's text width."""

    line: int
    side: Facing  # E or W; both ends of a same-column line are E
    y: int
    tab: int | None  # None: no tab, the line touches the box edge


@value
class FrameBox:
    """A box and its ends: east ends top to bottom, then west ends top to bottom."""

    box: Ident
    dashed: bool
    x: int
    y: int
    width: int
    height: int
    ends: tuple[FrameEnd, ...]

    def touch_x(self, end: FrameEnd) -> int:
        """Where the line touches: the box edge, or the outer edge of the end's tab."""
        reach = 0 if end.tab is None else tab_reach(end.tab)
        return self.x + self.width + reach if end.side is Facing.E else self.x - reach


@value
class FrameColumn:
    """A column on one sheet: `index` over the diagram, left edge `x`, the uniform box `width`."""

    index: int
    x: int
    width: int
    boxes: tuple[FrameBox, ...]


@value
class FrameTrack:
    """One run in a channel: line `line` (half `part`, 0 whole, 1 upper, 2 lower) on track `track`.

    `left_y` and `right_y` are the run's ends in y; a jogged core is two runs meeting at a jog y.
    """

    line: int
    part: int
    left_y: int
    right_y: int
    track: int


@value
class FrameChannel:
    """The room right of column `left` on a sheet; `right` is the next column, None after the last.

    From `start`: `tab_l`, `label`, tracks 1..`count` at `track_x(t)`, the `same` lines on the
    tracks after them, `label`, `tab_r`. `lines` run between `left` and `right`.
    """

    left: int
    right: int | None
    start: int
    tab_l: int
    tab_r: int
    label: int
    lines: tuple[int, ...]
    same: tuple[int, ...]
    tracks: tuple[FrameTrack, ...]
    count: int
    width: int

    def track_x(self, track: int) -> int:
        """The x of track `track` (1 first), left of the right column's tabs."""
        return self.start + self.tab_l + self.label + track * TRACK_PITCH


@value
class FrameCut:
    """Where column `left` ends a sheet and column `right` starts the next; no channel is drawn.

    `lines` cross it, `same` are `left`'s same-column lines; `label` is the widest of both. The
    zone is `tab_l`, `label`, marker on `left_sheet`; marker, `label`, `tab_r` from x 0 right.
    """

    left: int
    right: int
    left_sheet: int
    lines: tuple[int, ...]
    same: tuple[int, ...]
    tab_l: int
    tab_r: int
    label: int
    left_zone: int


@value
class FrameSheet:
    """One sheet, numbered from 1 left to right: its columns and the channels between them."""

    number: int
    columns: tuple[FrameColumn, ...]
    channels: tuple[FrameChannel, ...]


@value
class Frame:
    """Everything the router and labeller need: the sheets and the cuts between them."""

    sheets: tuple[FrameSheet, ...]
    cuts: tuple[FrameCut, ...]

    def ends_of(self, line: int) -> tuple[tuple[int, FrameBox, FrameEnd], ...]:
        """Each end of line `line` as (sheet number, its box, the end), in sheet order."""
        return tuple(
            (sheet.number, box, end)
            for sheet in self.sheets
            for column in sheet.columns
            for box in column.boxes
            for end in box.ends
            if end.line == line
        )
