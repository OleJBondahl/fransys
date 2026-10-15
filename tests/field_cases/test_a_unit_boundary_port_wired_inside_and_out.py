"""Field case: a supply output inside a unit feeds the unit's own load and also leaves through
the unit's interface to a field device in the container (model-0188).

The engineering shape: a cabinet unit holds a supply and a lamp wired to the supply's output;
the unit marks the supply an interface; its container wires a second lamp to the same output.
The output port is then the unit's boundary and has two drawn views: the supply on the unit's
page and a pin cell in the container's black box.

The bug: layout named one function per port. The lint refused a port named by two functions, and
chain discovery gave the port to the pin cell, which sorts last, so the unit's own wires read the
wrong spec and facing. The fix keys the port per connection end: the unit page draws as it does
alone. Decision model-0188.
"""

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
    u.detail.wire(lamp["1"], t1.output["+"], wire=("WH", 0.5))
    u.detail.wire(lamp["2"], t1.output["-"], wire=("WH", 0.5))
    return _Supply(t1)


def _design() -> fr.Design:
    @fr.unit("demo-container", **_UNIT)
    def container(c: Any) -> _Open:
        io = c.add(_supply_cab, "U1")
        lamp = c.device("H1", "DEMO-LAMP-24")
        c.detail.wire(lamp["1"], io.T1.output["+"], wire=("WH", 0.5))
        c.detail.wire(lamp["2"], io.T1.output["-"], wire=("WH", 0.5))
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
    wires = re.findall(r'<polyline class="wire" points="[^"]*"', svg)
    return sorted(wires), sorted(re.findall(r">([^<>]+)</text>", svg))


def _alone() -> fr.Design:
    d = fr.design("demo_parts")
    d.add(_supply_cab, "U1", place=None)
    return d


def test_a_boundary_port_wired_inside_and_out_draws_the_unit_page_as_if_alone() -> None:
    errors = [f.code for f in fr.build(_design()).findings if f.severity.name == "ERROR"]
    assert errors == []
    pages = _svgs(_design(), "demo-container")
    (container,) = (p for p in pages if "-U1-T1:+" in p)
    assert "-U1-T1:-" in container
    assert "-H1" in container
    (inside,) = _svgs(_alone(), "demo-supply-cab")
    assert _drawing(inside) in [_drawing(p) for p in pages]
