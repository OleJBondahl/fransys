"""Field case: a spare port of a unit's own device gives no warning.

The engineering shape: a cabinet unit holds an I/O device with two connectors and a terminal
strip. Only the first connector is wired, to the strip. The second connector is a spare: the
part has the port, so it cannot be removed.

The bug: `UNIT_CONNECTOR_DANGLING` warned on every such spare, and the consumer had no fix to make.
Fixed by decision model-0219: the code is retired, and `PORT_UNCONNECTED` (INFO) still reports it.
"""

from typing import Any, NamedTuple

import fransys as fr
from fransys.colours import BU


class _Cab(NamedTuple):
    X1: Any


def test_a_spare_port_of_an_own_device_gives_no_warning() -> None:
    @fr.unit("spare", revision=1, interface_version=1, date="2026-10-14", text="First", by="XX")
    def _spare(d: Any) -> _Cab:
        x1 = d.terminal_strip("X1", "DEMO-TB-2.5", 2, interface=True)
        io = d.device("A1", "DEMO-IO-2X")  # x2 stays free
        d.wire(x1[1], io.x1["1"], wire=(BU, 0.75))
        d.wire(x1[2], io.x1["2"], wire=(BU, 0.75))
        return _Cab(x1)

    d = fr.design("demo_parts")
    d.add(_spare, "U1")
    codes = {f.code for f in fr.build(d).findings}
    assert "PORT_UNCONNECTED" in codes  # the spare is still reported, as INFO
    assert "UNIT_CONNECTOR_DANGLING" not in codes
