"""Field case: a branch in parallel with a contactor draws beside it, not through markers.

The engineering shape: one unit holds a two-rail DC path, a chain per rail (strip, 2-pole switch,
fuse, contactor pole, strip). A branch of a resistor, a contactor pole and a fuse leaves the first
fuse's output, which is the first contactor's input, and rejoins at that contactor's output. The
branch has its own chain, authored resistor first, as it reads along the current.

The bug: the branch draws in a column of its own at the page top, so its two shared nets become
reference markers (`#n`) instead of short horizontal wires to the contactor's column. An authored
chain turned only terminals, and a join aligned only the ends of columns. Fixed by `beside=` on
`d.layout.chain` (decision layout-0174): the branch stands beside its host's column.
"""

import re
import tempfile
from itertools import pairwise
from pathlib import Path
from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from fransys_el import OPTIONS

from fransys_layout.engines.schematic.engine import stage_results
from fransys_layout.engines.schematic.read import read_inputs
from fransys_layout.stages.lookups import placed_keepout
from fransys_model.layout import Route, layout_of
from fransys_model.vocab.tables import functions

if TYPE_CHECKING:
    from fransys_layout.geometry import Box

_UNIT: dict[str, Any] = {
    "revision": 1,
    "interface_version": 1,
    "date": "2026-01-01",
    "text": "first",
    "by": "AB",
}
_RED, _BLACK = ("RD", 50), ("BK", 50)


class _Strips(NamedTuple):
    X1: Any


@fr.unit("demo-dc", **_UNIT)
def _dc(d: Any) -> _Strips:
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True)
    x2 = d.terminal_strip("X2", "DEMO-TB-2.5", 2, interface=True)
    with d.function("DC", "DC path"):
        s1 = d.device("S1", "DEMO-MCB-2P")
        f1, f2, f3 = (d.device(n, "DEMO-FUSE-DC-160") for n in ("F1", "F2", "F3"))
        k1, k2, k3 = (d.device(n, "DEMO-CTR-3P-24") for n in ("K1", "K2", "K3"))
        r1 = d.device("R1", "DEMO-LAMP-24")
        for a, b, wire in (
            (x1[1], s1.pole_1["1"], _RED),
            (s1.pole_1["2"], f1.element["1"], _RED),
            (f1.element["2"], k1.main["1"], _RED),
            (k1.main["2"], x2[1], _RED),
            (x1[2], s1.pole_2["3"], _BLACK),
            (s1.pole_2["4"], f2.element["1"], _BLACK),
            (f2.element["2"], k2.main["1"], _BLACK),
            (k2.main["2"], x2[2], _BLACK),
            (k1.main["2"], r1["1"], _RED),
            (r1["2"], k3.main["1"], _RED),
            (k3.main["2"], f3.element["1"], _RED),
            (f3.element["2"], f1.element["2"], _RED),
        ):
            d.wire(a, b, wire=wire)
    d.layout.chain(x1[1], s1.pole_1, f1.element, k1.main, x2[1])
    d.layout.chain(x1[2], s1.pole_2, f2.element, k2.main, x2[2])
    d.layout.chain(r1.lamp, k3.main, f3.element, beside=k1.main)
    return _Strips(x1)


def _build() -> tuple[fr.BuildResult, list[str]]:
    d = fr.design("demo_parts")
    d.add(_dc, "U1")
    root = Path(tempfile.mkdtemp())
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    cover = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-dc", cover=root / "c.md")
    result = fr.build(d, cover)
    fr.write(result, root / "out", intermediates=root / "inter")
    pages = [svg.read_text("utf-8") for svg in sorted((root / "inter").glob("layout.page-*.svg"))]
    return result, pages


def test_a_precharge_branch_draws_beside_its_contactor() -> None:
    result, pages = _build()
    codes = {finding.code for finding in result.findings}
    assert not codes & {"CHAIN_BROKEN", "FUNCTION_UNPLACED_IN_COLUMN"}
    (dc_page,) = (page for page in pages if "-R1" in page and "-K1" in page)
    assert re.findall(r">(#\d+-[0-9A-Z]+)</text>", dc_page) == []


_GRID = 16  # the wiring grid: a join leaves a crowded host pin by one grid


def _points(result: fr.BuildResult, branch: str, host: str) -> list[tuple[int, int]]:
    """The one route whose key names `branch` and `host`, as (x, y) points."""
    routes = [r for r in layout_of(result.model, Route).values() if branch in "/".join(r.key)]
    (wire,) = (r for r in routes if host in "/".join(r.key))
    return [(p.x, p.y) for p in wire.points]


def test_the_branch_fuse_joins_the_host_fuse_by_one_straight_horizontal() -> None:
    result, _ = _build()
    points = _points(result, "F3", "F1")
    assert len(points) == 2
    assert points[0][1] == points[1][1]
    assert points[0][0] != points[1][0]


def test_a_join_leaves_a_multi_pole_host_pin_before_it_turns_to_the_branch() -> None:
    """K1's other poles end on the pin's row: a level join would run through their pin ends."""
    result, _ = _build()
    points = _points(result, "R1/2:fn/4:lamp/4:port/1:1", "K1")
    host, first, second, branch = points if points[0][0] == points[1][0] else points[::-1]
    assert len(points) == 4
    assert host[0] == first[0], "it leaves the pin along the pin's own direction"
    assert abs(first[1] - host[1]) >= _GRID, "by at least one grid"
    assert first[1] == second[1], "then runs level"
    assert second[0] == branch[0], (
        "and enters the branch's box pin square to its edge (JOIN-VERTICAL)"
    )


def test_no_beside_join_runs_through_a_symbol_or_a_label() -> None:
    result, _ = _build()
    codes = {finding.code for finding in fr.check(result)}
    assert not codes & {"WIRE_THROUGH_SYMBOL", "WIRE_OVER_LABEL"}


def _host_keepout(result: fr.BuildResult) -> Box:
    """K1's main function keep-out on its page, from the one keep-out function."""
    layout = stage_results(result.model, read_inputs(result.model, options=OPTIONS))[0].layout
    (host,) = (
        f.id for f in functions(result.model).values() if "/".join(f.key).endswith("K1/fn/main")
    )
    (one,) = (p for p in layout.placed if p.function == host)
    return placed_keepout(one)


def test_no_beside_join_segment_meets_the_host_keepout_except_at_its_pin() -> None:
    """A join that touches the host's keep-out anywhere but its pin end crosses the host's ink."""
    result, _ = _build()
    keep = _host_keepout(result)
    points = _points(result, "R1/2:fn/4:lamp/4:port/1:1", "K1")
    pin = next(p for p in points if p[1] == keep.y + keep.height)
    for (ax, ay), (bx, by) in pairwise(points):
        x0, x1 = max(min(ax, bx), keep.x), min(max(ax, bx), keep.x + keep.width)
        y0, y1 = max(min(ay, by), keep.y), min(max(ay, by), keep.y + keep.height)
        meets = x0 <= x1 and y0 <= y1
        assert not meets or (x0, y0, x1, y1) == (*pin, *pin)
