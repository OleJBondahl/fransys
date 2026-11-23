"""The 16-channel output card on `solve`: every coil at its pin, one page (P7.1 B, SW8)."""

import fransys as fr
from _card_case import card_case_drafts
from conventions_fixtures import drawn_options, house
from fransys_el import build, symbol_kit

from electrical_symbols import LIBRARY
from fransys_layout.core import solve


def _score(channels: int):
    model = fr.build(*card_case_drafts(channels)).model
    conventions = house()
    kit = symbol_kit(model, LIBRARY)
    problem, _ = build(model, kit, conventions, LIBRARY)
    return solve(problem, drawn_options(model, kit, problem, conventions)).score


def test_the_sixteen_channel_card_has_every_coil_at_its_pin_on_one_page() -> None:
    score = _score(16)
    assert dict(score.P)["attached_off_pin"] == 0
    assert score.pages == 1
