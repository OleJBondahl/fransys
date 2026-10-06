"""Where each kind of text may stand: the sides in try-order, the steps along each, the priority.

One table, keyed lookup on the fact `text_kind` (registered in `stages.texts.candidates`): a row
is `(priority, sides)`, a side is `(facing, steps, mirror)`. A facing is `"n"`, `"e"`, `"s"`,
`"w"` or None, the owner's own facing. A lower priority is placed first (S15).
"""

from .rows import Row, Table

# Nearest step first, down (right) before up (left); a cross-reference starts one text height
# below the tag; a tag's last resort goes on past a vertical marker box beside the port (S20 F3).
_ALONG = (0, 1, -1, 2, -2)
_BELOW_TAG = (1, 2, 0, 3, -1)
_PAST_BOX = (3, -3, 4, -4)

_OWN_THEN_MIRROR = ((None, _ALONG, False), (None, _ALONG, True))


def _row(
    id_: str, kind: str, priority: int, sides: tuple[tuple[str | None, tuple[int, ...], bool], ...]
) -> Row:
    return Row(id_, ("text_kind", kind), (priority, sides))


TABLE = Table(
    "text candidates",
    "keyed lookup",
    (
        _row("T1.1", "reference", 0, ((None, (0,), False),)),
        _row("T1.2", "stub", 0, ((None, (0,), False),)),
        _row(
            "T1.3",
            "tag",
            1,
            (*_OWN_THEN_MIRROR, (None, _PAST_BOX, False), (None, _PAST_BOX, True)),
        ),
        _row("T1.4", "marking", 1, _OWN_THEN_MIRROR),
        _row("T1.5", "contact_image", 2, (("s", (0,), False),)),
        _row("T1.6", "cross_reference", 3, ((None, _BELOW_TAG, False), (None, _BELOW_TAG, True))),
        # layout-0114: a supply bar's text has one place, past the bar, away from its pin
        _row("T1.7", "power", 0, ((None, (0,), False),)),
    ),
)
