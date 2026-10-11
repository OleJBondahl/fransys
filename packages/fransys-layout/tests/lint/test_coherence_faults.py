"""`lint.coherence`: assembly faults raise, findings do not depend on input order (lint.md 6.8).

Each raise has a twin that must not raise.
"""

import dataclasses

import pytest
from coherence_helpers import (
    DRAWN,
    NO_UNITS,
    PLACED,
    decision,
    edge,
    group,
    layout_of,
    marker,
    named,
    port,
    subjects,
    wire,
)
from samples import connection, drawn, hid, placed

from fransys_layout.geometry import LayoutError
from fransys_layout.lint import check_coherence
from fransys_layout.lint.codes import (
    ALL_CODES,
    CONNECTION_NOT_DRAWN,
    ROUTE_WRONG_PORT,
)
from fransys_layout.stages import DrawnPort, LinkCase, MarkerSide, PortRef
from fransys_model.kernel import Severity

GOOD = ((104, 112), (104, 288))
C1 = connection(1, 1, 2)
NOT_DRAWN_3 = [(CONNECTION_NOT_DRAWN, (hid("conductor", 3),))]


GOOD_ROUTES = (wire(1, GOOD),)


def _check(*, routes=GOOD_ROUTES, functions=PLACED, connections=(C1,), functions_drawn=DRAWN):
    layout = layout_of(routes=routes, functions=functions)
    return named(check_coherence(layout, connections, (), functions_drawn, function_units=NO_UNITS))


def test_a_function_placed_twice_on_one_page_raises() -> None:
    """A function placed twice on one page raises."""
    with pytest.raises(LayoutError, match="placed twice"):
        _check(functions=(*PLACED, placed(1, x=104, y=96)))
    assert _check(functions=(*PLACED, placed(1, x=104, y=96, page=2))) == []


def test_a_route_with_one_point_raises() -> None:
    """A route with one point raises."""
    with pytest.raises(LayoutError, match="fewer than two points"):
        _check(routes=(wire(1, ((104, 112),)),))
    assert _check(routes=(wire(1, ((104, 112), (104, 112))),)) == [
        (ROUTE_WRONG_PORT, subjects(hid("conductor", 1), port(12), port(21)))
    ]


def test_a_named_ports_symbol_port_must_be_a_port_of_the_placed_geometry() -> None:
    """A named ports symbol port must be a port of the placed geometry."""
    nowhere = dataclasses.replace(
        drawn(1), ports=(drawn(1).ports[0], DrawnPort(port=port(12), symbol_port="nowhere"))
    )
    with pytest.raises(LayoutError, match="not a port of the symbol"):
        _check(functions_drawn=(nowhere, drawn(2), drawn(3)))
    unnamed = dataclasses.replace(
        drawn(1), ports=(DrawnPort(port=port(11), symbol_port="nowhere"), drawn(1).ports[1])
    )
    assert _check(functions_drawn=(unnamed, drawn(2), drawn(3))) == []


def test_a_port_named_with_two_functions_is_a_boundary_port() -> None:
    """A port named by a function and a pin cell (model-0188) is located per function."""
    elsewhere = dataclasses.replace(
        C1, handle=hid("conductor", 3), a=PortRef(function=hid("function", 9), port=port(12))
    )
    assert _check(connections=(C1, elsewhere)) == NOT_DRAWN_3
    other_net = dataclasses.replace(elsewhere, physical_net=hid("net", 3))
    with pytest.raises(LayoutError, match="two different physical nets"):
        _check(connections=(C1, other_net, elsewhere))


# --- order, severity ------------------------------------------------------------------

FANS = (
    placed(1, x=104, y=96, page=1),
    placed(2, x=104, y=304, page=1),
    placed(3, x=304, y=96, page=1, name="b"),
    placed(4, x=304, y=304, page=1, name="b"),
    placed(5, x=504, y=96, page=1, name="c"),
    placed(6, x=504, y=304, page=2, name="c"),
)
CONNECTIONS = (connection(1, 1, 2), connection(2, 3, 4), connection(3, 5, 6))
GROUPS = (group(7, ((1, 11), (2, 22), (3, 31))),)
ROUTES = (
    wire(1, ((304, 112), (304, 288)), a=12, b=21),  # drawn between the other fan's ports
    wire(2, ((104, 112), (104, 288)), a=32, b=41),
    edge(7, 11, 22, ((104, 80), (104, 320))),
    edge(7, 11, 22, ((104, 80), (104, 320))),  # drawn twice
    wire(9, GOOD),  # claims a conductor nobody gave
)
DECISIONS = (decision(hid("conductor", 3), 52, 61, LinkCase.SEVERED),)
MARKERS = (marker(hid("conductor", 3), 52, MarkerSide.OWNER, page=1, at=(504, 112)),)
EVERYTHING = (
    ROUTES,
    DECISIONS,
    MARKERS,
    FANS,
    CONNECTIONS,
    GROUPS,
    tuple(drawn(n) for n in range(1, 7)),
)


def _run(*arguments):
    routes, decisions, markers, functions, connections, groups, functions_drawn = arguments
    layout = layout_of(routes=routes, decisions=decisions, markers=markers, functions=functions)
    return check_coherence(layout, connections, groups, functions_drawn, function_units=NO_UNITS)


def _reorderings(items):
    """The tuple, reversed, and each rotation of it."""
    yield items[::-1]
    for start in range(1, len(items)):
        yield items[start:] + items[:start]


def test_every_finding_is_an_error_with_a_message_and_a_listed_code() -> None:
    """Every finding is an error with a message and a listed code."""
    findings = _run(*EVERYTHING)
    assert findings == tuple(sorted(findings, key=lambda one: (one.code, one.subjects)))
    for one in findings:
        assert one.severity is Severity.ERROR
        assert one.code in ALL_CODES
        assert one.message
