"""Every size, gap and pitch of the diagram engine, in G, each a named constant (BD5).

All are multiples of `WIRING_GRID` so boxes, tabs and tracks sit on the grid `grid_path` steps on.
"""

from fransys_layout.geometry import WIRING_GRID, snap_up

G = WIRING_GRID

PAGE_PAD = 2 * G  # clear space between the content box and the diagram
TEXT_PAD = G  # inside a box, left and right of its texts
TEXT_LEAD = G // 2  # between two text lines of a box
TAB_PAD = G // 2  # around a tab's text: its width is the text and twice this
LABEL_PAD = G  # either side of a line label, in its label room
ROW_GAP = 3 * G  # between two boxes of a column
TRACK_PITCH = 2 * G  # between two tracks of a channel
MARKER_W = 3 * G  # the room a cut line's marker takes past its stub end


def attach_pitch(text_height: int) -> int:
    """The distance between two line ends on a box edge: a tab, a label and room, on the grid."""
    return snap_up(2 * text_height + G)


def tab_height(text_height: int) -> int:
    """A tab's height: its text and its padding twice."""
    return text_height + 2 * TAB_PAD


def tab_width(text_width: int) -> int:
    """A tab's width: its text and its padding twice."""
    return text_width + 2 * TAB_PAD


def tab_reach(text_width: int) -> int:
    """How far a tab sticks out of its box edge, on the grid: where its line touches."""
    return snap_up(tab_width(text_width))


def label_room(label_width: int) -> int:
    """The room a line label takes in a channel, on the grid: its text and the padding twice."""
    return snap_up(label_width + 2 * LABEL_PAD)
