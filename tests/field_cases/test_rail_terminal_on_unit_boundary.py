"""Field case: a unit whose boundary is a bridged 24V run and a bridged GND run, fed by a DC supply
inside the unit, placed in a container whose lamps are wired to the boundary.

The bug: layout raised `LayoutError` "a unit's boundary names a function that has no spec". Layout
read drops a rail terminal (V3), so the boundary terminal had no `FunctionSpec`, yet the
container's page must draw it.

The rule (RB1, owner C2): the container's page draws the child's boundary terminal as its black-box
terminal with the container's wire to it (a stub on the lamp pin, as for any black box), also
where the unit's own pages draw the same terminal as its rail's power symbol. One data, two views.

The decision that fixes it: layout-0120.
"""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr

from fransys_model.layout import (
    DrawingSet,
    LinkMarker,
    Page,
    PowerSymbol,
    SymbolPlacement,
    layout_of,
)
from fransys_model.vocab.tables import functions, items, ports, unit_releases, units

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    rail: tuple[fr.Terminal, ...]


@fr.unit("demo-rail-box", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _box(u: fr.Design) -> _Io:
    u.location("C1", "Cabinet")
    psu = u.device("T1", "DEMO-PSU-24")
    lamp = u.device("P1", "DEMO-LAMP-24")
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True)
    plus, minus = x1.run("24V", 2, bridged=True), x1.run("GND", 2, bridged=True)
    dc = u.dc_supply("24V", plus=psu.output["+"], minus=psu.output["-"], voltage=24)
    u.wire(dc.plus.pin, plus[1], wire=("RD", 0.75))
    u.wire(dc.minus.pin, minus[1], wire=("BK", 0.75))
    u.wire(plus[1], lamp.lamp["1"], wire=("RD", 0.75))
    u.wire(minus[1], lamp.lamp["2"], wire=("BK", 0.75))
    return _Io((plus[1], plus[2], minus[1], minus[2]))


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    io = d.add(_box, "U1")
    lamps = (d.device("H1", "DEMO-LAMP-24"), d.device("H2", "DEMO-LAMP-24"))
    for pair, pole in ((io.rail[:2], "1"), (io.rail[2:], "2")):
        for terminal, lamp in zip(pair, lamps, strict=True):
            d.wire(terminal, lamp.lamp[pole], wire=("RD", 0.75))
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
        named[page.id] = (
            None if unit is None else unit_releases(model)[units(model)[unit].release].name
        )
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
    (item,) = (i for i in items(model) if fr.derive.printed_designation(model, i) == "-U1-X1:24V:1")
    (first,) = (f.id for f in functions(model).values() if f.item == item)
    drawn = {
        owner[s.page] for s in layout_of(model, SymbolPlacement).values() if s.function == first
    }
    assert drawn == {None}  # the unit's own pages draw it as no terminal (RB3)
    # the container's wire to a black box: a stub on the lamp pin naming the terminal (0080)
    stubs = layout_of(model, LinkMarker).values()
    assert any(
        owner[m.page] is None and m.far is not None and ports(model)[m.far].function == first
        for m in stubs
    )
    assert "demo-rail-box" in {owner[s.page] for s in layout_of(model, PowerSymbol).values()}
