"""Deep-dive D8 and D11 (amended 2026-09-24): `unit_outlines` draws one outline per run of
neighbouring columns of a unit whose mates stand at the same end, and a top end's outline stands
above its plug.

Hand-built stand-ins for the stage types: a face replica is one body of 4 x 8 grid units at its
`at`; `flip=False` is a top end (the replica above its plug, its body bottom on the mating line),
`flip=True` a bottom end.

Can-fail (each check, by one mutation of `stages/outlines.py`, undone after):
- the runs split by end: `_by_end(members, faces, cells, placed)` -> `([], members)`
  (`test_..._two_outlines`).
- a pin alone no longer joins its neighbours: `resolved[column] = joined if len(joined) == 1
  else {False}` -> `{False}` (`test_an_unmated_pin_alone_in_its_column_between_two_...`).
- a pin at its column's top no longer stands at the top end: `{all(m < t for m in mine for t in
  theirs)}` -> `{False}` (`test_a_pin_at_its_columns_top_between_two_top_end_mates_stands_in_...`).
- the runs of one end stay one: `runs += [([one], True) for one in top_set]`.
- another end's column cuts a run: `_column_runs(top_set, placed)` -> `_column_runs(top_set, ())`.
- the top-end bottom edge: `bottom = max(b.y + b.height for b in mating)` gets `+ margin`.
- the top-end title below-left when free: `title = below if free else above` -> `title = above`.
- ... else above-left: `free = not any(overlaps(below, other) for other in taken)` -> `free = True`.
- a non-face member takes its column's ends: `resolved[one.column]` -> `{False}` (in `_by_end`).
- a free column resolves within its stretch: `for stretch in _column_stretches(...)` -> one
  stretch of all the columns (`test_a_foreign_column_between_a_pin_alone_and_a_top_end_mate_...`).
- a run with no mate is a bottom-end box: `top_end = top_end and bool(mating)` -> `top_end =
  top_end` (`ValueError: max() iterable argument is empty` in `test_a_run_of_unmated_top_end_...`).
"""

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from fransys_layout.geometry import Box, Facing, Point
from fransys_layout.stages.outlines import OutlineInputs, _by_end, unit_outlines

if TYPE_CHECKING:
    from fransys_layout.stages.types import Column, FunctionSpec, Profile

_MARGIN = 4  # half a wiring grid
_HEIGHT = 8
_TOP, _BOTTOM = "top", "bottom"


def _one(
    function: str, column: str, x: int, y: int, ports: tuple[SimpleNamespace, ...] = ()
) -> SimpleNamespace:
    """A placed function of one body 4 x 8 at (x, y), its keepout the body."""
    body = Box(x=0, y=0, width=4, height=_HEIGHT)
    return SimpleNamespace(
        function=function,
        column=column,
        at=SimpleNamespace(x=x, y=y),
        geometry=SimpleNamespace(body=body, keepout=body, ports=ports),
    )


def _face(column: str, end: str) -> SimpleNamespace:
    """A column holding the face replica `f-<column>` of a mate at `end`."""
    cell = SimpleNamespace(function=f"f-{column}", face=True, replica=True, flip=end == _BOTTOM)
    return SimpleNamespace(key=column, cells=(cell,))


def _draw(placed: list, columns: list) -> tuple[list[Box], list[Box]]:
    """`unit_outlines` over `placed` (unit "U" but the functions named `other-*`) on one page: the
    outlines' boxes and the titles' boxes, each in the outline order."""
    specs = tuple(
        SimpleNamespace(
            function=one.function, unit=None if "other" in one.function else "U", ports=()
        )
        for one in placed
    )
    plan = SimpleNamespace(unit=None, drawing_set=1, number=1)
    inputs = OutlineInputs(
        functions=cast("tuple[FunctionSpec, ...]", specs),
        columns=cast("tuple[Column, ...]", tuple(columns)),
        profile=cast("Profile", SimpleNamespace(text_height=_HEIGHT)),
        title=lambda _unit: "U rev 01",
    )
    found, outlines = unit_outlines((plan,), [(tuple(placed), ())], (), inputs)
    return [o.box for o in outlines], [t.box for t in found[0][1]]


def test_neighbouring_columns_with_a_mate_at_each_end_stand_in_two_outlines() -> None:
    placed = [_one("f-a", "a", 20, 20), _one("f-b", "b", 40, 20)]
    boxes, _ = _draw(placed, [_face("a", _TOP), _face("b", _BOTTOM)])
    assert len(boxes) == 2


def test_neighbouring_columns_with_their_mates_at_one_end_stand_in_one_outline() -> None:
    placed = [_one("f-a", "a", 20, 20), _one("f-b", "b", 40, 20)]
    boxes, _ = _draw(placed, [_face("a", _TOP), _face("b", _TOP)])
    assert len(boxes) == 1


def test_a_column_of_the_other_end_between_two_columns_of_one_end_cuts_the_run() -> None:
    placed = [_one("f-a", "a", 20, 20), _one("f-b", "b", 40, 20), _one("f-c", "c", 60, 20)]
    columns = [_face("a", _TOP), _face("b", _BOTTOM), _face("c", _TOP)]
    boxes, _ = _draw(placed, columns)
    assert len(boxes) == 3


def test_a_top_end_outline_has_its_bottom_edge_on_the_replicas_body_bottom() -> None:
    placed = [_one("f-a", "a", 20, 20)]
    ((box,), _) = _draw(placed, [_face("a", _TOP)])
    assert box.y + box.height == 20 + _HEIGHT  # the mating line, the plug outside below it
    assert box.y == 20 - _MARGIN


def test_a_title_keeps_off_the_first_step_of_a_port_it_would_cover() -> None:
    """Layout-0088: the title above-left is free of every box, yet it would sit on the exit cell
    the router closes to other nets, so it goes below (a wide title, a port left of its end)."""
    north = SimpleNamespace(at=Point(x=2, y=0), facing=Facing.N)
    placed = [_one("f-a", "a", 20, 40, (north,))]
    ((box,), (title,)) = _draw(placed, [_face("a", _BOTTOM)])
    assert title.x == box.x
    assert title.y == box.y + box.height + _MARGIN


def test_a_title_stays_above_left_when_no_port_exit_is_under_it() -> None:
    south = SimpleNamespace(at=Point(x=2, y=8), facing=Facing.S)
    placed = [_one("f-a", "a", 20, 40, (south,))]
    ((box,), (title,)) = _draw(placed, [_face("a", _BOTTOM)])
    assert title.y == box.y - _MARGIN - _HEIGHT


def test_a_top_end_title_is_below_left_when_that_is_free() -> None:
    placed = [_one("f-a", "a", 20, 20)]
    ((box,), (title,)) = _draw(placed, [_face("a", _TOP)])
    assert title.x == box.x
    assert title.y == box.y + box.height + _MARGIN


def test_a_top_end_title_is_above_left_when_below_left_is_taken() -> None:
    plug = _one("other-plug", "a", 20, 20 + _HEIGHT + 2 * _MARGIN)  # on the below-left place
    placed = [_one("f-a", "a", 20, 20), plug]
    ((box,), (title,)) = _draw(placed, [_face("a", _TOP)])
    assert title.x == box.x
    assert title.y == box.y - _MARGIN - _HEIGHT


def test_a_member_that_is_no_face_takes_the_end_of_the_faces_of_its_column() -> None:
    faces = {("f-a", "a"): True, ("f-b", "b"): False, ("f-c", "c"): True, ("f-c2", "c"): False}
    face_a, face_b = _one("f-a", "a", 0, 0), _one("f-b", "b", 0, 0)
    side_a, side_d = _one("s-a", "a", 0, 0), _one("s-d", "d", 0, 0)
    both = [_one("f-c", "c", 0, 0), _one("f-c2", "c", 0, 0), _one("s-c", "c", 0, 0)]
    top, bottom = _by_end([face_a, face_b, side_a, side_d, *both], faces, {}, ())
    assert [one.function for one in top] == ["f-a", "s-a", "f-c", "s-c"]
    assert [one.function for one in bottom] == ["f-b", "s-d", "f-c2", "s-c"]


def _plain(column: str, *functions: str) -> SimpleNamespace:
    """A column of cells that are no mate: `functions` in row order, the cell's `index` its row."""
    cells = tuple(
        SimpleNamespace(function=name, index=index, face=False, replica=False, flip=False)
        for index, name in enumerate(functions)
    )
    return SimpleNamespace(key=column, cells=cells)


# D11 amended, first bullet: a column with no mate belongs to the end where its boundary pin stands.
# The stand-ins: columns at x = 20, 40, 60 (a, b, c; d at 80), all at y = 20 unless a test says so;
# the unit's pin is `pin-<column>` (unit "U"), another cell is `other-<column>` (no unit).


def test_an_unmated_pin_alone_in_its_column_between_two_top_end_mates_joins_their_run() -> None:
    """[a: top mate] [b: the pin alone] [c: top mate] -> ONE outline (the base gives three).

    A column that holds only the pin joins its neighbours' run. The run is a top-end one: its
    bottom edge stays on the mating line of a and c, and the box spans a to c.
    """
    placed = [_one("f-a", "a", 20, 20), _one("pin-b", "b", 40, 20), _one("f-c", "c", 60, 20)]
    columns = [_face("a", _TOP), _plain("b", "pin-b"), _face("c", _TOP)]
    boxes, _ = _draw(placed, columns)
    assert len(boxes) == 1
    (box,) = boxes
    assert box.y + box.height == 20 + _HEIGHT
    assert box.x <= 20
    assert box.x + box.width >= 60 + 4


def test_a_pin_at_its_columns_bottom_between_two_top_end_mates_has_its_own_outline() -> None:
    """[a: top mate] [b: `other-b` at row 0, the pin at row 1] [c: top mate] -> THREE outlines.

    The pin stands at its column's bottom, so b belongs to the bottom end (a guard: the base gives
    three too). The bottom-end outline of b has no mating line, so it is the pin's body and a
    margin: `box.y == pin_y - margin`, its bottom `pin_y + height + margin`.
    """
    pin_y = 40
    placed = [
        _one("f-a", "a", 20, 20),
        _one("other-b", "b", 40, 20),
        _one("pin-b", "b", 40, pin_y),
        _one("f-c", "c", 60, 20),
    ]
    columns = [_face("a", _TOP), _plain("b", "other-b", "pin-b"), _face("c", _TOP)]
    boxes, _ = _draw(placed, columns)
    assert len(boxes) == 3
    middle = next(box for box in boxes if box.x <= 40 <= box.x + box.width)
    assert middle.y == pin_y - _MARGIN
    assert middle.y + middle.height == pin_y + _HEIGHT + _MARGIN


def test_a_pin_at_its_columns_top_between_two_top_end_mates_stands_in_the_top_end_run() -> None:
    """[a: top mate] [b: the pin at row 0, `other-b` at row 1] [c: top mate] -> ONE outline.

    The pin stands at its column's top, so b belongs to the top end (the base gives three). For a
    top-end run `unit_outlines` takes the top edge from the members' bodies (`min y - margin`, here
    the pin's and a's body top, 20 - 4) and the bottom edge from the mating bodies only,
    `max(b.y + b.height for b in mating)`: the non-face pin adds no line. Here c's mate stands at
    y = 24, so the lowest mating line is 24 + 8.
    """
    placed = [
        _one("f-a", "a", 20, 20),
        _one("pin-b", "b", 40, 20),
        _one("other-b", "b", 40, 40),
        _one("f-c", "c", 60, 24),
    ]
    columns = [_face("a", _TOP), _plain("b", "pin-b", "other-b"), _face("c", _TOP)]
    boxes, _ = _draw(placed, columns)
    assert len(boxes) == 1
    (box,) = boxes
    assert box.y == 20 - _MARGIN
    assert box.y + box.height == 24 + _HEIGHT


def test_a_pin_alone_between_two_bottom_end_mates_is_unchanged() -> None:
    """[a: bottom mate] [b: pin alone] [c: bottom mate] -> ONE outline (a control: the base too)."""
    placed = [_one("f-a", "a", 20, 20), _one("pin-b", "b", 40, 20), _one("f-c", "c", 60, 20)]
    columns = [_face("a", _BOTTOM), _plain("b", "pin-b"), _face("c", _BOTTOM)]
    boxes, _ = _draw(placed, columns)
    assert len(boxes) == 1


def test_a_pin_alone_between_a_top_end_and_a_bottom_end_mate_takes_the_bottom_end() -> None:
    """[a: top mate] [b: pin alone] [c: bottom mate] -> TWO outlines (a control: the base too).

    Two different ends around it: the pin takes the bottom end, so a stands alone at its top end
    and one outline spans b and c.
    """
    placed = [_one("f-a", "a", 20, 20), _one("pin-b", "b", 40, 20), _one("f-c", "c", 60, 20)]
    columns = [_face("a", _TOP), _plain("b", "pin-b"), _face("c", _BOTTOM)]
    boxes, _ = _draw(placed, columns)
    assert len(boxes) == 2
    first, second = sorted(boxes, key=lambda box: box.x)
    assert first.x + first.width < 40
    assert second.x <= 40
    assert second.x + second.width >= 60 + 4


def test_a_pin_alone_next_to_one_top_end_mate_joins_it() -> None:
    """[a: pin alone] [b: top mate] -> ONE outline (the base gives two).

    Decided interpretation of the case the spec leaves open: an alone-pin column takes the end of
    its nearest mated (or end-placed) neighbour column on each side within its stretch of the
    unit's columns (no foreign column between); when those neighbours name exactly ONE end, it
    joins that end (a one-sided neighbour counts), otherwise (none, or two different ends) the
    bottom end.
    """
    placed = [_one("pin-a", "a", 20, 20), _one("f-b", "b", 40, 20)]
    boxes, _ = _draw(placed, [_plain("a", "pin-a"), _face("b", _TOP)])
    assert len(boxes) == 1


def test_a_foreign_column_between_a_pin_alone_and_a_top_end_mate_cuts_the_join() -> None:
    """[a: bottom mate] [b: foreign, `other-b` only] [c: pin alone] [d: top mate] -> TWO outlines.

    a stands alone; c joins d. The foreign column b cuts c's stretch, so c sees only d on its
    right and takes the top end. Without the cut c would see a (bottom) and d (top), two ends, and
    fall to the bottom end: three outlines. The base gives three too (c alone at the bottom end).
    """
    placed = [
        _one("f-a", "a", 20, 20),
        _one("other-b", "b", 40, 20),
        _one("pin-c", "c", 60, 20),
        _one("f-d", "d", 80, 20),
    ]
    columns = [_face("a", _BOTTOM), _plain("b", "other-b"), _plain("c", "pin-c"), _face("d", _TOP)]
    boxes, _ = _draw(placed, columns)
    assert len(boxes) == 2
    first, second = sorted(boxes, key=lambda box: box.x)
    assert first.x + first.width < 40
    assert second.x <= 60
    assert second.x + second.width >= 80 + 4


def test_a_run_of_unmated_top_end_columns_has_no_mating_line_and_is_drawn_as_a_bottom_end_box() -> (
    None
):
    """[a: the pin at row 0, `other-a` at row 1], no mate anywhere -> ONE outline.

    The pin stands at its column's top, so the column is in the top-end set; the run holds no
    mating body, so there is no bottom edge on a mating line: the box is the pin's body and a
    margin each side (as a bottom-end box with no mating line) and the title is above-left.
    """
    placed = [_one("pin-a", "a", 20, 20), _one("other-a", "a", 20, 40)]
    ((box,), (title,)) = _draw(placed, [_plain("a", "pin-a", "other-a")])
    assert box.y == 20 - _MARGIN
    assert box.y + box.height == 20 + _HEIGHT + _MARGIN
    assert title.x == box.x
    assert title.y == box.y - _MARGIN - _HEIGHT


def test_a_title_of_an_outline_at_the_frame_stands_a_text_gap_in() -> None:
    """layout-0104: the outline's left edge is on the content box's (x 0); its title is not."""
    placed = [_one("f-a", "a", _MARGIN, 20)]
    ((box,), (title,)) = _draw(placed, [_face("a", _BOTTOM)])
    assert box.x == 0
    assert title.x == 8  # the house text gap, one wiring grid, written out for the probe
