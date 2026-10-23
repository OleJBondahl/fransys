"""Decision model-0129: a generic box's pins stand a channel pitch apart, widened per text row."""

from itertools import pairwise

from fransys_layout.geometry import symbol_geometry
from fransys_layout.geometry.box_reach import Reach, Row, extent, spread
from fransys_layout.geometry.symbols import channel_pitch


def _reach(name: str, *rows: tuple[int, int, int, int]) -> Reach:
    return Reach(
        name=name, rows=tuple(Row(top=t, bottom=b, left=lf, right=r) for t, b, lf, r in rows)
    )


def test_the_channel_pitch_is_one_and_a_half_pole_pitches() -> None:
    three_pole = {p.name: p.at.x for p in symbol_geometry("circuit-breaker", poles=3).ports}
    assert channel_pitch() * 2 == (three_pole["2.in"] - three_pole["1.in"]) * 3


def test_pins_with_contacts_stand_a_channel_pitch_apart() -> None:
    base = {"a": ("s", 0), "b": ("s", 120), "c": ("s", 250), "d": ("n", 0)}
    placed = spread(base, tuple(_reach(n, (0, 16, 4, 20)) for n in "abc"), channel_pitch())
    assert placed == {"a": 0, "b": 48, "c": 96, "d": 0}  # a side with no contact stays as it was


def test_two_texts_at_one_height_push_the_next_pin_right() -> None:
    base = {"a": ("n", 0), "b": ("n", 48)}
    placed = spread(base, (_reach("a", (0, 16, 8, 20)), _reach("b", (8, 24, 20, 8))), 48)
    assert placed == {"a": 0, "b": 48}  # 20 + 8 + 20 = 48, exactly the pitch
    wider = spread(base, (_reach("a", (0, 16, 8, 30)), _reach("b", (8, 24, 20, 8))), 48)
    assert wider == {"a": 0, "b": 64}  # snap_up(30 + 8 + 20) = 64


def test_texts_at_different_heights_never_add_their_reaches() -> None:
    base = {"a": ("n", 0), "b": ("n", 48)}
    placed = spread(base, (_reach("a", (0, 16, 8, 100)), _reach("b", (40, 56, 100, 8))), 48)
    assert placed == {"a": 0, "b": 48}


def _side_xs(geometry) -> dict[str, list[int]]:
    xs: dict[str, list[int]] = {}
    for port in geometry.ports:
        xs.setdefault(port.facing.value, []).append(port.at.x)
    return {side: sorted(values) for side, values in xs.items()}


def _steps(geometry) -> list[int]:
    return [b - a for values in _side_xs(geometry).values() for a, b in pairwise(values)]


def _written_steps(placement) -> list[int]:
    by_side: dict[str, list[int]] = {}
    for side, x in zip(placement.sides, placement.port_offsets, strict=True):
        by_side.setdefault(side.value, []).append(x)
    return [b - a for xs in by_side.values() for a, b in pairwise(xs)]


def test_a_pin_clears_the_text_of_a_pin_two_places_before_it() -> None:
    """Pins a and c hold wide texts, b none: c stands clear of a's text, not one pitch from b."""
    # UNDO: geometry/box_reach.py:spread, `for o in names[:at]` -> `for o in names[at - 1 : at]`
    base = {"a": ("s", 0), "b": ("s", 48), "c": ("s", 96)}
    placed = spread(base, (_reach("a", (0, 16, 8, 90)), _reach("c", (0, 16, 20, 8))), 48)
    assert placed["b"] == 48
    assert placed["c"] == 120  # snap_up(90 + 8 + 20), not the 96 an adjacent-pair test settles for


def test_the_extent_covers_every_pin_and_every_row_hung_under_one() -> None:
    pins = {"a": 0, "b": 48}
    assert extent(pins, (_reach("a", (0, 16, 30, 4)), _reach("b", (0, 16, 4, 70)))) == (-30, 118)
    assert extent(pins, ()) == (0, 48)
