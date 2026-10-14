"""Field case: three requests of one device bind the channels they are wired to (model-0211, W1).

The engineering shape: one relay device has three changeover contacts, each asking for a digital
input name and each hand-wired to its own channel of a four-channel input module, out of channel
order (contact 1 to channel 3, contact 2 to channel 1, contact 3 to channel 2). Each channel's net
also holds the coil of another relay, which asks for a digital output (a shared return in the
field).

The bug: W1 keeps a channel only when no other request sits on its net. Every channel had one, so
no contact had a candidate and all fell to the free queue, which hands out the first free channel
in request order: channel 1 to contact 1, 2 to contact 2, 3 to contact 3. Every name sat on the
wrong channel and the wiring check raised errors.

Fixed by the W1b amendment of model-0211: W1b keeps the channels whose net holds the contact,
whatever else the net carries.
"""

import fransys as fr
from fransys.colours import BK

WIRED = {"co_1": 3, "co_2": 1, "co_3": 2}
MAKE = {"co_1": "14", "co_2": "24", "co_3": "34"}


def test_each_contact_name_lands_on_the_channel_it_is_wired_to() -> None:
    d = fr.design("demo_parts")
    rack = d.rack("U1")
    di = d.device("A1", "DEMO-PLC-DI-4P", parent=rack)
    k1 = d.device("K1", "DEMO-CO-4P-24")
    for fn, channel in WIRED.items():
        d.wire(
            getattr(k1, fn)[MAKE[fn]], getattr(di, f"di_{channel}")[str(channel)], wire=(BK, 1.0)
        )
    for n in (1, 2, 3):
        tap = d.device(f"K{n + 1}", "DEMO-CO-4P-24")
        d.wire(tap.coil["A2"], getattr(di, f"di_{n}")[str(n)], wire=(BK, 1.0))
        tap.coil.plc(fr.DO, f"K{n + 1} coil")
    for fn in WIRED:
        getattr(k1, fn).plc(fr.DI, f"K1 {fn}")
    rows = fr.derive.plc_channel_rows(fr.build(d).model)
    named = {row.pin: row.signal_name for row in rows}
    assert {f"K1 {fn}" for fn in WIRED} <= set(named.values())
    for fn, channel in WIRED.items():
        assert named[f"-A1:{channel}"] == f"K1 {fn}"
