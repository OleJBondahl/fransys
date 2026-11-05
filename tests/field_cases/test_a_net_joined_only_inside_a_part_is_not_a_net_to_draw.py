"""Field case: a module's header pin joins an inner coil port; pin 1 is wired out, pin 2 and the coil's other end are not.
The bug: the pin-2 net, joined only inside the part (no wire, core, bridge or busbar), reported NET_NOT_DRAWN.
Fixed by el-N5b (R1765): `_net` skips a net no conductor ends at."""

from typing import NamedTuple

import fransys as fr
from _model_build_cover import unit_document


class _Io(NamedTuple):
    M1: fr.Device


@fr.unit("demo-mod", revision=1, interface_version=1, date="2026-11-05", text="first", by="XX")
def _mod(u: fr.Design) -> _Io:
    dc = u.dc_supply("24VDC", u.device("G1", "DEMO-PSU-24").output)
    m1 = u.device("M1", "DEMO-RELAY-MOD-2")
    u.series(dc.plus, u.device("F1", "DEMO-FUSE-DC-160").element, m1.j1["1"], wire=0.75)
    return _Io(m1)


def test_a_join_only_net_gives_no_net_not_drawn() -> None:
    d = fr.design("demo_parts")
    d.add(_mod, "U1")
    codes = [f for f in fr.check(fr.build(d, unit_document("demo-mod"))) if f.code == "NET_NOT_DRAWN"]
    assert codes == []
