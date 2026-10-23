"""Field case: a wire that ends in a boxed connector's table runs inside no other table.

The engineering shape: a board with plugs stacked on headers (a plug over its header is two
rectangles, the table), a pin-cell row under them, and contactors wired to the cells.

The bug: the router's retry opened every connector rectangle, so a wire to a cell also ran
through the table of the plug above its own (layout-0209, extending layout-0158). The route keeps
every table blocked first and opens every table only as the last resort. A wire still runs down
through its own table's text rows to its cell: the drawing convention, not the router. Layout-0211
turned the cells to face their device and the line out of the other edge: no foreign hit is left,
and the own hits left are one box on two overfull pages whose coil stands against or over it.

The ratchet counts, over six builds, the route segments that run inside or along a table
rectangle, by whether the wire ends in that table (own) or not (foreign). The counts may only
fall: lower them when they do.

The two shape tests (layout-0211) read every celled box with a plug on the six builds' pages:
its cells face the wires to its own device, and the harness line leaves from the other edge.
One shape has the line's far end elsewhere; in the other it lies on the device's side, and the
one line turns around the table.
"""

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from _drawn_pages import drawn_pages

if TYPE_CHECKING:
    from fransys_layout.drawing import DrawnWire

_HERE = Path(__file__).parent


def _module(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _HERE / f"{name}.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _builds() -> list[Any]:
    table = _module("test_a_contact_table_under_the_lowest_cell_stays_in_the_content_box")
    overfull = _module("test_a_harness_line_on_an_overfull_page_still_routes")
    return [
        table._built(),
        table._built_with_lugs(),
        table._built_with_lugs(1, low=True),
        overfull._built(1),
        overfull._built(2, 0, 2, looms=False),
        overfull._built(2, 0, 6, looms=False),
    ]


@pytest.fixture(scope="module")
def results() -> list[list[DrawnWire]]:
    """The six builds' drawn wires, read once for the module's tests."""
    return [
        [w for drawing in drawn_pages(built.model).values() for w in drawing.wires]
        for built in _builds()
    ]


# The core writes no ConnectorBox, Route or HarnessLine: a table rectangle, a cell row, a plug and a
# harness line are not readable from a built model, so the three claims below read the drawn wires
# and stop at the first fact they cannot read.
def test_table_runs_only_fall(results: list[list[DrawnWire]]) -> None:
    assert all(wires for wires in results)
    unreadable = "not readable on the core: the table rectangles, to count own and foreign runs"
    raise AssertionError(unreadable)


def test_a_line_whose_far_end_lies_elsewhere_leaves_the_edge_away_from_the_cells(
    results: list[list[DrawnWire]],
) -> None:
    assert all(wires for wires in results)
    unreadable = "not readable on the core: a celled box, its plug and the harness line's edge"
    raise AssertionError(unreadable)


def test_a_line_whose_far_end_lies_on_the_device_side_turns_around_the_table_as_one_line(
    results: list[list[DrawnWire]],
) -> None:
    assert all(wires for wires in results)
    unreadable = "not readable on the core: a celled box, its plug and the harness line's far end"
    raise AssertionError(unreadable)
