"""Field case: a supply in a unit feeds its own load and also leaves through the unit's interface to a field device outside.
The bug: layout named one function per port, so the lint refused a port named by two functions (model-0188, one port per connection end).
The unit page draws its own wires as alone and a stub for the conductor that leaves (model-0422)."""

import re
import tempfile
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr

_UNIT: dict[str, Any] = {
    "revision": 1,
    "interface_version": 1,
    "date": "2026-01-01",
    "text": "first",
    "by": "AB",
}


class _Open(NamedTuple):
    pass


class _Supply(NamedTuple):
    T1: Any


@fr.unit("demo-supply-cab", **_UNIT)
def _supply_cab(u: Any) -> _Supply:
    t1 = u.device("T1", "DEMO-PSU-24", interface=("output",))
    lamp = u.device("H2", "DEMO-LAMP-24")
    u.series(lamp["1"], t1.output["+"], wire=("WH", 0.5))
    u.series(lamp["2"], t1.output["-"], wire=("WH", 0.5))
    return _Supply(t1)


def _design() -> fr.Design:
    @fr.unit("demo-container", **_UNIT)
    def container(c: Any) -> _Open:
        io = c.add(_supply_cab, "U1")
        lamp = c.device("H1", "DEMO-LAMP-24")
        c.series(lamp["1"], io.T1.output["+"], wire=("WH", 0.5))
        c.series(lamp["2"], io.T1.output["-"], wire=("WH", 0.5))
        return _Open()

    d = fr.design("demo_parts")
    d.add(container, "C1", place=None)
    return d


def _svgs(design: fr.Design, unit: str) -> list[str]:
    root = Path(tempfile.mkdtemp())
    (root / "c.md").write_text("# c\n", encoding="utf-8")
    cover = fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, unit, cover=root / "c.md")
    fr.write(fr.build(design, cover), root / "out", intermediates=root / "inter")
    return [svg.read_text("utf-8") for svg in (root / "inter").glob("layout.page-*.svg")]


def _drawing(svg: str) -> tuple[list[str], list[str]]:
    """A page's wire polylines and texts, the page's own look without its id."""
    wires = re.findall(r'<polyline points="[^"]*"', svg)
    assert wires, "the page draws no wire polyline: the comparison would read texts only"
    return sorted(wires), sorted(re.findall(r">([^<>]+)</text>", svg))


def _connections(wires: list[str]) -> set[tuple[tuple[str, ...], ...]]:
    """The connections a page draws: each wire's pin it leaves and the pin column it enters, not its geometry."""
    ends = [re.findall(r"[-\d.]+,[-\d.]+", w) for w in wires]
    return {((e[0],), (e[-1].split(",")[0],)) for e in ends}


def _alone() -> fr.Design:
    d = fr.design("demo_parts")
    d.add(_supply_cab, "U1", place=None)
    return d


def test_a_boundary_port_wired_inside_and_out_draws_its_own_wires_as_alone_and_a_stub_for_the_conductor_that_leaves() -> None:
    codes = [f.code for f in fr.build(_design()).findings]
    assert "CONNECTION_NOT_DRAWN" not in codes
    assert codes.count("OVERLAP") <= 1  # looks class: KI-596
    assert codes.count("WIRE_OVER_MARKER") <= 1  # looks class: KI-597
    assert not [f for f in fr.build(_design()).findings if f.severity.name == "ERROR"]
    pages = _svgs(_design(), "demo-container")
    (container,) = (p for p in pages if "-U1-T1:+" in p)
    assert "-U1-T1:-" in container
    assert "-H1" in container
    texts_c = _drawing(container)[1]
    assert "← -U1-T1:+" in texts_c, "the container pin H1:1 names its conductor to T1:+ in a stub"
    assert "→ -U1-T1:-" in texts_c, "the container pin H1:2 names its conductor to T1:- in a stub"
    (inside,) = _svgs(_alone(), "demo-supply-cab")
    assert len(_drawing(inside)[0]) == 2, "the unit's own two wires (H2 to T1 + and -) are drawn, counted apart from the comparison"
    wires, texts = _drawing(inside)
    (unit_page,) = (p for p in pages if "-H2" in p)
    unit_wires, unit_texts = _drawing(unit_page)
    assert _connections(unit_wires) == _connections(wires), "the unit page draws the same connections as the page drawn alone"
    assert sorted(unit_texts) == sorted([*texts, "→ -C1-H1:1", "→ -C1-H1:2"]), "one stub a boundary pin the container continues, at T1:+ and T1:-"


def test_every_wire_point_on_the_unit_page_lies_on_the_wiring_grid() -> None:
    (unit_page,) = (p for p in _svgs(_design(), "demo-container") if "-H2" in p)
    points = [float(v) for pl in re.findall(r'<polyline points="([^"]*)"', unit_page) for v in re.split(r"[ ,]+", pl.strip())]
    assert points, "the unit page draws wire points"
    assert all(abs(v / 2.5 - round(v / 2.5)) < 1e-6 for v in points), points
