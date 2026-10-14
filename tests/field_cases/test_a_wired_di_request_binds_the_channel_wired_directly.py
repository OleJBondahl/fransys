"""Field case: a PLC request takes the channel wired directly to its pin (model-0211, W3).

The engineering shape: a relay contact is wired straight to input channel 2 of a four-channel
digital input module, and also to a terminal strip terminal. Input channel 1 of the same module
is wired to that same terminal (a loop channel). The contact asks for a digital input name.

The bug: the contact's net also reached channel 1, so two channels qualified and the first in
serving order won. The name landed on the loop channel, channel 2 stayed unnamed, and no finding
said so.

The rule (decision model-0211): among the channels of the asked signal on the request's net,
the one joined to the requester's pin by a direct conductor wins.
"""

import fransys as fr
from fransys.colours import BK


def test_the_name_lands_on_the_channel_wired_directly_to_the_contact() -> None:
    d = fr.design("demo_parts")
    rack = d.rack("U1")
    di = d.device("A1", "DEMO-PLC-DI-4P", parent=rack)
    strip = d.terminal_strip("X3", "DEMO-TB-2.5", 3)
    relay = d.device("K5", "DEMO-RLY-2CO-24")
    d.wire(strip[3], di.di_1["1"], wire=(BK, 1.0))
    d.wire(strip[3], relay.co_1["14"], wire=(BK, 1.0))
    d.wire(relay.co_1["11"], strip[1], wire=(BK, 1.0))
    d.wire(relay.co_1["14"], di.di_2["2"], wire=(BK, 1.0))
    relay.co_1.plc(fr.DI, "K5 closed")
    rows = fr.derive.plc_channel_rows(fr.build(d).model)
    named = {row.channel_designation: row.signal_name for row in rows}
    assert named["-A1:2"] == "K5 closed"
    assert not named["-A1:1"]
