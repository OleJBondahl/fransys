"""SW8 row P7.6 at `solve` level: input cards rebuilt from their named tests (Ruling 43.2).

The study's counts: w01 crossings 0 from 84, w09 crossings 0 from 17, p02 terminals 0 off column
(`junction_off_line`) from 13, w03 crossings 0 from 25 (el-0011). The kit's card and connector pick
(KIT-PINS, el-0014) lifted the xfails. The builds give w01 0 (today 83), p02 (0, 0)
(today 2 crossings, 13 off column) and the interleaved extra 0 (today 0). w09 is the fan, `__2` of
its test; `w09_interleaved`, its first build, is an extra.
"""

from dataclasses import replace

import pytest
from input_card_designs import built, counts, solve_problem, solved

#: Options with the card's pins left at the card's own pitch: the family's rule off.
PINS_NOT_SPREAD = {"box_pin_pitch_min": 1000}


@pytest.mark.parametrize("name", ["w01", "w09_interleaved"])
def test_a_card_with_its_wires_hung_under_it_has_no_crossing(name: str) -> None:
    found = counts(solved(name))
    assert found["X"] == 0, f"{name}: {found}"


def test_a_strip_wired_to_a_card_has_every_terminal_on_its_column() -> None:
    found = counts(solved("p02"))
    assert (found["X"], found["junction_off_line"]) == (0, 0), f"p02: {found}"


@pytest.mark.parametrize("name", ["w01", "w09_interleaved"])
def test_the_count_fails_when_the_cards_pins_are_not_spread(name: str) -> None:
    found = counts(solved(name, **PINS_NOT_SPREAD))
    assert found["X"] > 0, f"{name}: {found}"


def test_the_p02_count_fails_when_the_card_has_no_movable_pins() -> None:
    _, problem = built("p02")
    fixed = replace(problem, symbols=tuple(replace(s, box=None) for s in problem.symbols))
    found = counts(solve_problem(fixed))
    assert found["X"] > 0, f"p02: {found}"


def test_the_fan_of_w09_has_no_crossing() -> None:
    """Study w09 (17 crossings): the fan wires a connector, one symbol per pin."""
    assert counts(solved("w09"))["X"] == 0


def test_the_later_channel_card_has_no_crossing() -> None:
    """Study w03 (25 crossings): each channel is wired to a connector header."""
    assert counts(solved("w03"))["X"] == 0


def test_the_p02_terminals_fall_off_their_column_when_no_wire_is_straight(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Planted: with no straight vertical wire the terminals fall off, so the 0 above can fail.

    Today's engine on this build leaves 13 terminals off column (the study's score file).
    """
    monkeypatch.setattr("fransys_layout.core.score_placement._straight", lambda _scene: set())
    assert counts(solved("p02"))["junction_off_line"] > 0
