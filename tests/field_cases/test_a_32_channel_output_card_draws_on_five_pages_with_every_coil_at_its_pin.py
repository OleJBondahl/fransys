"""Field case: a 32-channel output card draws on at most five pages, every coil at its pin (SW8).

The engineering shape: one output card, a box with 32 channel pins in one group, and a relay coil
wired from each channel in a second group. The card and its coils only: a mixed unit with feeders
and strips is SCHEMATIC-FLIP's acceptance (P7.1 B, question 4).

The bug: today's engine draws the 32 columns on one page, so the card and the coils from K22 on
leave the content box. The core path (P7.1) spreads the pins to the coils' pitch, takes both
edges of the card and carries what does not fit to further pages, with a straight wire from each
pin to its coil (placement design section 5, items 1 and 2: "Spread pins, straight wires").

The rule (decision el-0006, SW8): on the core path the card draws on 5 pages or fewer (the
16-channel card: 1) and the wire from every channel pin to its coil is straight. The 16-channel
card passes (SW8, amendment 3). PAGE-CUT (R435a): the columns that do not fit the card's edges
go to the next page with a tag pair each, so the 32-channel card passes too.
"""

import fransys as fr
from _card_case import card_case_drafts, coil_wires_straight, page_count


def _built(channels: int) -> fr.BuildResult:
    design, document = card_case_drafts(channels)
    return fr.build(design, document)


def test_a_16_channel_card_draws_on_one_page_with_every_coil_at_its_pin() -> None:
    result = _built(16)
    assert page_count(result) == 1
    assert coil_wires_straight(result)


def test_a_32_channel_card_draws_on_five_pages_with_every_coil_at_its_pin() -> None:
    result = _built(32)
    assert page_count(result) <= 5
    assert coil_wires_straight(result)
    assert not [
        f for f in result.findings if f.code == "ROUTE_FAILED"
    ]  # a tag pair joins the spill
