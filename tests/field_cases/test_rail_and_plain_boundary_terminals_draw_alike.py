"""Field case: a unit's boundary strip holds a bridged `24V` rail terminal and a plain terminal, both wired to a lamp.
The bug: the container's page drew a bridged rail boundary terminal differently from a plain one wired the same way.
Fixed by layout-0120 (owner ruling 2026-10-06), a rail boundary terminal is drawn and connected as a non-rail one of its strip."""

from typing import TYPE_CHECKING, Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages, markers_in, ref_texts, tag_texts

from fransys_model.layout import DrawingSet, Page, layout_of

if TYPE_CHECKING:
    from pathlib import Path


class _Io(NamedTuple):
    rail: tuple[fr.Terminal, ...]
    gnd: tuple[fr.Terminal, ...]
    plain: fr.Terminal


@fr.unit("demo-mixed-box", revision=1, interface_version=1, date="2026-01-01", text="first", by="AB")
def _box(u: fr.Design) -> _Io:
    u.location("C1", "Cabinet")
    psu = u.device("T1", "DEMO-PSU-24")
    lamp = u.device("P1", "DEMO-LAMP-24")
    sig = u.device("P2", "DEMO-LAMP-24")
    tap = u.device("P3", "DEMO-LAMP-24")
    x1 = u.terminal_strip("X1", "DEMO-TB-2.5-TWIN", interface=True)
    plus, minus = x1.run("24V", 2, bridged=True, rail=True), x1.run("GND", 2, bridged=True, rail=True)
    plain = x1.run("SIG", 1)
    dc = u.dc_supply("24V", plus=psu.output["+"], minus=psu.output["-"], voltage=24)
    u.series(dc.plus.pin, plus[1].inner, wire=("RD", 0.75))
    u.series(dc.minus.pin, minus[1].inner, wire=("BK", 0.75))
    u.series(plus[1].inner, lamp.lamp["1"], wire=("RD", 0.75))
    u.series(minus[1].inner, lamp.lamp["2"], wire=("BK", 0.75))
    u.series(plain[1].inner, sig.lamp["1"], wire=("WH", 0.75))
    u.series(minus[2].inner, sig.lamp["2"], wire=("BK", 0.75))
    u.series(plus[2].inner, tap.lamp["1"], wire=("RD", 0.75))
    u.series(minus[2].inner, tap.lamp["2"], wire=("BK", 0.75))
    return _Io((plus[1], plus[2]), (minus[1], minus[2]), plain[1])


def _build(tmp_path: Path) -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cabinet = d.location("C1", "Cabinet")
    io = d.add(_box, "U1")
    h1, h2, h3 = (d.device(tag, "DEMO-LAMP-24") for tag in ("H1", "H2", "H3"))
    d.series(io.rail[0].outer, h1.lamp["1"], wire=("RD", 0.75))
    d.series(io.gnd[0].outer, h1.lamp["2"], wire=("BK", 0.75))
    d.series(io.plain.outer, h2.lamp["1"], wire=("WH", 0.75))
    d.series(io.gnd[1].outer, h2.lamp["2"], wire=("BK", 0.75))
    d.series(io.rail[1].outer, h3.lamp["1"], wire=("RD", 0.75))
    d.series(io.gnd[1].outer, h3.lamp["2"], wire=("BK", 0.75))
    (tmp_path / "own.md").write_text("# Mixed box\n", encoding="utf-8")
    (tmp_path / "box.md").write_text("# Container\n", encoding="utf-8")
    preset = fr.DocumentPreset.CABINET_SCHEMATIC
    own = fr.document(preset, "demo-mixed-box", cover=tmp_path / "own.md")
    return fr.build(d, own, fr.document(preset, cabinet, cover=tmp_path / "box.md"))


def _drawn(model: Any, designation: str) -> list[tuple[Any, ...]]:
    """What the container's pages hold for one boundary terminal, as comparable shapes.

    The terminal's symbol is the one nearest its printed designation (a drawn symbol names no
    subject); its stubs are the markers that print the designation.
    """
    sets = layout_of(model, DrawingSet)
    container = {p.id for p in layout_of(model, Page).values() if sets[p.drawing_set].unit is None}
    out: list[tuple[Any, ...]] = []
    for page, drawing in drawn_pages(model).items():
        if page not in container:
            continue
        for tag in tag_texts(drawing, designation):
            mine = min(
                drawing.symbols,
                key=lambda s, tag=tag: abs(s.x - tag.box.x) + abs(s.y - tag.box.y),
            )
            out.append(("symbol", mine.key, mine.poles, mine.orient, mine.offsets, mine.sides))
            out.extend(("route", len(w.points)) for w in drawing.wires if (mine.x, mine.y) in {w.points[0], w.points[-1]})
        out.extend(("marker", m.key, m.orient) for m in markers_in(drawing) if any(designation in text for text in ref_texts(m)))
    return out


def test_the_container_draws_a_rail_boundary_terminal_as_it_draws_a_plain_one(
    tmp_path: Path,
) -> None:
    """Both are a black-box terminal wired to the lamp pin and both stand a stub naming their far end inside the unit (R895).
    The bridge no longer joins the rail's two terminals (R1128 A4), so the rail's far end lies outside the container's joined sets,
    as the plain one's does."""
    result = _build(tmp_path)
    assert [f for f in fr.check(result) if f.severity is fr.Severity.ERROR] == []
    rail = _drawn(result.model, "-U1-X1:24V:2")
    plain = _drawn(result.model, "-U1-X1:SIG:1")
    assert rail == [("symbol", "marker-arrow-turned", 1, "R180", (), ())]  # the stub of its far end -U1-P3:1, inside the unit
    assert plain == [("symbol", "marker-arrow-turned", 1, "R180", (), ())]  # the stub stands at the terminal's other pin
