"""Field case: one output card with 32 channel pins in one group, a relay coil wired from each channel in a second group.
The bug: the engine drew all 32 columns on one page, so the card and the coils from K22 on left the content box.
Fixed by el-0006 (SW8), the card draws on 5 pages or fewer with each channel wire straight; PAGE-CUT (R435a) carries the overflow."""

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
    over = [f for f in result.findings if f.code == "CARD_OVERFULL"]
    assert [f.severity for f in over] == [fr.Severity.INFO]  # R1154: a spill joined by tag pairs loses no fact
