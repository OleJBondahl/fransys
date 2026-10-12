"""A chain's box-drawn head or tail (layout-0181): it stays in its box and anchors the chain.

Function `n` is the sample through symbol (`samples`): port index 0 is `13` (N) and 1 is `14` (S).
Function 1 stands in the box here; functions 2 and 3 are the chain's drawn steps.
"""

from typing import Any

import pytest
from samples import drawn, function_spec, hid
from test_columns import _wire

from fransys_layout.geometry import HintError
from fransys_layout.stages import Chain, ChainEntry, columns_from_chains

_BOX = function_spec(1)
_TWO, _THREE = function_spec(2), function_spec(3)
_OTHER = function_spec(4)
_ZERO = function_spec(0)


def _chain(number: int, steps: tuple[tuple[int, bool], ...]) -> Chain:
    return Chain(
        chain=hid("layout.chain", number),
        key=("invented", f"chain{number}"),
        entries=tuple(
            ChainEntry(function=hid("function", f), index=i, box=box)
            for i, (f, box) in enumerate(steps)
        ),
    )


def _columns(chains: tuple[Chain, ...], wires: tuple[Any, ...], boxes=None) -> tuple[Any, ...]:
    specs = (_ZERO, _TWO, _THREE, _OTHER)
    shown = tuple(drawn(n) for n in (0, 2, 3, 4))
    boxed = {_BOX.function: _BOX} if boxes is None else boxes
    columns, _ = columns_from_chains(chains, specs, drawn=shown, connections=wires, boxes=boxed)
    return columns


def _flipped(columns: tuple[Any, ...]) -> set[Any]:
    return {cell.function for column in columns for cell in column.cells if cell.flip}


def _cells(columns: tuple[Any, ...]) -> list[Any]:
    return [cell.function for column in columns for cell in column.cells]


def test_a_box_drawn_head_is_no_cell_of_the_column_but_anchors_its_neighbour() -> None:
    """The box lands on port 14 (S) of function 2: it is entered at 14, so the chain reads up."""
    wires = (_wire(1, (_BOX, 1), (_TWO, 1)), _wire(2, (_TWO, 0), (_THREE, 1)))
    columns = _columns((_chain(1, ((1, True), (2, False), (3, False))),), wires)
    assert _cells(columns).count(_BOX.function) == 0
    assert _flipped(columns) == {_TWO.function, _THREE.function}


def test_a_box_drawn_head_on_the_north_port_leaves_the_neighbour_unflipped() -> None:
    wires = (_wire(1, (_BOX, 1), (_TWO, 0)), _wire(2, (_TWO, 1), (_THREE, 0)))
    columns = _columns((_chain(1, ((1, True), (2, False), (3, False))),), wires)
    assert _flipped(columns) == set()


def test_a_box_drawn_tail_anchors_a_lone_step_by_the_port_away_from_it() -> None:
    """The box lands on 13 (N) of function 2; function 2 leaves by 14, so it is entered at 14."""
    wires = (_wire(1, (_BOX, 0), (_TWO, 0)), _wire(2, (_TWO, 1), (_OTHER, 0)))
    columns = _columns((_chain(1, ((2, False), (1, True))),), wires)
    assert _flipped(columns) == {_TWO.function}


def test_a_box_drawn_tail_on_the_south_port_leaves_a_lone_step_unflipped() -> None:
    wires = (_wire(1, (_BOX, 1), (_TWO, 1)), _wire(2, (_TWO, 0), (_OTHER, 1)))
    columns = _columns((_chain(1, ((2, False), (1, True))),), wires)
    assert _flipped(columns) == set()


def test_one_box_may_end_two_chains() -> None:
    wires = (_wire(1, (_BOX, 1), (_TWO, 0)), _wire(2, (_ZERO, 1), (_BOX, 0)))
    chains = (_chain(1, ((1, True), (2, False))), _chain(2, ((0, False), (1, True))))
    cells = _cells(_columns(chains, wires))
    assert _BOX.function not in cells
    assert _TWO.function in cells
    assert _ZERO.function in cells


def test_a_box_drawn_function_in_the_middle_of_a_chain_raises() -> None:
    wires = (_wire(1, (_TWO, 1), (_BOX, 0)), _wire(2, (_BOX, 1), (_THREE, 0)))
    with pytest.raises(HintError, match="only at its head or its tail"):
        _columns((_chain(1, ((2, False), (1, True), (3, False))),), wires)


def test_a_chain_of_box_drawn_functions_alone_raises() -> None:
    with pytest.raises(HintError, match="only box-drawn functions"):
        _columns((_chain(1, ((1, True),)),), ())


def test_a_box_drawn_end_not_joined_to_its_neighbour_raises() -> None:
    with pytest.raises(HintError, match="not joined"):
        _columns((_chain(1, ((1, True), (3, False))),), ())


def test_a_box_end_missing_from_the_boxes_is_not_drawn() -> None:
    wires = (_wire(1, (_BOX, 0), (_TWO, 0)),)
    with pytest.raises(HintError, match="not drawn"):
        _columns((_chain(1, ((1, True), (2, False))),), wires, boxes={})
