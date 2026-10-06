"""S12: `place.page_stack` gives each port the offset `place` gives it, on `place`'s own inputs.

Hand-made values, no model. Column `a`: function 1, then function 2 attached under it (R7.1,
glued at the row gap), then function 3, whose keep-out a label box above its body grows 24 G
upward (C8(b)). Column `b`: function 4. One page, no band with two members, so `place` moves no
row after it has stacked the page and each placed port stands at its stacked offset below the
page's first row top.
"""

from samples import PROFILE, SHEET, column, drawn, hid, page_plan

from fransys_layout.geometry import Box
from fransys_layout.stages import Cell, Column, Role, place
from fransys_layout.stages.page_stacking import PageStacking
from fransys_layout.stages.place import page_stack

_A = Column(
    key=("invented", "a"),
    cells=(
        Cell(function=hid("function", 1), index=0),
        Cell(function=hid("function", 2), index=1, host=hid("function", 1), port="out"),
        Cell(function=hid("function", 3), index=2),
    ),
    group=hid("aspect_node", 1),
    role=Role.CONTROL,
    location=hid("aspect_node", 100),
)
# a label 24 G above function 3's keep-out top (-16), in symbol coordinates
_LABELS = {hid("function", 3): [("marking.in", Box(x=16, y=-40, width=16, height=8))]}


def test_every_port_stands_at_its_stacked_offset_below_one_top() -> None:
    """`place`'s port y less `page_stack`'s offset is one number for the page: its first top."""
    # UNDO: stages/place.py `_stack_page`: `stacking.label_boxes` -> `{}` in the `_cells` call
    #     (the stack no longer sees the label that grows function 3): function 3's ports then
    #     stand 24 G lower than their offsets say, and this fails
    plan, columns = page_plan(("a", "b")), (_A, column("b", (4,)))
    functions = tuple(drawn(n) for n in (1, 2, 3, 4))
    stacking = PageStacking(profile=PROFILE, sheet=SHEET, label_boxes=_LABELS)
    stack = page_stack(plan, columns, functions, stacking)
    placed, _ = place(plan, columns, functions, stacking)
    ports = {port.port: (one.function, port.symbol_port) for one in functions for port in one.ports}
    at = {one.function: one for one in placed}
    tops = set()
    for (_, port), stacked in stack.ports.items():
        function, name = ports[port]
        one = at[function]
        y = one.at.y + next(g.at.y for g in one.geometry.ports if g.name == name)
        tops.add(y - stacked.offset)
    assert len(tops) == 1
    assert stack.last == {("invented", "a"): 1, ("invented", "b"): 0}  # function 2 in row 0
