"""Where a nested unit's function stands as a black box (`stages.black_box`)."""

import dataclasses

from samples import function_spec, hid

from fransys_layout.stages.black_box import black_box_tops, is_black_box
from fransys_layout.stages.references.types import BlackBoxReads

inner, outer, top = hid("unit", 1), hid("unit", 2), hid("unit", 3)


def test_a_nested_function_is_a_black_box_in_its_parents_set() -> None:
    assert is_black_box(inner, outer, None, {inner})


def test_a_function_is_no_black_box_in_its_own_set() -> None:
    assert not is_black_box(inner, inner, None, {inner})


def test_a_top_level_units_function_is_no_black_box() -> None:
    """A unit that is not nested stubs at its home: it is a black box nowhere."""
    assert not is_black_box(outer, None, None, {inner})


def test_an_edge_function_is_a_black_box_only_under_its_own_top() -> None:
    assert is_black_box(inner, top, top, {inner})
    assert not is_black_box(inner, outer, top, {inner})


def test_tops_name_only_a_nested_units_edge_functions() -> None:
    """An inner function off the edge, and an edge function of a unit not nested, get none."""
    edge, plain, other = (function_spec(n) for n in (1, 2, 3))
    specs = [
        dataclasses.replace(edge, unit=inner),
        dataclasses.replace(plain, unit=inner),
        dataclasses.replace(other, unit=outer),
    ]
    reads = BlackBoxReads(
        nested=frozenset({inner}),
        edges=frozenset({edge.function, other.function}),
        top=lambda _unit: top,
    )
    assert black_box_tops(specs, reads) == {edge.function: top}
