"""Every size, gap and pitch of the diagram engine, in G, each a named constant.

All are multiples of `WIRING_GRID` so boxes, tabs and tracks sit on the grid `grid_path` steps on.
"""

lazy from collections.abc import Iterable

from fransys_layout.core import grid_up
from fransys_layout.engines.overview.sheet_values import BoxFacts, Ident, LineFacts
from fransys_layout.geometry import WIRING_GRID, text_width_g

G = WIRING_GRID

TEXT_PAD = G  # inside a box, left and right of its texts
TEXT_LEAD = G // 2  # the lead beside a text line: one clearance value for text
TAB_PAD = G // 2  # around a tab's text: its width is the text and twice this
LABEL_PAD = G  # either side of a line label, in its label room
ROW_GAP = 3 * G  # between two boxes of a column
TRACK_PITCH = 2 * G  # between two tracks of a channel
MARKER_W = 3 * G  # the room a cut line's marker takes past its stub end


def attach_pitch(text_height: int) -> int:
    """The distance between two line ends on a box edge: a tab, a label and room, on the grid."""
    return grid_up(2 * text_height + G, WIRING_GRID)


def tab_height(text_height: int) -> int:
    """A tab's height: its text and its padding twice."""
    return text_height + 2 * TAB_PAD


def tab_reach(text_width: int) -> int:
    """How far a tab sticks out of its box edge, on the grid: where its line touches (its text and its padding twice)."""
    return grid_up(text_width + 2 * TAB_PAD, WIRING_GRID)


def stub_reach(label_width: int) -> int:
    """The length of a jump stub: a marker's width, or its label's width and a lead either side."""
    return max(MARKER_W, grid_up(label_width + 2 * TEXT_LEAD, WIRING_GRID))


def label_room(label_width: int) -> int:
    """The room a line label takes in a channel, on the grid: its text and the padding twice."""
    return grid_up(label_width + 2 * LABEL_PAD, WIRING_GRID)


def measured_box(box: Ident, texts: Iterable[str], height: int, *, dashed: bool) -> BoxFacts:
    """A box's facts: the width of each text line at `height`."""
    return BoxFacts(box=box, text_widths=tuple(text_width_g(t, height=height) for t in texts), dashed=dashed)


def measured_line(ends: tuple[Ident, Ident, Ident], label: str, tabs: tuple[str | None, str | None], height: int) -> LineFacts:
    """A line `(cable, a, b)`'s facts: its label's width and the width of each tab it has (None for no tab)."""
    tab_a, tab_b = (None if t is None else text_width_g(t, height=height) for t in tabs)
    return LineFacts(cable=ends[0], a=ends[1], b=ends[2], label_width=text_width_g(label, height=height), tab_a=tab_a, tab_b=tab_b)
