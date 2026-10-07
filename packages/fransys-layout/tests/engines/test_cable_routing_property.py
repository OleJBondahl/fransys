"""Every random 1:3 and 2:2 cable of 2 to 8 cores routes (CT5-3 P4, spec acceptance 19, Q4).

Hand-built facts: each core takes a random top end and bottom end, ends fill by lowest core key
and pins by core key, as `end_rows` and `drawn_pins` give them. The profile is derandomized so
the gate is reproducible. A case that does not route is a design question, not a skip. Every end
of a drawn case also carries one row link (CT5-LINK, acceptance 24): two extra pins and a core
between them.
"""

from itertools import pairwise

from cable_checks import assert_no_shared_stretch, assert_on_the_grid, assert_outside_the_box
from cable_facts import block_facts
from hypothesis import example, given, settings
from hypothesis import strategies as st

from fransys_layout.engines.cable.place import place_block

_SHAPES = ((1, 3), (2, 2))


@st.composite
def _assignment(draw, ends: int, cores: int) -> list[int]:
    """One end index per core, every end used at least once."""
    extra = draw(st.lists(st.integers(0, ends - 1), min_size=cores - ends, max_size=cores - ends))
    return draw(st.permutations([*range(ends), *extra]))


@st.composite
def _cable(draw):
    top_ends, bottom_ends = draw(st.sampled_from(_SHAPES))
    cores = draw(st.integers(max(top_ends, bottom_ends), 8))
    pairs = list(
        zip(draw(_assignment(top_ends, cores)), draw(_assignment(bottom_ends, cores)), strict=True)
    )
    loops = [(True, n) for n in range(top_ends)] + [(False, n) for n in range(bottom_ends)]
    return pairs, draw(st.sampled_from((16, 48, 120))), draw(st.sampled_from((16, 40, 64))), loops


def _touches(run, box) -> bool:
    """Whether any segment of `run` has a point on or inside the closed cable box."""
    x, y, width, height = box
    return any(
        min(a.x, b.x) <= x + width
        and max(a.x, b.x) >= x
        and min(a.y, b.y) <= y + height
        and max(a.y, b.y) >= y
        for a, b in pairwise(run)
    )


@settings(derandomize=True, deadline=None, max_examples=300, database=None)
@example(
    ([(0, 0), (0, 1), (0, 0), (0, 0)], 48, 40, [(False, 0)])
)  # top pin 3 is the link's first pin
@given(_cable())
def test_every_random_cable_routes_cleanly(case):
    """Acceptance 19, 24: it routes with a link on every end, no two wires share a stretch, none
    enters the box, all on grid, no link touches the box. The example stands a crossing core's
    top column on a link pin, so the link must join the channel's constraints.

    Probe: `place._plan` passing no `links` to `plan_channel`.
    """
    pairs, label, text, loops = case
    facts = block_facts(pairs, label=label, text=text, loops=loops)
    block = place_block(facts)
    assert block is not None, case
    cores = facts.cables[0].cores
    by_conductor = {w.conductor: w for w in block.wires}
    crossing = [by_conductor[c.conductor] for c in cores if not c.link]
    links = [by_conductor[c.conductor] for c in cores if c.link]
    assert len(crossing) == len(pairs)
    assert len(links) == len(loops)
    polylines = [(*w.run_a, *w.run_b[::-1][1:]) for w in links]
    uppers = [w.run_a for w in crossing]
    lowers = [w.run_b[::-1] for w in crossing]
    assert_no_shared_stretch([*uppers, *lowers, *polylines])
    box = tuple(getattr(block.boxes[0].box, a) for a in ("x", "y", "width", "height"))
    runs = [run for w in block.wires for run in (w.run_a, w.run_b)]
    assert_outside_the_box(runs, box)
    assert_on_the_grid(runs)
    assert not any(_touches(line, box) for line in polylines), case
    assert all(len(w.run_a) == 2 for w in crossing)  # the upper band is straight
    assert all((len(w.run_a), len(w.run_b)) == (3, 2) for w in links)  # the link encoding
    x_of = {cell.port: cell.x for end in block.ends for cell in end.cells}
    for wire, core in zip(crossing, [c for c in cores if not c.link], strict=True):
        top_x, pin_x = x_of[core.end_a], x_of[core.end_b]
        assert (wire.text_x, wire.run_b[-1].x, wire.run_b[0].x) == (top_x, top_x, pin_x)
    for wire, core in zip(links, [c for c in cores if c.link], strict=True):
        assert (wire.run_a[0].x, wire.run_b[0].x) == (x_of[core.end_a], x_of[core.end_b])
