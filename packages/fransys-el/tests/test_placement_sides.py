"""The sides of a generic box's pins (BOX-SIDES B): the first half north."""

import sys
from pathlib import Path

import fransys as fr
from conventions_fixtures import house
from fransys_el import build, symbol_kit
from fransys_el.placement_sides import half_split

from electrical_symbols import LIBRARY

sys.path.append(str(Path(__file__).parents[3] / "tests"))
from _card_case import card_case_drafts


def test_the_first_half_of_the_wired_pins_stands_north() -> None:
    assert half_split([True] * 16, [None] * 16) == ("n",) * 8 + ("s",) * 8
    assert half_split([True] * 9, [None] * 9) == ("n",) * 5 + ("s",) * 4


def test_an_unwired_pin_follows_the_pin_before_it() -> None:
    assert half_split([True, False, True, True], [None] * 4) == ("n", "n", "n", "s")


def test_a_bundle_stays_on_the_side_of_its_first_member() -> None:
    assert half_split([True] * 4, ["a", "b", "b", "c"]) == ("n", "n", "n", "s")
    assert half_split([True] * 4, [None] * 4) == ("n", "n", "s", "s")


def test_a_loose_pin_is_moved_when_all_pins_land_on_one_side() -> None:
    assert half_split([False, False], [None, None]) == ("n", "s")


def test_the_sixteen_channel_card_stands_ch01_over_ch09() -> None:
    model = fr.build(*card_case_drafts(16)).model
    conventions = house()
    problem, _ = build(model, symbol_kit(model, LIBRARY), conventions, LIBRARY)
    (card,) = [s for s in problem.symbols if s.box is not None]
    pins = {p.id.rstrip("-"): p for p in card.pins}
    assert [pins[f"CH{i:02d}"].side for i in (1, 8, 9, 16)] == ["N", "N", "S", "S"]
    assert all(pins[f"CH{i:02d}"].dx == pins[f"CH{i + 8:02d}"].dx for i in range(1, 9))
