"""Field case: a powered device whose connector function, on the unit's interface, is left unwired builds.
The bug (v0.21.1): the build raised KeyError Id(kind='port') in write_skipped._spare_functions, reading port ids as function ids.
Fixed by el-0063, spare subjects are read through function_of, and SPARE_FUNCTIONS is an INFO finding naming the item."""

from typing import NamedTuple

import fransys as fr
from _model_build_cover import unit_document
from fransys.colours import BK


class _Io(NamedTuple):
    x1: fr.TerminalStrip


@fr.unit("hub", revision=1, interface_version=1, date="2026-10-23", text="first", by="AB")
def _hub(d: fr.Design) -> _Io:
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True)
    h1 = d.device("A1", "DEMO-HUB-PWR", interface=("port_1",))
    d.series(x1[1].inner, h1.PWR["+"], wire=(BK, 0.5))
    d.series(x1[2].inner, h1.PWR["-"], wire=(BK, 0.5))
    return _Io(x1)


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", "intake_parts")
    d.add(_hub, "U1")
    return fr.build(d, unit_document("hub"))


def test_the_unwired_connector_is_a_spare_function_info() -> None:
    result = _built()
    errors = [f.message for f in result.findings if f.severity == fr.Severity.ERROR]
    assert errors == []
    spare = [f for f in result.findings if f.code == "SPARE_FUNCTIONS"]
    assert [f.severity for f in spare] == [fr.Severity.INFO]
