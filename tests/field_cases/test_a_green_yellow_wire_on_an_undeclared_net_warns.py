"""Field case: a green-yellow wire joins two lamp pins that no declared net lists.

The bug: the build was silent. `GNYE_NOT_PE` read only the nets some declared net lists, so a
signal carried on a green-yellow core (a consumer harness did this) raised nothing.

Fix (model-0246): a green-yellow conductor on a net that is not PE and that no declared net lists
is a WARNING `GNYE_NOT_PE` naming the fix. A PE net, declared by `d.earth`, stays silent.
"""

import fransys as fr
from fransys.colours import GNYE


def _codes(*, earthed: bool) -> list[fr.Finding]:
    d = fr.design("demo_parts")
    a, b = (d.device(tag, "DEMO-LAMP-24") for tag in ("P1", "P2"))
    d.wire(a[1], b[1], wire=(GNYE, 0.75))
    if earthed:
        d.earth(a[1], b[1])
    return [f for f in fr.build(d).findings if f.code == "GNYE_NOT_PE"]


def test_green_yellow_on_an_undeclared_net_warns_with_its_fix() -> None:
    (finding,) = _codes(earthed=False)
    assert finding.severity.name == "WARNING"
    assert "recolour" in finding.message
    assert "d.earth" in finding.message


def test_green_yellow_on_a_declared_pe_net_stays_silent() -> None:
    assert _codes(earthed=True) == []
