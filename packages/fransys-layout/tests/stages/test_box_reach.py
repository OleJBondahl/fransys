"""V5, model-0129: a generic box's pins stand a channel pitch apart, widened only per text row."""

from itertools import pairwise

import pytest
from layout_cabinet import build_cabinet
from wired_cabinet import wired_cabinet

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.engines.schematic.read.write_keys import write_keys
from fransys_layout.engines.schematic.write import write_layout
from fransys_layout.geometry import GENERIC_BOX_KEY, generic_box_geometry, symbol_geometry
from fransys_layout.geometry.box_reach import Reach, Row, extent, spread
from fransys_layout.geometry.symbols import channel_pitch
from fransys_layout.stages.box_reach import _with_hung
from fransys_model.kernel import freeze
from fransys_model.layout import SymbolPlacement


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


@pytest.mark.parametrize("right", [0, 8, 20, 41, 90])
def test_no_two_contact_pins_on_one_side_are_nearer_than_the_channel_pitch(right: int) -> None:
    names, sides = ("p.abcdefgh", "p.2", "p.3", "q.1"), ("s", "s", "s", "n")
    wide = generic_box_geometry(names, sides, tuple(_reach(n, (0, 16, 4, right)) for n in names))
    assert min(_steps(wide)) >= channel_pitch()


def _side_xs(geometry) -> dict[str, list[int]]:
    xs: dict[str, list[int]] = {}
    for port in geometry.ports:
        xs.setdefault(port.facing.value, []).append(port.at.x)
    return {side: sorted(values) for side, values in xs.items()}


def _steps(geometry) -> list[int]:
    return [b - a for values in _side_xs(geometry).values() for a, b in pairwise(values)]


def _box_placements(model):
    results, _ = stage_results(model, read_inputs(model))
    written = write_layout(model, results, write_keys(model))
    placements = list(dict(written.tables["layout.symbol_placement"]).values())
    return [p for p in placements if isinstance(p, SymbolPlacement) and p.symbol == GENERIC_BOX_KEY]


def _written_steps(placement) -> list[int]:
    by_side: dict[str, list[int]] = {}
    for side, x in zip(placement.sides, placement.port_offsets, strict=True):
        by_side.setdefault(side.value, []).append(x)
    return [b - a for xs in by_side.values() for a, b in pairwise(xs)]


def test_on_the_cabinets_written_box_the_offsets_keep_each_sides_pitch() -> None:
    """Model-0129 acceptance: no two pins of any box side nearer than the channel pitch.

    The wired cabinet: HL1 draws the cabinet's `W1` as a line, and its lamp box is then not widened.
    """
    seen = 0
    for model in (freeze(wired_cabinet()),):
        for placement in _box_placements(model):
            if not placement.port_offsets:
                continue
            assert min(_written_steps(placement), default=0) >= channel_pitch(), placement.key
            seen += 1
    assert seen > 0, "no widened box on any fixture: the check would pass over nothing"


def test_the_stage_results_hold_the_widened_geometry() -> None:
    model = freeze(build_cabinet())
    results, _ = stage_results(model, read_inputs(model))
    assert any(one.reach for one in results.drawn)


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


def test_the_boxs_keepout_covers_the_texts_that_hang_beyond_its_pins() -> None:
    """V5: the keep-out the column width reads spans the rows, so no neighbour overlaps a text."""
    # UNDO: stages/box_reach.py:_with_hung, the `grow_keepout(...)` -> `geometry`
    geometry = generic_box_geometry(("a", "b"), ("s", "s"))
    room = {"b": (Row(top=0, bottom=16, left=4, right=200),)}
    keepout = _with_hung(geometry, room).keepout
    pin_b = next(p.at.x for p in geometry.ports if p.name == "b")
    assert keepout.x + keepout.width >= pin_b + 200
    assert keepout.x + keepout.width > geometry.keepout.x + geometry.keepout.width
