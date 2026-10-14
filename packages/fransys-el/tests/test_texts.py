"""`fransys_el.TEXTS`: the text placement table, one row per kind (T1.1 to T1.8, layout-0090)."""

import pytest
from fransys_el import OPTIONS, TEXT_ROW_IDS, TEXTS

from fransys_layout import Facing, LayoutOptions, TextKind

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
    """T1.n: the row of one kind has its sides, steps, mirrors and priority."""
    assert TEXT_ROW_IDS[[r[0] for r in _ROWS].index(row_id)] == row_id
    row = TEXTS[kind.value]
    assert row.priority == priority
    assert [(s.facing, s.steps, s.mirror) for s in row.sides] == list(sides)


def test_the_row_ids_are_t1_1_to_t1_8_one_per_kind() -> None:
    """The ids the layout design map checks against its rule docs."""
    assert tuple(row[0] for row in _ROWS) == TEXT_ROW_IDS
    assert set(TEXTS) == {kind.value for kind in TextKind}


def test_the_options_carry_the_table() -> None:
    assert isinstance(OPTIONS, LayoutOptions)
    assert OPTIONS.texts is TEXTS
