"""LC1 (layout-0215): a tall column cut between its rows, through the public API.

The engineering shape is the field case's single series of 18 fuses between two terminals, built
from `demo_parts` as `tests/field_cases/test_a_long_chain_in_one_block_keeps_its_order.py` builds
it. The fuse column runs taller than one page, so it is cut between its rows: the fuses stay in
reading order on the sheets, the conductor across a cut is a marker pair and the rest are routes.
"""

import pathlib
import re
import tempfile
from collections import defaultdict
from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import RD

from fransys_model.derive import net_of

_N = 18
_FUSE = re.compile(r"^G\d+$")


class _Cab(NamedTuple):
    pass


def _document(name: str) -> fr.Draft:
    cover = pathlib.Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# cover\n", encoding="utf-8")
    return fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, name, cover=cover)


def _series_result(n: int, tap: tuple[int, int] | None = None) -> fr.BuildResult:
    """The series of `n` fuses; `tap` = (i, j) also wires fuse i's pin 2 to fuse j's pin 1."""

    @fr.unit("chain-b", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
    def series_unit(d):
        with d.function("B1", "Block"):
            strip = d.terminal_strip("X1", "DEMO-TB-2.5")
            run_a, run_b = strip.run("A", 1), strip.run("B", 1)
            _ = run_a[1], run_b[1]
            fuses = [d.device(f"G{i}", "DEMO-FUSE-DC-160") for i in range(1, n + 1)]
        d.series(*[f.element for f in fuses], wire=(RD, 1.0))
        d.detail.wire(run_a[1], fuses[0].element["1"], wire=(RD, 1.0))
        d.detail.wire(fuses[-1].element["2"], run_b[1], wire=(RD, 1.0))
        if tap is not None:
            d.detail.wire(
                fuses[tap[0] - 1].element["2"], fuses[tap[1] - 1].element["1"], wire=(RD, 1.0)
            )
        return _Cab()

    d = fr.design("demo_parts")
    d.add(series_unit, "U1")
    return fr.build(d, _document("chain-b"))


@pytest.fixture(scope="module")
def series() -> fr.BuildResult:
    return _series_result(_N)


@pytest.fixture(scope="module")
def placed(series) -> list[tuple[int, int, int, str]]:
    """Each fuse placement as (page number, x, y, tag), read off the drawn pages."""
    return _drawn_fuses(series)


def _port_tags(model) -> dict[str, str]:
    """Each port's value to its item's tag: a drawn symbol names its ports by value."""
    tables: Any = model.tables
    return {
        pid.value: tables["item"][tables["function"][p.function].item].tag
        for pid, p in tables["port"].items()
    }


def _drawn_fuses(result) -> list[tuple[int, int, int, str]]:
    """Each fuse symbol the core drew as (page number, x, y, tag); markers are not fuses."""
    tables: Any = result.model.tables
    number = {pid: p.number for pid, p in tables["layout.page"].items()}
    tags = _port_tags(result.model)
    return [
        (number[pid], s.x, s.y, tags[s.ports[0]])
        for pid, drawing in result.drawings.items()
        for s in drawing.symbols
        if s.key == "fuse"
    ]


def _marks_and_routes(result) -> tuple[dict[str, list], set[str]]:
    """The drawn markers by the port value they stand at, and the nets the wires draw."""
    drawings = list(result.drawings.values())
    markers: dict[str, list] = defaultdict(list)
    for d in drawings:
        for s in d.symbols:
            if s.key.startswith("marker"):
                markers[s.ports[0]].append(s)
    return markers, {w.net for d in drawings for w in d.wires}


def test_the_series_fits_the_sheets_without_overflow(series) -> None:
    codes = [f.code for f in fr.check(series)]
    assert "OUT_OF_CONTENT_BOX" not in codes
    assert "PAGE_OVERFULL" not in codes


def test_the_fuses_stand_in_reading_order_and_across_two_x(placed) -> None:
    order = [tag for _, _, _, tag in sorted(placed, key=lambda r: (r[0], r[1], r[2]))]
    assert order == [f"G{i}" for i in range(1, _N + 1)]
    xs_on_a_page = defaultdict(set)
    for page, x, _, _ in placed:
        xs_on_a_page[page].add(x)
    assert max(len(xs) for xs in xs_on_a_page.values()) >= 2


def test_a_wire_across_the_cut_is_a_marker_pair_and_the_rest_are_routes(series) -> None:
    tables: Any = series.model.tables
    tags = _port_tags(series.model)
    x_of = {tag: x for _, x, _, tag in _drawn_fuses(series)}
    markers, routed = _marks_and_routes(series)

    across, between = 0, 0
    for c in tables["conductor"].values():
        fa, fb = tables["port"][c.a].function, tables["port"][c.b].function
        ends = [c.a.value, c.b.value]
        if not all(_FUSE.match(tags[v] or "") for v in ends) or fa == fb:
            continue
        found = net_of(series.model, c.a)
        assert found is not None
        net = found.ports[0].value
        if x_of[tags[ends[0]]] != x_of[tags[ends[1]]]:
            across += 1
            assert net not in routed
            assert all(len(markers[v]) == 1 for v in ends)
        else:
            between += 1
            assert net in routed
            assert not markers[ends[0]]
            assert not markers[ends[1]]
    assert across >= 1
    assert between >= 1


def test_a_middle_fuses_pin_wired_past_the_cut_gets_one_marker_pair() -> None:
    """G3's pin 2 also wired to G15's pin 1, a column and a cut away: the net has three ports, so
    the tap is a pair of markers (a star), never a routed wire across the columns.
    """
    result = _series_result(_N, tap=(3, 15))
    tables: Any = result.model.tables
    tags = _port_tags(result.model)
    x_of = {tag: x for _, x, _, tag in _drawn_fuses(result)}
    markers, routed = _marks_and_routes(result)
    taps = [
        c
        for c in tables["conductor"].values()
        if {tags[c.a.value], tags[c.b.value]} == {"G3", "G15"}
    ]
    assert len(taps) == 1
    c = taps[0]
    assert x_of["G3"] != x_of["G15"]
    net = net_of(result.model, c.a)
    assert net is not None
    assert net.ports[0].value not in routed
    ends = [s.ports[0] for v in (c.a.value, c.b.value) for s in markers[v]]
    assert sorted(ends) == sorted([c.a.value, c.b.value])
