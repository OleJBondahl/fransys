"""The 16-channel output card on `solve`: every coil at its pin, one page (P7.1 B, SW8)."""

import sys
from pathlib import Path

import fransys as fr
from conventions_fixtures import house
from fransys_el import build, options, symbol_kit

from electrical_symbols import LIBRARY
from fransys_layout.core import solve

sys.path.append(str(Path(__file__).parents[3] / "tests"))
from _card_case import card_case_drafts


def _score(channels: int):
    model = fr.build(*card_case_drafts(channels)).model
    conventions = house()
    problem, _ = build(model, symbol_kit(model, LIBRARY), conventions, LIBRARY)
    return solve(problem, options(conventions, LIBRARY)).score


def test_the_sixteen_channel_card_has_every_coil_at_its_pin_on_one_page() -> None:
    score = _score(16)
    assert dict(score.P)["attached_off_pin"] == 0
    assert score.pages == 1
