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
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

import pytest
from fransys_el import OPTIONS

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.stages.box_views import NEAR
from fransys_layout.stages.space import Run, crosses, runs_along

if TYPE_CHECKING:
    from fransys_layout.geometry import Box

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
def results() -> list[Any]:
    """The six builds' stage results, built once for the module's tests."""
    return [
        stage_results(built.model, read_inputs(built.model, options=OPTIONS))[0]
        for built in _builds()
    ]


def _runs(points: list[tuple[int, int]]) -> list[Run]:
    return [
        Run(x=min(x0, x1), y=min(y0, y1), to_x=max(x0, x1), to_y=max(y0, y1))
        for (x0, y0), (x1, y1) in pairwise(points)
    ]


def _inside(box: Box, x: int, y: int) -> bool:
    return box.x <= x <= box.x + box.width and box.y <= y <= box.y + box.height


def _table_runs(results: Any) -> tuple[int, int]:
    """(own, foreign): route segments inside or along a table rectangle, by wire end."""
    own = foreign = 0
    for route in results.layout.routes:
        points = [(p.at.x, p.at.y) for p in route.points]
        for table in results.boxes:
            if (table.drawing_set, table.page) != (route.drawing_set, route.page):
                continue
            mine = any(_inside(table.box, x, y) for x, y in (points[0], points[-1]))
            for run in _runs(points):
                if crosses(table.box, run) or runs_along(table.box, run):
                    own, foreign = own + mine, foreign + (not mine)
    return own, foreign


# Measured at layout-0211 (layout-0209: 28 and 18). The 10 own hits are -U1-Q1-J1 on the two
# PAGE_OVERFULL builds, its coil against or over the box (ruled to stay, CONNECTOR-FACE).
# Lower a count when a change takes hits away; never raise one.
# 11 since the near-edge guard (layout-0211, designer 2026-10-14): -U1-Q1-J1 of the overfull build
# (2, 0, 2) is on a PAGE_OVERFULL page where no facing leaves room: its cells keep the pins' edge.
OWN_MAX = 11
FOREIGN_MAX = 0


def test_table_runs_only_fall(results: list[Any]) -> None:
    counts = [_table_runs(one) for one in results]
    own, foreign = sum(c[0] for c in counts), sum(c[1] for c in counts)
    assert own <= OWN_MAX, counts
    assert foreign <= FOREIGN_MAX, counts


class _Stack(NamedTuple):
    """One celled box with its plug on one page: the leads' and the line's points."""

    where: str
    box: Box
    plug: Box
    cells_on_top: bool
    leads: list[list[tuple[int, int]]]
    line: list[tuple[int, int]]
    far: list[tuple[int, int]]


def _plug(results: Any, table: Any) -> Box | None:
    """The cell-less box touching `table` face to face on its page, if any."""
    box = table.box
    for other in results.boxes:
        b = other.box
        if (other.drawing_set, other.page) != (table.drawing_set, table.page) or other.cells:
            continue
        if (
            b.x < box.x + box.width
            and box.x < b.x + b.width
            and box.y in (b.y + b.height, b.y - box.height)
        ):
            return b
    return None


def _line_from(results: Any, table: Any, plug: Box) -> tuple[Any, list[tuple[int, int]]] | None:
    """The line polyline with one end on the plug and not on the table, that end first."""
    for line in results.lines.lines:
        if (line.drawing_set, line.page) != (table.drawing_set, table.page):
            continue
        points = [(p.x, p.y) for p in line.points]
        for one in (points, points[::-1]):
            if _inside(plug, *one[0]) and not _inside(table.box, *one[0]):
                return line.harness, one
    return None


def _far_ends(results: Any, table: Any, harness: Any, plug: Box) -> list[tuple[int, int]]:
    """The line's ends on the page but the plug's: polyline ends no other polyline shares."""
    ends: list[tuple[int, int]] = []
    for line in results.lines.lines:
        if (line.harness, line.drawing_set, line.page) == (harness, table.drawing_set, table.page):
            ends.extend((p.x, p.y) for p in (line.points[0], line.points[-1]))
    return [one for one in ends if ends.count(one) == 1 and not _inside(plug, *one)]


def _stacks(results: Any, n: int) -> list[_Stack]:
    found = []
    for table in (one for one in results.boxes if one.cells):
        plug = _plug(results, table)
        line = None if plug is None else _line_from(results, table, plug)
        if plug is None or line is None:
            continue
        top = table.cells[0].box.y == table.box.y
        where = f"build {n} page {table.drawing_set},{table.page}"
        far = _far_ends(results, table, line[0], plug)
        found.append(_Stack(where, table.box, plug, top, _leads(results, table), line[1], far))
    return found


def _leads(results: Any, table: Any) -> list[list[tuple[int, int]]]:
    """Each route with an end in `table` on its page, that end first."""
    found = []
    for route in results.layout.routes:
        if (route.drawing_set, route.page) != (table.drawing_set, table.page):
            continue
        points = [(p.at.x, p.at.y) for p in route.points]
        if _inside(table.box, *points[-1]):
            points.reverse()
        if _inside(table.box, *points[0]):
            found.append(points)
    return found


def _middle(box: Box) -> int:
    return box.y + box.height // 2


def _device_below(one: _Stack) -> bool:
    """Whether the leads' far ends lie below the table, by count."""
    middle = _middle(one.box)
    below = sum(lead[-1][1] > middle for lead in one.leads)
    return below > sum(lead[-1][1] < middle for lead in one.leads)


def _turns(one: _Stack) -> bool:
    """Whether a far end of the line lies beyond the table on the device's side."""
    if _device_below(one):
        return any(y > one.box.y + one.box.height for _, y in one.far)
    return any(y < one.box.y for _, y in one.far)


def _touches(box: Box, points: list[tuple[int, int]]) -> bool:
    return any(crosses(box, run) or runs_along(box, run) for run in _runs(points))


def _check(one: _Stack) -> None:
    """Cells face the leads; no lead or line runs in the table; the line leaves the far edge."""
    assert one.cells_on_top is not _device_below(one), one.where
    for lead in one.leads:
        assert not _touches(one.box, lead), (one.where, lead)
        assert not _touches(one.plug, lead), (one.where, lead)
    assert not _touches(one.box, one.line), (one.where, one.line)
    assert not _touches(one.plug, one.line), (one.where, one.line)
    edge = one.plug.y + one.plug.height if one.cells_on_top else one.plug.y
    assert one.line[0][1] == edge, (one.where, one.line)


def _against(one: _Stack) -> bool:
    """Whether a lead ends on, in or within `NEAR` of its table: a symbol stands against it.

    Only the overfull builds have one (a coil on -U1-Q1-J1); no cells edge leaves room, and the
    rule keeps the pins' edge there (ruled to stay, CONNECTOR-FACE, near-edge case 2026-10-14).
    """
    box = one.box
    return any(box.y - NEAR <= lead[-1][1] <= box.y + box.height + NEAR for lead in one.leads)


def _shape(results: list[Any], *, turns: bool) -> list[_Stack]:
    stacks = [one for n, built in enumerate(results) for one in _stacks(built, n)]
    found = [one for one in stacks if one.leads and not _against(one) and _turns(one) is turns]
    assert found, "the six builds hold no page of this shape"
    return found


def test_a_line_whose_far_end_lies_elsewhere_leaves_the_edge_away_from_the_cells(
    results: list[Any],
) -> None:
    for one in _shape(results, turns=False):
        _check(one)


def test_a_line_whose_far_end_lies_on_the_device_side_turns_around_the_table_as_one_line(
    results: list[Any],
) -> None:
    for one in _shape(results, turns=True):
        _check(one)
