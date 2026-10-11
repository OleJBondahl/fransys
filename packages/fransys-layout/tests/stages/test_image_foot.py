"""layout-0171: a contact table's push below the power symbol under its coil, hand-made values."""

from dataclasses import replace

from samples import PROFILE, column, drawn, hid

from fransys_layout.stages import PowerEnd
from fransys_layout.stages._image_foot import marker_feet, table_push, with_marker_push
from fransys_layout.stages.images import _Reserve, table_height


def _ground(number: int, port: int) -> PowerEnd:
    """A ground end on port `port` of function `number`."""
    return PowerEnd(port=hid("port", number * 10 + port), kind="ground", symbol="ground", text=None)


def test_a_ground_symbol_under_the_coil_pushes_the_table_below_its_lead_and_body() -> None:
    """The through symbol's S port is at y 16; the ground stands y 24 to 52."""
    # UNDO: stages/_image_foot.py:table_push, return 0 for every foot
    feet = marker_feet([drawn(1)], [_ground(1, 2)], PROFILE)
    foot = feet[hid("function", 1)]
    assert (foot.x, foot.top) == (4, 16 + PROFILE.marker_padding)
    assert table_push(foot, table_height(1, PROFILE), PROFILE) == 36  # 52 + gap 2 - top 18 = 36


def test_a_symbol_on_the_top_port_or_none_at_all_pushes_nothing() -> None:
    """Only a bottom port's symbol hangs under the table; no foot, no push."""
    # UNDO: stages/_image_foot.py:marker_feet, `p.facing is Facing.S` -> `True`
    assert marker_feet([drawn(1)], [_ground(1, 1)], PROFILE) == {}
    assert marker_feet([drawn(1)], [], PROFILE) == {}
    assert table_push(None, table_height(1, PROFILE), PROFILE) == 0


def test_the_reserve_of_a_table_grows_by_its_push_and_one_without_a_table_does_not() -> None:
    """`with_marker_push`: down 40 becomes 76 under a foot with a ground symbol."""
    # UNDO: stages/_image_foot.py:with_marker_push, `reserve.tables` -> `False`
    feet = marker_feet([drawn(1), drawn(2)], [_ground(1, 2)], PROFILE)
    key = column("a", (1,)).key
    holds = _Reserve(down=40, tables=(30,))
    reserves = {
        (key, hid("function", 1)): holds,
        (key, hid("function", 2)): replace(holds, tables=()),
    }
    grown = with_marker_push(reserves, feet, PROFILE)
    assert grown[key, hid("function", 1)].down == 40 + 36
    assert grown[key, hid("function", 2)].down == 40
