"""The 24V net of the 16-input panel reaches every device end in the card's set (R418, layout-0378, layout-0634).

The card's own supply pin hung from the trunk its inputs drive, one y node above and below the
trunk. The whole net left its fan, was cut as one tag pair, and F21, K1, S1, S5, S6 and DI1 got
"""

from __future__ import annotations

from typing import Any

import pytest

DEVICE_ENDS = {
    ("U1-F21", "out"),
    ("U1-K1", "in"),
    ("U1-S1", "in"),
    ("U1-S5", "in"),
    ("U1-S6", "in"),
    ("U1-DI1", "power.24V"),
}


def _reached(layout: Any, net_id: str) -> set[tuple[str, str]]:
    points = {(pr.page, p) for pr in layout.routes.pages for w in pr.wires if w.net == net_id for p in w.points}
    return {(pl.sym.split()[0], q.pin) for pp in layout.placement.pages for pl in pp.placed for q in pl.pin_xy if (pl.page, (q.x, q.y)) in points}


@pytest.mark.private_input  # reads internal/ (R462)
def test_every_device_end_of_the_card_supply_net_is_wired() -> None:
    from placement_corpus.run import observed

    found = []
    for problem, _, layout in observed("panel_di16p").caught("solves"):
        for net in problem.nets:
            ends = {(p.sym.split()[0], p.pin) for p in net.pins}
            if ends >= DEVICE_ENDS:
                found.append(DEVICE_ENDS - _reached(layout, net.id))
    assert found == [set()]
