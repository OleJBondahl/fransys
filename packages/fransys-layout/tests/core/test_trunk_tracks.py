"""ROUTING (R391, R396): trunks of different nets never share a track, ends included.

A box's pins drive fans whose columns wrap into later rows. Each later row's trunk reaches back
to its box pin, so stage 5 must level the trunk over the span it draws, box pin included.
"""

from __future__ import annotations

from itertools import combinations, pairwise
from typing import TYPE_CHECKING

import pytest

from fransys_layout.core.values import Size

from .blocks_fixtures import box_sym
from .flow_builders import free, net, problem
from .pipeline_fixtures import solved_of

if TYPE_CHECKING:
    from fransys_layout.core.outputs import Routes, Wire
    from fransys_layout.core.values import PlacementProblem

XY = tuple[int, int]


def wrapped_box_fans(fans: int = 10, width: int = 300) -> PlacementProblem:
    """Box K drives fan t<i> to A<i> and B<i>; the narrow area wraps the columns into rows."""
    syms = [box_sym("K", "PLC", fans)]
    nets = []
    for i in range(1, fans + 1):
        syms += [free(f"A{i}", group=f"G{i}"), free(f"B{i}", group=f"G{i}")]
        nets.append(net(f"t{i}", f"K.p{i}", f"A{i}.e", f"B{i}.e"))
    return problem(syms, nets, area=Size(width, 854))


def _runs(w: Wire) -> list[tuple[int, int, int]]:
    """(y, x0, x1) of each horizontal run of a wire."""
    return [(a[1], min(a[0], b[0]), max(a[0], b[0])) for a, b in pairwise(w.points) if a[1] == b[1]]


def trunk_touches(routes: Routes) -> list[tuple[str, str, int]]:
    """(net, net, y) for horizontal runs of trunks of different nets that share a point."""
    out = []
    for page in routes.pages:
        trunks = [w for w in page.wires if w.kind == "trunk"]
        for v, w in combinations(trunks, 2):
            out.extend(
                (v.net, w.net, y)
                for y, a0, a1 in _runs(v)
                for z, b0, b1 in _runs(w)
                if v.net != w.net and y == z and max(a0, b0) <= min(a1, b1)
            )
    return out


@pytest.mark.rule("ROUTING")
@pytest.mark.parametrize(("fans", "width"), [(10, 300), (12, 340)])
def test_trunks_of_different_nets_never_share_a_track(fans: int, width: int) -> None:
    """Whole class: every pair of trunks on a page, wrapped rows and box-pin spans included."""
    layout = solved_of(wrapped_box_fans(fans, width))
    trunks = [w for p in layout.routes.pages for w in p.wires if w.kind == "trunk"]
    assert len({w.net for w in trunks}) >= fans  # every fan draws a trunk line
    assert trunk_touches(layout.routes) == []
