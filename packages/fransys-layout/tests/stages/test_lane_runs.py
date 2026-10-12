"""Lane runs fill first and never part lanes that overlap or are linked (decision layout-0182)."""

from itertools import pairwise

from fransys_layout.stages.lane_runs import lane_runs

FIVE = [(0, 90), (100, 190), (200, 290), (300, 390), (400, 490)]


def test_runs_fill_first() -> None:
    """Room 190 holds two lanes of the five; the last lane is left alone."""
    # UNDO: stages/lane_runs.py:lane_runs, `> room` -> `>= 0` (every lane is cut alone)
    assert lane_runs(FIVE, [], 190) == ((0, 2), (2, 4), (4, 5))


def test_a_run_exactly_as_wide_as_the_room_fits() -> None:
    """A two-lane span of 190 under room 190 stays whole."""
    # UNDO: stages/lane_runs.py:lane_runs, `> room` -> `>= room`
    assert lane_runs(FIVE[:2], [], 190) == ((0, 2),)


def test_everything_that_fits_is_one_run() -> None:
    """A room wider than the whole row gives one run."""
    # UNDO: stages/lane_runs.py:lane_runs, `runs.append((start, len(extents)))` -> `pass`
    assert lane_runs(FIVE, [], 10_000) == ((0, 5),)


def test_a_lane_reaching_back_over_the_previous_lane_is_not_parted_from_it() -> None:
    """Lane 0 reaches 250, so lane 1 starts inside it: they share a run whatever the room."""
    # UNDO: stages/lane_runs.py:_blocks, `extents[i][0] >= reach` -> `True`
    extents = [(0, 250), (100, 190), (300, 390)]
    assert lane_runs(extents, [], 50) == ((0, 2), (2, 3))


def test_a_link_keeps_lanes_in_one_run_in_either_order() -> None:
    """A link (3, 1) spans lanes 1..3 like (1, 3): they stay together."""
    # UNDO: stages/lane_runs.py:_held, `min(a, b) + 1, max(a, b) + 1` -> `a + 1, b + 1`
    assert lane_runs(FIVE, [(1, 3)], 100) == ((0, 1), (1, 4), (4, 5))
    assert lane_runs(FIVE, [(3, 1)], 100) == ((0, 1), (1, 4), (4, 5))


def test_a_block_wider_than_the_room_stands_alone() -> None:
    """The linked block 1..3 is wider than the room; lanes after it still fill."""
    # UNDO: stages/lane_runs.py:lane_runs, `start = first` -> `start = stop`
    extents = [*FIVE, (500, 590)]
    assert lane_runs(extents, [(1, 3)], 190) == ((0, 1), (1, 4), (4, 6))


def test_no_lanes_is_no_runs() -> None:
    """An empty row has nothing to cut."""
    # UNDO: stages/lane_runs.py:lane_runs, `if not extents: return ()` -> removed (IndexError)
    assert lane_runs([], [], 100) == ()


def test_runs_cover_every_lane_once_in_order() -> None:
    """Whatever the room and links, the runs tile 0..n without gaps or overlap."""
    # UNDO: stages/lane_runs.py:lane_runs, `start = first` -> `start = first + 1` (a gap)
    cases = [(FIVE, [], 90), (FIVE, [(0, 4)], 10), ([(0, 250), (100, 190), (300, 390)], [], 120)]
    for extents, links, room in cases:
        runs = lane_runs(extents, links, room)
        assert runs[0][0] == 0
        assert runs[-1][1] == len(extents)
        assert all(a[1] == b[0] for a, b in pairwise(runs))
