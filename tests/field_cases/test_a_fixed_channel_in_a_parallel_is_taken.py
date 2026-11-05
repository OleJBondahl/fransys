"""Field case: a button in series with a branch holding a digital input channel fixed by the IO list (`a1.di_1`), then a second button.
The bug: `take_channels` read only the top-level elements of a series, so a fixed channel inside a `d.parallel` was not marked taken.
Fixed by author-0047 P4 (amended for C6.5-FIX), a fixed channel is taken wherever it sits, even inside a d.parallel."""

import fransys as fr
from _field_designs import plc_di_design
from fransys.colours import BU

from fransys_model.derive import plc_channel_rows


def test_a_fixed_channel_inside_a_parallel_is_skipped_by_a_later_whole_module() -> None:
    d, dc, a1 = plc_di_design()
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
