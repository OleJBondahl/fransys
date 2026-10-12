"""An over-wide column cut between its lanes (layout-0182): hand-made columns, no engine."""

from dataclasses import replace

from samples import hid

from fransys_layout.geometry import Box
from fransys_layout.stages.lane_runs import lane_runs
from fransys_layout.stages.types import Cell, Column, Role
from fransys_layout.stages.wide_columns import (
    _lane_parts,
    lane_of,
    part_key,
    split_column,
    with_parts,
)

KEY = ("chain", "K1")


def _bank(lanes: int) -> Column:
    """A row of attachments, a row of `lanes` coils with a side cell on the last, one box below."""
    coils = [Cell(function=hid("coil", n), index=1, lane=n) for n in range(lanes)]
    attached = [
        Cell(function=hid("terminal", n), index=0, lane=k, host=hid("coil", n))
        for k, n in enumerate((lanes - 1, 0))
    ]
    side = Cell(
        function=hid("diode", 1), index=1, lane=lanes, side=True, carrier=coils[-1].function
    )
    box = Cell(function=hid("box", 1), index=2, lane=0)
    return Column(
        key=KEY,
        cells=(*attached, *coils, side, box),
        group=None,
        role=Role.CONTROL,
        location=None,
    )


def _cut(lanes: int) -> tuple[Column, ...]:
    """The bank cut by `lane_runs`: every lane 100 wide, three lanes to a part."""
    runs = lane_runs([(n * 100, n * 100 + 90) for n in range(lanes)], [], 290)
    return split_column(_bank(lanes), [tuple(range(s, e)) for s, e in runs])


def test_a_side_cell_and_an_attachment_stand_in_their_carriers_lane() -> None:
    """The diode goes with the last coil, each terminal with its host coil."""
    # UNDO: stages/wide_columns.py:lane_of, a hosted cell keeps its own lane
    lanes = lane_of(_bank(5))
    assert lanes[hid("diode", 1)] == 4
    assert lanes[hid("terminal", 4)] == 4
    assert lanes[hid("terminal", 0)] == 0


def test_each_part_counts_its_lanes_from_zero_and_drops_its_empty_rows() -> None:
    """Part two holds coils 3, 4, the diode and terminal 4, one attachment row and one coil row."""
    # UNDO: stages/wide_columns.py:_part, `cell.lane - first` -> `cell.lane`
    first, second = _cut(5)
    assert first.key == KEY
    assert second.key == (*KEY, "lane", "0003")
    assert [(c.function, c.index, c.lane) for c in second.cells] == [
        (hid("terminal", 4), 0, 0),
        (hid("coil", 3), 1, 0),
        (hid("coil", 4), 1, 1),
        (hid("diode", 1), 1, 2),
    ]
    assert hid("box", 1) in {c.function for c in first.cells}
    assert [(c.index, c.lane) for c in first.cells if c.host is not None] == [(0, 0)]


def test_a_lane_added_at_the_end_changes_only_the_last_part() -> None:
    """D17: seven lanes and eight lanes share their first two parts, keys and cells."""
    # UNDO: stages/wide_columns.py:part_key, key the part by its ordinal, not its first lane
    seven, eight = _cut(7), _cut(8)
    assert seven[:2] == eight[:2]
    assert seven[2].key == eight[2].key == (*KEY, "lane", "0006")
    assert seven[2].cells != eight[2].cells


def test_a_part_cut_again_counts_its_lanes_from_the_bundle() -> None:
    """A part from lane 3, cut at its own lane 2, starts at the bundle's lane 5."""
    # UNDO: stages/wide_columns.py:part_key, drop the bundle offset
    assert part_key(part_key(KEY, 3), 2) == (*KEY, "lane", "0005")
    assert part_key(KEY, 10) > part_key(KEY, 9)


def test_the_parts_of_a_cut_column_stand_in_its_place_among_every_column() -> None:
    """The row labels' columns are cut by the same lanes, from their own cells, in place."""
    # UNDO: stages/wide_columns.py:with_parts, put the parts from `columns` in place
    other = Column(key=("chain", "K9"), cells=(), group=None, role=Role.CONTROL, location=None)
    bank = _bank(5)
    unmoved = replace(bank, cells=tuple(c for c in bank.cells if c.host is None))
    found = with_parts((unmoved, other), (*_cut(5), other))
    assert [c.key for c in found] == [KEY, (*KEY, "lane", "0003"), other.key]
    assert all(c.host is None for part in found for c in part.cells)
    assert {c.function for c in found[1].cells} == {hid("coil", 3), hid("coil", 4), hid("diode", 1)}
    assert with_parts((bank, other), (bank, other)) == (bank, other)


def _ink() -> dict:
    """Each coil's ink: 90 wide at a pitch of 100, as `_cut` measures them."""
    return {(KEY, hid("coil", n)): [Box(x=n * 100, y=0, width=90, height=10)] for n in range(5)}


def test_pole_linked_lanes_are_never_cut_apart() -> None:
    """Room 190 would cut lanes 1 and 2 apart; a link joins them, so they stay in one part."""
    # UNDO: stages/lane_runs.py:_held, `range(min(a, b) + 1, max(a, b) + 1)` -> `range(0)`
    free = _lane_parts(_bank(5), _ink(), [], 190)
    linked = _lane_parts(_bank(5), _ink(), [(1, 2)], 190)
    assert [lanes for lanes, _ in free] == [(0, 1), (2, 3), (4,)]
    assert [lanes for lanes, _ in linked] == [(0,), (1, 2), (3, 4)]
