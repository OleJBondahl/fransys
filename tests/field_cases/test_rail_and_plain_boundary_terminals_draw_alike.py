"""Field case: one unit whose boundary strip holds a bridged `24V` rail terminal and a plain
terminal, both wired from the container to a lamp.

The rule (RB1, owner C2, designer's ruling 2026-10-06): the container's page draws a rail boundary
terminal, and its connection, exactly as it draws a non-rail boundary terminal of the same strip
wired the same way. The comparison covers the kind of drawing (symbol, stub or routed wire)
and the shape of the connection.

The decision that pins it: layout-0120.
"""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr

from fransys_model.layout import DrawingSet, LinkMarker, Page, Route, SymbolPlacement, layout_of
from fransys_model.vocab.tables import functions, items, ports

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    rail: tuple[fr.Terminal, ...]
    gnd: tuple[fr.Terminal, ...]
    plain: fr.Terminal


@fr.unit(
    "demo-mixed-box", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB"
)
def _box(u: fr.Design) -> _Io:
    u.location("C1", "Cabinet")
    psu = u.device("T1", "DEMO-PSU-24")
    lamp = u.device("P1", "DEMO-LAMP-24")
    sig = u.device("P2", "DEMO-LAMP-24")
    tap = u.device("P3", "DEMO-LAMP-24")
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5", interface=True)
    plus, minus = x1.run("24V", 2, bridged=True), x1.run("GND", 2, bridged=True)
    plain = x1.run("SIG", 1)
    dc = u.dc_supply("24V", plus=psu.output["+"], minus=psu.output["-"], voltage=24)
    u.wire(dc.plus.pin, plus[1], wire=("RD", 0.75))
    u.wire(dc.minus.pin, minus[1], wire=("BK", 0.75))
    u.wire(plus[1], lamp.lamp["1"], wire=("RD", 0.75))
    u.wire(minus[1], lamp.lamp["2"], wire=("BK", 0.75))
    u.wire(plain[1], sig.lamp["1"], wire=("WH", 0.75))
    u.wire(minus[2], sig.lamp["2"], wire=("BK", 0.75))
    u.wire(plus[2], tap.lamp["1"], wire=("RD", 0.75))
    return _Io((plus[1], plus[2]), (minus[1], minus[2]), plain[1])


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    io = d.add(_box, "U1")
    h1, h2, h3 = (d.device(tag, "DEMO-LAMP-24") for tag in ("H1", "H2", "H3"))
    d.wire(io.rail[0], h1.lamp["1"], wire=("RD", 0.75))
    d.wire(io.gnd[0], h1.lamp["2"], wire=("BK", 0.75))
    d.wire(io.plain, h2.lamp["1"], wire=("WH", 0.75))
    d.wire(io.gnd[1], h2.lamp["2"], wire=("BK", 0.75))
    d.wire(io.rail[1], h3.lamp["1"], wire=("RD", 0.75))
    (tmp_path / "own.md").write_text("# Mixed box\n", encoding="utf-8")
    (tmp_path / "box.md").write_text("# Container\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    own = fr.document(preset, "demo-mixed-box", cover=tmp_path / "own.md")
    return fr.build(d, own, fr.document(preset, cabinet, cover=tmp_path / "box.md"))


def _drawn(model: Any, designation: str) -> list[tuple[Any, ...]]:
    """What the container's pages hold for one boundary terminal, as comparable shapes."""
    sets = layout_of(model, DrawingSet)
    container = {p.id for p in layout_of(model, Page).values() if sets[p.drawing_set].unit is None}
    (item,) = (i for i in items(model) if fr.derive.printed_designation(model, i) == designation)
    funcs = {f.id for f in functions(model).values() if f.item == item}
    mine = {p.id for p in ports(model).values() if p.function in funcs}
    out: list[tuple[Any, ...]] = [
        ("symbol", s.view, s.symbol, s.poles, s.orientation, s.ports, s.sides)
        for s in layout_of(model, SymbolPlacement).values()
        if s.page in container and s.function in funcs
    ]
    out.extend(
        ("route", r.conductor is not None, len(r.points))
        for r in layout_of(model, Route).values()
        if r.page in container and mine & {r.a, r.b}
    )
    for m in layout_of(model, LinkMarker).values():
        if m.page in container and (m.port in mine or m.far in mine):
            shape = (m.side, m.star, m.facing, m.vertical, m.stub_extra, m.via_x is None)
            out.append(("marker", m.port in mine, *shape))
    return out


def test_the_container_draws_a_rail_boundary_terminal_as_it_draws_a_plain_one(
    tmp_path: Path,
) -> None:
    """Both are a black-box terminal symbol on the container's page and an OFF stub on the lamp pin
    that names them: the same kinds of drawing, in the same shape, none a routed wire."""
    result = _build(tmp_path)
    assert [f for f in fr.check(result) if f.severity is fr.Severity.ERROR] == []
    rail = _drawn(result.model, "-U1-X1:24V:2")
    plain = _drawn(result.model, "-U1-X1:SIG:1")
    assert {entry[0] for entry in plain} == {"symbol", "marker"}  # the plain one is the reference
    assert rail == plain
