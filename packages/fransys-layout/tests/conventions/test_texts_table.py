"""`conventions.texts`: the text candidate table, one row per kind (T1.1 to T1.8, layout-0090)."""

import pytest

from fransys_layout.conventions.texts import TABLE
from fransys_layout.geometry import Facing
from fransys_layout.stages.texts.candidates import (
    DEFAULT_TABLE,
    PRIORITY,
    TextKind,
    ranked_candidates,
)

_ALONG = (0, 1, -1, 2, -2)
_BELOW = (1, 2, 0, 3, -1)
_PAST = (3, -3, 4, -4)
# id, kind, priority, (facing or None for the owner's, steps, mirror) per side
_ROWS = (
    ("T1.1", TextKind.REFERENCE, 0, ((None, (0,), False),)),
    ("T1.2", TextKind.STUB, 0, ((None, (0,), False),)),
    (
        "T1.3",
        TextKind.TAG,
        1,
        ((None, _ALONG, False), (None, _ALONG, True), (None, _PAST, False), (None, _PAST, True)),
    ),
    ("T1.4", TextKind.MARKING, 1, ((None, _ALONG, False), (None, _ALONG, True))),
    ("T1.5", TextKind.CONTACT_IMAGE, 2, ((Facing.S, (0,), False),)),
    ("T1.6", TextKind.CROSS_REFERENCE, 3, ((None, _BELOW, False), (None, _BELOW, True))),
    ("T1.7", TextKind.POWER, 0, ((None, (0,), False),)),
    ("T1.8", TextKind.HARNESS_LINE, 1, ((None, _ALONG, False), (None, _ALONG, True))),
)


@pytest.mark.parametrize(("row_id", "kind", "priority", "sides"), _ROWS, ids=[r[0] for r in _ROWS])
def test_each_row_gives_its_sides_in_order_and_its_priority(
    row_id: str, kind: TextKind, priority: int, sides: tuple
) -> None:
    """T1.n: the row of one kind, hit alone, has its sides, steps, mirrors and priority."""
    assert [r.id for r in TABLE.rows if r.when == ("text_kind", kind.value)] == [row_id]
    assert PRIORITY[kind] == priority
    assert [(s.facing, s.steps, s.mirror) for s in DEFAULT_TABLE[kind]] == list(sides)
    ranked = ranked_candidates(kind, Facing.E, (30, 7), DEFAULT_TABLE)
    assert len(ranked) == sum(len(steps) for _, steps, _ in sides)
