"""Field case: a relay contact wired straight to input channel 2 of a four-channel digital input module, and also to a strip terminal.
The bug: channel 1 was also wired to that terminal, so two channels qualified, the first in serving order won, and no finding said so.
Fixed by model-0211 (W3), among the channels of the asked signal on the request's net, the one joined to the requester's pin directly wins."""

import fransys as fr
from fransys.colours import BK


def test_the_name_lands_on_the_channel_wired_directly_to_the_contact() -> None:
    d = fr.design("demo_parts")
    rack = d.rack("U1")
    di = d.device("A1", "DEMO-PLC-DI-4P", parent=rack)
    strip = d.terminal_strip("X3", "DEMO-TB-2.5-TWIN", 3)
    relay = d.device("K5", "DEMO-RLY-2CO-24")
    d.series(strip[3].inner, di.di_1["1"], wire=(BK, 1.0))
    d.series(strip[3].inner, relay.co_1["14"], wire=(BK, 1.0))
    d.series(relay.co_1["11"], strip[1].inner, wire=(BK, 1.0))
    d.series(relay.co_1["14"], di.di_2["2"], wire=(BK, 1.0))
    relay.co_1.plc(fr.DI, "K5 closed")
    rows = fr.derive.plc_channel_rows(fr.build(d).model)
    named = {row.pin: row.signal_name for row in rows}
    assert named["-A1:2"] == "K5 closed"
    assert not named["-A1:1"]
