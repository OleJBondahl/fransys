"""The cable placer's lower band as a channel (CT5-3 P2, CD8; spec acceptance 4 and 19).

Hand-built facts, no model: F1 is a 1:3 fan-out, F2 a 2:2 swap. Each test names its probe.
"""

from dataclasses import replace
from itertools import permutations

from cable_checks import assert_no_shared_stretch, assert_on_the_grid, assert_outside_the_box
from cable_facts import block_facts

from fransys_layout.engines.cable.place import place_block
from fransys_layout.stages.channel import plan_channel, plan_links, rise

F1 = [(0, 0), (0, 1), (0, 2)]  # top: one end of 3 pins; bottom: three ends of one pin
F2 = [(0, 0), (0, 1), (1, 0), (1, 1)]  # A1-C1, A2-D1, B1-C2, B2-D2: cores 2 and 3 swap columns


def _wires(block):
    """Each core's lower run, from the cable box's foot down to its bottom pin."""
    return [w.run_b[::-1] for w in block.wires]


def _rect(block):
    return (
        block.boxes[0].box.x,
        block.boxes[0].box.y,
        block.boxes[0].box.width,
        block.boxes[0].box.height,
    )


def _bands_below(block):
    return (
        next(e for e in block.ends if not e.top).y
        - (block.boxes[0].box.y + block.boxes[0].box.height)
    ) // 8 - 1


def test_f1_fan_out_bends_in_two_tracks_without_sharing():
    """Acceptance 4: a 1:3 fan-out with two overlapping bends takes two tracks, no shared stretch.

    Probe: the vertical demand (`one.top == other.bottom`) dropped from `channel._above`.
    """
    block = place_block(block_facts(F1))
    assert block is not None
    runs = _wires(block)
    assert [len(r) for r in runs] == [2, 4, 4]  # core 1 straight, cores 2 and 3 bend
    assert _bands_below(block) == 2
    assert_no_shared_stretch(runs)
    assert_outside_the_box(runs, _rect(block))
    assert_on_the_grid(runs)
    assert all(len(w.run_a) == 2 for w in block.wires)  # the upper band is straight


def test_f2_swap_draws_one_jog_at_three_tracks():
    """Acceptance 19: the swap is a cycle; the highest-keyed core jogs, the band holds 3 tracks.

    Probe: `_split` returning None, so the cycle is not broken.
    """
    block = place_block(block_facts(F2))
    assert block is not None
    runs = _wires(block)
    assert sorted(len(r) for r in runs) == [2, 2, 4, 6]
    assert _bands_below(block) == 3
    assert_no_shared_stretch(runs)
    assert_outside_the_box(runs, _rect(block))
    assert_on_the_grid(runs)
    jog = max(runs, key=len)
    assert isinstance(jog, tuple)
    assert jog[0].x == block.wires[2].run_a[0].x  # core 3, the highest key on the cycle


def test_plan_of_a_swap_and_of_a_cycle_free_pair():
    """The channel: a swap needs a jog, so 3 tracks for 2 cores; two disjoint bends share one."""
    swap = plan_channel([(1, 72, 168), (2, 168, 72)])
    assert swap is not None
    assert (len(swap.nets), swap.count) == (3, 3)
    apart = plan_channel([(1, 24, 72), (2, 120, 168)])
    assert apart is not None
    assert (len(apart.nets), apart.count) == (2, 1)
    straight = plan_channel([(1, 24, 24)])
    assert straight is not None
    assert straight.count == 0  # a straight core takes no track


def _shuffled(facts, order):
    cores = tuple(facts.cables[0].cores[i] for i in order)
    return replace(facts, cables=(replace(facts.cables[0], cores=cores),))


def _same_block(one, other):
    """Equal blocks, wires compared by conductor (their listing order follows the cores')."""
    assert replace(one, wires=()) == replace(other, wires=())
    assert {w.conductor: w for w in one.wires} == {w.conductor: w for w in other.wires}


def test_the_plan_does_not_depend_on_the_order_the_cores_are_listed():
    """Layout invariant 5: every core listing order gives the same block. The jog and the tracks
    follow core keys, not list position. Positive: each case bends, one jogs.

    Probe: `plan_channel` taking a core's list position as its key (no sort by key).
    """
    for cores in (F2, [(0, 2), (0, 0), (0, 1), (0, 2), (0, 2)]):
        facts = block_facts(cores)
        base = place_block(facts)
        assert base is not None
        assert any(len(w.run_b) > 2 for w in base.wires)
        for order in permutations(range(len(cores))):
            other = place_block(_shuffled(facts, order))
            assert other is not None
            _same_block(base, other)


def test_a_link_pin_under_a_core_column_puts_that_core_above_the_link():
    """CD5 at L1: core 2's column stands on link 1's pin, so core 2 takes track 1, the link 2.

    Without `links` core 1 is an ordinary bend, takes track 1 and the demand is gone.
    Probe: `Net.pins` returning only `(self.bottom,)`.
    """
    columns = [(1, 16, 48), (2, 16, 80)]
    linked = plan_channel(columns, {1})
    assert linked is not None
    assert [net.core for net in linked.nets] == [1, 2]
    assert linked.tracks == (2, 1)
    plain = plan_channel(columns)
    assert plain is not None
    assert plain.tracks == (1, 2)


def test_a_link_track_has_head_more_room_above_it():
    """CD8 at L1: `rise` adds `head` once for each link track at or above `level`.

    Probe: `rise` ignoring `head`.
    """
    plan = plan_channel([(1, 16, 48), (2, 16, 80)], {1})
    assert plan is not None
    assert (plan.count, rise(plan, 1, 16), rise(plan, 2, 16)) == (2, 8, 32)  # link on track 2
    assert rise(plan, 2, 0) == 16
    unlinked = plan_channel([(1, 16, 48), (2, 16, 80)])
    assert unlinked is not None
    assert rise(unlinked, 2, 16) == 16  # no link track, no head


def test_plan_links_fills_tracks_by_left_edge():
    """The upper band: disjoint links share track 1, an overlapping one takes track 2, and links
    that only touch at an x overlap. The answer follows the input order.

    Probe: `plan_links` filling by core key instead of by left edge.
    """
    assert plan_links([(1, 16, 80), (2, 32, 48), (3, 96, 120)]) == (1, 2, 1)
    assert plan_links([(1, 16, 48), (2, 48, 80)]) == (1, 2)
    assert plan_links([(1, 96, 120), (2, 16, 80)]) == (1, 1)
    assert plan_links([]) == ()
