"""The column arrangement rules (D8): hand-made values, no model and no engine."""

from dataclasses import replace
from typing import TYPE_CHECKING, Any

from samples import column, function_spec, hid

from fransys_layout.stages.arrange import cut_locations, edge_mates, join_strip_rows
from fransys_layout.stages.types import Cell, FunctionSpec, MatedFunctions

if TYPE_CHECKING:
    from fransys_model.kernel import Id

PARENT = hid("unit", 1)
CHILD = hid("unit", 2)


def _in_unit(number: int, unit: Id[Any] | None) -> FunctionSpec:
    return replace(function_spec(number), unit=unit)


def test_a_pin_mated_to_the_boundary_pin_of_a_unit_nested_in_its_own_is_paired() -> None:
    """Function 1 stands in the parent unit, function 2 is a boundary pin of the child unit."""
    # UNDO: stages/arrange.py:edge_mates, `((mate.a, mate.b), (mate.b, mate.a))` ->
    #     `((mate.a, mate.b),)` (a mate authored the other way round is missed)
    specs = (_in_unit(1, PARENT), _in_unit(2, CHILD))
    plug = MatedFunctions(a=hid("function", 1), b=hid("function", 2))
    parent_of = {hid("function", 2): PARENT}

    assert edge_mates(parent_of, specs, (plug,)) == (plug,)
    assert edge_mates(parent_of, specs, (MatedFunctions(a=plug.b, b=plug.a),)) == (plug,)


def test_a_boundary_pin_whose_unit_has_no_parent_pairs_only_with_a_top_level_pin() -> None:
    """The unit is top level (`parent` is `None`): a pin in another unit is not its parent's."""
    # UNDO: stages/arrange.py:edge_mates, `and parent_of[owner] == spec_of[a].unit` -> `and True`
    parent_of = {hid("function", 2): None}
    plug = MatedFunctions(a=hid("function", 1), b=hid("function", 2))
    inside = (_in_unit(1, PARENT), _in_unit(2, CHILD))
    top = (_in_unit(1, None), _in_unit(2, CHILD))

    assert edge_mates(parent_of, inside, (plug,)) == ()
    assert edge_mates(parent_of, top, (plug,)) == (plug,)


def test_a_column_is_cut_where_the_top_level_location_of_its_rows_changes() -> None:
    """Functions 2 and 3 stand in another location: they head a column of their own."""
    # UNDO: stages/arrange.py:cut_locations, `if len(runs) < 2:` -> `if len(runs) < 3:`
    elsewhere = (
        replace(function_spec(number), location_path=(hid("aspect_node", 200),))
        for number in (2, 3)
    )
    specs = (function_spec(1), *elsewhere)

    cut = cut_locations((column("a", (1, 2, 3)),), specs)

    assert [tuple(cell.function for cell in one.cells) for one in cut] == [
        (hid("function", 1),),
        (hid("function", 2), hid("function", 3)),
    ]
    assert [one.key for one in cut] == [("invented", "a"), ("chain", "", "invented", "fn2")]
    assert [cell.index for one in cut for cell in one.cells] == [0, 0, 1]


def test_a_column_in_one_location_is_kept_as_it_is() -> None:
    """No change of location, no cut."""
    only = column("a", (1, 2))

    assert cut_locations((only,), (function_spec(1), function_spec(2))) == (only,)


def test_a_terminal_column_joins_the_row_of_its_strip_as_the_next_lane() -> None:
    """Terminal 3 of strip X1 has a row in another column: it joins it and its column goes."""
    # UNDO: stages/arrange.py:_strip_rows, `one.roles.terminal and one.strip_text` ->
    #     `False and one.strip_text`
    terminals = (
        replace(function_spec(number, kind="terminal"), strip_text="X1") for number in (2, 3)
    )
    specs = (function_spec(1), *terminals)
    host, joiner = column("a", (1, 2)), column("b", (3,))

    joined = join_strip_rows((host, joiner), specs)

    assert joined == (
        replace(
            host,
            cells=(*host.cells, Cell(function=hid("function", 3), index=1, lane=1)),
        ),
    )
