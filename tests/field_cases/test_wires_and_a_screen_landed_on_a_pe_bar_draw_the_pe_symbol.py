"""Field case: wires and a one-ended screen landed on a PE bar draw the earth symbol, not the bar.

The engineering shape: a cabinet unit with a 20-screw protective-earth bar. The PE pins of three
motors are wired to the bar, and one instrument cable's screen is earthed at one end on it. A
second unit holds a cut-to-length bar with 25 landings.

The bug: the bar was built as a generic item. The build raised `SYMBOL_PORT_MISSING` (a bar has no
drawn symbol with its screws as ports), and the wire list named a screw the wiring never
recorded (`-PE1:1`) instead of the bar.
The rules: a bar is never drawn on the schematic, and each end landed on it draws the
protective-earth symbol (layout-0219); every landing takes its own screw, yet a list prints the
bar alone, `-PE1` (parts-0019, model-0221).
"""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
import pytest
from fransys.colours import GNYE

from fransys_model.derive import ItemKind, item_kind
from fransys_model.layout import EndBox, EndStyle, PowerSymbol, SymbolPlacement, layout_of
from fransys_model.vocab import OpenCoreFacet
from fransys_model.vocab.bars import bar_items, is_bar_port
from fransys_model.vocab.tables import conductors, facets_of, functions, items, ports

if TYPE_CHECKING:
    from pathlib import Path

BAR = "-U1-PE1"
MOTORS = ("M1", "M2", "M3")
LANDINGS = 25


class _Unit(NamedTuple):
    """A unit with no interface to hand back."""


@fr.unit("pe-cab", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _cab(c: Any) -> _Unit:
    x1 = c.terminal_strip("X1", "DEMO-TB-2.5", 4)
    h1 = c.device("H1", "DEMO-LAMP-24")
    pe1 = c.device("PE1", "DEMO-PEBAR-20").pe
    for name in MOTORS:
        c.detail.wire(c.device(name, "DEMO-MOTOR-4KW").motor["PE"], pe1, wire=(GNYE, 2.5))
    w2 = c.cable("W2", "DEMO-CBL-2X2X0.75-SP", length_m=25)
    w2.core(1, x1[2], h1[2])
    w2.core(5, pe1)
    w2.spare()
    return _Unit()


@fr.unit("pe-cut", revision=1, interface_version=1, date="2026-10-14", text="first", by="AB")
def _cut(c: Any) -> _Unit:
    strip = c.terminal_strip("X1", "DEMO-TB-PE-2.5", LANDINGS)
    pe1 = c.device("PE1", "DEMO-PEBAR-CUT").pe
    for n in range(1, LANDINGS + 1):
        c.detail.wire(strip[n], pe1, wire=(GNYE, 2.5))
    return _Unit()


def _build(unit: Any, name: str, folder: Path) -> fr.BuildResult:
    d = fr.design("demo_parts")
    d.add(unit, "U1")
    cover = folder / f"{name}.md"
    cover.write_text("# C\n", encoding="utf-8")
    pages = (fr.PageKind.HARNESS_DRAWING, fr.PageKind.CABLE_LIST)
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    return fr.build(d, fr.document(preset, name, cover=cover, add=pages))


@pytest.fixture(scope="module")
def cab(tmp_path_factory: pytest.TempPathFactory) -> fr.BuildResult:
    return _build(_cab, "pe-cab", tmp_path_factory.mktemp("cab"))


@pytest.fixture(scope="module")
def cut(tmp_path_factory: pytest.TempPathFactory) -> fr.BuildResult:
    return _build(_cut, "pe-cut", tmp_path_factory.mktemp("cut"))


def _wire_ends(model: Any) -> list[str]:
    return [end for row in fr.derive.wire_rows(model) for end in (row.from_, row.to)]


def _screws(model: Any) -> list[str]:
    """The name of the screw each landing took: conductor ends and open cores on the bar."""
    landed = [end for c in conductors(model).values() for end in (c.a, c.b)]
    landed += [o.at for o in facets_of(model, OpenCoreFacet).values() if o.at is not None]
    return [ports(model)[p].name for p in landed if is_bar_port(model, p)]


def test_the_wire_list_and_the_core_list_print_the_bar_alone(cab: fr.BuildResult) -> None:
    """A2a: three wire-list ends and the screen's core-list end print `-U1-PE1`, no screw."""
    model = cab.model
    assert [e for e in _wire_ends(model) if "PE1" in e] == [BAR] * len(MOTORS)
    cores = [
        row.at_designation
        for item in items(model)
        if item_kind(model, item) is ItemKind.CABLE
        for row in fr.derive.open_core_rows(model, item)
        if row.index == 5
    ]
    assert cores == [BAR]


def test_the_four_ends_take_four_screws(cab: fr.BuildResult) -> None:
    """A2b: three wires and a screen on one bar take four different screws."""
    screws = _screws(cab.model)
    assert len(screws) == len(MOTORS) + 1
    assert len(set(screws)) == len(MOTORS) + 1


def test_the_bar_is_not_drawn_and_each_pe_pin_draws_the_symbol(cab: fr.BuildResult) -> None:
    """A2c: no placement for the bar's function; each motor's PE pin has one earth symbol."""
    model = cab.model
    (bar,) = bar_items(model)
    bar_functions = {f.id for f in functions(model).values() if f.item == bar}
    placements = layout_of(model, SymbolPlacement).values()
    assert placements
    assert not [p for p in placements if p.function in bar_functions]
    drawn = [
        s.port for s in layout_of(model, PowerSymbol).values() if s.symbol == "protective-earth"
    ]
    for name in MOTORS:
        (pin,) = [
            p.id
            for p in ports(model).values()
            if fr.derive.port_designation(model, p.id) == f"-U1-{name}:PE"
        ]
        assert drawn.count(pin) == 1


def test_the_bar_end_box_is_earth_and_a_strip_end_box_stays_solid(cab: fr.BuildResult) -> None:
    """B3: the bar's end box in the cable drawing is EARTH; the other end boxes are SOLID."""
    model = cab.model
    (bar,) = bar_items(model)
    styles = {box.item: box.style for box in layout_of(model, EndBox).values()}
    assert styles[bar] is EndStyle.EARTH
    others = [style for item, style in styles.items() if item != bar]
    assert others
    assert set(others) == {EndStyle.SOLID}


def test_the_build_has_no_missing_port_and_no_error(cab: fr.BuildResult) -> None:
    """A2d: neither finding of the bug appears, and no finding is an ERROR."""
    findings = fr.check(cab)
    assert {f.code for f in findings}.isdisjoint({"SYMBOL_PORT_MISSING", "CONNECTION_TO_UNDRAWN"})
    assert not [f for f in findings if f.severity is fr.Severity.ERROR]


def test_the_bar_is_one_bom_line(cab: fr.BuildResult) -> None:
    """B3: the bar is one line of the bill of materials, with its one designation."""
    lines = [b for b in fr.derive.bom_lines(cab.model) if b.mpn == "DEMO-PEBAR-20"]
    assert [(b.count, b.designations) for b in lines] == [(1, (BAR,))]


def test_a_cut_to_length_bar_prints_the_bar_for_each_of_25_landings(cut: fr.BuildResult) -> None:
    """A3: 25 landings on a cut-to-length bar print `-U1-PE1` each and take 25 screws."""
    ends = _wire_ends(cut.model)
    assert [e for e in ends if "PE1" in e] == [BAR] * LANDINGS
    assert len(set(_screws(cut.model))) == LANDINGS
