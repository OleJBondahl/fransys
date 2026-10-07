"""`grid_path` equals the pre-0156 oracle on random small grids, `None` and ties included.

Open grids with both penalties zero make many equal-cost paths, so the tie-break is exercised.
The profile is derandomized so the gate is reproducible.
"""

from grid_path_oracle import oracle_path
from hypothesis import event, given, settings
from hypothesis import strategies as st

from fransys_layout.geometry import FACING_STEP, WIRING_GRID, Box, Facing, Point
from fransys_layout.stages.grid_path import Field, grid_path
from fransys_layout.stages.space import End, Obstacle, lane

G = WIRING_GRID
_PENALTIES = st.sampled_from((0, 0, 1, G, 2 * G, 5 * G))


@st.composite
def _calls(draw):
    columns, rows = draw(st.integers(2, 7)), draw(st.integers(1, 6))
    cells = [(x * G, y * G) for x in range(columns + 1) for y in range(rows + 1)]
    cell = st.sampled_from(cells)
    facing = st.sampled_from(list(Facing))

    def inward(x: int, y: int) -> st.SearchStrategy[Facing]:
        # mostly a facing whose first step stays in the region, else any (so None still occurs)
        ok = [f for f in Facing if 0 <= x + FACING_STEP[f][0] <= columns * G]
        ok = [f for f in ok if 0 <= y + FACING_STEP[f][1] <= rows * G]
        return st.sampled_from(ok) if ok and draw(st.integers(0, 4)) else facing

    start, goal = (
        End(at=Point(x=x, y=y), facing=draw(inward(x, y))) for x, y in (draw(cell), draw(cell))
    )
    boxes = []
    for _ in range(draw(st.integers(0, 2))):
        (x, y), (to_x, to_y) = draw(cell), draw(cell)
        boxes.append(Box(x=min(x, to_x), y=min(y, to_y), width=abs(x - to_x), height=abs(y - to_y)))
    obstacles = tuple(
        Obstacle(
            box=box,
            lanes=tuple(
                lane(End(at=Point(x=x, y=y), facing=draw(facing)), box)
                for x, y in draw(st.lists(cell, max_size=2))
            ),
        )
        for box in boxes
    )
    cell_set = (
        st.frozensets(cell, max_size=len(cells) // 2)
        if draw(st.booleans())
        else st.just(frozenset())
    )
    axes_cell = st.dictionaries(cell, st.sampled_from(("h", "v", "hv")).map(frozenset), max_size=3)
    field = Field(
        region=Box(x=0, y=0, width=columns * G, height=rows * G),
        obstacles=obstacles,
        free=draw(cell_set),
        busy=draw(cell_set),
        turn_penalty=draw(_PENALTIES),
        crossing_penalty=draw(_PENALTIES),
        axes=draw(axes_cell) if draw(st.integers(0, 3)) == 0 else {},
    )
    return start, goal, field


@settings(max_examples=300, deadline=None, derandomize=True)
@given(_calls())
def test_grid_path_equals_the_oracle(call) -> None:
    start, goal, field = call
    expected = oracle_path(start, goal, field)
    event("found" if expected else "none")
    event("free" if field.free else "no free")
    assert grid_path(start, goal, field) == expected
