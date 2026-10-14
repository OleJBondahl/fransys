"""Field case: a long chain in one function block keeps its order on the sheets.

The engineering shape: one function block holds a daisy chain of 18 identical two-port modules.
Each module has a power function (minus, plus) and a 4-pin comms IN and OUT connector pair. Module
n's plus goes to module n+1's minus, and its OUT pin k goes to the IN pin k of module n+1. The
ends close on a lamp. A second shape is a single series of 10 or 18 fuses between two terminals.

The bug: every function (power, IN, OUT) is placed as its own column, so a module is spread
over several columns and sheets, the modules stand out of chain order, most hops have a wire
whose two ends share no sheet, and the fuse series runs one row wider than the page
(OUT_OF_CONTENT_BOX).

Fixed by: LONG-CHAIN, pending. The parts are `demo_parts`' invented ones.
"""

import pathlib
import tempfile
from itertools import pairwise
from typing import Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import BK, RD

_N = 18
_PENDING = pytest.mark.xfail(strict=True, reason="LONG-CHAIN pending")


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
def placed() -> list[tuple[int, int, int, str]]:
    """Every placed module function as (sheet, x, module number, function name)."""
    tables: Any = _chain_result().model.tables
    number = {pid: p.number for pid, p in tables["layout.page"].items()}
    rows = []
    for sp in tables["layout.symbol_placement"].values():
        module = sp.key[4].split("/")[-1]
        if module.startswith("D"):
            rows.append((number[sp.page], sp.x, int(module[1:]), sp.key[6]))
    return rows


@pytest.fixture(scope="module", params=[10, 18])
def series_codes(request: pytest.FixtureRequest) -> list[str]:
    return [f.code for f in fr.check(_series_result(request.param))]


def _sheets_of(placed: list[tuple[int, int, int, str]], module: int) -> set[int]:
    return {sheet for sheet, _, m, _ in placed if m == module}


@_PENDING
def test_the_modules_appear_in_chain_order_sheet_by_sheet(placed) -> None:
    first: dict[int, tuple[int, int]] = {}
    for sheet, x, module, _ in sorted(placed, key=lambda r: (r[0], r[1])):
        first.setdefault(module, (sheet, x))
    order = sorted(first, key=lambda m: first[m])
    assert order == list(range(1, _N + 1))


@_PENDING
def test_consecutive_modules_share_a_sheet_or_sit_on_adjacent_sheets(placed) -> None:
    gaps = {
        m: max(abs(a - b) for a in _sheets_of(placed, m) for b in _sheets_of(placed, m + 1))
        for m in range(1, _N)
    }
    assert {m: g for m, g in gaps.items() if g > 1} == {}


@_PENDING
def test_each_modules_functions_stand_on_one_sheet(placed) -> None:
    spread = {m: sorted(_sheets_of(placed, m)) for m in range(1, _N + 1)}
    assert {m: s for m, s in spread.items() if len(s) > 1} == {}


@_PENDING
def test_a_series_of_fuses_stays_in_the_content_box(series_codes) -> None:
    assert "OUT_OF_CONTENT_BOX" not in series_codes
