"""Which placed ports draw no marker and need no cover (layout-0080): hand-made values, no model.

Units: `P` is top-level, `N` is nested in `P`. Functions (each with one port of its own number):
1 and 2 stand in `N`, 3 in `P`, 4 in no unit. Drawing sets: 1 is the top-level set, 2 is `P`'s
set, 3 is `N`'s set. A function placed in a set that is not its unit's is a black box there.
"""

from dataclasses import replace

import pytest
from samples import function_spec, hid, page_plan, placed

from fransys_layout.stages import Connection, PortRef, Role
from fransys_layout.stages.exempt import ExemptInputs, UnitNesting, boundary_exempt, open_ends

_P, _N = hid("unit", 1), hid("unit", 2)
_UNIT_OF = {1: _N, 2: _N, 3: _P, 4: None}
_SET_UNIT = {1: None, 2: _P, 3: _N}
_NESTING = UnitNesting(
    inside={_P: frozenset({_P}), _N: frozenset({_N, _P})}, nested=frozenset({_N})
)


def _port(number: int):
    return hid("port", number)


def _wire(a: int, b: int) -> Connection:
    """A conductor from the port of function `a` to the port of function `b`."""
    return Connection(
        handle=hid("conductor", a * 10 + b),
        physical_net=hid("net", 0),
        role=Role.CONTROL,
        a=PortRef(function=hid("function", a), port=_port(a)),
        b=PortRef(function=hid("function", b), port=_port(b)),
    )


def _exempt(wires: list[tuple[int, int]], stands: list[tuple[int, int]]) -> set:
    """`boundary_exempt` of the conductors `wires`, the functions placed as `(function, set)`."""
    inputs = ExemptInputs(
        connections=tuple(_wire(a, b) for a, b in wires),
        net_groups=(),
        functions=tuple(
            replace(function_spec(n), function=hid("function", n), unit=u)
            for n, u in _UNIT_OF.items()
        ),
        plans=tuple(
            replace(page_plan(("a",)), drawing_set=number, unit=unit)
            for number, unit in _SET_UNIT.items()
        ),
        seats=tuple(
            replace(placed(n, x=0, y=0), drawing_set=drawing_set) for n, drawing_set in stands
        ),
    )
    return set(boundary_exempt(inputs, _NESTING))


def test_a_top_level_units_black_box_pin_is_exempt_and_no_other_pin_is() -> None:
    """Unit `P` (function 3) wired to function 4, which stands in no unit. The black box in the
    top-level set is exempt (its stub is another rule); `P`'s own pin in `P`'s set gets a stub, and
    function 4, in the top-level set that is its own, is no boundary pin."""
    # UNDO: stages/exempt.py `boundary_exempt`, the own-set branch: drop `nested and` (the
    #   top-level unit's own pin is exempt in its own set too)
    exempt = _exempt([(3, 4)], [(3, 1), (4, 1), (3, 2)])
    assert exempt == {(_port(3), 1)}


@pytest.mark.parametrize(
    ("wires", "stands", "expected"),
    [
        pytest.param([(1, 2)], [(1, 2), (2, 2)], {(_port(1), 2), (_port(2), 2)}, id="net-inside"),
        pytest.param([(1, 3)], [(1, 2), (3, 2)], set(), id="net-leaves"),
    ],
)
def test_a_nested_units_black_box_pin_is_exempt_in_the_parents_set_when_its_net_stays_inside(
    wires, stands, expected
) -> None:
    """Both functions of `N` (1, 2) wired together: the net is `N`'s own wiring, exempt in `P`'s
    set. Function 1 wired to function 3 of `P`: the net is `P`'s wiring, an ordinary member."""
    # UNDO: stages/exempt.py `boundary_exempt`, the black-box branch:
    #   `exempt = not nested or not any(leaves(mate, unit) for mate in net[port])` -> `True`
    assert _exempt(wires, stands) == expected


@pytest.mark.parametrize(
    ("wires", "stands", "expected"),
    [
        pytest.param([(1, 3)], [(1, 2), (1, 3)], {(_port(1), 3)}, id="every-conductor-leaves"),
        pytest.param([(1, 3), (1, 2)], [(1, 2), (1, 3)], set(), id="also-wired-inside"),
        pytest.param([(1, 3)], [(1, 3)], set(), id="no-black-box"),
    ],
)
def test_a_nested_units_own_pin_is_exempt_when_it_has_a_black_box_and_every_conductor_leaves(
    wires, stands, expected
) -> None:
    """Function 1 of `N` placed as a black box in `P`'s set (2) and in its own set (3): the pin in
    `N`'s set is exempt when each conductor of it goes to `P`; not when it is also wired to
    function 2 of `N`, and not when the function has no black box in the parent's set."""
    # UNDO: stages/exempt.py `boundary_exempt`, the own-set branch: `all(leaves(...))` -> `any(...)`
    # UNDO: same branch: `one.function in black_boxes` -> `True` (the `no-black-box` case)
    assert _exempt(wires, stands) == expected


def _spec(number: int, pin_of: int | None = None):
    """Function `number`, a pin view of function `pin_of` when that is given."""
    pin = None if pin_of is None else hid("function", pin_of)
    return replace(function_spec(number), function=hid("function", number), pin_function=pin)


def test_open_ends_are_the_boundary_functions_and_no_other_function() -> None:
    """Functions 1 and 2, the boundary function 1: only function 1 is an open end."""
    # UNDO: stages/exempt.py `open_ends`: the `in edges` test -> `not in edges` (function 2 only)
    assert open_ends((_spec(1), _spec(2)), frozenset({hid("function", 1)})) == {hid("function", 1)}


def test_open_ends_follow_a_pin_view_to_its_boundary_function() -> None:
    """Function 3 is a pin view of the boundary function 1: an open end though its own id is no
    boundary. Function 1 as a pin view of function 2 is not: its `pin_function` is what counts."""
    # UNDO: stages/exempt.py `open_ends`: `(spec.pin_function or spec.function) in edges` ->
    #   `spec.function in edges` (function 3 is dropped, function 1 kept)
    specs = (_spec(1, pin_of=2), _spec(2), _spec(3, pin_of=1))
    assert open_ends(specs, frozenset({hid("function", 1)})) == {hid("function", 3)}
