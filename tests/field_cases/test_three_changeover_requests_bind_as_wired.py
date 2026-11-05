"""Field case: three requests of one device bind the channels they are wired to (model-0211, W1).
The bug: W1 kept a channel only when no other request sat on its net, so every contact fell to the free queue in request order.
Fixed by model-0211 W1b: W1b keeps the channels whose net holds the contact, whatever else the net carries."""

import fransys as fr
from fransys.colours import BK

WIRED = {"co_1": 3, "co_2": 1, "co_3": 2}
MAKE = {"co_1": "14", "co_2": "24", "co_3": "34"}


def test_each_contact_name_lands_on_the_channel_it_is_wired_to() -> None:
    d = fr.design("demo_parts")
    rack = d.rack("U1")
    di = d.device("A1", "DEMO-PLC-DI-4P", parent=rack)
    do = d.device("A2", "DEMO-PLC-DO-16", parent=rack)
    k1 = d.device("K1", "DEMO-RLY-4CO-24")
    for fn, channel in WIRED.items():
        d.series(getattr(k1, fn)[MAKE[fn]], getattr(di, f"di_{channel}")[str(channel)], wire=(BK, 1.0))
    for n in (1, 2, 3):
        tap = d.device(f"K{n + 1}", "DEMO-RLY-4CO-24")
        d.series(tap.coil["A2"], getattr(di, f"di_{n}")[str(n)], wire=(BK, 1.0))
        d.series(tap.coil["A1"], getattr(do, f"do_{n}")[str(n)], wire=(BK, 1.0))
        tap.coil.plc(fr.DO, f"K{n + 1} coil")
    for fn in WIRED:
        getattr(k1, fn).plc(fr.DI, f"K1 {fn}")
    rows = fr.derive.plc_channel_rows(fr.build(d).model)
    named = {row.pin: row.signal_name for row in rows}
    assert {f"K1 {fn}" for fn in WIRED} <= set(named.values())
    for fn, channel in WIRED.items():
        assert named[f"-A1:{channel}"] == f"K1 {fn}"
