"""Field case: a fixed PLC channel written inside a `d.parallel` is taken like any fixed channel.

The engineering shape: a button in series with a branch that holds a digital input channel fixed
by the IO list (`a1.di_1`) beside a relay coil, then a second button wired to the whole input
module.

The bug: `take_channels` read only the top-level elements of a series, so a fixed channel inside
a `d.parallel` was not marked taken. The later call took the same channel, and the two requests
met on one channel (`PLC_CHANNEL_CONTESTED` at build, no error at the call).

The rule (decision author-0047 P4, amended for C6.5-FIX): a fixed channel is taken wherever it
sits in the call, including inside a `d.parallel`, so the later call takes the next free one.
"""

from typing import Any

import fransys as fr
from fransys.colours import BU

from fransys_model.derive import plc_channel_rows


def _design() -> tuple[fr.Design, Any, Any]:
    d = fr.design("demo_parts", place="C1")
    d.location("C1", "Cabinet")
    dc = d.dc_supply("24VDC", d.device("G1", "DEMO-PSU-24"), names=("P24", "P0"))
    return d, dc, d.device("A1", "DEMO-PLC-DI-16")


def test_a_fixed_channel_inside_a_parallel_is_skipped_by_a_later_whole_module() -> None:
    d, dc, a1 = _design()
    first = d.device("S1", "DEMO-PB-NC")
    first.sw.plc(fr.DI, "First")
    coil = d.device("K1", "DEMO-CTR-3P-24")
    d.series(dc.plus, first.sw, d.parallel(a1.di_1, coil.coil), dc.minus, wire=(BU, 0.75))
    second = d.device("S3", "DEMO-PB-NC")
    second.sw.plc(fr.DI, "Second")
    d.series(dc.plus, second.sw, a1, wire=(BU, 0.75))
    result = fr.build(d)
    rows = plc_channel_rows(result.model)
    assert {row.signal_name: row.pin for row in rows if row.signal_name} == {
        "First": "-A1:1",
        "Second": "-A1:2",
    }
    assert not [f for f in result.findings if f.code == "PLC_CHANNEL_CONTESTED"]
