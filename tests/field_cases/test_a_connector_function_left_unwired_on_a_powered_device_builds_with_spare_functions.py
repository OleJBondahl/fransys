"""Field case: a powered device whose connector function is left unwired builds.

The engineering shape: a unit with a two-terminal interface strip. One device has a load
function wired to the strip and a second function of kind `connector` with two pins, none of
them wired. The connector is on the unit's interface (`interface=("port_1",)`).

The bug (v0.21.1): the build raises KeyError Id(kind='port') in
`write_skipped._spare_functions`. The unwired connector's pins are not placed, the placement
reports them as skipped spare functions by their port ids, and the finding maker reads each id as
a function id. v0.20 built and wrote. The correct behaviour: the build succeeds and
SPARE_FUNCTIONS is an INFO finding naming the item.

Covered by: R364 (SPARE_FUNCTIONS, NO-SILENT-DROP) - fransys-el.
Decision: el-0063 (spare subjects are read through `function_of`).
"""

import sys
import tempfile
from pathlib import Path
from typing import NamedTuple

import fransys as fr
from fransys.colours import BK

sys.path.insert(0, str(Path(__file__).parent / "data"))  # the invented powered-hub part


class _Io(NamedTuple):
    x1: fr.TerminalStrip


@fr.unit("hub", revision=1, interface_version=1, date="2026-10-23", text="first", by="AB")
def _hub(d: fr.Design) -> _Io:
    x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True)
    h1 = d.device("A1", "DEMO-HUB-PWR", interface=("port_1",))
    d.detail.wire(x1[1], h1.PWR["+"], wire=(BK, 0.5))
    d.detail.wire(x1[2], h1.PWR["-"], wire=(BK, 0.5))
    return _Io(x1)


def _built() -> fr.BuildResult:
    d = fr.design("demo_parts", "intake_parts")
    d.add(_hub, "U1")
    cover = Path(tempfile.mkdtemp()) / "cover.md"
    cover.write_text("# Hub\n", encoding="utf-8")
    return fr.build(d, fr.document(fr.DocumentPreset.CABINET_SCHEMATIC, "hub", cover=cover))


def test_the_unwired_connector_is_a_spare_function_info() -> None:
    result = _built()
    errors = [f.message for f in result.findings if f.severity == fr.Severity.ERROR]
    assert errors == []
    spare = [f for f in result.findings if f.code == "SPARE_FUNCTIONS"]
    assert [f.severity for f in spare] == [fr.Severity.INFO]
