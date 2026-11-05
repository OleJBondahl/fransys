"""Field case: a cabinet unit's interface strip is wired to a PLC input module inside and to a field strip outside.
The bug (v0.18.1): a wire to the fourth channel had no path, boxed in by neighbours: three CONNECTION_NOT_DRAWN.
Fixed by layout-0223, a wire with no path tries once more across other nets' exit cells."""

from functools import cache
from typing import Any, NamedTuple

import fransys as fr
from _drawn_pages import drawn_pages
from _model_build_cover import unit_document
from fransys.colours import BU

from electrical_symbols import LIBRARY, is_generic_box
from fransys_layout.drawing import port_points
from fransys_model.derive import function_item, strip_of
from fransys_model.kernel import Severity
from fransys_model.layout import LinkMarker, layout_of
from fransys_model.vocab import ports

_COUNT = 5


class _Io(NamedTuple):
    X: Any


@fr.unit("demo-plc-cab", revision=1, interface_version=1, date="2026-01-01", text="1", by="AB")
def _cab(u: Any) -> _Io:
    x = u.terminal_strip("X", "DEMO-TB-2.5", _COUNT, interface=True)
    k1 = u.device("K1", "DEMO-PLC-DI-16")
    for n in range(1, _COUNT + 1):
        u.series(x[n].inner, getattr(k1, f"di_{n}")[str(n)], wire=(BU, 0.5))
    return _Io(x)


@cache
def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cab = d.add(_cab, "U1")
    field = d.terminal_strip("X9", "DEMO-TB-2.5", _COUNT, external=True)
    for n in range(1, _COUNT + 1):
        d.series(cab.X[n].outer, field[n].inner, wire=(BU, 0.5))
    return fr.build(d, unit_document("demo-plc-cab"))


def test_no_wire_fails_to_route() -> None:
    codes = sorted(f.code for f in _built().findings if f.severity is Severity.ERROR)
    assert codes == []


def test_every_strip_to_module_wire_is_drawn() -> None:
    """The module is the page's one generic box; a wire ends at each of five of its pins."""
    drawn = 0
    for drawing in drawn_pages(_built().model).values():
        pins = {point for s in drawing.symbols if is_generic_box(s.key) for point, _ in port_points(s, LIBRARY)}
        drawn += sum(1 for w in drawing.wires if {w.points[0], w.points[-1]} & pins)
    assert drawn == _COUNT


def test_each_strip_terminal_is_copied_to_the_page_of_its_outside_wire_and_stands_no_reference() -> None:
    model = _built().model
    table = ports(model)
    on_strip = [m for m in layout_of(model, LinkMarker).values() if strip_of(model, function_item(model, table[m.port].function)) is not None]
    assert on_strip == []
    terminals = [sum(1 for s in drawing.symbols if s.key == "terminal") for drawing in drawn_pages(model).values()]
    assert terminals == [2 * _COUNT, 2 * _COUNT]
