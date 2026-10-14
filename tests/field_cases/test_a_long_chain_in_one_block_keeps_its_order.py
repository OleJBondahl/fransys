"""Field case: a long chain in one function block keeps its order on the sheets.

The engineering shape: one function block holds a daisy chain of 18 identical two-port modules.
Each module has a power function (minus, plus) and a 4-pin comms IN and OUT connector pair. Module
n's plus goes to module n+1's minus, and its OUT pin k goes to the IN pin k of module n+1. The
ends close on a lamp. A second shape is a single series of 10 or 18 fuses between two terminals.

The bug: every function (power, IN, OUT) is placed as its own column, so a module is spread
over several columns and sheets, the modules stand out of chain order, most hops have a wire
whose two ends share no sheet, and the fuse series runs one row wider than the page
(OUT_OF_CONTENT_BOX).

The asserts follow the spec's A1-A3 and its new assert (at most two sheets).

Fixed by: decision layout-0215 (LONG-CHAIN). The parts are `demo_parts`' invented ones.
"""

import pathlib
import re
import tempfile
from itertools import pairwise
from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BK, RD

_N = 18
_MODULE = re.compile(r"^D(\d+)$")


class _Cab(NamedTuple):
    pass


def _document(name: str) -> fr.Draft:
    cover = pathlib.Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# cover\n", encoding="utf-8")
    return fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, name, cover=cover)


def _chain_result() -> fr.BuildResult:
    @fr.unit("chain-a", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
    def chain_unit(d):
        with d.function("CH", "Chain"):
            mods = [d.device(f"D{i}", "DEMO-MODULE-2P-COM4") for i in range(1, _N + 1)]
            lamp = d.device("R1", "DEMO-LAMP-24")
        for a, b in pairwise(mods):
            d.wire(a.pwr["plus"], b.pwr["minus"], wire=(RD, 1.0))
            for pin in "1234":
                d.wire(a.OUT[pin], b.IN[pin], wire=(BK, 0.5))
        d.wire(mods[0].pwr["minus"], lamp["1"], wire=(BK, 1.0))
        d.wire(mods[-1].pwr["plus"], lamp["2"], wire=(RD, 1.0))
        return _Cab()

    d = fr.design("demo_parts")
    d.add(chain_unit, "U1")
    return fr.build(d, _document("chain-a"))


def _series_result(n: int) -> fr.BuildResult:
    @fr.unit("chain-b", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
    def series_unit(d):
        with d.function("B1", "Block"):
            strip = d.terminal_strip("X1", "DEMO-TB-2.5")
            run_a, run_b = strip.run("A", 1), strip.run("B", 1)
            _ = run_a[1], run_b[1]
            fuses = [d.device(f"G{i}", "DEMO-FUSE-DC-160") for i in range(1, n + 1)]
        d.series(*[f.element for f in fuses], wire=(RD, 1.0))
        d.wire(run_a[1], fuses[0].element["1"], wire=(RD, 1.0))
        d.wire(fuses[-1].element["2"], run_b[1], wire=(RD, 1.0))
        return _Cab()

    d = fr.design("demo_parts")
    d.add(series_unit, "U1")
    return fr.build(d, _document("chain-b"))


@pytest.fixture(scope="module")
def chain() -> fr.BuildResult:
    return _chain_result()


def _module_of(key: tuple[str, ...]) -> int | None:
    """The module number from a placement key, today's per-function or the item's own."""
    for segment in key:
        match = _MODULE.match(segment.split("/")[-1])
        if match:
            return int(match[1])
    return None


@pytest.fixture(scope="module")
def placed(chain) -> list[tuple[int, int, int, int, str]]:
    """Every placed module as (sheet, x, y, module number, function id)."""
    tables: Any = chain.model.tables
    number = {pid: p.number for pid, p in tables["layout.page"].items()}
    rows = []
    for sp in tables["layout.symbol_placement"].values():
        module = _module_of(sp.key)
        if module is not None:
            rows.append((number[sp.page], sp.x, sp.y, module, sp.function.value))
    return rows


@pytest.fixture(scope="module", params=[10, 18])
def series_codes(request: pytest.FixtureRequest) -> list[str]:
    return [f.code for f in fr.check(_series_result(request.param))]


def _sheets_of(placed: list[tuple[int, int, int, int, str]], module: int) -> set[int]:
    return {sheet for sheet, _, _, m, _ in placed if m == module}


def test_the_modules_appear_in_chain_order_sheet_by_sheet(placed) -> None:
    first: dict[int, tuple[int, int, int]] = {}
    for sheet, x, y, module, _ in sorted(placed, key=lambda r: (r[0], r[1], r[2])):
        first.setdefault(module, (sheet, x, y))
    order = sorted(first, key=lambda m: first[m])
    assert order == list(range(1, _N + 1))


def test_consecutive_modules_share_a_sheet_or_sit_on_adjacent_sheets(placed) -> None:
    gaps = {
        m: max(abs(a - b) for a in _sheets_of(placed, m) for b in _sheets_of(placed, m + 1))
        for m in range(1, _N)
    }
    assert {m: g for m, g in gaps.items() if g > 1} == {}


def test_each_module_stands_on_one_sheet_in_one_box(placed) -> None:
    spread = {m: sorted(_sheets_of(placed, m)) for m in range(1, _N + 1)}
    assert {m: s for m, s in spread.items() if len(s) > 1} == {}
    boxes = {m: sum(1 for r in placed if r[3] == m) for m in range(1, _N + 1)}
    assert {m: n for m, n in boxes.items() if n != 1} == {}


def test_each_module_box_holds_the_pins_of_all_its_functions(chain) -> None:
    """A3's one box: its pins name the power function and the connectors it wires (P2 bites here).

    The first module wires no IN and the last no OUT: an unwired pin is not drawn (2026-10-13).
    """
    tables: Any = chain.model.tables
    held = {
        _module_of(sp.key): {pin.split(".")[0] for pin in sp.ports}
        for sp in tables["layout.symbol_placement"].values()
        if _module_of(sp.key) is not None
    }
    every = {m: {"pwr", "IN", "OUT"} for m in range(1, _N + 1)}
    assert held == {**every, 1: {"pwr", "OUT"}, _N: {"pwr", "IN"}}


def test_the_chain_draws_on_at_most_two_sheets_and_a_hop_down_a_column_is_a_wire(
    chain, placed
) -> None:
    tables: Any = chain.model.tables
    assert len({r[0] for r in placed}) <= 2
    tag = {
        pid: tables["item"][tables["function"][p.function].item].tag
        for pid, p in tables["port"].items()
    }
    spot = {m: (s, x) for s, x, _, m, _ in placed}
    routed = {r.conductor for r in tables["layout.route"].values()}
    marked = {lm.port for lm in tables["layout.link_marker"].values()}
    bad, checked = [], 0
    hops = [m for m in range(1, _N) if spot[m] == spot[m + 1]]
    for m in hops:
        ends = {f"D{m}", f"D{m + 1}"}
        for cid, c in tables["conductor"].items():
            if {tag[c.a], tag[c.b]} == ends:
                checked += 1
                if cid not in routed or {c.a, c.b} & marked:
                    bad.append((m, cid))
    assert bad == []
    assert hops  # the chain stands in columns, so some hops run down one
    assert checked == 5 * len(hops)  # plus to minus and the four comms pins of each hop


def test_a_series_of_fuses_stays_in_the_content_box(series_codes) -> None:
    assert "OUT_OF_CONTENT_BOX" not in series_codes


def test_every_column_of_the_cut_series_keeps_one_row_pitch() -> None:
    """The fuses of all three columns of 18 stand one pitch apart (fixed column spacing)."""
    tables: Any = _series_result(18).model.tables
    columns: dict[int, list[int]] = {}
    for sp in tables["layout.symbol_placement"].values():
        if "B1/G" in "".join(sp.key):
            columns.setdefault(sp.x, []).append(sp.y)
    pitches = {b - a for ys in columns.values() for a, b in pairwise(sorted(ys))}
    assert len(columns) == 3
    assert len(pitches) == 1, pitches
