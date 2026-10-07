"""`stages.harness_route`: HL15's line polylines and HL16's label, on hand-built points only.

The grid is 8. Ends stand on grid points; a box's outer edge faces away from it, so an end
on a box's bottom edge faces S. Each test names the one Edit that makes it fail.
"""

from itertools import pairwise

import pytest
from samples import hid

from fransys_layout.geometry import Box, Facing, LayoutError, Point
from fransys_layout.stages.grid_path import cells_of
from fransys_layout.stages.harness_route import (
    Grid,
    LineEnd,
    line_paths,
    line_text,
    longest_run,
    root,
    text_centre,
)
from fransys_layout.stages.space import End, Obstacle, Shape, Space
from fransys_layout.stages.texts.candidates import DEFAULT_TABLE
from fransys_layout.stages.texts.place_texts import place_texts

_OPEN = Grid(region=Box(x=-80, y=-80, width=320, height=320), obstacles=(), turn_penalty=8)
_HARNESS = hid("item", 13)


def _end(branch: int, x: int, y: int, facing: Facing, *, interface: bool = False) -> LineEnd:
    return LineEnd(branch=branch, end=End(at=Point(x=x, y=y), facing=facing), interface=interface)


def _orthogonal(points: tuple[Point, ...]) -> bool:
    return all(one.x == two.x or one.y == two.y for one, two in pairwise(points))


def test_a_two_end_line_is_one_orthogonal_polyline_from_end_to_end_round_a_keep_out() -> None:
    """HL15: two ends give one path, the root's, that avoids the box between them. UNDO: drop
    the grid's obstacles in `_path`, and it runs straight through."""
    block = Box(x=-8, y=24, width=24, height=8)
    grid = Grid(region=_OPEN.region, obstacles=(Obstacle(box=block, lanes=()),), turn_penalty=8)
    ends = (_end(1, 0, 0, Facing.S), _end(2, 0, 64, Facing.N))
    paths = line_paths(ends, grid)
    assert list(paths) == [1]
    path = paths[1]
    assert (path[0], path[-1]) == (Point(x=0, y=0), Point(x=0, y=64))
    assert _orthogonal(path)
    assert len(path) > 2
    assert not any(-8 <= x <= 16 and 24 <= y <= 32 for x, y in cells_of(path))


def test_three_ends_run_a_trunk_to_one_split_then_legs_that_share_their_run() -> None:
    """HL15: the trunk ends at the split where every leg starts; the deeper west leg runs along
    the first leg's row. UNDO: route each leg with no free cells, and it parts at the split."""
    ends = (
        _end(1, 80, 0, Facing.S, interface=True),
        _end(2, 0, 96, Facing.N),
        _end(3, 16, 128, Facing.N),
    )
    paths = line_paths(ends, _OPEN)
    trunk, one, two = paths[1], paths[2], paths[3]
    split = trunk[-1]
    assert trunk[0] == Point(x=80, y=0)
    assert split == Point(x=80, y=48)
    assert one[0] == two[0] == split
    assert (one[-1], two[-1]) == (Point(x=0, y=96), Point(x=16, y=128))
    assert all(_orthogonal(path) for path in paths.values())
    assert two[1:3] == (Point(x=80, y=88), Point(x=16, y=88))
    assert Point(x=80, y=88) in one


def test_the_root_is_the_first_interface_end_else_the_first_end() -> None:
    """HL15: the interface end is root although it is second; with none, the first. UNDO:
    `root` returns `ends[0]`."""
    plain = (_end(1, 0, 0, Facing.S), _end(2, 8, 0, Facing.S), _end(3, 16, 0, Facing.S))
    marked = (plain[0], _end(2, 8, 0, Facing.S, interface=True), plain[2])
    assert root(plain) is plain[0]
    assert root(marked) is marked[1]


def test_each_leg_keeps_its_ends_branch_and_the_trunk_is_the_roots() -> None:
    """Acceptance 18: branches 4, 7 and 9 with the interface at 7; each key's path ends at its
    own end and the trunk is 7's. Probe: the root keyed 0 and the others counted from 1."""
    ends = (
        _end(4, 0, 96, Facing.N),
        _end(7, 80, 0, Facing.S, interface=True),
        _end(9, 160, 96, Facing.N),
    )
    paths = line_paths(ends, _OPEN)
    assert sorted(paths) == [4, 7, 9]
    assert paths[7][0] == Point(x=80, y=0)
    assert paths[4][-1] == Point(x=0, y=96)
    assert paths[9][-1] == Point(x=160, y=96)
    assert paths[4][0] == paths[9][0] == paths[7][-1]


def test_a_line_the_grid_cannot_draw_is_a_layout_error() -> None:
    """A goal outside the region has no path; it raises, naming the branch."""
    small = Grid(region=Box(x=0, y=0, width=16, height=16), obstacles=(), turn_penalty=8)
    with pytest.raises(LayoutError, match="branch 1"):
        line_paths((_end(1, 0, 0, Facing.S), _end(2, 0, 64, Facing.N)), small)


def test_a_line_whose_start_is_shut_in_by_a_keep_out_still_draws_over_the_free_region() -> None:
    """layout-0154: a keep-out on the first step leaves no path; `_path` retries without them.

    UNDO: drop the `or grid_path(..., replace(field, obstacles=()))` fallback in `_path`.
    """
    shut = Box(x=-8, y=0, width=24, height=16)
    grid = Grid(region=_OPEN.region, obstacles=(Obstacle(box=shut, lanes=()),), turn_penalty=8)
    paths = line_paths((_end(1, 0, 0, Facing.S), _end(2, 0, 64, Facing.N)), grid)
    assert (paths[1][0], paths[1][-1]) == (Point(x=0, y=0), Point(x=0, y=64))


# The longest run is the second segment, x 0..80 at y 16. Text 30 by 7 above it, the house text
# gap (8) off it (layout-0158): candidate 0 is centred over it at x 25..55, y 1..8, candidate 1
# one text height right, x 32..62.
_LINE = (Point(x=0, y=0), Point(x=0, y=16), Point(x=80, y=16), Point(x=80, y=24))


def test_the_longest_run_is_the_longest_segment_not_the_first() -> None:
    """HL16. UNDO: `longest_run` returns the first segment."""
    assert longest_run(_LINE) == (Point(x=0, y=16), Point(x=80, y=16))


def test_the_label_takes_the_first_candidate_above_the_longest_run() -> None:
    """HL16: the text stands centred over the longest run, horizontal, `TEXT_GAP` off it."""
    placed, findings = place_texts(
        (line_text(_HARNESS, 1, _LINE, (30, 7)),), Space(shapes=()), DEFAULT_TABLE
    )
    assert findings == ()
    assert placed[0].box == Box(x=25, y=1, width=30, height=7)
    assert text_centre(placed[0]) == Point(x=40, y=4)


def test_a_blocked_first_candidate_moves_the_label_to_the_next_along_the_run() -> None:
    """Acceptance 17: a shape over candidate 0 only, and the text takes candidate 1. Probe: the
    label placed at a fixed spot, and it stays on the blocked one."""
    space = Space(shapes=(Shape(owner=None, box=Box(x=24, y=1, width=4, height=7)),))
    placed, findings = place_texts((line_text(_HARNESS, 1, _LINE, (30, 7)),), space, DEFAULT_TABLE)
    assert findings == ()
    assert text_centre(placed[0]) == Point(x=47, y=4)


def test_two_legs_of_one_harness_place_their_labels_in_one_call() -> None:
    """One handle, one slot per branch: two legs never clash in the placer's key."""
    other = (Point(x=0, y=40), Point(x=0, y=120))
    texts = (line_text(_HARNESS, 1, _LINE, (30, 7)), line_text(_HARNESS, 2, other, (30, 7)))
    placed, _ = place_texts(texts, Space(shapes=()), DEFAULT_TABLE)
    assert {one.slot for one in placed} == {"1", "2"}
    assert text_centre(next(one for one in placed if one.slot == "2")) == Point(x=23, y=80)
