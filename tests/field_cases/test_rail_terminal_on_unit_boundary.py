"""Field case: a unit whose boundary is a bridged 24V run and GND run, fed by a DC supply inside it, inside a container with lamps.
The bug: layout raised LayoutError (a unit's boundary names a function that has no spec), since layout read dropped the rail terminal (V3).
Fixed by layout-0120, the container's page draws the child's boundary terminal as its black-box terminal, one data and two views."""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages, markers_in, ref_texts, tag_texts

from fransys_model.derive import boundary_rail_wires, conductor_ends
from fransys_model.derive.stands import stands
from fransys_model.layout import DrawingSet, Page, PowerSymbol, layout_of
from fransys_model.vocab.tables import unit_releases, units

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    rail: tuple[fr.Terminal, ...]


@fr.unit("demo-rail-box", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _box(u: fr.Design) -> _Io:
    u.location("C1", "Cabinet")
    psu = u.device("T1", "DEMO-PSU-24")
    lamp = u.device("P1", "DEMO-LAMP-24")
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5-TWIN", interface=True)
    plus, minus = x1.run("24V", 2, bridged=True, rail=True), x1.run("GND", 2, bridged=True, rail=True)
    dc = u.dc_supply("24V", plus=psu.output["+"], minus=psu.output["-"], voltage=24)
    u.series(dc.plus.pin, plus[1].inner, wire=("RD", 0.75))
    u.series(dc.minus.pin, minus[1].inner, wire=("BK", 0.75))
    u.series(plus[1].inner, lamp.lamp["1"], wire=("RD", 0.75))
    u.series(minus[1].inner, lamp.lamp["2"], wire=("BK", 0.75))
    return _Io((plus[1], plus[2], minus[1], minus[2]))


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    io = d.add(_box, "U1")
    lamps = (d.device("H1", "DEMO-LAMP-24"), d.device("H2", "DEMO-LAMP-24"))
    for pair, pole in ((io.rail[:2], "1"), (io.rail[2:], "2")):
        for terminal, lamp in zip(pair, lamps, strict=True):
            d.series(terminal.outer, lamp.lamp[pole], wire=("RD", 0.75))
    (tmp_path / "own.md").write_text("# Rail box\n", encoding="utf-8")
    (tmp_path / "box.md").write_text("# Container\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    own = fr.document(preset, "demo-rail-box", cover=tmp_path / "own.md")
    return fr.build(d, own, fr.document(preset, cabinet, cover=tmp_path / "box.md"))


def _set_unit_names(model: Any) -> dict[Any, str | None]:
    """The unit release name of each page's drawing set (`None`: the container's own set)."""
    sets = layout_of(model, DrawingSet)
    named = {}
    for page in layout_of(model, Page).values():
        unit = sets[page.drawing_set].unit
        named[page.id] = None if unit is None else unit_releases(model)[units(model)[unit].release].name
    return named


def test_the_container_draws_the_boundary_terminal_and_the_unit_its_power_symbol(
    tmp_path: Path,
) -> None:
    """No LayoutError, 0 ERROR; `-U1-X1:24V:1` is on the container's page with its wire; the
    unit's own pages hold the rail's power symbol."""
    result = _build(tmp_path)
    assert [f for f in fr.check(result) if f.severity is fr.Severity.ERROR] == []
    model = result.model
    owner = _set_unit_names(model)
    pages = drawn_pages(model)
    designation = "-U1-X1:24V:1"
    tagged = {owner[page] for page, d in pages.items() if tag_texts(d, designation)}
    assert tagged == {None}  # the unit's own pages draw it as no terminal
    # the container draws the boundary strip itself, wired to the lamp: no stub names the terminal (R729)
    assert not any(designation in text for d in pages.values() for m in markers_in(d) for text in ref_texts(m))
    assert "demo-rail-box" in {owner[s.page] for s in layout_of(model, PowerSymbol).values()}


def test_the_wires_into_the_boundary_rail_terminals_are_the_four_lamp_wires(tmp_path: Path) -> None:
    """The container's four lamp wires end on a rail terminal of the unit boundary; the unit's inner wires do not."""
    model = _build(tmp_path).model
    assert len(boundary_rail_wires(model)) == 4


def test_no_function_is_left_unwired_and_no_connection_undrawn(tmp_path: Path) -> None:
    """DS2 part 7: the lamp wires into the boundary rail terminals are nets, so every terminal is wired and drawn."""
    codes = [f.code for f in fr.check(_build(tmp_path))]
    assert "FUNCTION_NOT_WIRED" not in codes
    assert "CONNECTION_NOT_DRAWN" not in codes


def test_a_pin_wired_to_a_boundary_rail_terminal_stands_no_power_symbol(tmp_path: Path) -> None:
    """R868: the four lamp pins are drawn by their wires, so no anchor stands on them; the unit's own rail pins still do."""
    model = _build(tmp_path).model
    wired = {p for w in boundary_rail_wires(model) for p in conductor_ends(model, w)}
    stood = stands(model)
    assert wired
    assert not wired & stood.keys()
    assert stood  # the unit's own lamp and supply pins stand their rails
