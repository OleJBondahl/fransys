"""Where each kind of text may stand: the sides in try-order, the steps along each, the priority.

One row per `TextKind` (T1.1 to T1.8). A side is `Side(facing, steps, mirror)`: a facing is
`"n"`, `"e"`, `"s"`, `"w"` or None, the owner's own facing. A lower priority is placed first
(layout-0090).
"""

from fransys_layout import Facing, LayoutOptions, Side, TextKind, TextPlacement

# Nearest step first, down (right) before up (left); a cross-reference starts one text height
# below the tag; a tag's last resort goes on past a vertical marker box beside the port.
_ALONG = (0, 1, -1, 2, -2)
_BELOW_TAG = (1, 2, 0, 3, -1)
_PAST_BOX = (3, -3, 4, -4)

_OWN_THEN_MIRROR = (Side(facing=None, steps=_ALONG), Side(facing=None, steps=_ALONG, mirror=True))

_ROWS: tuple[tuple[str, TextKind, TextPlacement], ...] = (
    ("T1.1", TextKind.REFERENCE, TextPlacement(priority=0, sides=(Side(facing=None, steps=(0,)),))),
    ("T1.2", TextKind.STUB, TextPlacement(priority=0, sides=(Side(facing=None, steps=(0,)),))),
    (
        "T1.3",
        TextKind.TAG,
        TextPlacement(
            priority=1,
            sides=(
                *_OWN_THEN_MIRROR,
                Side(facing=None, steps=_PAST_BOX),
                Side(facing=None, steps=_PAST_BOX, mirror=True),
            ),
        ),
    ),
    ("T1.4", TextKind.MARKING, TextPlacement(priority=1, sides=_OWN_THEN_MIRROR)),
    (
        "T1.5",
        TextKind.CONTACT_IMAGE,
        TextPlacement(priority=2, sides=(Side(facing=Facing.S, steps=(0,)),)),
    ),
    (
        "T1.6",
        TextKind.CROSS_REFERENCE,
        TextPlacement(
            priority=3,
            sides=(
                Side(facing=None, steps=_BELOW_TAG),
                Side(facing=None, steps=_BELOW_TAG, mirror=True),
            ),
        ),
    ),
    # layout-0114: a supply bar's text has one place, past the bar, away from its pin
    ("T1.7", TextKind.POWER, TextPlacement(priority=0, sides=(Side(facing=None, steps=(0,)),))),
    # layout-0154: a harness line's designation, beside its longest run, then across it
    ("T1.8", TextKind.HARNESS_LINE, TextPlacement(priority=1, sides=_OWN_THEN_MIRROR)),
)

TEXT_ROW_IDS = tuple(row_id for row_id, _, _ in _ROWS)
TEXTS = frozendict({kind.value: placement for _, kind, placement in _ROWS})
OPTIONS = LayoutOptions(texts=TEXTS, chain_boxes=True)
