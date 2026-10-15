"""The router meter of ROUTE-METER (layout-0253): counts what the schematic router does per build.

`metered()` wraps the router's `_search`, `_draw` and `route` for the length of a `with` block and
returns a `Counter`. It reads results only and changes none: a build under it is byte-identical.
"""

import importlib
from collections import Counter
from contextlib import contextmanager
from itertools import pairwise
from typing import TYPE_CHECKING, Any

from fransys_layout.lint._segments import runs_of
from fransys_layout.lint.page_counts import wire_crossings
from fransys_layout.stages import lookups, onepage, pagerun
from fransys_layout.stages.space import runs_along

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

_route = importlib.import_module("fransys_layout.stages._edge_paths")
engine = importlib.import_module("fransys_layout.engines.schematic.engine")


def _dirs(points: Sequence[Any]) -> list[tuple[int, int]]:
    return [((b.x > a.x) - (b.x < a.x), (b.y > a.y) - (b.y < a.y)) for a, b in pairwise(points)]


def _uturns(points: Sequence[Any]) -> int:
    """Three segments whose first and third run opposite ways."""
    d = _dirs(points)
    return sum(
        1
        for d1, d2, d3 in zip(d, d[1:], d[2:], strict=False)
        if d1 != d2 and d1 == (-d3[0], -d3[1])
    )


def _stage(log: list[tuple[bool, int, bool]], *, with_exits: bool) -> str:
    """The retry that first found a path: strict, soft_open (layout-0209), exits_open (0223)."""
    base = log[0][1]
    for exits_none, shapes, ok in log:
        if ok:
            if exits_none and with_exits:
                return "exits_open"
            return "soft_open" if shapes < base else "strict"
    return "failed"


def _along_outline(routes: Sequence[Any], placed: Any, drawn: Any) -> int:
    fn_of = {port.port: one.function for one in drawn for port in one.ports}
    boxes = [(one.function, lookups.placed_keepout(one)) for one in placed]
    count = 0
    for r in routes:
        own = {fn_of.get(r.a), fn_of.get(r.b)}
        if any(
            owner not in own and runs_along(box, run) for owner, box in boxes for run in runs_of(r)
        ):
            count += 1
    return count


def _crossings(
    counts: Counter[str], routes: Sequence[Any], lines: Sequence[Any], fans: Sequence[Any]
) -> None:
    """Add each page's crossings, and those of its core lines and legs apart (layout-0260)."""
    cables = [*lines, *fans]
    pages = {(r.drawing_set, r.page) for r in routes} | {(c.drawing_set, c.page) for c in cables}
    for page in pages:
        here = [r for r in routes if (r.drawing_set, r.page) == page]
        on = [[c for c in group if (c.drawing_set, c.page) == page] for group in (lines, fans)]
        both = wire_crossings(here, *on)
        counts["crossings"] += both
        counts["core_crossings"] += both - wire_crossings(here)


@contextmanager
def metered() -> Iterator[Counter[str]]:
    """Count every route, retry, crossing, bend and search of the builds run inside the block."""
    counts: Counter[str] = Counter()
    log: list[tuple[bool, int, bool]] = []
    search, draw, route = _route._search, _route._draw, pagerun.route
    chosen, draw_lines = onepage.keep_chosen_edges, engine.draw_lines
    final: list[Any] = []

    def _search(edge: Any, page: Any, used: Any, along: Any = None, port_exits: Any = None) -> Any:
        found = search(edge, page, used, along, port_exits)
        log.append((port_exits is None, len(page.space.shapes), found is not None))
        counts["search_calls"] += 1
        return found

    def _draw(edge: Any, page: Any, used: Any, along: Any = None, port_exits: Any = None) -> Any:
        del log[:]
        found = draw(edge, page, used, along, port_exits)
        if log:
            counts[f"draw_{_stage(log, with_exits=port_exits is not None)}"] += 1
            first = next((i for i, one in enumerate(log) if one[2]), None)
            if first is not None and len(log) > first + 1:
                counts["wrap_search"] += 1
                counts["wrap_improved"] += log[-1][2]
        return found

    def _route_page(connections: Any, net_groups: Any, placed: Any, drawn: Any, room: Any) -> Any:
        routes, findings = route(connections, net_groups, placed, drawn, room)
        counts["pages"] += 1
        counts["routes"] += len(routes)
        counts["route_failed"] += len(findings)
        counts["bends"] += sum(max(0, len(r.points) - 2) for r in routes)
        counts["uturns"] += sum(_uturns([p.at for p in r.points]) for r in routes)
        counts["along_outline"] += _along_outline(routes, placed, drawn)
        return routes, findings

    def _chosen(*args: Any, **kwargs: Any) -> Any:
        """Keep the page's final routes, which the harness lines are drawn over (layout-0258)."""
        final[:] = chosen(*args, **kwargs)
        return final

    def _draw_lines(*args: Any, **kwargs: Any) -> Any:
        found = draw_lines(*args, **kwargs)
        _crossings(counts, final, found.lines, found.fan_outs)
        return found

    patches = (
        (_route, "_search", _search),
        (_route, "_draw", _draw),
        (pagerun, "route", _route_page),
        (onepage, "keep_chosen_edges", _chosen),
        (engine, "draw_lines", _draw_lines),
    )
    saved = [(mod, name, getattr(mod, name)) for mod, name, _ in patches]
    for mod, name, fn in patches:
        setattr(mod, name, fn)
    try:
        yield counts
    finally:
        for mod, name, fn in saved:
            setattr(mod, name, fn)
