"""`lint.coherence`: two physical nets touching on a page (`ROUTE_SHORTS_NETS`).

The routes are hand-made and need not end at their ports; only each claim (connection, a, b)
must be valid. The functions stand far off, so no route lies on a placed port and only the
touching half of the check can fire. Every case has a near-identical twin that must stay silent.
"""

import dataclasses

import pytest
from coherence_helpers import NO_UNITS, layout_of, port, subjects, wire
from samples import connection, drawn, hid, placed

from fransys_layout.lint import check_coherence
from fransys_layout.lint._harness import NO_INK
from fransys_layout.lint.codes import ROUTE_SHORTS_NETS
from fransys_layout.lint.naming import (
    Where,
    _groups_on,
    _pages_of,
    append_pages_and_designations,
)
from fransys_model.derive.drawing_text import position_text

FAR = tuple(placed(n, x=2000, y=2000 + 100 * n, name="b") for n in range(1, 7))
FAR_DRAWN = tuple(drawn(n) for n in range(1, 7))
CONNECTIONS = (connection(1, 1, 2), connection(2, 3, 4), connection(3, 5, 6))  # nets 1, 2, 3

CROSS_A = ((104, 112), (104, 288))  # vertical
CROSS_B = ((48, 200), (304, 200))  # horizontal, crossing CROSS_A at (104, 200)


def _route(number, points, *, page=1, drawing_set=1):
    """Conductor `number`'s route: a valid claim (ports `20n - 8` and `20n + 1`), any points."""
    route = wire(number, points, a=20 * number - 8, b=20 * number + 1, page=page)
    return dataclasses.replace(route, drawing_set=drawing_set)


def _who(*numbers):
    """The subjects of a finding about the routes of conductors `numbers`."""
    return subjects(
        *(h for n in numbers for h in (hid("conductor", n), port(20 * n - 8), port(20 * n + 1)))
    )


def _at(x, y, *, page=1, drawing_set=1):
    """The message of a touch at `(x, y)` on a page, in `position_text`'s form."""
    where = position_text(page, None, None, (), drawing_set)
    return f"two physical nets touch at ({x}, {y}) ({where})"


def _all(routes, *, connections=CONNECTIONS, net_groups=()):
    layout = layout_of(routes=routes, functions=FAR)
    findings = check_coherence(layout, connections, net_groups, FAR_DRAWN, function_units=NO_UNITS)
    touches = [one for one in findings if one.code == ROUTE_SHORTS_NETS]
    # the page and drawing set come from the engine's last pass, as the user reads them
    where = Where(pages=_pages_of(layout, (), NO_INK), groups=_groups_on(layout), labels={})
    return list(append_pages_and_designations({}, where, touches))


def _touches(routes, **kwargs):
    """The `ROUTE_SHORTS_NETS` findings of `routes` as `(subjects, message)`, in check order."""
    return [(one.subjects, one.message) for one in _all(routes, **kwargs)]


def _between(a, b, cell, *, page=1, drawing_set=1):
    """What nets 1 and 2 drawn as `a` and `b` yield, in either route order; `cell` None: silent."""
    routes = (
        _route(1, a, page=page, drawing_set=drawing_set),
        _route(2, b, page=page, drawing_set=drawing_set),
    )
    expected = (
        [] if cell is None else [(_who(1, 2), _at(*cell, page=page, drawing_set=drawing_set))]
    )
    assert _touches(routes) == expected
    assert _touches(routes[::-1]) == expected


SAME_NET = (
    CONNECTIONS[0],
    dataclasses.replace(CONNECTIONS[1], physical_net=hid("net", 1)),
    CONNECTIONS[2],
)


@pytest.mark.parametrize(
    ("page", "drawing_set", "a", "b", "cell"),
    [
        (2, 3, CROSS_A, ((104, 200), (104, 400)), (104, 200)),  # a shared segment
        (4, 2, ((104, 112), (104, 200), (200, 200)), CROSS_B, (104, 200)),  # a corner
        (
            1,
            1,
            ((104, 288), (104, 120), (304, 120), (304, 200)),
            ((104, 288), (304, 288), (304, 200)),
            (104, 288),  # touching at (104, 288) and (304, 200): the smaller in (x, y) order
        ),
    ],
    ids=["shared segment", "corner", "two cells"],
)
def test_the_message_names_page_drawing_set_and_the_smallest_touched_cell(
    page, drawing_set, a, b, cell
) -> None:
    """The touch point is the smallest cell in `(x, y)` order, not in `(y, x)` order."""
    _between(a, b, cell, page=page, drawing_set=drawing_set)


TRIANGLE = (
    _route(1, ((104, 112), (104, 288))),
    _route(2, ((104, 200), (304, 200))),  # ends on 1's wire, and on 3's end
    _route(3, ((104, 112), (304, 112), (304, 200))),  # starts on 1's end
)
