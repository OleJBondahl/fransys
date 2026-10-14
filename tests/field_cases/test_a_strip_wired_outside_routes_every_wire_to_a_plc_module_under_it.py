"""Field case: a unit strip wired to a PLC module inside and to a field strip outside.

The engineering shape: a cabinet unit holds an interface strip `-X` of five terminals and a PLC
input module `-K1`. Each terminal is wired to the channel of the same number, so inside the unit
the wires run straight from the strip to the module. The container wires every terminal's outer
side to a field strip `-X9`. The unit's own document draws the strip's terminals in one row, 24
apart, over the module's channel pins, 16 apart, with 32 between the rows.

The bug (v0.18.1): the unit alone drew, but with the outer wires present, the router found no
path for the wire to the fourth channel, a pin boxed in by its neighbours' first steps, a label
and a wire corner. `fr.check` gave one `ROUTE_FAILED` and three `CONNECTION_NOT_DRAWN`, and
`fr.write` was blocked.

The rule (decision layout-0223): a wire with no path tries once more across other nets' exit cells.
"""

import tempfile
from functools import cache
from pathlib import Path
from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import BU

from fransys_model.kernel import Severity
from fransys_model.layout import Route, layout_of

_COUNT = 5


class _Io(NamedTuple):
    X: Any


@fr.unit("demo-plc-cab", revision=1, interface_version=1, date="2026-01-01", text="1", by="AB")
def _cab(u: Any) -> _Io:
    x = u.terminal_strip("X", "DEMO-TB-2.5", _COUNT, interface=True)
    k1 = u.device("K1", "DEMO-PLC-DI-16")
    for n in range(1, _COUNT + 1):
        u.wire(x[n], getattr(k1, f"di_{n}")[str(n)], wire=(BU, 0.5))
    return _Io(x)


@cache
def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", place="C1")
    cab = d.add(_cab, "U1")
    field = d.terminal_strip("X9", "DEMO-TB-2.5", _COUNT, external=True)
    for n in range(1, _COUNT + 1):
        d.wire(cab.X[n], field[n], wire=(BU, 0.5))
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Cabinet\n", encoding="utf-8")
    return fr.build(
        d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "demo-plc-cab", cover=cover)
    )


def test_no_wire_fails_to_route() -> None:
    codes = sorted(f.code for f in _built().findings if f.severity is Severity.ERROR)
    assert codes == []


def test_every_strip_to_module_wire_is_drawn() -> None:
    model = _built().model
    drawn = [
        r
        for r in layout_of(model, Route).values()
        if "K1" in str((model.key_of(r.a), model.key_of(r.b)))
    ]
    assert len(drawn) == _COUNT
