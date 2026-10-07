"""The cable placer's bands (CT5-3 P1, CD8): only the lower band grows, one track at a time.

Hand-built facts, no model. Each test names the probe that must make it fail.
"""

from cable_facts import block_facts

from fransys_layout.engines.cable.place import ROW, place_block, place_tracks
from fransys_layout.geometry import WIRING_GRID

G = WIRING_GRID
_STRAIGHT = [(0, 0), (0, 0), (0, 0)]


def _placed(facts, tracks):
    block = place_tracks(facts, tracks)
    assert block is not None
    return block


def _bands(block):
    top = next(e for e in block.ends if e.top)
    bottom = next(e for e in block.ends if not e.top)
    return top, bottom, bottom.y - (block.boxes[0].box.y + block.boxes[0].box.height)


def test_one_track_is_ct5_2s_block():
    """One track keeps CT5-2's geometry: a 2G band each side of the 4G box (acceptance 18).

    Probe: the lower band constant changed from 2G.
    """
    top, bottom, lower = _bands(_placed(block_facts(_STRAIGHT), 1))
    assert (top.y, lower) == (ROW, 2 * G)
    assert place_block(block_facts(_STRAIGHT)) == _placed(block_facts(_STRAIGHT), 1)
    box = _placed(block_facts(_STRAIGHT), 1).boxes[0].box
    assert bottom.y == 3 * ROW + box.height + 2 * G


def test_only_the_lower_band_grows():
    """Three tracks: the lower band is 4G, the upper band, the box and the top row stay.

    Probe: `_place_rows` growing the band above the cable box too.
    """
    one = _placed(block_facts(_STRAIGHT), 1)
    three = _placed(block_facts(_STRAIGHT), 3)
    top1, _, lower1 = _bands(one)
    top3, _, lower3 = _bands(three)
    assert (lower1, lower3) == (2 * G, 4 * G)
    assert (top3.y, three.boxes) == (top1.y, one.boxes)
    assert three.height == one.height + 2 * G
    for a, b in zip(one.wires, three.wires, strict=True):
        assert a.run_a == b.run_a  # the upper run is the same
        assert b.run_b[0].y - a.run_b[0].y == 2 * G  # the lower run's foot moved down
