"""Field case: landings on a cut-to-length bar make screws and raise no part mismatch.

The engineering shape: a relay whose coil pins A1 and A2 each take a PE wire to one copper flat
bar cut to length, whose part writes no port.

The bug: `fr.check` raised `ITEM_PART_MISMATCH` on every screw the landings made ("has port '1',
which no port template declares"), because the part check matched the screw against templates.
The rule: a portless bar function's screws are made by landings, not declared (PE-BAR amendment 1,
model-0234), so the check reads the one bar fact and skips their template match.
"""

import fransys as fr
from fransys.colours import GNYE


def test_a_cut_bar_landed_from_a_relay_gives_no_part_mismatch() -> None:
    d = fr.design("demo_parts")
    pe1 = d.device("PE1", "DEMO-PEBAR-CUT")
    k1 = d.device("K1", "DEMO-RLY-2CO-24")
    d.detail.wire(k1.coil["A1"], pe1.pe, wire=(GNYE, 2.5))
    d.detail.wire(k1.coil["A2"], pe1.pe, wire=(GNYE, 2.5))
    assert [f for f in fr.check(fr.build(d)) if f.code == "ITEM_PART_MISMATCH"] == []
